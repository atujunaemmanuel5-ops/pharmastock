"""
Forecasting for PharmaStock AI.

What this file does
-------------------
1. Loads and validates a daily sales file (product groups OR individual drugs).
2. Scores five forecasting methods with ROLLING-ORIGIN evaluation: at many past
   dates, forecast the NEXT 7 DAYS using only data known on that date, compare
   with what really happened, and average the errors. This measures the task the
   app actually performs (a 7-day forecast), unlike one 180-day recursive forecast.
3. Picks the best method per series by MAE and saves the evaluation table.
4. Produces the live 7-day forecast using each series' winning method.

Methods
-------
- Naive                       : repeat the last observed day.
- Moving Average (7-day)      : repeat the mean of the last 7 days.
- Seasonal Naive (7-day)      : same weekday last week.
- Weekday Average (4 weeks)   : mean of the same weekday over the last 4 weeks.
- Random Forest (lags)        : one RandomForestRegressor per series, using lag,
                                rolling-mean and calendar features, applied
                                recursively for 7 steps.

Leakage rules (be ready to explain these)
-----------------------------------------
- Every feature for day i is computed from values BEFORE day i only.
- The Random Forest is trained only on data before the first test origin.
- At each test origin the history passed to a method ends the day before the
  forecast starts. No method ever sees the days it is predicting.

Run from the project root:
    python -m src.forecasting
To forecast the simulated drug-level sales instead, call run_pipeline() with the
columns of sales_daily_simulated.csv (see the bottom of this file).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

try:
    from .config import (
        PROCESSED_PATH,
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
        FORECAST_DIR,
        EVALUATION_PATH,
    )
except ImportError:
    from config import (
        PROCESSED_PATH,
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
        FORECAST_DIR,
        EVALUATION_PATH,
    )

# ---------------------------------------------------------------------
# Settings (write the reasons in notes/evaluation_plan.md)
# ---------------------------------------------------------------------
HORIZON = 7            # the app forecasts 7 days ahead
TEST_DAYS = 182        # 26 weeks of rolling test origins, one origin per 7 days
MIN_HISTORY = 28       # minimum days before lag features and weekday averages work
MIN_TRAIN_DAYS = 120   # minimum days before a Random Forest is worth fitting

FORECAST_PATH = FORECAST_DIR / "weekly_sales_forecast.csv"
BEST_METHODS_PATH = FORECAST_DIR / "best_methods.csv"

NAIVE = "Naive"
MOVING_AVERAGE = "Moving Average (7-day)"
SEASONAL_NAIVE = "Seasonal Naive (7-day)"
WEEKDAY_AVERAGE = "Weekday Average (4 weeks)"
RANDOM_FOREST = "Random Forest (lags)"

# Minimum number of past days each method needs.
MIN_DAYS_REQUIRED = {
    NAIVE: 1,
    MOVING_AVERAGE: 7,
    SEASONAL_NAIVE: 7,
    WEEKDAY_AVERAGE: 28,
    RANDOM_FOREST: MIN_TRAIN_DAYS,
}

RF_PARAMS = dict(
    n_estimators=200,
    min_samples_leaf=5,
    random_state=42,   # fixed seed so results are repeatable
    n_jobs=-1,
)


# ---------------------------------------------------------------------
# 1. Loading and validation
# ---------------------------------------------------------------------
def load_daily_series(
    path=PROCESSED_PATH,
    date_col=OUTPUT_DATE_COLUMN,
    group_col=OUTPUT_GROUP_COLUMN,
    value_col=OUTPUT_VALUE_COLUMN,
):
    """Load a long-format daily file and validate it."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path, parse_dates=[date_col])

    required = [date_col, group_col, value_col]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df.empty:
        raise ValueError("The dataset is empty.")

    if df[required].isnull().any().any():
        raise ValueError("Missing values found in required columns.")

    df[value_col] = pd.to_numeric(df[value_col], errors="raise")

    if (df[value_col] < 0).any():
        raise ValueError("Negative sales quantities found.")

    df = df.sort_values([group_col, date_col]).reset_index(drop=True)

    # Each series must have exactly one observation per calendar day.
    for group, group_df in df.groupby(group_col):
        dates = group_df[date_col]

        if dates.duplicated().any():
            raise ValueError(f"Duplicate dates found for {group}.")

        expected = pd.date_range(dates.min(), dates.max(), freq="D")
        if len(dates) != len(expected) or not dates.isin(expected).all():
            raise ValueError(f"Missing calendar dates found for {group}.")

    print(f"Loaded dataset: {path}")
    print(f"Rows: {len(df):,}   Series: {df[group_col].nunique()}")
    print(f"Date range: {df[date_col].min().date()} to {df[date_col].max().date()}")
    return df


