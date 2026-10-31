"""Deterministic expiry and FEFO rules."""

from __future__ import annotations

from math import ceil

import pandas as pd


def expiry_status(days_to_expiry: int) -> str:
    if days_to_expiry < 0:
        return "Expired"
    if days_to_expiry <= 30:
        return "Critical"
    if days_to_expiry <= 90:
        return "Watch"
    return "OK"


def add_expiry_fields(batches: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with days/status fields and FEFO suggestions."""
    required = {"drug_id", "batch_id", "qty_on_hand", "expiry_date", "as_of_date"}
    missing = required.difference(batches.columns)
    if missing:
        raise ValueError(f"Missing expiry columns: {sorted(missing)}")
    result = batches.copy()
    for column in ("expiry_date", "as_of_date"):
        result[column] = pd.to_datetime(result[column], errors="raise")
    result["days_to_expiry"] = (result["expiry_date"] - result["as_of_date"]).dt.days.astype(int)
    result["expiry_status"] = result["days_to_expiry"].map(expiry_status)
    result["is_fefo_pick"] = False
    candidates = result[(result["days_to_expiry"] >= 0) & (result["qty_on_hand"] > 0)].sort_values(["drug_id", "expiry_date", "batch_id"])
    result.loc[candidates.drop_duplicates("drug_id").index, "is_fefo_pick"] = True
    return result.sort_values(["days_to_expiry", "drug_id", "batch_id"]).reset_index(drop=True)


def fefo_pick(batches: pd.DataFrame, drug_id: str) -> dict | None:
    """Pick the earliest unexpired batch with stock, or return ``None``."""
    report = add_expiry_fields(batches)
    candidates = report[(report["drug_id"] == drug_id) & (report["days_to_expiry"] >= 0) & (report["qty_on_hand"] > 0)].sort_values(["expiry_date", "batch_id"])
    return None if candidates.empty else candidates.iloc[0].to_dict()


def usable_stock(batches: pd.DataFrame, drug_id: str | None = None) -> int:
    report = add_expiry_fields(batches)
    if drug_id is not None:
        report = report[report["drug_id"] == drug_id]
    return int(report.loc[report["days_to_expiry"] >= 0, "qty_on_hand"].sum())


def units_at_risk(qty_on_hand: float, daily_demand: float, days_to_expiry: int) -> int:
    """Units not expected to sell before expiry, never below zero."""
    if days_to_expiry < 0:
        return max(0, int(ceil(qty_on_hand)))
    return max(0, int(ceil(qty_on_hand - max(0.0, daily_demand) * days_to_expiry)))


def expiry_risk_report(batches: pd.DataFrame, daily_demand: dict[str, float] | None = None) -> pd.DataFrame:
    report = add_expiry_fields(batches)
    demand = daily_demand or {}
    report["units_at_risk"] = [units_at_risk(row.qty_on_hand, demand.get(row.drug_id, 0.0), row.days_to_expiry) for row in report.itertuples()]
    return report
