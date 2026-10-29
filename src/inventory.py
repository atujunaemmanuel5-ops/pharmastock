"""Inventory loading, validation, expiry monitoring, and stock summaries."""

import logging

import pandas as pd

try:
    from .config import (
        DRUGS_PATH,
        INVENTORY_BATCHES_PATH,
        BATCH_ID_COLUMN,
        DRUG_ID_COLUMN,
        QUANTITY_ON_HAND_COLUMN,
        EXPIRY_DATE_COLUMN,
        RECEIVED_DATE_COLUMN,
        AS_OF_DATE_COLUMN,
        EXPIRY_REPORT_PATH,
    )
except ImportError:
    from config import (
        DRUGS_PATH,
        INVENTORY_BATCHES_PATH,
        BATCH_ID_COLUMN,
        DRUG_ID_COLUMN,
        QUANTITY_ON_HAND_COLUMN,
        EXPIRY_DATE_COLUMN,
        RECEIVED_DATE_COLUMN,
        AS_OF_DATE_COLUMN,
        EXPIRY_REPORT_PATH,
    )


logger = logging.getLogger(__name__)


def load_inventory_batches() -> pd.DataFrame:
    """Load inventory batches and validate required data."""

    if not INVENTORY_BATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Inventory batches file not found: {INVENTORY_BATCHES_PATH}"
        )

    # Read first so we can check column names before parsing dates.
    batches = pd.read_csv(INVENTORY_BATCHES_PATH)

    required_columns = [
        BATCH_ID_COLUMN,
        "batch_no",
        DRUG_ID_COLUMN,
        QUANTITY_ON_HAND_COLUMN,
        EXPIRY_DATE_COLUMN,
        RECEIVED_DATE_COLUMN,
        AS_OF_DATE_COLUMN,
        "lead_time_days",
        "pack_size",
        "is_simulated",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in batches.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Inventory file is missing required columns: {missing_columns}"
        )

    if batches.empty:
        raise ValueError("Inventory file is empty.")

    # Convert date columns explicitly. Invalid dates raise an error.
    date_columns = [
        EXPIRY_DATE_COLUMN,
        RECEIVED_DATE_COLUMN,
        AS_OF_DATE_COLUMN,
    ]

    for column in date_columns:
        batches[column] = pd.to_datetime(
            batches[column],
            errors="raise",
        )

    if batches[date_columns].isna().any().any():
        raise ValueError("Inventory contains missing dates.")

    if batches[DRUG_ID_COLUMN].isna().any():
        raise ValueError("Inventory contains missing drug IDs.")

    if batches[BATCH_ID_COLUMN].isna().any():
        raise ValueError("Inventory contains missing batch IDs.")

    if batches["batch_no"].isna().any():
        raise ValueError("Inventory contains missing batch numbers.")

    if batches[BATCH_ID_COLUMN].duplicated().any():
        raise ValueError("Inventory contains duplicate batch IDs.")

    batches[QUANTITY_ON_HAND_COLUMN] = pd.to_numeric(
        batches[QUANTITY_ON_HAND_COLUMN],
        errors="raise",
    )

    if batches[QUANTITY_ON_HAND_COLUMN].isna().any():
        raise ValueError("Inventory contains missing quantities.")

    if (batches[QUANTITY_ON_HAND_COLUMN] < 0).any():
        raise ValueError("Inventory contains negative quantities.")

    # Keep quantities as whole numbers for this stock-counting system.
    if (
        batches[QUANTITY_ON_HAND_COLUMN] % 1 != 0
    ).any():
        raise ValueError("Inventory quantities must be whole numbers.")

    batches[QUANTITY_ON_HAND_COLUMN] = (
        batches[QUANTITY_ON_HAND_COLUMN].astype(int)
    )

    if batches["is_simulated"].isna().any():
        raise ValueError("Inventory contains missing simulation flags.")

    batches["is_simulated"] = (
        batches["is_simulated"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )

    if batches["is_simulated"].isna().any():
        raise ValueError(
            "is_simulated must contain true or false values."
        )

    logger.info("Loaded %s inventory batches.", len(batches))

    return batches


def load_drug_catalogue() -> pd.DataFrame:
    """Load the drug catalogue and validate its required columns."""

    if not DRUGS_PATH.exists():
        raise FileNotFoundError(
            f"Drug catalogue not found: {DRUGS_PATH}"
        )

    drugs = pd.read_csv(DRUGS_PATH)

    required_columns = ["drug_id", "generic_name"]

    missing_columns = [
        column
        for column in required_columns
        if column not in drugs.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Drug catalogue is missing columns: {missing_columns}"
        )

    if drugs.empty:
        raise ValueError("Drug catalogue is empty.")

    if drugs["drug_id"].isna().any():
        raise ValueError("Drug catalogue contains missing drug IDs.")

    if drugs["drug_id"].duplicated().any():
        raise ValueError(
            "Drug catalogue contains duplicate drug IDs."
        )

    return drugs


def add_drug_names(
    batches: pd.DataFrame,
    drugs: pd.DataFrame,
) -> pd.DataFrame:
    """Attach generic names to inventory batches."""

    inventory = batches.merge(
        drugs[["drug_id", "generic_name"]],
        on="drug_id",
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched = inventory[inventory["_merge"] == "left_only"]

    if not unmatched.empty:
        missing_ids = unmatched["drug_id"].unique().tolist()

        raise ValueError(
            f"Inventory contains drug IDs missing from the catalogue: "
            f"{missing_ids}"
        )

    return inventory.drop(columns="_merge")


def identify_expired_batches(
    batches: pd.DataFrame,
) -> pd.DataFrame:
    """Identify batches expired on their recorded as-of date."""

    return batches[
        batches["expiry_date"] < batches["as_of_date"]
    ].copy()


def identify_expiring_batches(
    batches: pd.DataFrame,
    days: int = 30,
) -> pd.DataFrame:
    """Identify non-expired batches expiring within the specified days."""

    if days < 0:
        raise ValueError("days cannot be negative.")

    days_to_expiry = (
        batches["expiry_date"] - batches["as_of_date"]
    ).dt.days

    return batches[
        (days_to_expiry >= 0)
        & (days_to_expiry <= days)
    ].copy()


def create_expiry_report(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Classify every batch and identify the FEFO batch for each drug.

    Status thresholds:
    - Expired: before the as-of date
    - Critical: 0–30 days remaining
    - Watch: 31–90 days remaining
    - OK: more than 90 days remaining

    The report uses each batch's recorded as-of date.
    """

    report = inventory.copy()

    report["days_to_expiry"] = (
        report["expiry_date"] - report["as_of_date"]
    ).dt.days

    report["expiry_status"] = "OK"

    report.loc[
        report["days_to_expiry"].between(31, 90),
        "expiry_status",
    ] = "Watch"

    report.loc[
        report["days_to_expiry"].between(0, 30),
        "expiry_status",
    ] = "Critical"

    report.loc[
        report["days_to_expiry"] < 0,
        "expiry_status",
    ] = "Expired"

    # FEFO candidates must be unexpired and have stock available.
    eligible = report[
        (report["expiry_date"] >= report["as_of_date"])
        & (report["qty_on_hand"] > 0)
    ].copy()

    report["is_fefo_pick"] = False

    # The earliest-expiring eligible batch gets the FEFO flag.
    # Batch ID provides a stable tie-breaker when expiry dates match.
    fefo_indices = (
        eligible.sort_values(
            ["drug_id", "expiry_date", "batch_id"]
        )
        .drop_duplicates(subset=["drug_id"])
        .index
    )

    report.loc[fefo_indices, "is_fefo_pick"] = True

    # Include every status so the dashboard can show the full picture.
    return report.sort_values(
        ["days_to_expiry", "drug_id"],
        ascending=[True, True],
    ).reset_index(drop=True)


def summarize_stock(
    batches: pd.DataFrame,
) -> pd.DataFrame:
    """Summarise physical and usable stock for every drug."""

    physical = (
        batches.groupby("drug_id")["qty_on_hand"]
        .sum()
        .rename("total_stock")
    )

    usable_batches = batches[
        batches["expiry_date"] >= batches["as_of_date"]
    ]

    usable = (
        usable_batches.groupby("drug_id")["qty_on_hand"]
        .sum()
        .rename("usable_stock")
    )

    summary = pd.concat(
        [physical, usable],
        axis=1,
    ).fillna(0)

    summary["total_stock"] = summary["total_stock"].astype(int)
    summary["usable_stock"] = summary["usable_stock"].astype(int)

    return summary.reset_index()


def summarise_usable_stock(
    batches: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate non-expired recorded stock for each drug."""

    usable_batches = batches[
        batches["expiry_date"] >= batches["as_of_date"]
    ]

    usable_stock = (
        usable_batches.groupby("drug_id")["qty_on_hand"]
        .sum()
        .reset_index()
        .rename(columns={"qty_on_hand": "usable_stock"})
    )

    return usable_stock


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    batches = load_inventory_batches()
    drugs = load_drug_catalogue()

    inventory = add_drug_names(batches, drugs)

    stock_summary = summarize_stock(batches)
    expiry_report = create_expiry_report(inventory)

    print("\nStock summary:")
    print(stock_summary.head().to_string(index=False))

    print("\nExpiry report:")
    print(
        expiry_report[
            [
                "generic_name",
                "batch_no",
                "qty_on_hand",
                "expiry_date",
                "days_to_expiry",
                "expiry_status",
                "is_fefo_pick",
            ]
        ].to_string(index=False)
    )

    EXPIRY_REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    expiry_report.to_csv(
        EXPIRY_REPORT_PATH,
        index=False,
    )

    print(f"\nExpiry report saved to: {EXPIRY_REPORT_PATH}")