def load_processed_data():
    """Load the real Kaggle product-group data (kept for older code that imports it)."""
    return load_daily_series()


# ---------------------------------------------------------------------
# 2. Forecasting methods
#    Every method has the same shape:
#        method(history, future_dates) -> list of len(future_dates) floats
#    `history` holds ACTUAL values up to the day before the first future date.
# ---------------------------------------------------------------------
def forecast_naive(history, future_dates):
    """Repeat the last observed day."""
    return [float(history[-1])] * len(future_dates)


def forecast_moving_average(history, future_dates, window=7):
    """Repeat the mean of the last `window` days."""
    return [float(np.mean(history[-window:]))] * len(future_dates)


def _same_weekday_values(history, step, weeks):
    """
    Values from the same weekday as the target day, 1..`weeks` weeks back.

    `step` is 0 for the first forecast day, 1 for the second, and so on (up to 6).
    The first forecast day sits at position end, so the same weekday one week
    earlier is at end - 7. For step s it is end - 7 + s. All of these positions
    are inside the known history, so nothing is leaked.
    """
    end = len(history)
    return [history[end - 7 * k + step] for k in range(1, weeks + 1)]


def forecast_seasonal_naive(history, future_dates):
    """Same weekday last week."""
    return [float(_same_weekday_values(history, s, 1)[0]) for s in range(len(future_dates))]


def forecast_weekday_average(history, future_dates, weeks=4):
    """Mean of the same weekday over the last `weeks` weeks."""
    return [float(np.mean(_same_weekday_values(history, s, weeks))) for s in range(len(future_dates))]


# ---- Random Forest ---------------------------------------------------
FEATURE_NAMES = [
    "lag_1", "lag_2", "lag_7", "lag_14", "lag_28",
    "mean_7", "mean_28", "day_of_week", "month",
]


def make_feature_row(history, end, date):
    """
    Features for the day at position `end`, built ONLY from history[:end].

    The same function builds training rows and prediction rows, so the two can
    never disagree about how a feature is calculated.
    """
    return [
        history[end - 1],                       # yesterday
        history[end - 2],
        history[end - 7],                       # same weekday last week
        history[end - 14],
        history[end - 28],
        float(np.mean(history[end - 7:end])),   # mean of the previous 7 days
        float(np.mean(history[end - 28:end])),  # mean of the previous 28 days
        date.day_of_week,                         # 0 = Monday ... 6 = Sunday
        date.month,
    ]


def train_random_forest(values, dates):
    """Fit one Random Forest on the series passed in (pass ONLY training data)."""
    n = len(values)
    if n < MIN_TRAIN_DAYS:
        raise ValueError(f"Need at least {MIN_TRAIN_DAYS} days to train a Random Forest (got {n}).")

    rows, targets = [], []
    for i in range(MIN_HISTORY, n):
        rows.append(make_feature_row(values, i, dates[i]))
        targets.append(values[i])

    model = RandomForestRegressor(**RF_PARAMS)
    model.fit(np.array(rows, dtype=float), np.array(targets, dtype=float))
    return model


def forecast_random_forest(history, future_dates, model):
    """
    Recursive multi-step forecast. Each prediction becomes part of the history
    used for the next day's lag features, because the true future is unknown.
    """
    hist = [float(v) for v in history]
    predictions = []
    for date in future_dates:
        x = np.array([make_feature_row(hist, len(hist), date)], dtype=float)
        prediction = max(0.0, float(model.predict(x)[0]))   # sales cannot be negative
        predictions.append(prediction)
        hist.append(prediction)
    return predictions


BASELINES = {
    NAIVE: forecast_naive,
    MOVING_AVERAGE: forecast_moving_average,
    SEASONAL_NAIVE: forecast_seasonal_naive,
    WEEKDAY_AVERAGE: forecast_weekday_average,
}


