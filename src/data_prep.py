"""Load, validate, clean and save the daily sales data.

Pipeline (each step is its own function so it can be tested alone):
    load_raw_data -> validate_and_prepare_data -> standardise_columns -> complete_calendar
    -> drop_partial_days -> to_long -> final_checks -> save_processed

Run from the project root:
    python -m src.data_prep
    python -m src.data_prep data/test_broken/negative.csv     (test a different file)
"""

import sys
from pathlib import Path

import pandas as pd

from config import (
    ABSENT_DAY_FILL_VALUE,
    DATE_COLUMN,
    DATE_FORMAT,
    DROP_FIRST_PARTIAL_DAY,
    DROP_LAST_PARTIAL_DAY,
    OUTPUT_DATE_COLUMN,
    OUTPUT_GROUP_COLUMN,
    OUTPUT_VALUE_COLUMN,
    PROCESSED_PATH,
    RAW_DATA_PATH,
    SALES_COLUMNS,
)


# ---------------------------------------------------------------------------
# Step 1: load
# ---------------------------------------------------------------------------
def load_raw_data(file_path) -> pd.DataFrame:
    """Loading the raw sales CSV file."""

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(f"Could not find the file: {file_path}")

    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"The CSV file is empty: {file_path}") from exc

    if df.empty:
        raise ValueError(f"The CSV file contains no data rows: {file_path}")

    return df


# ---------------------------------------------------------------------------
# Step 2: validate
# ---------------------------------------------------------------------------
def validate_and_prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and prepare the daily sales DataFrame."""

    df = df.copy()

    # Preserve CSV line numbers.
    # This assumes the DataFrame came directly from read_csv() and still has its original RangeIndex.
    source_lines = pd.Series(range(2, len(df) + 2), index=df.index)

    # 1. Checking required columns.
    required_columns = [DATE_COLUMN, *SALES_COLUMNS]
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Dataset is missing these columns: {missing_columns}")

    # 2. Parse dates and report invalid values.
    original_dates = df[DATE_COLUMN].copy()
    parsed_dates = pd.to_datetime(original_dates, format=DATE_FORMAT, errors="coerce")
    bad_dates = parsed_dates.isna()

    if bad_dates.any():
        problems = []
        for index in df.index[bad_dates]:
            value = original_dates.loc[index]
            if pd.isna(value):
                value = "<missing>"
            problems.append(f"File line {source_lines.loc[index]}: invalid date {value!r}")
        raise ValueError("Invalid or missing dates:\n" + "\n".join(problems[:10]))

    df[DATE_COLUMN] = parsed_dates

    # 3. Convert sales columns to numeric values.
    for column in SALES_COLUMNS:
        original_values = df[column].copy()
        numeric_values = pd.to_numeric(original_values, errors="coerce")
        bad_values = numeric_values.isna()

        if bad_values.any():
            problems = []
            for index in df.index[bad_values]:
                value = original_values.loc[index]
                if pd.isna(value):
                    value = "<missing>"
                problems.append(
                    f"File line {source_lines.loc[index]}: column {column}, invalid value {value!r}"
                )
            raise ValueError("Invalid or missing sales values:\n" + "\n".join(problems[:10]))

        df[column] = numeric_values

    # 4. Report negative sales values.
    negative_mask = df[SALES_COLUMNS] < 0
    if negative_mask.any().any():
        negative_positions = negative_mask.stack()
        negative_positions = negative_positions[negative_positions].index

        problems = []
        for index, column in negative_positions[:10]:
            problems.append(
                f"File line {source_lines.loc[index]}: date {df.loc[index, DATE_COLUMN]}, "
                f"column {column}, value {df.loc[index, column]}"
            )
        raise ValueError("Negative sales values were found:\n" + "\n".join(problems))

    # 5. Check for duplicate dates.
    duplicate_mask = df[DATE_COLUMN].duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_rows = df.loc[duplicate_mask, DATE_COLUMN]
        raise ValueError(f"Duplicate dates were found: {duplicate_rows.astype(str).tolist()[:10]}")

    # 6. Sort dates chronologically.
    df = df.sort_values(by=DATE_COLUMN)
    df = df.reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Step 3: keep only what we need and rename the date column
# ---------------------------------------------------------------------------
def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the date and the eight sales columns; rename the date column.

    Year, Month, Hour and Weekday Name are dropped: the first three can be rebuilt from the date,
    and Hour is an artifact (the daily file was built by adding up the hourly file).
    """

    df = df[[DATE_COLUMN, *SALES_COLUMNS]].copy()
    df = df.rename(columns={DATE_COLUMN: OUTPUT_DATE_COLUMN})
    return df


