"""Small, reusable velocity and trend calculations."""

from __future__ import annotations

import numbers

import pandas as pd

from src.config import RAW_DATA_PATH


def _load_sales(sales) -> pd.DataFrame:
    if sales is None:
        return pd.read_csv(RAW_DATA_PATH)
    if isinstance(sales, (str, bytes)):
        return pd.read_csv(sales)
    if isinstance(sales, pd.DataFrame):
        return sales.copy()
    raise TypeError("sales must be a pandas DataFrame, CSV path, or None")


def calculate_daily_velocity(sales=None, days: int = 7) -> pd.DataFrame:
    """Return average daily volume for the most recent ``days`` days."""
    if days < 1:
        raise ValueError("days must be positive")
    frame = _load_sales(sales)
    date_column = "sale_date" if "sale_date" in frame.columns else "datum"
    if date_column not in frame.columns:
        raise ValueError("sales must contain sale_date or datum")
    frame[date_column] = pd.to_datetime(frame[date_column], errors="raise")
    end = frame[date_column].max()
    start = end - pd.Timedelta(days=days - 1)
    frame = frame[frame[date_column].between(start, end)].copy()

    if "quantity" in frame.columns:
        group_column = "drug_id" if "drug_id" in frame.columns else "product_group" if "product_group" in frame.columns else None
        if group_column is None:
            return pd.DataFrame({"daily_velocity": [frame["quantity"].sum() / days]})
        result = frame.groupby(group_column, as_index=False)["quantity"].sum()
        result = result.rename(columns={"quantity": "total_volume"})
        result["daily_velocity"] = result["total_volume"] / days
        return result

    excluded = {date_column, "Year", "Month", "Hour", "Weekday Name"}
    value_columns = [column for column in frame.columns if column not in excluded and pd.api.types.is_numeric_dtype(frame[column])]
    if not value_columns:
        raise ValueError("wide sales data has no numeric product columns")
    return pd.DataFrame({"product_group": value_columns, "daily_velocity": [frame[column].sum() / days for column in value_columns]})


def calculate_sales_growth(current_sales, previous_sales):
    """Return percentage growth from a previous period to a current period."""
    if isinstance(current_sales, numbers.Number) and isinstance(previous_sales, numbers.Number):
        if previous_sales == 0:
            return 0.0 if current_sales == 0 else float("inf")
        return (float(current_sales) - float(previous_sales)) / abs(float(previous_sales))
    current = pd.Series(current_sales, dtype="float64")
    previous = pd.Series(previous_sales, dtype="float64")
    if len(current) != len(previous):
        raise ValueError("current_sales and previous_sales must have the same length")
    result = (current - previous) / previous.abs().replace(0, pd.NA)
    return result.fillna(0.0).replace([float("inf"), -float("inf")], float("inf"))


def classify_sales_trend(growth_rate: float, stable_band: float = 0.05) -> str:
    """Classify growth as Increasing, Stable, or Declining."""
    if stable_band < 0:
        raise ValueError("stable_band must be non-negative")
    if growth_rate > stable_band:
        return "Increasing"
    if growth_rate < -stable_band:
        return "Declining"
    return "Stable"
