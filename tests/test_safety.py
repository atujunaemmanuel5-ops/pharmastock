import pandas as pd

from src.safety.dispense_check import check_cart
from src.safety.interactions import check_interactions


def catalogue():
    return pd.DataFrame([
        {"drug_id": "D029", "generic_name": "Misoprostol", "atc_level4": "G02AD", "is_simulated": True},
        {"drug_id": "D005", "generic_name": "Ibuprofen", "atc_level4": "M01AE", "is_simulated": True},
        {"drug_id": "D047", "generic_name": "Warfarin", "atc_level4": "B01AA", "is_simulated": True},
    ])


def batches():
    return pd.DataFrame([
        {"drug_id": "D029", "batch_id": "B29", "batch_no": "29-1", "qty_on_hand": 10, "expiry_date": "2027-01-01", "as_of_date": "2026-01-01"},
        {"drug_id": "D005", "batch_id": "B5", "batch_no": "5-1", "qty_on_hand": 10, "expiry_date": "2027-01-01", "as_of_date": "2026-01-01"},
        {"drug_id": "D047", "batch_id": "B47", "batch_no": "47-1", "qty_on_hand": 10, "expiry_date": "2027-01-01", "as_of_date": "2026-01-01"},
    ])


def rules():
    return pd.DataFrame([
        {"drug_id": "D029", "generic_name": "Misoprostol", "rule": "prescription_required", "status": "VERIFIED", "source_name": "source", "source_ref": "https://example.test/source", "enforceable": True},
        {"drug_id": "D005", "generic_name": "Ibuprofen", "rule": "none", "status": "VERIFIED", "source_name": "source", "source_ref": "https://example.test/source", "enforceable": False},
        {"drug_id": "D047", "generic_name": "Warfarin", "rule": "none", "status": "VERIFIED", "source_name": "source", "source_ref": "https://example.test/source", "enforceable": False},
    ])


def test_prescription_gate_blocks_then_reference_allows():
    blocked = check_cart(["D029"], catalogue(), batches(), rules=rules())
    allowed = check_cart(["D029"], catalogue(), batches(), prescription_reference="RX-1", rules=rules())
    assert blocked["decision"] == "BLOCK"
    assert allowed["decision"] == "OK"


def test_major_interaction_stops_and_reversed_pair_matches():
    assert check_interactions(["D047", "D005"])[0]["severity"] == "Major"
    assert check_interactions(["D005", "D047"])[0]["severity"] == "Major"
    result = check_cart(["D047", "D005"], catalogue(), batches(), rules=rules())
    assert result["decision"] == "STOP"
    overridden = check_cart(["D047", "D005"], catalogue(), batches(), override_reason="Pharmacist reviewed", rules=rules())
    assert overridden["decision"] == "STOP_OVERRIDDEN"


def test_unknown_drug_wins_and_expired_stock_blocks():
    unknown = check_cart(["D999"], catalogue(), batches(), rules=rules())
    assert unknown["decision"] == "UNKNOWN"
    expired = batches().copy()
    expired.loc[expired["drug_id"] == "D005", "expiry_date"] = "2025-01-01"
    result = check_cart(["D005"], catalogue(), expired, rules=rules())
    assert result["decision"] == "BLOCK"