# ---------------------------------------------------------------------
# 3. Rolling-origin evaluation
# ---------------------------------------------------------------------
def evaluate_forecast(actual, predicted):
    """MAE and RMSE in the same units as sales."""
    return {
        "MAE": mean_absolute_error(actual, predicted),
        "RMSE": mean_squared_error(actual, predicted) ** 0.5,
    }


def rolling_origin_evaluation(values, dates, horizon=HORIZON, test_days=TEST_DAYS):
    """
    Score every method on identical rolling windows for ONE series.

    Origins start at len(values) - test_days and step forward by `horizon`.
    At each origin the history ends the day before, the method forecasts the next
    `horizon` days, and the forecast is compared with the actual values.
    Returns (metrics_by_method, number_of_origins).
    """
    n = len(values)
    first_origin = n - test_days
    if first_origin < MIN_TRAIN_DAYS:
        raise ValueError(
            f"Series too short: {n} days, need at least {MIN_TRAIN_DAYS + test_days}."
        )

    methods = dict(BASELINES)

    # Train the Random Forest on data BEFORE the first test origin only.
    model = train_random_forest(values[:first_origin], dates[:first_origin])
    methods[RANDOM_FOREST] = lambda history, future_dates: forecast_random_forest(
        history, future_dates, model
    )

    actuals = []
    predictions = {name: [] for name in methods}
    origins = 0

    for origin in range(first_origin, n - horizon + 1, horizon):
        history = values[:origin]                      # ends the day before the forecast
        future_dates = dates[origin:origin + horizon]
        actual = values[origin:origin + horizon]
        actuals.extend(actual)

        for name, method in methods.items():
            predictions[name].extend(method(history, future_dates))
        origins += 1

    metrics = {
        name: evaluate_forecast(actuals, predicted)
        for name, predicted in predictions.items()
    }
    return metrics, origins


# ---------------------------------------------------------------------
# 4. Live forecast
# ---------------------------------------------------------------------
def forecast_next_days(
    group_df,
    method=WEEKDAY_AVERAGE,
    forecast_days=HORIZON,
    date_col=OUTPUT_DATE_COLUMN,
    group_col=OUTPUT_GROUP_COLUMN,
    value_col=OUTPUT_VALUE_COLUMN,
):
    """
    Forecast the next `forecast_days` days for ONE series with the chosen method.

    If the history is too short for the chosen method, fall back to the 7-day
    moving average and say so in the forecast_method column. Fewer than 7 days
    of history raises a clear error.
    """
    group_df = group_df.sort_values(date_col).reset_index(drop=True)
    values = group_df[value_col].to_numpy(dtype=float)
    dates = pd.DatetimeIndex(group_df[date_col])

    if len(values) < MIN_DAYS_REQUIRED[MOVING_AVERAGE]:
        raise ValueError(
            f"Need at least {MIN_DAYS_REQUIRED[MOVING_AVERAGE]} observations to forecast."
        )

    used = method
    if method not in MIN_DAYS_REQUIRED:
        raise ValueError(f"Unknown forecasting method: {method}")
    if len(values) < MIN_DAYS_REQUIRED[method]:
        used = MOVING_AVERAGE
        label = f"{MOVING_AVERAGE} (fallback: short history)"
    else:
        label = method

    future_dates = pd.date_range(dates[-1] + pd.Timedelta(days=1), periods=forecast_days, freq="D")

    if used == RANDOM_FOREST:
        model = train_random_forest(values, dates)      # live forecast may use all history
        predictions = forecast_random_forest(values, future_dates, model)
    else:
        predictions = BASELINES[used](values, future_dates)

    return pd.DataFrame({
        date_col: future_dates,
        group_col: group_df[group_col].iloc[0],
        "predicted_quantity": predictions,
        "forecast_method": label,
    })


