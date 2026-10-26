
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

if __package__:
    from .config import (
        PROCESSED_PATH,
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
        FORECAST_DIR,
        EVALUATION_PATH,
    )
else:
    from config import (
        PROCESSED_PATH,
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
        FORECAST_DIR,
        EVALUATION_PATH,
    )

def load_processed_data():
    """Load and validate the processed daily sales dataset."""
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(
            f"Processed dataset not found: {PROCESSED_PATH}"
        )

    df = pd.read_csv(
        PROCESSED_PATH,
        parse_dates=[OUTPUT_DATE_COLUMN],
    )

    required_columns = [
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
    ]

    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError("The processed dataset is empty.")

    if df[required_columns].isnull().any().any():
        raise ValueError("Missing values found in required columns.")

    df[OUTPUT_VALUE_COLUMN] = pd.to_numeric(
        df[OUTPUT_VALUE_COLUMN],
        errors="raise",
    )

    if (df[OUTPUT_VALUE_COLUMN] < 0).any():
        raise ValueError("Negative sales quantities found.")

    # Each product group must have one observation per calendar day.
    df = df.sort_values(
        [OUTPUT_GROUP_COLUMN, OUTPUT_DATE_COLUMN]
    ).reset_index(drop=True)

    for group, group_df in df.groupby(OUTPUT_GROUP_COLUMN):
        dates = group_df[OUTPUT_DATE_COLUMN]

        if dates.duplicated().any():
            raise ValueError(
                f"Duplicate dates found for product group {group}."
            )

        expected_dates = pd.date_range(
            start=dates.min(),
            end=dates.max(),
            freq="D",
        )

        if len(dates) != len(expected_dates) or not dates.isin(
            expected_dates
        ).all():
            raise ValueError(
                f"Missing calendar dates found for product group {group}."
            )

    print(f"Loaded processed dataset: {PROCESSED_PATH}")
    print(f"Rows: {len(df):,}")
    print(f"Product groups: {df[OUTPUT_GROUP_COLUMN].nunique()}")
    print(
        f"Date range: {df[OUTPUT_DATE_COLUMN].min().date()} "
        f"to {df[OUTPUT_DATE_COLUMN].max().date()}"
    )

    return df


def split_data(group_df, test_days=180):
    """Split one product group's data chronologically."""
    group_df = group_df.sort_values(
        OUTPUT_DATE_COLUMN
    ).reset_index(drop=True)

    if len(group_df) <= test_days:
        raise ValueError(
            f"Not enough observations for a {test_days}-day test."
        )

    train_df = group_df.iloc[:-test_days].copy()
    test_df = group_df.iloc[-test_days:].copy()

    if train_df[OUTPUT_DATE_COLUMN].max() >= test_df[
        OUTPUT_DATE_COLUMN
    ].min():
        raise ValueError("Chronological split failed.")

    return train_df, test_df


def naive_forecast(train_df, test_df):
    """Predict every test day using the last training day's sales."""
    last_value = train_df[OUTPUT_VALUE_COLUMN].iloc[-1]

    return pd.Series(
        last_value,
        index=test_df.index,
        dtype=float,
    )


def moving_average_forecast(train_df, test_df, window=7):
    """Predict each day using the previous seven actual observations."""
    history = train_df[OUTPUT_VALUE_COLUMN].astype(float).tolist()
    predictions = []

    for _ in range(len(test_df)):
        prediction = sum(history[-window:]) / window
        predictions.append(prediction)

        # Use the forecast, not the test day's actual value.
        # This creates a genuine multi-step forecast.
        history.append(prediction)

    return pd.Series(
        predictions,
        index=test_df.index,
        dtype=float,
    )


def seasonal_naive_forecast(train_df, test_df, season_length=7):
    """
    Forecast by repeating the final observed training week's pattern.
    """
    history = train_df[OUTPUT_VALUE_COLUMN].astype(float).tolist()
    predictions = []

    for _ in range(len(test_df)):
        prediction = history[-season_length]
        predictions.append(prediction)
        history.append(prediction)

    return pd.Series(
        predictions,
        index=test_df.index,
        dtype=float,
    )


