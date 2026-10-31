"""Database-backed persistence with a reliable local SQLite default.

The API uses the same repository interface for local SQLite and optional
PostgreSQL. Set ``PHARMASTOCK_DB_BACKEND=postgres`` and ``DATABASE_URL`` when
you are ready to point the application at a hosted database. Local startup is
fully offline and seeds from the checked-in CSV/demo inputs.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text, UniqueConstraint, create_engine, delete, func, insert, select, text

try:
    from .config import PROJECT_ROOT, PROCESSED_PATH, SYNTHETIC_DATA_DIR
except ImportError:
    from config import PROJECT_ROOT, PROCESSED_PATH, SYNTHETIC_DATA_DIR

DB_PATH = PROJECT_ROOT / "data" / "pharmastock.db"
metadata = MetaData()

drugs_table = Table(
    "drugs", metadata,
    Column("drug_id", String(50), primary_key=True), Column("generic_name", String(255), nullable=False),
    Column("strength", String(100)), Column("form", String(100)), Column("atc_code", String(50)),
    Column("atc_level4", String(100)), Column("dataset_group", String(100)), Column("sim_base_daily_units", Float),
    Column("pack_size", Integer, nullable=False), Column("lead_time_days", Integer, nullable=False),
    Column("is_simulated", Boolean, nullable=False, default=True),
)
inventory_table = Table(
    "inventory_batches", metadata,
    Column("batch_id", String(50), primary_key=True), Column("drug_id", String(50), nullable=False),
    Column("batch_no", String(100), nullable=False), Column("qty_on_hand", Integer, nullable=False),
    Column("expiry_date", Date, nullable=False), Column("received_date", Date, nullable=False),
    Column("lead_time_days", Integer, nullable=False), Column("pack_size", Integer, nullable=False),
    Column("as_of_date", Date, nullable=False), Column("is_simulated", Boolean, nullable=False, default=True),
)
sales_table = Table(
    "sales_daily", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True), Column("sale_date", Date, nullable=False),
    Column("drug_id", String(50)), Column("product_group", String(50)), Column("quantity", Float, nullable=False),
    Column("is_simulated", Boolean, nullable=False, default=False),
    UniqueConstraint("sale_date", "drug_id", "product_group", name="uq_sales_daily_key"),
)
rx_table = Table(
    "rx_rules", metadata,
    Column("drug_id", String(50), primary_key=True), Column("generic_name", String(255), nullable=False),
    Column("rule", String(50), nullable=False), Column("status", String(100), nullable=False),
    Column("source_name", Text), Column("source_ref", Text), Column("verified_by", String(255)), Column("verified_on", Date),
)
interaction_table = Table(
    "interaction_pairs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True), Column("drug_a_id", String(50), nullable=False),
    Column("drug_b_id", String(50), nullable=False), Column("severity", String(30), nullable=False),
    Column("mechanism_text", Text), Column("management_text", Text), Column("source_url", Text),
    UniqueConstraint("drug_a_id", "drug_b_id", name="uq_interaction_pair"),
)
document_table = Table(
    "doc_chunks", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True), Column("doc_name", String(255), nullable=False),
    Column("page", Integer), Column("section", String(255)), Column("text", Text, nullable=False), Column("source_url", Text),
)
dispense_table = Table(
    "dispensing_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True), Column("created_at", DateTime(timezone=True), nullable=False),
    Column("cart_json", Text, nullable=False), Column("decision", String(50), nullable=False),
    Column("reasons_json", Text, nullable=False), Column("prescription_ref", Text), Column("override_reason", Text),
)


def database_url() -> str:
    backend = os.getenv("PHARMASTOCK_DB_BACKEND", "sqlite").lower()
    if backend == "postgres" and os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH.as_posix()}"


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(database_url(), pool_pre_ping=True, future=True)


def initialize_database() -> None:
    metadata.create_all(get_engine())


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict]:
    values = frame.copy()
    for column in columns:
        if column not in values:
            values[column] = None
        else:
            values[column] = values[column].where(pd.notna(values[column]), None)
    result = []
    for row in values[columns].to_dict(orient="records"):
        result.append({key: (None if pd.isna(value) else value) for key, value in row.items()})
    return result


def seed_database(force: bool = False) -> None:
    """Idempotently load catalogue, sales, inventory, rules and RAG chunks."""
    initialize_database()
    engine = get_engine()
    with engine.begin() as connection:
        existing = connection.execute(select(func.count()).select_from(drugs_table)).scalar_one()
        if existing and not force:
            return
        for table in (dispense_table, document_table, interaction_table, rx_table, sales_table, inventory_table, drugs_table):
            connection.execute(delete(table))

        from .simulate_drugs import load_drugs
        drugs = load_drugs()
        connection.execute(insert(drugs_table), _records(drugs, ["drug_id", "generic_name", "strength", "form", "atc_code", "atc_level4", "dataset_group", "sim_base_daily_units", "pack_size", "lead_time_days", "is_simulated"]))

        batches = pd.read_csv(SYNTHETIC_DATA_DIR / "inventory_batches.csv")
        base_drug_ids = set(batches["drug_id"])
        additional_rows = []
        for row in drugs[~drugs["drug_id"].isin(base_drug_ids)].itertuples():
            additional_rows.append({
                "batch_id": f"BDEMO-{row.drug_id}-1",
                "drug_id": row.drug_id,
                "batch_no": f"{row.drug_id}-DEMO-1",
                "qty_on_hand": max(20, int(float(row.sim_base_daily_units) * 30)),
                "expiry_date": date(2027, 12, 31),
                "received_date": date(2026, 1, 15),
                "lead_time_days": int(row.lead_time_days),
                "pack_size": int(row.pack_size),
                "as_of_date": date(2026, 10, 24),
                "is_simulated": True,
            })
        if additional_rows:
            batches = pd.concat([batches, pd.DataFrame(additional_rows)], ignore_index=True)
        for column in ("expiry_date", "received_date", "as_of_date"):
            batches[column] = pd.to_datetime(batches[column]).dt.date
        connection.execute(insert(inventory_table), _records(batches, ["batch_id", "drug_id", "batch_no", "qty_on_hand", "expiry_date", "received_date", "lead_time_days", "pack_size", "as_of_date", "is_simulated"]))

        sales = pd.read_csv(PROCESSED_PATH, parse_dates=["sale_date"])
        sales["product_group"] = sales["product_group"].astype(str)
        sales["sale_date"] = sales["sale_date"].dt.date
        sales["drug_id"] = None
        sales["is_simulated"] = False
        connection.execute(insert(sales_table), _records(sales, ["sale_date", "drug_id", "product_group", "quantity", "is_simulated"]))

        simulated = pd.read_csv(SYNTHETIC_DATA_DIR / "sales_daily_simulated.csv", parse_dates=["sale_date"])
        simulated["sale_date"] = simulated["sale_date"].dt.date
        simulated["product_group"] = None
        connection.execute(insert(sales_table), _records(simulated, ["sale_date", "drug_id", "product_group", "quantity", "is_simulated"]))

        from .safety.rx_gate import load_rx_rules
        rules = load_rx_rules()
        rules["verified_on"] = pd.to_datetime(rules["verified_on"], errors="coerce").dt.date
        connection.execute(insert(rx_table), _records(rules, ["drug_id", "generic_name", "rule", "status", "source_name", "source_ref", "verified_by", "verified_on"]))

        from .safety.interactions import load_ddinter_pairs
        load_ddinter_pairs.cache_clear()
        pairs = load_ddinter_pairs()
        if not pairs.empty:
            connection.execute(insert(interaction_table), _records(pairs, ["drug_a_id", "drug_b_id", "severity", "mechanism_text", "management_text", "source_url"]))

        from .rag.ingest import load_corpus
        corpus = pd.DataFrame(load_corpus())
        if not corpus.empty:
            connection.execute(insert(document_table), _records(corpus, ["doc_name", "page", "section", "text", "source_url"]))


@lru_cache(maxsize=1)
def ensure_seeded() -> None:
    seed_database()


def table_frame(table: Table) -> pd.DataFrame:
    ensure_seeded()
    with get_engine().connect() as connection:
        return pd.read_sql(select(table), connection)


def record_dispense(result: dict, confirmed: bool = False) -> int:
    initialize_database()
    from datetime import datetime, timezone
    decision = "CONFIRMED" if confirmed else str(result.get("decision", "UNKNOWN"))
    with get_engine().begin() as connection:
        inserted = connection.execute(insert(dispense_table).values(
            created_at=datetime.now(timezone.utc), cart_json=json.dumps(result.get("drug_ids", [])),
            decision=decision, reasons_json=json.dumps(result.get("reasons", []), default=str),
            prescription_ref=result.get("prescription_reference"), override_reason=result.get("override_reason"),
        ))
        return int(inserted.inserted_primary_key[0])


def register_medication(payload: dict) -> dict:
    """Register a medicine and an optional opening stock batch in local storage."""
    initialize_database()
    drug_id = (payload.get("drug_id") or f"U{uuid4().hex[:8].upper()}").strip()
    generic_name = str(payload.get("generic_name", "")).strip()
    if not generic_name:
        raise ValueError("generic_name is required")
    expiry = payload.get("expiry_date") or (date.today() + timedelta(days=365)).isoformat()
    as_of = date.today()
    pack_size = int(payload.get("pack_size") or 1)
    lead_time = int(payload.get("lead_time_days") or 7)
    stock = int(payload.get("initial_stock") or 0)
    if pack_size <= 0 or lead_time < 0 or stock < 0:
        raise ValueError("pack_size must be positive; lead time and stock cannot be negative")
    drug = {
        "drug_id": drug_id, "generic_name": generic_name,
        "strength": payload.get("strength"), "form": payload.get("form"),
        "atc_code": payload.get("atc_code"), "atc_level4": payload.get("atc_level4"),
        "dataset_group": None, "sim_base_daily_units": 0.0,
        "pack_size": pack_size, "lead_time_days": lead_time, "is_simulated": True,
    }
    rule = "prescription_required" if payload.get("prescription_required") else "none"
    with get_engine().begin() as connection:
        if connection.execute(select(func.count()).select_from(drugs_table).where(drugs_table.c.drug_id == drug_id)).scalar_one():
            raise ValueError(f"drug_id already exists: {drug_id}")
        connection.execute(insert(drugs_table).values(**drug))
        connection.execute(insert(rx_table).values(
            drug_id=drug_id, generic_name=generic_name, rule=rule,
            status="USER_ADDED_REVIEW_REQUIRED", source_name=payload.get("source_name"),
            source_ref=payload.get("source_ref"), verified_by=None, verified_on=None,
        ))
        if stock > 0:
            connection.execute(insert(inventory_table).values(
                batch_id=f"B-{drug_id}-1", drug_id=drug_id, batch_no=f"{drug_id}-OPENING-1",
                qty_on_hand=stock, expiry_date=pd.to_datetime(expiry).date(),
                received_date=as_of, lead_time_days=lead_time, pack_size=pack_size,
                as_of_date=as_of, is_simulated=True,
            ))
    return {**drug, "initial_stock": stock, "expiry_date": str(expiry), "prescription_required": rule == "prescription_required"}


def replace_uploaded_sales(wide_frame: pd.DataFrame) -> int:
    """Replace real product-group sales after the upload has passed validation."""
    from .data_prep import to_long
    long_frame = to_long(wide_frame)
    long_frame["sale_date"] = pd.to_datetime(long_frame["sale_date"]).dt.date
    long_frame["drug_id"] = None
    long_frame["is_simulated"] = False
    ensure_seeded()
    with get_engine().begin() as connection:
        connection.execute(delete(sales_table).where(sales_table.c.product_group.is_not(None)))
        connection.execute(insert(sales_table), _records(long_frame, ["sale_date", "drug_id", "product_group", "quantity", "is_simulated"]))
    return len(long_frame)


def database_status() -> str:
    try:
        initialize_database()
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return "sqlite" if database_url().startswith("sqlite") else "postgresql"
    except Exception:
        return "unavailable"
