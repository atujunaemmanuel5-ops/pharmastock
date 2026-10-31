import pandas as pd

from src.expiry import fefo_pick, units_at_risk
from src.inventory import reorder_recommendation
from src.velocity import calculate_daily_velocity, calculate_sales_growth, classify_sales_trend


def test_fefo_ignores_expired_and_picks_earliest_unexpired():
    batches = pd.DataFrame([
        {"drug_id": "D1", "batch_id": "expired", "qty_on_hand": 10, "expiry_date": "2026-01-01", "as_of_date": "2026-01-10"},
        {"drug_id": "D1", "batch_id": "later", "qty_on_hand": 10, "expiry_date": "2026-04-01", "as_of_date": "2026-01-10"},
        {"drug_id": "D1", "batch_id": "first", "qty_on_hand": 10, "expiry_date": "2026-02-01", "as_of_date": "2026-01-10"},
    ])
    assert fefo_pick(batches, "D1")["batch_id"] == "first"


def test_units_at_risk_never_negative():
    assert units_at_risk(100, 5, 30) == 0
    assert units_at_risk(100, 2, 30) == 40


def test_reorder_rounds_up_to_pack_and_never_negative():
    result = reorder_recommendation(3, 2, lead_time_days=5, pack_size=10)
    assert result["reorder_quantity"] == 10
    assert reorder_recommendation(100, 2, 5, 10)["reorder_quantity"] == 0


def test_velocity_helpers_cover_wide_and_scalar_inputs():
    sales = pd.DataFrame({"datum": ["2025-01-01", "2025-01-02"], "M01AB": [10, 0], "R03": [2, 4]})
    report = calculate_daily_velocity(sales, days=2)
    assert report.set_index("product_group").loc["M01AB", "daily_velocity"] == 5
    assert calculate_sales_growth(12, 10) == 0.2
    assert classify_sales_trend(0.2) == "Increasing"
    assert classify_sales_trend(0.01) == "Stable"
    assert classify_sales_trend(-0.2) == "Declining"
