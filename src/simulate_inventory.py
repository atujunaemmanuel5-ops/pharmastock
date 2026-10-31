"""Load and validate the fixed-seed simulated inventory pack."""

from __future__ import annotations

import pandas as pd

try:
    from .config import INVENTORY_BATCHES_PATH
except ImportError:
    from config import INVENTORY_BATCHES_PATH


def load_simulated_batches() -> pd.DataFrame:
    if not INVENTORY_BATCHES_PATH.exists():
        raise FileNotFoundError(f"Inventory batches not found: {INVENTORY_BATCHES_PATH}")
    batches = pd.read_csv(INVENTORY_BATCHES_PATH)
    required = {"batch_id", "drug_id", "batch_no", "qty_on_hand", "expiry_date", "received_date", "lead_time_days", "pack_size", "as_of_date", "is_simulated"}
    missing = required.difference(batches.columns)
    if missing:
        raise ValueError(f"Inventory batches missing columns: {sorted(missing)}")
    for column in ("expiry_date", "received_date", "as_of_date"):
        batches[column] = pd.to_datetime(batches[column], errors="raise")
    batches["qty_on_hand"] = pd.to_numeric(batches["qty_on_hand"], errors="raise")
    if (batches["qty_on_hand"] < 0).any() or (batches["qty_on_hand"] % 1 != 0).any():
        raise ValueError("Inventory quantities must be non-negative whole numbers")
    if batches["batch_id"].duplicated().any():
        raise ValueError("Inventory batches contain duplicate batch IDs")
    batches["qty_on_hand"] = batches["qty_on_hand"].astype(int)
    return batches
