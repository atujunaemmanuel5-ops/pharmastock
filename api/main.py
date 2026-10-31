"""FastAPI entry point for the local-first PharmaStock demo."""

from __future__ import annotations

import io
import logging
import os
from math import sqrt
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import AskRequest, DispenseRequest, MedicationCreate, ProductGroup, UploadSummary
from src.config import ATC_CODES, PROCESSED_PATH
from src.db import database_status, ensure_seeded, record_dispense, replace_uploaded_sales, table_frame, drugs_table, inventory_table, sales_table, rx_table, register_medication
from src.data_prep import complete_calendar, standardise_columns, validate_and_prepare_data
from src.expiry import add_expiry_fields, expiry_risk_report
from src.forecasting import forecast_next_days, load_daily_series, WEEKDAY_AVERAGE
from src.inventory import add_drug_names, create_expiry_report, load_drug_catalogue, load_inventory_batches, reorder_recommendation, summarize_stock, velocity_report
from src.rag.answer import answer_question
from src.safety.dispense_check import check_cart
from src.safety.interactions import load_ddinter_pairs, load_interactions
from src.safety.rx_gate import load_rx_rules
from src.simulate_drugs import load_simulated_sales

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="PharmaStock AI API", version="0.2.0")
frontend_origins = [origin.strip() for origin in os.getenv("PHARMASTOCK_FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=frontend_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@lru_cache(maxsize=1)
def sales_data() -> pd.DataFrame:
    try:
        ensure_seeded()
        data = table_frame(sales_table)
        data = data[data["product_group"].notna()].copy()
        data["sale_date"] = pd.to_datetime(data["sale_date"])
        return data[["sale_date", "product_group", "quantity"]].sort_values(["product_group", "sale_date"]).reset_index(drop=True)
    except Exception:
        return load_daily_series(PROCESSED_PATH)


def inventory_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        ensure_seeded()
        batches = table_frame(inventory_table)
        drugs = table_frame(drugs_table)
        for column in ("expiry_date", "received_date", "as_of_date"):
            batches[column] = pd.to_datetime(batches[column])
    except Exception:
        batches = load_inventory_batches()
        drugs = load_drug_catalogue()
    return batches, drugs


def active_rx_rules() -> pd.DataFrame:
    """Read the persisted rule set, falling back to the checked-in CSV."""
    try:
        ensure_seeded()
        rules = table_frame(rx_table)
        if not rules.empty:
            rules["verified_on"] = pd.to_datetime(rules["verified_on"], errors="coerce").dt.date
            rules["enforceable"] = rules["rule"].eq("prescription_required") & rules["source_ref"].fillna("").astype(str).str.strip().ne("")
            return rules
    except Exception:
        pass
    return load_rx_rules()


@app.get("/health")
def health_status():
    return {"status": "ok", "service": "pharmastock-api", "database": database_status(), "is_simulated_inventory": True}


@app.get("/products", response_model=list[ProductGroup])
def products():
    df = sales_data()
    return [{"code": code, "description": ATC_CODES.get(code, code), "first_date": str(group.sale_date.min().date()), "last_date": str(group.sale_date.max().date())} for code, group in df.groupby("product_group")]


@app.get("/products/{code}/history")
def product_history(code: str, days: int = 90):
    if days < 1 or days > 2000:
        raise HTTPException(422, "days must be between 1 and 2000")
    df = sales_data()
    if code not in set(df["product_group"]):
        raise HTTPException(404, f"Unknown product group: {code}")
    result = df[df["product_group"] == code].tail(days)
    return result.to_dict(orient="records")


@app.get("/forecast/{code}")
def forecast(code: str, horizon: int = 7):
    if horizon < 1 or horizon > 7:
        raise HTTPException(422, "horizon must be between 1 and 7")
    df = sales_data()
    group_df = df[df["product_group"] == code]
    if group_df.empty:
        raise HTTPException(404, f"Unknown product group: {code}")
    method = WEEKDAY_AVERAGE
    try:
        winners = pd.read_csv(__import__("src.config", fromlist=["FORECAST_DIR"]).FORECAST_DIR / "best_methods.csv")
        match = winners[winners["product_group"] == code]
        if not match.empty:
            method = match.iloc[0]["method"]
    except (FileNotFoundError, KeyError):
        pass
    result = forecast_next_days(group_df, method=method, forecast_days=horizon)
    return {"product_group": code, "forecast_method": result["forecast_method"].iloc[0], "is_simulated": False, "forecasts": result.to_dict(orient="records")}


@app.get("/stockout-risk/{code}")
def stockout_risk(code: str):
    recommendation = recommendation_for_group(code)
    return recommendation


def recommendation_for_group(code: str) -> dict:
    df = sales_data()
    group_df = df[df["product_group"] == code]
    if group_df.empty:
        raise HTTPException(404, f"Unknown product group: {code}")
    batches, drugs = inventory_data()
    group_drugs = drugs[drugs["atc_level4"] == code]
    group_ids = set(group_drugs["drug_id"])
    inventory = add_expiry_fields(batches[batches["drug_id"].isin(group_ids)])
    stock = int(inventory.loc[inventory["days_to_expiry"] >= 0, "qty_on_hand"].sum())
    daily_history = group_df.tail(28)["quantity"]
    daily = float(daily_history.mean())
    lead_time = int(round(float(group_drugs["lead_time_days"].mean()))) if not group_drugs.empty else 5
    forecast_values = forecast(code, horizon=7)["forecasts"]
    forecast_daily = float(pd.DataFrame(forecast_values)["predicted_quantity"].mean())
    result = reorder_recommendation(stock, forecast_daily, lead_time_days=lead_time, pack_size=1, forecast_error=float(daily_history.std() or 0))
    return {"product_group": code, **result, "stockout_risk": result["risk_level"], "historical_daily_demand": round(daily, 3), "assumptions": "Real group-level sales forecast applied to simulated unexpired batch stock; pack size is normalized to one sales-volume unit.", "is_simulated": True}


@app.get("/reorder/{code}")
def reorder(code: str):
    return recommendation_for_group(code)


@app.get("/reorder/{code}/what-if")
def reorder_what_if(code: str, usable_stock: int | None = None, demand_multiplier: float = 1.0, lead_time_days: int | None = None):
    """Recalculate a planning recommendation for an interactive demo scenario."""
    if demand_multiplier < 0.1 or demand_multiplier > 5:
        raise HTTPException(422, "demand_multiplier must be between 0.1 and 5")
    if usable_stock is not None and usable_stock < 0:
        raise HTTPException(422, "usable_stock cannot be negative")
    if lead_time_days is not None and (lead_time_days < 0 or lead_time_days > 365):
        raise HTTPException(422, "lead_time_days must be between 0 and 365")
    base = recommendation_for_group(code)
    lead = base["lead_time_days"] if lead_time_days is None else lead_time_days
    stock = base["usable_stock"] if usable_stock is None else usable_stock
    demand = base["average_daily_demand"] * demand_multiplier
    error = base["safety_stock"] / (1.65 * sqrt(lead)) if lead > 0 and base["safety_stock"] else 0.0
    result = reorder_recommendation(stock, demand, lead, base["pack_size"], forecast_error=error)
    return {"product_group": code, "baseline": base, "demand_multiplier": demand_multiplier, **result}


@app.get("/recommendations")
def recommendations():
    return [recommendation_for_group(code) for code in sales_data()["product_group"].drop_duplicates()]


@app.get("/inventory/expiry")
def expiry_report():
    batches, drugs = inventory_data()
    inventory = add_drug_names(batches, drugs)
    demand = load_simulated_sales().groupby("drug_id")["quantity"].mean().to_dict()
    return expiry_risk_report(inventory, demand).to_dict(orient="records")


@app.get("/inventory/stock-summary")
def stock_summary():
    batches, _ = inventory_data()
    return summarize_stock(batches).to_dict(orient="records")


@app.get("/inventory/drugs")
def drugs():
    _, catalogue = inventory_data()
    records = []
    for row in catalogue.to_dict(orient="records"):
        records.append({key: (None if pd.isna(value) else value) for key, value in row.items()})
    return records


@app.get("/inventory/velocity")
def inventory_velocity():
    sales = load_simulated_sales()
    return velocity_report(sales, load_drug_catalogue()).to_dict(orient="records")


@app.get("/inventory/product")
def get_atc_codes():
    return [{"code": code, "description": description} for code, description in ATC_CODES.items()]


@app.post("/inventory/medications")
def add_medication(request: MedicationCreate):
    try:
        created = register_medication(request.model_dump())
        load_ddinter_pairs.cache_clear()
        return created
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/safety/rules")
def safety_rules():
    rules = active_rx_rules().copy()
    return [{key: (None if pd.isna(value) else value) for key, value in row.items()} for row in rules.to_dict(orient="records")]


@app.get("/safety/interactions")
def safety_interactions():
    pairs = load_interactions()
    records = []
    for row in pairs.to_dict(orient="records"):
        records.append({key: (None if pd.isna(value) else value) for key, value in row.items()})
    return records


@app.post("/dispense/check")
def dispense_check(request: DispenseRequest):
    batches, catalogue = inventory_data()
    result = check_cart(request.drug_ids, catalogue, batches, request.prescription_reference, request.override_reason, rules=active_rx_rules(), pairs=load_interactions())
    result["audit_id"] = record_dispense(result)
    return result


@app.post("/dispense/confirm")
def dispense_confirm(request: DispenseRequest):
    result = dispense_check(request)
    if not result["can_confirm"]:
        raise HTTPException(403, detail={"message": "Dispense cannot be confirmed", "check": result})
    result["confirmed"] = True
    result["audit_id"] = record_dispense(result, confirmed=True)
    return result


@app.post("/ask")
def ask(request: AskRequest):
    return answer_question(request.question)


@app.post("/upload", response_model=UploadSummary)
async def upload(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Upload a CSV file")
    try:
        raw = pd.read_csv(io.BytesIO(await file.read()))
        cleaned = standardise_columns(validate_and_prepare_data(raw))
        complete_calendar(cleaned)
        rows = replace_uploaded_sales(cleaned)
        sales_data.cache_clear()
    except (ValueError, pd.errors.ParserError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return UploadSummary(rows=rows, groups=len(ATC_CODES), first_date=str(cleaned["datum"].min().date()), last_date=str(cleaned["datum"].max().date()), message="CSV validated and persisted as the active product-group sales history.")