# ---------------------------------------------------------------------
# 5. The full pipeline
# ---------------------------------------------------------------------
def run_pipeline(
    df,
    date_col=OUTPUT_DATE_COLUMN,
    group_col=OUTPUT_GROUP_COLUMN,
    value_col=OUTPUT_VALUE_COLUMN,
    evaluation_path=EVALUATION_PATH,
    best_path=BEST_METHODS_PATH,
    forecast_path=FORECAST_PATH,
    test_days=TEST_DAYS,
):
    """Evaluate every method, pick winners, save tables, produce live forecasts."""
    rows, skipped = [], []

    for group, group_df in df.groupby(group_col):
        group_df = group_df.sort_values(date_col).reset_index(drop=True)
        values = group_df[value_col].to_numpy(dtype=float)
        dates = pd.DatetimeIndex(group_df[date_col])

        try:
            metrics, origins = rolling_origin_evaluation(values, dates, test_days=test_days)
        except ValueError as exc:
            skipped.append((group, str(exc)))
            continue

        for method, m in metrics.items():
            rows.append({
                group_col: group,
                "method": method,
                "MAE": m["MAE"],
                "RMSE": m["RMSE"],
                "origins": origins,
                "forecast_days_scored": origins * HORIZON,
            })

    if not rows:
        raise ValueError("No series had enough history to evaluate.")

    results = pd.DataFrame(rows)

    # ---- report -------------------------------------------------------
    print("\nMAE PER SERIES AND METHOD (rolling 7-day windows, identical for every method)")
    print("=" * 90)
    mae_table = results.pivot(index=group_col, columns="method", values="MAE")
    print(mae_table.round(3).to_string())

    best = results.loc[results.groupby(group_col)["MAE"].idxmin()].copy()
    seasonal = results[results.method == SEASONAL_NAIVE].set_index(group_col)["MAE"]
    best["seasonal_naive_MAE"] = best[group_col].map(seasonal)
    best["improvement_vs_seasonal_naive_pct"] = (
        100 * (best["seasonal_naive_MAE"] - best["MAE"]) / best["seasonal_naive_MAE"]
    )

    print("\nWINNING METHOD PER SERIES (lowest MAE)")
    print("=" * 90)
    print(best[[group_col, "method", "MAE", "RMSE", "improvement_vs_seasonal_naive_pct"]]
          .round(3).to_string(index=False))

    # Scale-free summary: each method's MAE relative to seasonal naive, averaged.
    rel = results.copy()
    rel["relative_MAE"] = rel["MAE"] / rel[group_col].map(seasonal)
    summary = rel.groupby("method")["relative_MAE"].mean().sort_values()
    wins = best["method"].value_counts()
    print("\nSUMMARY ACROSS SERIES (relative MAE: below 1.0 beats seasonal naive)")
    print("=" * 90)
    for method, value in summary.items():
        print(f"{method:<28} mean relative MAE {value:6.3f}   wins {int(wins.get(method, 0))}")

    if skipped:
        print(f"\nSkipped {len(skipped)} series with too little history, e.g. {skipped[0]}")

    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(evaluation_path, index=False)
    best.to_csv(best_path, index=False)
    print(f"\nEvaluation saved to: {evaluation_path}")
    print(f"Winning methods saved to: {best_path}")

    # ---- live forecasts using each series' winner ---------------------
    winners = dict(zip(best[group_col], best["method"]))
    forecasts = []
    for group, group_df in df.groupby(group_col):
        forecasts.append(forecast_next_days(
            group_df,
            method=winners.get(group, WEEKDAY_AVERAGE),
            date_col=date_col,
            group_col=group_col,
            value_col=value_col,
        ))
    forecasts_df = pd.concat(forecasts, ignore_index=True)
    forecasts_df.to_csv(forecast_path, index=False)

    print(f"\nFuture forecasts saved to: {forecast_path}")
    print("\nNEXT SEVEN DAYS (first 14 rows shown)")
    print("=" * 90)
    preview = forecasts_df.head(14).copy()
    preview["predicted_quantity"] = preview["predicted_quantity"].round(3)
    print(preview.to_string(index=False))

    return results, best, forecasts_df


def main():
    df = load_daily_series()
    run_pipeline(df)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------
# Drug-level forecasting on the simulated sales (use from a separate script
# or the Python prompt, not here):
#
#     from src.config import SALES_DAILY_PATH, FORECAST_DIR
#     from src.forecasting import load_daily_series, run_pipeline
#
#     df = load_daily_series(SALES_DAILY_PATH, "sale_date", "drug_id", "quantity")
#     run_pipeline(
#         df, "sale_date", "drug_id", "quantity",
#         evaluation_path=FORECAST_DIR / "drug_forecast_evaluation.csv",
#         best_path=FORECAST_DIR / "drug_best_methods.csv",
#         forecast_path=FORECAST_DIR / "drug_forecast.csv",
#     )
#
# Label these results SIMULATED: the sales behind them are simulated.
# ---------------------------------------------------------------------
