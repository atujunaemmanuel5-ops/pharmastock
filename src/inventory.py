"""This file handles our inventory"""


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
        EXPIRY_REPORT_PATH
    )



def load_inventory_batches() ->pd.DataFrame:
    """Loads and handles basic validation of the inventory batches"""

    if not INVENTORY_BATCHES_PATH.exists():
        raise FileNotFoundError("Inventory batches file not found")

    batches=pd.read_csv(INVENTORY_BATCHES_PATH,
                        parse_dates=[
                            EXPIRY_DATE_COLUMN,
                            RECEIVED_DATE_COLUMN,
                            AS_OF_DATE_COLUMN
                        ])

    required_columns = [
        BATCH_ID_COLUMN,DRUG_ID_COLUMN,QUANTITY_ON_HAND_COLUMN,
        EXPIRY_DATE_COLUMN,RECEIVED_DATE_COLUMN,AS_OF_DATE_COLUMN
    ]

    missing_columns=[column
                     for column in required_columns
                     if column not in batches.columns]

    if missing_columns:
        raise ValueError(f"Your inventory file is missing required columns: {missing_columns}")

    if batches.empty:
        raise ValueError("Inventory file is empty")
    print(f"Loaded {len(batches)} inventory batch records.")

    return batches


def load_drug_catalogue() -> pd.DataFrame:
    """Load the drug catalogue and check its required columns."""

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

    if drugs["drug_id"].duplicated().any():
        raise ValueError(
            "Drug catalogue contains duplicate drug IDs."
        )

    print(f"Loaded {len(drugs)} drugs from the catalogue.")

    return drugs

def add_drug_names(
    batches: pd.DataFrame,
    drugs: pd.DataFrame,
) -> pd.DataFrame:
    """Attach generic names to inventory batch records."""

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
            f"Inventory contains drug IDs missing from the catalogue: {missing_ids}"
        )

    inventory = inventory.drop(columns="_merge")

    return inventory


def create_expiry_report(
    inventory: pd.DataFrame,
    days: int = 30,
) -> pd.DataFrame:
    """Create a report of expired and soon-to-expire batches."""

    report = inventory.copy()

    report["days_to_expiry"] = (
        report["expiry_date"] - report["as_of_date"]
    ).dt.days

    report["expiry_status"] = "Not expiring soon"

    report.loc[
        report["days_to_expiry"] < 0,
        "expiry_status",
    ] = "Expired"

    report.loc[
        report["days_to_expiry"].between(0, days),
        "expiry_status",
    ] = "Expiring soon"

    report = report[
        report["expiry_status"] != "Not expiring soon"
    ].copy()

    return report.sort_values("days_to_expiry")




def summarize_stock(batches:pd.DataFrame) ->pd.DataFrame:
    """Calculate recorded stock for each drug"""

    stock_summary = (
        batches
        .groupby("drug_id")["qty_on_hand"]
        .sum()
        .reset_index()
    )

    stock_summary = stock_summary.rename(
    columns={"qty_on_hand": "total_stock"}
        )

    return stock_summary

def identify_expired_batches(batches:pd.DataFrame) ->pd.DataFrame:
    """Identify expired batches basing on the their recorded as of date"""

    expired = batches[
    batches["expiry_date"] < batches["as_of_date"]
].copy()

    return expired


def summarise_usable_stock(batches: pd.DataFrame) -> pd.DataFrame:
    """Calculate non-expired recorded stock for each drug."""

    usable_batches = batches[
        batches["expiry_date"] >= batches["as_of_date"]
    ].copy()

    usable_stock = (
        usable_batches
        .groupby("drug_id")["qty_on_hand"]
        .sum()
        .reset_index()
    )

    usable_stock = usable_stock.rename(
        columns={"qty_on_hand": "usable_stock"}
    )

    return usable_stock

def identify_expiring_batches(
    batches: pd.DataFrame,
    days: int = 30,
) -> pd.DataFrame:
    """Return non-expired batches expiring within the specified days."""

    reference_date = batches["as_of_date"]

    expiry_deadline = reference_date + pd.Timedelta(days=days)

    expiring = batches[
        (batches["expiry_date"] >= reference_date)
        & (batches["expiry_date"] <= expiry_deadline)
    ].copy()

    return expiring



if __name__ == "__main__":
    batches = load_inventory_batches()
    stock_summary = summarize_stock(batches)
    usable_stock = summarise_usable_stock(batches)

    print("\nUsable stock summary:")
    print(usable_stock.head().to_string(index=False))

    print("\nStock summary:")
    print(stock_summary.head().to_string(index=False))
    drugs = load_drug_catalogue()

    inventory = add_drug_names(batches, drugs)
    expiry_report = create_expiry_report(inventory)
    EXPIRY_REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

    expiry_report.to_csv(
    EXPIRY_REPORT_PATH,
    index=False,
    )

    print(f"\nExpiry report saved to: {EXPIRY_REPORT_PATH}")

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
            ]
        ].to_string(index=False)
    )

    print(f"\nBatches requiring attention: {len(expiry_report)}")