def evaluate_forecast(actual, predicted):
    """Calculate forecast error using MAE and RMSE."""
    mae = mean_absolute_error(actual, predicted)

    rmse = mean_squared_error(
        actual,
        predicted,
    ) ** 0.5

    return {
        "MAE": mae,
        "RMSE": rmse,
    }

def forecast_next_days(group_df, forecast_days=7, window=7):
    """Forecast future sales using a rolling moving-average baseline."""

    group_df = group_df.sort_values(
        OUTPUT_DATE_COLUMN
    ).reset_index(drop=True)

    history = group_df[OUTPUT_VALUE_COLUMN].astype(float).tolist()

    if len(history) < window:
        raise ValueError(
            f"Need at least {window} observations to forecast."
        )

    last_date = group_df[OUTPUT_DATE_COLUMN].max()
    predictions = []

    for _ in range(forecast_days):
        prediction = sum(history[-window:]) / window

        predictions.append(prediction)

        # Use this prediction when calculating the next day's forecast.
        history.append(prediction)

    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=forecast_days,
        freq="D",
    )

    return pd.DataFrame({
        OUTPUT_DATE_COLUMN: future_dates,
        OUTPUT_GROUP_COLUMN: group_df[OUTPUT_GROUP_COLUMN].iloc[0],
        "predicted_quantity": predictions,
        "forecast_method": f"{window}-day moving average",
    })

def generate_future_forecasts(df, forecast_days=7):
    """Generate and save future sales forecasts for all groups."""

    forecasts = []

    for group, group_df in df.groupby(OUTPUT_GROUP_COLUMN):
        group_forecast = forecast_next_days(
            group_df,
            forecast_days=forecast_days,
            window=7,
        )

        forecasts.append(group_forecast)

    forecasts_df = pd.concat(
        forecasts,
        ignore_index=True,
    )

    forecast_path = FORECAST_DIR / "weekly_sales_forecast.csv"

    FORECAST_DIR.mkdir(parents=True, exist_ok=True)

    forecasts_df.to_csv(
        forecast_path,
        index=False,
    )

    print(f"\nFuture forecasts saved to: {forecast_path}")
    print("\nNEXT SEVEN DAYS OF FORECASTED SALES")
    print("=" * 60)

    print(forecasts_df.round(3).to_string(index=False))

    return forecasts_df

def main():
    df = load_processed_data()
    results = []

    for group, group_df in df.groupby(OUTPUT_GROUP_COLUMN):
        train_df, test_df = split_data(
            group_df,
            test_days=180,
        )

        actual = test_df[OUTPUT_VALUE_COLUMN]

        methods = {
            "Naive": naive_forecast(train_df, test_df),
            "Moving Average (7-day)": moving_average_forecast(
                train_df, test_df, window=7
            ),
            "Seasonal Naive (7-day)": seasonal_naive_forecast(
                train_df, test_df, season_length=7
            ),
        }

        for method_name, predictions in methods.items():
            metrics = evaluate_forecast(actual, predictions)

            results.append({
                "product_group": group,
                "method": method_name,
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
            })

    results_df = pd.DataFrame(results)

    print("\nFORECAST EVALUATION RESULTS")
    print("=" * 75)

    print(
        results_df.round(3).to_string(index=False)
    )

    print("\nBEST METHOD FOR EACH PRODUCT GROUP (BY MAE)")
    print("=" * 75)

    best_methods = results_df.loc[
        results_df.groupby("product_group")["MAE"].idxmin()
    ]

    print(
        best_methods[
            ["product_group", "method", "MAE", "RMSE"]
        ].round(3).to_string(index=False)
    )
    
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(EVALUATION_PATH, index=False)

    print(f"\nEvaluation results saved to: {EVALUATION_PATH}")
    generate_future_forecasts(df, forecast_days=7)


if __name__ == "__main__":
    main()
