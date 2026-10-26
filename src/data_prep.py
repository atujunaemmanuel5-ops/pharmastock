"""
PharmaStock AI — Daily Sales Data Preparation
==============================================

Purpose
-------
Prepare the raw daily sales dataset for forecasting and stock-related
analysis.

The pipeline performs these steps:

1. Load the raw CSV file.
2. Check that the file is readable and contains the required columns.
3. Parse dates and validate numerical sales values.
4. Detect missing dates without automatically inventing zero-sales records.
5. Remove configured partial days.
6. Convert the dataset from wide format to long format.
7. Run final validation checks.
8. Save the processed dataset.
9. Reload the saved file to verify that it can be read correctly.

Expected output columns
-----------------------
sale_date, product_group, quantity

Important limitation
--------------------
The dataset contains historical sales for eight product groups. It does
not contain actual inventory balances, stockout records, supplier lead
times, or individual medicine-level inventory records.

Therefore, this file prepares sales data; it does not establish actual
stock levels or prove that a stockout occurred.
"""

import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# 1. IMPORT PROJECT CONFIGURATION
# ---------------------------------------------------------------------

# Support both ways of running this file:
#
# A. Direct execution from the project root:
#       python src/data_prep.py
#
# B. Module execution from the project root:
#       python -m src.data_prep
#
# When executed as a module, Python recognises src as the package and
# the relative import is appropriate.
#
# When executed directly, __package__ is empty, so we import config
# from the same directory as this script.
if __package__:
    from .config import (
        DATE_COLUMN,
        DATE_FORMAT,
        DROP_FIRST_PARTIAL_DAY,
        DROP_LAST_PARTIAL_DAY,
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
        PROCESSED_DIR,
        PROCESSED_PATH,
        RAW_DATA_PATH,
        SALES_COLUMNS,
    )
else:
    from config import (
        DATE_COLUMN,
        DATE_FORMAT,
        DROP_FIRST_PARTIAL_DAY,
        DROP_LAST_PARTIAL_DAY,
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
        PROCESSED_DIR,
        PROCESSED_PATH,
        RAW_DATA_PATH,
        SALES_COLUMNS,
    )


# ---------------------------------------------------------------------
# 2. LOAD THE RAW DATA
# ---------------------------------------------------------------------

def load_raw_data(file_path: Path) -> pd.DataFrame:
    """
    Read the raw CSV file into a pandas DataFrame.

    Parameters
    ----------
    file_path:
        Path to the CSV file containing the original sales data.

    Returns
    -------
    pd.DataFrame
        The unmodified raw dataset.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.

    ValueError
        If the CSV file is empty or contains no usable rows.

    Notes
    -----
    We do not clean or modify the data here. Keeping loading separate
    from validation makes the pipeline easier to understand and test.
    """

    # Fail early if the expected file cannot be found.
    if not file_path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {file_path}"
        )

    # A zero-byte file or a CSV with no readable header can cause
    # pandas to raise EmptyDataError.
    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError as error:
        raise ValueError(
            f"The CSV file is empty or has no readable header: {file_path}"
        ) from error

    # A DataFrame can be empty even if a file exists.
    if df.empty:
        raise ValueError(
            f"The CSV file contains no data rows: {file_path}"
        )

    print(f"Raw file: {file_path}")
    print(
        f"Raw shape: {df.shape[0]} rows x {df.shape[1]} columns"
    )

    return df


# ---------------------------------------------------------------------
# 3. VALIDATE AND PREPARE THE RAW DATA
# ---------------------------------------------------------------------

