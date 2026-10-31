"""Prescription rules. The result is a lookup, never an AI decision."""

from __future__ import annotations

import pandas as pd

try:
    from ..config import SYNTHETIC_DATA_DIR
except ImportError:
    from config import SYNTHETIC_DATA_DIR

RX_RULES_PATH = SYNTHETIC_DATA_DIR / "rx_rules.csv"


def load_rx_rules(path=RX_RULES_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prescription rules not found: {path}")
    rules = pd.read_csv(path, keep_default_na=False)
    additions_path = SYNTHETIC_DATA_DIR / "catalogue_additions.csv"
    if path == RX_RULES_PATH and additions_path.exists():
        additions = pd.read_csv(additions_path, keep_default_na=False)
        additions = additions.rename(columns={
            "prescription_rule": "rule",
            "rule_status": "status",
        })
        additions["source_name"] = additions.get("source_name", "")
        additions["source_ref"] = additions.get("source_ref", "")
        additions["verified_by"] = additions.get("verified_by", "")
        additions["verified_on"] = additions.get("verified_on", "")
        additions = additions[["drug_id", "generic_name", "rule", "status", "source_name", "source_ref", "verified_by", "verified_on"]]
        rules = pd.concat([rules, additions], ignore_index=True)
    required = {"drug_id", "generic_name", "rule", "status", "source_name", "source_ref"}
    missing = required.difference(rules.columns)
    if missing:
        raise ValueError(f"Prescription rules missing columns: {sorted(missing)}")
    if rules["drug_id"].duplicated().any():
        raise ValueError("Prescription rules contain duplicate drug IDs")
    if not rules["rule"].isin({"prescription_required", "none"}).all():
        raise ValueError("Prescription rules contain an unknown rule")
    # Proposed rows stay visible for pharmacist review but are not enforced.
    if "enforceable" not in rules:
        rules["enforceable"] = rules["rule"].eq("prescription_required") & rules["source_ref"].str.strip().ne("")
    return rules


def prescription_check(drug_ids: list[str], prescription_reference: str | None, rules=None) -> list[dict]:
    rules = load_rx_rules() if rules is None else rules
    by_id = rules.set_index("drug_id", drop=False)
    results = []
    for drug_id in drug_ids:
        if drug_id not in by_id.index:
            results.append({"drug_id": drug_id, "required": False, "known": False, "message": "Drug has no prescription rule."})
            continue
        row = by_id.loc[drug_id]
        required = bool(row["enforceable"])
        has_reference = bool((prescription_reference or "").strip())
        results.append({
            "drug_id": drug_id,
            "required": required,
            "known": True,
            "has_reference": has_reference,
            "source_name": row["source_name"],
            "source_ref": row["source_ref"],
            "message": "Prescription reference supplied." if required and has_reference else "Prescription reference required." if required else "No sourced prescription gate is configured for this drug.",
        })
    return results
