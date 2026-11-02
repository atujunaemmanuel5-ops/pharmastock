"""Deterministic fallback data for a clean checkout or an offline demo.

The real Kaggle and synthetic files remain preferred when present. This small
fallback means the API can still boot when those local, licence-sensitive
inputs are not included in a deployment artifact.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd


GROUPS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]


def processed_sales() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range(date.today() - timedelta(days=365), periods=365, freq="D")
    bases = {group: 3 + index * 2 for index, group in enumerate(GROUPS)}
    rows = []
    for group in GROUPS:
        for offset, sale_date in enumerate(dates):
            seasonal = 1.0 + 0.15 * np.sin(offset / 14.0)
            quantity = max(0.0, float(rng.poisson(bases[group] * seasonal)))
            rows.append({"sale_date": sale_date, "product_group": group, "quantity": quantity})
    return pd.DataFrame(rows)


def drugs() -> pd.DataFrame:
    rows = [
        ("D005", "Ibuprofen", "200 mg", "tablet", "M01AE"),
        ("D006", "Naproxen", "250 mg", "tablet", "M01AE"),
        ("D008", "Diclofenac", "50 mg", "tablet", "M01AB"),
        ("D010", "Diazepam", "5 mg", "tablet", "N05B"),
        ("D029", "Misoprostol", "200 microgram", "tablet", "G02AD"),
        ("D047", "Warfarin", "5 mg", "tablet", "B01AA"),
        ("D056", "Amoxicillin", "500 mg", "capsule", "J01CA"),
        ("D057", "Metronidazole", "400 mg", "tablet", "J01XD"),
    ]
    return pd.DataFrame([
        {"drug_id": drug_id, "generic_name": name, "strength": strength, "form": form,
         "atc_code": atc, "atc_level4": atc, "dataset_group": atc if atc in GROUPS else None,
         "sim_base_daily_units": 10.0, "pack_size": 10, "lead_time_days": 7, "is_simulated": True}
        for drug_id, name, strength, form, atc in rows
    ])


def inventory_batches() -> pd.DataFrame:
    today = date.today()
    return pd.DataFrame([
        {"batch_id": f"BDEMO-{row.drug_id}", "drug_id": row.drug_id,
         "batch_no": f"{row.drug_id}-DEMO-1", "qty_on_hand": 100,
         "expiry_date": today + timedelta(days=365), "received_date": today,
         "lead_time_days": int(row.lead_time_days), "pack_size": int(row.pack_size),
         "as_of_date": today, "is_simulated": True}
        for row in drugs().itertuples()
    ])


def simulated_sales() -> pd.DataFrame:
    rng = np.random.default_rng(43)
    dates = pd.date_range(date.today() - timedelta(days=89), periods=90, freq="D")
    rows = []
    for index, row in enumerate(drugs().itertuples()):
        for offset, sale_date in enumerate(dates):
            rows.append({"sale_date": sale_date, "drug_id": row.drug_id,
                         "quantity": int(rng.poisson(max(1, 2 + index % 5 + offset % 3)),),
                         "is_simulated": True})
    return pd.DataFrame(rows)


def rx_rules() -> pd.DataFrame:
    return pd.DataFrame([
        {"drug_id": row.drug_id, "generic_name": row.generic_name,
         "rule": "prescription_required" if row.drug_id == "D029" else "none",
         "status": "VERIFIED" if row.drug_id == "D029" else "UNVERIFIED_PROPOSED",
         "source_name": "Demo fallback source" if row.drug_id == "D029" else "",
         "source_ref": "https://www.nda.or.ug/" if row.drug_id == "D029" else "",
         "verified_by": "" if row.drug_id != "D029" else "demo", "verified_on": ""}
        for row in drugs().itertuples()
    ])