def validate_and_prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the required columns, dates, and sales values.

    The function raises an informative error if the input data violates
    the assumptions required for this pipeline.

    It does not silently replace invalid dates, missing sales values,
    or negative sales quantities.
    """

    # Work on a copy so that validation does not unexpectedly modify
    # the DataFrame supplied by the caller.
    df = df.copy()

    # Remove accidental spaces around column names.
    # For example, " M01AB " becomes "M01AB".
    df.columns = df.columns.str.strip()

    # If stripping spaces creates duplicate column names, stop rather
    # than accidentally using the wrong column.
    if df.columns.duplicated().any():
        duplicates = df.columns[df.columns.duplicated()].tolist()

        raise ValueError(
            f"Duplicate column names found after removing spaces: {duplicates}"
        )

    # The date column and all eight sales columns must be present.
    required_columns = [DATE_COLUMN, *SALES_COLUMNS]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # CSV line numbers start at 1 for the header.
    # The first data row is therefore line 2.
    #
    # pandas uses a zero-based DataFrame index by default, so adding 2
    # gives the corresponding line number in a normal CSV with one header.
    csv_line_numbers = pd.Series(
        range(2, len(df) + 2),
        index=df.index,
    )

    # -------------------------------------------------------------
    # 3A. VALIDATE THE DATE COLUMN
    # -------------------------------------------------------------

    # Keep the original values for error messages.
    original_dates = df[DATE_COLUMN].copy()

    # Convert strings such as "01/02/2014" to pandas datetime values.
    # errors="coerce" turns invalid dates into NaT, allowing us to report
    # exactly which values could not be parsed.
    parsed_dates = pd.to_datetime(
        original_dates,
        format=DATE_FORMAT,
        errors="coerce",
    )

    invalid_date_mask = parsed_dates.isna()

    if invalid_date_mask.any():
        invalid_rows = []

        for index in df.index[invalid_date_mask]:
            invalid_rows.append(
                {
                    "CSV line": int(csv_line_numbers.loc[index]),
                    "Value": repr(original_dates.loc[index]),
                }
            )

        raise ValueError(
            "Invalid or missing dates found. "
            f"Expected format: {DATE_FORMAT}. "
            f"Problem rows: {invalid_rows[:20]}"
        )

    # Store the parsed dates in the DataFrame.
    df[DATE_COLUMN] = parsed_dates

    # -------------------------------------------------------------
    # 3B. VALIDATE THE SALES COLUMNS
    # -------------------------------------------------------------

    # Each sales column must contain numeric values.
    # We preserve decimal values because sales quantities in this
    # dataset are not always whole numbers.
    for column in SALES_COLUMNS:

        # Keep the original values so we can identify bad entries.
        original_values = df[column].copy()

        # Convert valid numbers to numeric types.
        # Text that cannot be converted becomes NaN.
        numeric_values = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        # Identify text or other non-empty values that could not be
        # converted to numbers.
        #
        # A genuinely blank cell is handled separately as a missing value.
        non_empty_mask = (
            original_values.notna()
            & original_values.astype("string").str.strip().ne("")
        )

        invalid_number_mask = (
            numeric_values.isna()
            & non_empty_mask
        )

        if invalid_number_mask.any():
            invalid_rows = []

            for index in df.index[invalid_number_mask]:
                invalid_rows.append(
                    {
                        "CSV line": int(csv_line_numbers.loc[index]),
                        "Date": str(df.loc[index, DATE_COLUMN].date()),
                        "Column": column,
                        "Value": repr(original_values.loc[index]),
                    }
                )

            raise ValueError(
                "Non-numeric sales values found. "
                f"Problem rows: {invalid_rows[:20]}"
            )

        # Missing values are not automatically treated as zero.
        # A missing value may mean unknown or unrecorded sales.
        missing_value_mask = numeric_values.isna()

        if missing_value_mask.any():
            missing_rows = []

            for index in df.index[missing_value_mask]:
                missing_rows.append(
                    {
                        "CSV line": int(csv_line_numbers.loc[index]),
                        "Date": str(df.loc[index, DATE_COLUMN].date()),
                        "Column": column,
                    }
                )

            raise ValueError(
                "Missing sales values found. "
                f"Problem rows: {missing_rows[:20]}"
            )

        # Replace the original column with its validated numeric values.
        df[column] = numeric_values

        # Negative sales values are unexpected for this dataset.
        # We report the date and value so the source can be investigated.
        negative_mask = df[column] < 0

        if negative_mask.any():
            negative_rows = []

            for index in df.index[negative_mask]:
                negative_rows.append(
                    {
                        "CSV line": int(csv_line_numbers.loc[index]),
                        "Date": str(df.loc[index, DATE_COLUMN].date()),
                        "Column": column,
                        "Value": float(df.loc[index, column]),
                    }
                )

            raise ValueError(
                "Negative sales quantities found. "
                f"Problem rows: {negative_rows[:20]}"
            )

    # -------------------------------------------------------------
    # 3C. CHECK FOR DUPLICATE DATES
    # -------------------------------------------------------------

    # This pipeline expects one daily record per date.
    # If two rows have the same date, we should investigate them before
    # aggregating or removing anything.
    duplicate_dates = df.loc[
        df[DATE_COLUMN].duplicated(keep=False),
        DATE_COLUMN,
    ]

    if not duplicate_dates.empty:
        duplicate_values = (
            duplicate_dates.dt.strftime("%Y-%m-%d")
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate dates found in the daily dataset: "
            f"{duplicate_values[:20]}"
        )

    # Sort by date so later operations are chronological.
    df = df.sort_values(DATE_COLUMN).reset_index(drop=True)

    print("Validation passed.")

    return df


# ---------------------------------------------------------------------
# 4. STANDARDISE THE DATASET COLUMNS
# ---------------------------------------------------------------------

def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only the date and eight sales columns needed by this pipeline.

    The raw file also contains calendar-related columns such as Year,
    Month, Hour, and Weekday Name.

    We do not need those columns for this initial preparation step.
    Date-derived features can be generated later during feature
    engineering, when we can control exactly how they are calculated.
    """

    required_columns = [DATE_COLUMN, *SALES_COLUMNS]

    # Select the columns in a predictable order.
    # This also removes unrelated metadata columns.
    df = df[required_columns].copy()

    return df