# ---------------------------------------------------------------------------
# Step 4: one row for every calendar day
# ---------------------------------------------------------------------------
def complete_calendar(df: pd.DataFrame):
    """Make sure every day between the first and last date has a row.

    Returns (completed DataFrame, list of dates that were absent and have been added).
    An absent day is filled with ABSENT_DAY_FILL_VALUE (zero), which is only justified by the
    evidence that zeros are recorded values in this dataset. Existing missing values are NOT touched
    (validation already guarantees there are none).
    """

    df = df.set_index(OUTPUT_DATE_COLUMN).sort_index()

    full_calendar = pd.date_range(df.index.min(), df.index.max(), freq="D")
    absent_days = full_calendar.difference(df.index)

    # fill_value is applied ONLY to the rows that reindex has to create
    df = df.reindex(full_calendar, fill_value=ABSENT_DAY_FILL_VALUE)
    df.index.name = OUTPUT_DATE_COLUMN

    return df.reset_index(), list(absent_days)


# ---------------------------------------------------------------------------
# Step 5: drop days whose totals are known to be incomplete
# ---------------------------------------------------------------------------
def drop_partial_days(df: pd.DataFrame):
    """Remove the first and/or last day if the config says their totals are incomplete.

    Returns (DataFrame, list of dropped dates).
    """

    dropped = []
    df = df.sort_values(OUTPUT_DATE_COLUMN).reset_index(drop=True)

    if DROP_LAST_PARTIAL_DAY:
        dropped.append(df[OUTPUT_DATE_COLUMN].iloc[-1])
        df = df.iloc[:-1]

    if DROP_FIRST_PARTIAL_DAY:
        dropped.append(df[OUTPUT_DATE_COLUMN].iloc[0])
        df = df.iloc[1:]

    return df.reset_index(drop=True), dropped


# ---------------------------------------------------------------------------
# Step 6: wide -> long (one row per date per product group)
# ---------------------------------------------------------------------------
def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Turn eight sales columns into rows: sale_date, product_group, quantity."""

    long_df = df.melt(
        id_vars=OUTPUT_DATE_COLUMN,
        value_vars=SALES_COLUMNS,
        var_name=OUTPUT_GROUP_COLUMN,
        value_name=OUTPUT_VALUE_COLUMN,
    )
    long_df = long_df.sort_values([OUTPUT_DATE_COLUMN, OUTPUT_GROUP_COLUMN]).reset_index(drop=True)
    return long_df


# ---------------------------------------------------------------------------
# Step 7: facts that must be true before we save
# ---------------------------------------------------------------------------
def final_checks(long_df: pd.DataFrame) -> dict:
    """Stop with a clear message if the clean data breaks any rule. Returns a small summary."""

    problems = []

    if long_df[OUTPUT_VALUE_COLUMN].isna().any():
        problems.append("There are missing quantities.")

    if (long_df[OUTPUT_VALUE_COLUMN] < 0).any():
        problems.append("There are negative quantities.")

    if long_df.duplicated([OUTPUT_DATE_COLUMN, OUTPUT_GROUP_COLUMN]).any():
        problems.append("There are duplicate (date, product group) rows.")

    groups_found = sorted(long_df[OUTPUT_GROUP_COLUMN].unique())
    if groups_found != sorted(SALES_COLUMNS):
        problems.append(f"Product groups are not the expected eight: {groups_found}")

    first = long_df[OUTPUT_DATE_COLUMN].min()
    last = long_df[OUTPUT_DATE_COLUMN].max()
    expected_days = (last - first).days + 1
    counts = long_df.groupby(OUTPUT_GROUP_COLUMN)[OUTPUT_DATE_COLUMN].count()
    wrong = counts[counts != expected_days]
    if not wrong.empty:
        problems.append(
            f"Every group should have {expected_days} daily rows, but these do not:\n{wrong.to_string()}"
        )

    if len(long_df) != expected_days * len(SALES_COLUMNS):
        problems.append(
            f"Expected {expected_days * len(SALES_COLUMNS)} rows, found {len(long_df)}."
        )

    if problems:
        raise ValueError("Final checks failed:\n- " + "\n- ".join(problems))

    return {"first_date": first, "last_date": last, "days": expected_days, "rows": len(long_df)}


# ---------------------------------------------------------------------------
# Step 8: save
# ---------------------------------------------------------------------------
def save_processed(df: pd.DataFrame, path) -> None:
    """Save the clean data to a CSV file."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Clean data saved to: {path}")


