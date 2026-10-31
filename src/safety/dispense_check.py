"""Single deterministic decision engine for the dispense console."""

from __future__ import annotations

from datetime import datetime, timezone

from .interactions import check_interactions, duplication_alerts
from .rx_gate import prescription_check


def check_cart(drug_ids: list[str], catalogue, batches, prescription_reference: str | None = None, override_reason: str | None = None, rules=None, pairs=None) -> dict:
    """Check every rule and return all reasons; the worst result wins."""
    from ..expiry import add_expiry_fields, fefo_pick

    if not drug_ids:
        raise ValueError("Cart must contain at least one drug")
    unique = list(dict.fromkeys(drug_ids))
    known_ids = set(catalogue["drug_id"])
    reasons = []
    unknown = [drug_id for drug_id in unique if drug_id not in known_ids]
    if unknown:
        reasons.append({"code": "unknown_drug", "message": f"Unknown drug IDs: {', '.join(unknown)}"})

    for result in prescription_check(unique, prescription_reference, rules=rules):
        if result.get("required") and not result.get("has_reference"):
            reasons.append({"code": "prescription_required", "drug_id": result["drug_id"], "message": result["message"], "source_ref": result.get("source_ref", "")})

    expiry = add_expiry_fields(batches)
    fefo = {}
    for drug_id in unique:
        pick = fefo_pick(expiry, drug_id)
        if pick is None:
            reasons.append({"code": "no_unexpired_stock", "drug_id": drug_id, "message": "No unexpired stock is available; expired stock cannot be sold."})
        else:
            fefo[drug_id] = {"batch_id": pick["batch_id"], "batch_no": pick.get("batch_no", ""), "expiry_date": pick["expiry_date"].date().isoformat() if hasattr(pick["expiry_date"], "date") else str(pick["expiry_date"]), "qty_on_hand": int(pick["qty_on_hand"])}
            if int(pick["days_to_expiry"]) <= 30:
                reasons.append({"code": "near_expiry", "drug_id": drug_id, "message": "Use the earliest-expiring unexpired batch first.", "batch_id": pick["batch_id"]})

    interactions = check_interactions(unique, pairs=pairs)
    for interaction in interactions:
        if interaction["severity"] == "Major":
            reasons.append({"code": "major_interaction", "message": f"Major interaction: {interaction['drug_a_id']} + {interaction['drug_b_id']}. Pharmacist review required.", "details": interaction})
        elif interaction["severity"] == "Moderate":
            reasons.append({"code": "moderate_interaction", "message": f"Moderate interaction: {interaction['drug_a_id']} + {interaction['drug_b_id']}.", "details": interaction})
    for alert in duplication_alerts(unique, catalogue):
        reasons.append({"code": "therapeutic_duplication", "message": alert["note"], "details": alert})

    if unknown:
        decision = "UNKNOWN"
    elif any(item["code"] in {"prescription_required", "no_unexpired_stock"} for item in reasons):
        decision = "BLOCK"
    elif any(item["code"] == "major_interaction" for item in reasons):
        decision = "STOP_OVERRIDDEN" if (override_reason or "").strip() else "STOP"
    elif any(item["code"] in {"moderate_interaction", "therapeutic_duplication"} for item in reasons):
        decision = "WARN"
    elif any(item["code"] == "near_expiry" for item in reasons):
        decision = "INFO"
    else:
        decision = "OK"

    return {"decision": decision, "can_confirm": decision in {"OK", "INFO", "WARN", "STOP_OVERRIDDEN"}, "drug_ids": unique, "prescription_reference": prescription_reference, "override_reason": override_reason, "reasons": reasons, "interactions": interactions, "fefo_picks": fefo, "checked_at": datetime.now(timezone.utc).isoformat(), "is_simulated": True}