# ---------------------------------------------------------------------
# 5. CHECK THAT THE DAILY CALENDAR IS COMPLETE
# ---------------------------------------------------------------------

def complete_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Check whether every calendar date between the first and last dates
    exists in the dataset.

    Important:
    This function does NOT fill missing dates with zero sales.

    A date absent from the file is not necessarily a zero-sales day.
    It could indicate a missing record or a data collection problem.
    The pipeline therefore stops if a date is absent, allowing the
    cause to be investigated before modelling.
    """

    if df.empty:
        raise ValueError(
            "Cannot check the calendar because the dataset is empty."
        )

    # Construct the expected sequence of daily dates.
    expected_dates = pd.date_range(
        start=df[DATE_COLUMN].min(),
        end=df[DATE_COLUMN].max(),
        freq="D",
    )

    # Compare the expected calendar against the dates actually present.
    actual_dates = pd.DatetimeIndex(df[DATE_COLUMN])

    missing_dates = expected_dates.difference(actual_dates)

    # Do not silently assume missing dates mean zero sales.
    if len(missing_dates) > 0:
        missing_date_strings = [
            date.strftime("%Y-%m-%d")
            for date in missing_dates[:20]
        ]

        additional_count = max(len(missing_dates) - 20, 0)

        message = (
            f"Found {len(missing_dates)} missing calendar dates. "
            f"Examples: {missing_date_strings}"
        )

        if additional_count:
            message += f" (and {additional_count} more)"

        message += (
            ". Investigate these dates before deciding how to handle them."
        )

        raise ValueError(message)

    print("Calendar check passed: no missing dates found.")

    return df


# ---------------------------------------------------------------------
# 6. REMOVE CONFIGURED PARTIAL DAYS
# ---------------------------------------------------------------------

def drop_partial_days(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove the first and/or last date according to config.py.

    This function removes a boundary date only when the corresponding
    configuration setting is True.

    The current configuration drops the last date because the hourly
    dataset ends at 19:00 on that date. The first date is retained, but
    that decision should be revisited if the source confirms that it is
    incomplete.
    """

    if df.empty:
        raise ValueError(
            "Cannot remove partial days because the dataset is empty."
        )

    # Work with a copy to avoid modifying the caller's DataFrame.
    df = df.copy()

    # Capture the boundary dates before dropping anything.
    first_date = df[DATE_COLUMN].min()
    last_date = df[DATE_COLUMN].max()

    dates_to_drop = []

    if DROP_FIRST_PARTIAL_DAY:
        dates_to_drop.append(first_date)

    # Avoid listing the same date twice if the dataset contains only one day.
    if DROP_LAST_PARTIAL_DAY and last_date not in dates_to_drop:
        dates_to_drop.append(last_date)

    # Only filter the DataFrame if there are dates to remove.
    if dates_to_drop:
        df = df.loc[
            ~df[DATE_COLUMN].isin(dates_to_drop)
        ].copy()

        dropped_dates = [
            date.strftime("%Y-%m-%d")
            for date in dates_to_drop
        ]

        print(f"Partial days dropped: {dropped_dates}")
    else:
        print("Partial days dropped: none")

    # Removing boundary dates must not leave the dataset empty.
    if df.empty:
        raise ValueError(
            "Removing the configured partial days left no data."
        )

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------
# 7. CONVERT WIDE DATA TO LONG FORMAT
# ---------------------------------------------------------------------

