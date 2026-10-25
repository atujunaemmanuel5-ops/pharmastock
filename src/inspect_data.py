
"""
inspect_data.py  (Day 2 - throwaway script)

PURPOSE: LOOK at every raw file and print facts. It never changes, fixes or saves any data.
The printed facts go into notes/data_findings.md. Decisions come later, in data_prep.py.

Run from the project root (the pharmastock folder):
    python src/inspect_data.py
To keep the output for your notes:
    python src/inspect_data.py > notes/inspection_output.txt
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ---- settings  -------------------------------------------------
DATA_DIR = Path("data/raw")          # where the Kaggle CSV files live
DATE_COL = "datum"                   # date column name seen in your output
ATC_COLS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]
SHOW_PLOTS = True                   # set True to also see histograms
# -------------------------------------------------------------------------------

# showing every column when printing tables
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)


def section(title: str) -> None:
    """Print a clear heading so the output is easy to scan."""
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def load_csv(path: Path) -> pd.DataFrame:
    """Read a CSV exactly as it is on disk. Nothing is cleaned here."""
    return pd.read_csv(path)


def guess_frequency(dates: pd.Series):
    """Look at the most common gap between sorted dates and return (label, pandas freq string)."""
    gaps = dates.sort_values().diff().dropna()
    if gaps.empty:
        return "unknown", None
    typical = gaps.mode().iloc[0]
    if typical == pd.Timedelta(hours=1):
        return "hourly", "h"
    if typical == pd.Timedelta(days=1):
        return "daily", "D"
    if typical == pd.Timedelta(days=7):
        return "weekly", "7D"
    if pd.Timedelta(days=28) <= typical <= pd.Timedelta(days=31):
        return "monthly", "ME"
    return f"unusual (most common gap = {typical})", None


def inspect_file(path: Path) -> pd.DataFrame:
    """Print an inspection report for one CSV file and return the loaded data."""
    df = load_csv(path)
    section(f"FILE: {path.name}   ({path.stat().st_size / 1024:.1f} KB)")

    # 1. size and names ----------------------------------------------------------
    print(f"Rows: {df.shape[0]}   Columns: {df.shape[1]}")
    print(f"Column names: {df.columns.tolist()}")
    spaced = [c for c in df.columns if c != c.strip()]
    if spaced:
        print(f"WARNING: these column names have extra spaces: {spaced}")

    # 2. types and first/last rows -----------------------------------------------
    print("\n--- Data types ---")
    print(df.dtypes)
    print("\n--- First 3 rows ---")
    print(df.head(3))
    print("\n--- Last 5 rows (look for a partial final period) ---")
    print(df.tail(5))

    # 3. missing values and duplicates -------------------------------------------
    print("\n--- Missing values per column (count, percent) ---")
    missing = pd.DataFrame({"missing": df.isna().sum(), "percent": (df.isna().mean() * 100).round(2)})
    print(missing)
    print(f"\nFully duplicated rows: {df.duplicated().sum()}")

    # 4. the date column ---------------------------------------------------------
    if DATE_COL not in df.columns:
        print(f"\nWARNING: date column '{DATE_COL}' not found in {path.name}. Skipping date checks.")
        return df

    print(f"\n--- Date column '{DATE_COL}' ---")
    print(f"Raw examples: {df[DATE_COL].head(3).tolist()}")
    # the parsed dates live in a separate variable; the DataFrame is not modified
    dates = pd.to_datetime(df[DATE_COL], errors="coerce")
    unparsed = int(dates.isna().sum())
    print(f"Dates that could not be parsed: {unparsed}")
    if unparsed:
        print("Examples of unparseable values:", df.loc[dates.isna(), DATE_COL].head(5).tolist())
    dates = dates.dropna()

    if dates.empty:
        print("No valid dates found.")
        return df

    print(f"First date: {dates.min()}")
    print(f"Last date:  {dates.max()}")
    print(f"Unique dates: {dates.nunique()}   Duplicated dates: {int(dates.duplicated().sum())}")
    print(f"Dates already in order (oldest first): {dates.is_monotonic_increasing}")

    label, freq = guess_frequency(dates)
    print(f"Looks like a {label} file")
    print("\nGap sizes between consecutive dates (how many times each occurs):")
    print(dates.sort_values().diff().value_counts().head(8))

    if freq is not None:
        expected = pd.date_range(dates.min(), dates.max(), freq=freq)
        absent = expected.difference(pd.DatetimeIndex(dates.unique()))
        print(f"\nDates expected between first and last: {len(expected)}   Dates present: {dates.nunique()}")
        print(f"Dates ABSENT from the file: {len(absent)}")
        if len(absent):
            print("First absent dates:", [str(d) for d in absent[:15]])
            if freq == "D":
                print("Absent days by weekday:")
                print(pd.Series(absent.day_name()).value_counts())

    # 5. numeric columns ---------------------------------------------------------
    atc = [c for c in ATC_COLS if c in df.columns]
    if atc:
        print("\n--- Sales columns: summary (one row per product group) ---")
        print(df[atc].describe().T.round(2))
        print("\nNumber of zeros per sales column:")
        print((df[atc] == 0).sum())
        print("\nNumber of negative values per sales column:")
        print((df[atc] < 0).sum())
        print("\nNumber of fractional (non-whole) values per sales column:")
        print((df[atc] % 1 != 0).sum())

        # does the last row look much smaller than normal? (hint of a partial final period)
        ratio = (df[atc].iloc[-1] / df[atc].median()).round(2)
        print("\nLast row divided by the column median (values far below 1 hint at a partial period):")
        print(ratio)

    # 6. small label-like columns ------------------------------------------------
    for col in ["Year", "Month", "Hour", "Weekday Name"]:
        if col in df.columns:
            print(f"\n--- Counts in column '{col}' ---")
            print(df[col].value_counts().sort_index().head(15))

    return df


def visual_inspection(df: pd.DataFrame, name: str) -> None:
    """Quick histograms to see the shape of each sales column. Looking only."""
    atc = [c for c in ATC_COLS if c in df.columns]
    if not atc:
        return
    df[atc].hist(figsize=(12, 8), bins=20)
    plt.suptitle(f"Distribution of each product group - {name}")
    plt.tight_layout()
    plt.show()


def cross_file_check(frames: dict) -> None:
    """Compare daily sums with the monthly file for a few months. Do the files agree?"""
    if "salesdaily.csv" not in frames or "salesmonthly.csv" not in frames:
        return
    section("CROSS-FILE CHECK: daily file summed by month vs monthly file")
    daily = frames["salesdaily.csv"].copy()          # a copy, so the original is untouched
    monthly = frames["salesmonthly.csv"].copy()
    daily["month"] = pd.to_datetime(daily[DATE_COL], errors="coerce").dt.to_period("M")
    monthly["month"] = pd.to_datetime(monthly[DATE_COL], errors="coerce").dt.to_period("M")
    atc = [c for c in ATC_COLS if c in daily.columns and c in monthly.columns]
    from_daily = daily.groupby("month")[atc].sum()
    from_monthly = monthly.set_index("month")[atc]
    common = from_daily.index.intersection(from_monthly.index)
    if len(common) == 0:
        print("No overlapping months found.")
        return
    ratio = (from_daily.loc[common] / from_monthly.loc[common]).round(3)
    print("Ratio = (daily summed) / (monthly file). Values near 1.000 mean the files agree.")
    print("First 4 months:")
    print(ratio.head(4))
    print("Last 4 months:")
    print(ratio.tail(4))
    print("\nMedian ratio per product group:")
    print(ratio.median())


def main() -> None:
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {DATA_DIR.resolve()}. Check the folder name.")
        return
    print(f"Found {len(files)} CSV file(s): {[f.name for f in files]}")

    frames = {}
    for path in files:
        frames[path.name] = inspect_file(path)
        if SHOW_PLOTS:
            visual_inspection(frames[path.name], path.name)

    cross_file_check(frames)

    section("DONE - now write what you saw into notes/data_findings.md (numbers, not impressions)")


if __name__ == "__main__":
    main()