# ---------------------------------------------------------------------------
# The whole pipeline in one call (the API will use this later)
# ---------------------------------------------------------------------------
def prepare_daily_sales(raw_path=RAW_DATA_PATH):
    """Run every step and return (clean long DataFrame, report dictionary)."""

    raw_df = load_raw_data(raw_path)
    validated = validate_and_prepare_data(raw_df)
    standard = standardise_columns(validated)
    completed, added_days = complete_calendar(standard)
    trimmed, dropped_days = drop_partial_days(completed)
    long_df = to_long(trimmed)
    summary = final_checks(long_df)

    report = {
        "raw_rows": len(raw_df),
        "raw_columns": raw_df.shape[1],
        "absent_days_added": added_days,
        "partial_days_dropped": dropped_days,
        **summary,
    }
    return long_df, report


def main(raw_path=RAW_DATA_PATH) -> None:
    """Prepare the data, print a report, save it, and prove the saved file reloads."""

    clean_df, report = prepare_daily_sales(raw_path)

    print("Raw file:", raw_path)
    print(f"Raw shape: {report['raw_rows']} rows x {report['raw_columns']} columns")
    print("Validation passed.")
    print(f"Absent days added: {len(report['absent_days_added'])}")
    if report["absent_days_added"]:
        print("  e.g.", [str(d.date()) for d in report["absent_days_added"][:5]])
    print(f"Partial days dropped: {[str(d.date()) for d in report['partial_days_dropped']]}")
    print(f"Date range: {report['first_date'].date()} to {report['last_date'].date()} ({report['days']} days)")
    print(f"Final shape: {report['rows']} rows = {report['days']} days x {len(SALES_COLUMNS)} groups")

    print("\nQuantity summary per product group:")
    print(clean_df.groupby(OUTPUT_GROUP_COLUMN)[OUTPUT_VALUE_COLUMN].describe().round(2))

    save_processed(clean_df, PROCESSED_PATH)

    # Reload test: the saved file must come back with the same shape and real dates.
    check = pd.read_csv(PROCESSED_PATH, parse_dates=[OUTPUT_DATE_COLUMN])
    print("\nReload verification:")
    print("Reloaded shape:", check.shape)
    print("Reloaded date dtype:", check[OUTPUT_DATE_COLUMN].dtype)
    if check.shape != clean_df.shape:
        raise ValueError("The reloaded file does not match the data that was saved.")
    if check[OUTPUT_VALUE_COLUMN].isna().any():
        raise ValueError("The reloaded file contains missing quantities.")
    print("Reload check passed.")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else RAW_DATA_PATH)