def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the dataset from wide format to long format.

    Wide format:
        datum       M01AB   M01AE   ...
        2014-01-02  5.0     3.0     ...

    Long format:
        sale_date   product_group   quantity
        2014-01-02  M01AB            5.0
        2014-01-02  M01AE            3.0

    Long format is useful for working with multiple product groups using
    the same forecasting and evaluation code.
    """

    # melt() moves the eight product-group columns into a single column.
    # Each original date therefore appears once for every product group.
    long_df = df.melt(
        id_vars=[DATE_COLUMN],
        value_vars=SALES_COLUMNS,
        var_name=OUTPUT_GROUP_COLUMN,
        value_name=OUTPUT_VALUE_COLUMN,
    )

    # Rename the original date column to the clearer output name.
    long_df = long_df.rename(
        columns={
            DATE_COLUMN: OUTPUT_DATE_COLUMN,
        }
    )

    # Sort the output so dates and groups are organised consistently.
    long_df = long_df.sort_values(
        [OUTPUT_DATE_COLUMN, OUTPUT_GROUP_COLUMN]
    ).reset_index(drop=True)

    return long_df


# ---------------------------------------------------------------------
# 8. RUN FINAL CHECKS ON THE PROCESSED DATA
# ---------------------------------------------------------------------

def final_checks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Verify that the final long-format dataset is suitable for saving.

    These checks catch problems that may have been introduced during
    reshaping or other processing steps.
    """

    expected_columns = [
        OUTPUT_DATE_COLUMN,
        OUTPUT_GROUP_COLUMN,
        OUTPUT_VALUE_COLUMN,
    ]

    # The output must contain exactly the expected columns.
    if list(df.columns) != expected_columns:
        raise ValueError(
            f"Unexpected output columns. Expected {expected_columns}, "
            f"received {list(df.columns)}."
        )

    # An empty processed dataset is not useful for forecasting.
    if df.empty:
        raise ValueError(
            "The processed dataset is empty."
        )

    # Dates must be parsed datetime values, not unparsed strings.
    if not pd.api.types.is_datetime64_any_dtype(
        df[OUTPUT_DATE_COLUMN]
    ):
        raise TypeError(
            f"{OUTPUT_DATE_COLUMN} must have a datetime dtype."
        )

    # All output fields must contain values.
    if df[expected_columns].isna().any().any():
        raise ValueError(
            "Missing values found in the final processed dataset."
        )

    # The output should contain exactly the eight configured groups.
    actual_groups = set(df[OUTPUT_GROUP_COLUMN].unique())
    expected_groups = set(SALES_COLUMNS)

    if actual_groups != expected_groups:
        raise ValueError(
            "Unexpected product groups. "
            f"Expected {sorted(expected_groups)}, "
            f"received {sorted(actual_groups)}."
        )

    # Every date should have one record for each product group.
    # A duplicated date/group combination would make that impossible.
    duplicate_pairs = df.duplicated(
        subset=[OUTPUT_DATE_COLUMN, OUTPUT_GROUP_COLUMN]
    )

    if duplicate_pairs.any():
        examples = df.loc[
            duplicate_pairs,
            [OUTPUT_DATE_COLUMN, OUTPUT_GROUP_COLUMN],
        ].head(10)

        raise ValueError(
            "Duplicate date/product-group combinations found:\n"
            f"{examples.to_string(index=False)}"
        )

    # Sales quantities should remain non-negative.
    if (df[OUTPUT_VALUE_COLUMN] < 0).any():
        raise ValueError(
            "Negative quantities found in the processed dataset."
        )

    # Check that each date has all eight product groups.
    groups_per_date = df.groupby(
        OUTPUT_DATE_COLUMN
    )[OUTPUT_GROUP_COLUMN].nunique()

    if not (groups_per_date == len(SALES_COLUMNS)).all():
        problem_dates = groups_per_date[
            groups_per_date != len(SALES_COLUMNS)
        ]

        raise ValueError(
            "Some dates do not have all eight product groups. "
            f"Problem dates: {problem_dates.head(10).to_dict()}"
        )

    print("Final checks passed.")

    return df


# ---------------------------------------------------------------------
# 9. SAVE THE PROCESSED DATA
# ---------------------------------------------------------------------

