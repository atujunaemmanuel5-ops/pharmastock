"""Load the seeded drug-level demonstration data.

Real sales are available only at ATC group level; drug rows are simulated
allocations and must remain labelled that way.
"""

from __future__ import annotations

import pandas as pd

try:
    from .config import DRUGS_PATH, DRUG_SHARES_PATH, SALES_DAILY_PATH, SYNTHETIC_DATA_DIR
except ImportError:
    from config import DRUGS_PATH, DRUG_SHARES_PATH, SALES_DAILY_PATH, SYNTHETIC_DATA_DIR


def load_drugs() -> pd.DataFrame:
    if not DRUGS_PATH.exists():
        raise FileNotFoundError(f"Drug catalogue not found: {DRUGS_PATH}")
    frames = [pd.read_csv(DRUGS_PATH)]
    additions_path = SYNTHETIC_DATA_DIR / "catalogue_additions.csv"
    if additions_path.exists():
        frames.append(pd.read_csv(additions_path, keep_default_na=False))
    drugs = pd.concat(frames, ignore_index=True)
    required = {"drug_id", "generic_name", "atc_level4", "pack_size", "lead_time_days"}
    missing = required.difference(drugs.columns)
    if missing:
        raise ValueError(f"Drug catalogue missing columns: {sorted(missing)}")
    if drugs["drug_id"].duplicated().any():
        raise ValueError("Drug catalogue contains duplicate drug IDs")
    return drugs


def load_drug_shares() -> pd.DataFrame:
    shares = pd.read_csv(DRUG_SHARES_PATH)
    required = {"dataset_group", "drug_id", "share_of_group"}
    missing = required.difference(shares.columns)
    if missing:
        raise ValueError(f"Drug shares missing columns: {sorted(missing)}")
    totals = shares.groupby("dataset_group")["share_of_group"].sum()
    if not ((totals - 1.0).abs() < 0.002).all():
        raise ValueError("Drug shares must sum to 1 for every dataset group")
    return shares


def load_simulated_sales() -> pd.DataFrame:
    if not SALES_DAILY_PATH.exists():
        raise FileNotFoundError(f"Simulated sales not found: {SALES_DAILY_PATH}")
    sales = pd.read_csv(SALES_DAILY_PATH, parse_dates=["sale_date"])
    required = {"sale_date", "drug_id", "quantity", "is_simulated"}
    missing = required.difference(sales.columns)
    if missing:
        raise ValueError(f"Simulated sales missing columns: {sorted(missing)}")
    if (sales["quantity"] < 0).any():
        raise ValueError("Simulated sales cannot be negative")
    return sales