def save_processed(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Save the validated processed dataset to a CSV file.

    The output directory is created automatically if it does not exist.
    index=False prevents pandas from writing an extra index column.
    """

    # Create the destination directory if necessary.
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Write the processed data without the DataFrame index.
    df.to_csv(
        output_path,
        index=False,
    )

    print(f"Clean data saved to: {output_path}")


# ---------------------------------------------------------------------
# 10. RELOAD THE SAVED FILE TO VERIFY IT
# ---------------------------------------------------------------------

def verify_saved_file(
    output_path: Path,
    expected_shape: tuple[int, int],
) -> pd.DataFrame:
    """
    Reload the saved CSV and check that it can be read correctly.

    CSV files do not preserve pandas data types automatically.
    parse_dates tells pandas to restore the sale_date column as datetime.
    """

    reloaded_df = pd.read_csv(
        output_path,
        parse_dates=[OUTPUT_DATE_COLUMN],
    )

    # The reloaded data should have the same number of rows and columns
    # as the DataFrame that was saved.
    if reloaded_df.shape != expected_shape:
        raise ValueError(
            "Reload verification failed: shape changed. "
            f"Expected {expected_shape}, received {reloaded_df.shape}."
        )

    # Confirm that dates were parsed as datetimes.
    if not pd.api.types.is_datetime64_any_dtype(
        reloaded_df[OUTPUT_DATE_COLUMN]
    ):
        raise TypeError(
            "Reload verification failed: sale_date is not datetime."
        )

    # Confirm that the quantity column is numeric.
    if not pd.api.types.is_numeric_dtype(
        reloaded_df[OUTPUT_VALUE_COLUMN]
    ):
        raise TypeError(
            "Reload verification failed: quantity is not numeric."
        )

    print("\nReload verification:")
    print(f"Reloaded shape: {reloaded_df.shape}")
    print(
        f"Reloaded date dtype: "
        f"{reloaded_df[OUTPUT_DATE_COLUMN].dtype}"
    )
    print("Reload check passed.")

    return reloaded_df


# ---------------------------------------------------------------------
# 11. RUN THE COMPLETE PREPARATION PIPELINE
# ---------------------------------------------------------------------

def prepare_daily_sales() -> pd.DataFrame:
    """
    Execute all data-preparation steps in the correct order.

    The function returns the final processed DataFrame after validating
    and saving it.
    """

    # Step 1: Read the original CSV file.
    df = load_raw_data(RAW_DATA_PATH)

    # Step 2: Validate dates, numeric values, and duplicate dates.
    df = validate_and_prepare_data(df)

    # Step 3: Keep only the date and sales columns needed for modelling.
    df = standardise_columns(df)

    # Step 4: Stop if any calendar dates are missing.
    # We do not invent zero-sales records.
    df = complete_calendar(df)

    # Step 5: Remove configured partial boundary days.
    df = drop_partial_days(df)

    # Step 6: Convert the dataset from wide format to long format.
    df = to_long(df)

    # Step 7: Validate the structure and values of the final dataset.
    df = final_checks(df)

    # Step 8: Display a summary to help us inspect the output.
    print("\nProcessed data summary:")
    print(
        f"Date range: "
        f"{df[OUTPUT_DATE_COLUMN].min().date()} to "
        f"{df[OUTPUT_DATE_COLUMN].max().date()}"
    )

    number_of_days = df[OUTPUT_DATE_COLUMN].nunique()
    number_of_groups = df[OUTPUT_GROUP_COLUMN].nunique()

    print(f"Number of days: {number_of_days}")
    print(f"Number of product groups: {number_of_groups}")
    print(f"Final shape: {df.shape}")

    print("\nQuantity summary per product group:")

    # describe() gives the count, mean, standard deviation, minimum,
    # quartiles, and maximum for each group.
    print(
        df.groupby(OUTPUT_GROUP_COLUMN)[OUTPUT_VALUE_COLUMN]
        .describe()
        .round(2)
    )

    # Step 9: Save the validated dataset.
    save_processed(
        df,
        PROCESSED_PATH,
    )

    # Step 10: Reload the file and confirm that saving worked.
    verify_saved_file(
        PROCESSED_PATH,
        expected_shape=df.shape,
    )

    return df


# ---------------------------------------------------------------------
# 12. ENTRY POINT
# ---------------------------------------------------------------------

def main() -> None:
    """
    Entry point for running this file as a script.

    The exception handler prints a readable error message and exits with
    a failure status if validation or file processing fails.
    """

    try:
        prepare_daily_sales()

    except (ValueError, TypeError, FileNotFoundError, OSError) as error:
        print(
            f"\nDATA PREPARATION FAILED: {error}",
            file=sys.stderr,
        )

        # A non-zero exit code tells the terminal or another program
        # that the pipeline did not complete successfully.
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()