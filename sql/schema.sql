-- PostgreSQL schema for the deployed adapter. The API currently uses the
-- local-file fallback when DATABASE_URL is unavailable.

CREATE TABLE IF NOT EXISTS drugs (
    drug_id TEXT PRIMARY KEY,
    generic_name TEXT NOT NULL,
    strength TEXT,
    form TEXT,
    atc_code TEXT,
    atc_level4 TEXT,
    dataset_group TEXT,
    sim_base_daily_units NUMERIC(12,3),
    pack_size INTEGER NOT NULL CHECK (pack_size > 0),
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    is_simulated BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS inventory_batches (
    batch_id TEXT PRIMARY KEY,
    drug_id TEXT NOT NULL REFERENCES drugs(drug_id),
    batch_no TEXT NOT NULL,
    qty_on_hand INTEGER NOT NULL CHECK (qty_on_hand >= 0),
    expiry_date DATE NOT NULL,
    received_date DATE NOT NULL,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    pack_size INTEGER NOT NULL CHECK (pack_size > 0),
    as_of_date DATE NOT NULL,
    is_simulated BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS sales_daily (
    sale_date DATE NOT NULL,
    drug_id TEXT,
    product_group TEXT,
    quantity NUMERIC NOT NULL CHECK (quantity >= 0),
    is_simulated BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (sale_date, drug_id, product_group)
);

CREATE TABLE IF NOT EXISTS rx_rules (
    drug_id TEXT PRIMARY KEY REFERENCES drugs(drug_id),
    generic_name TEXT NOT NULL,
    rule TEXT NOT NULL CHECK (rule IN ('prescription_required', 'none')),
    status TEXT NOT NULL,
    source_name TEXT,
    source_ref TEXT,
    verified_by TEXT,
    verified_on DATE
);

CREATE TABLE IF NOT EXISTS interaction_pairs (
    drug_a_id TEXT NOT NULL REFERENCES drugs(drug_id),
    drug_b_id TEXT NOT NULL REFERENCES drugs(drug_id),
    severity TEXT NOT NULL,
    mechanism_text TEXT,
    management_text TEXT,
    source_url TEXT,
    PRIMARY KEY (drug_a_id, drug_b_id)
);

CREATE TABLE IF NOT EXISTS dispensing_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cart_json JSONB NOT NULL,
    decision TEXT NOT NULL,
    reasons_json JSONB NOT NULL,
    prescription_ref TEXT,
    override_reason TEXT
);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id BIGSERIAL PRIMARY KEY,
    doc_name TEXT NOT NULL,
    page INTEGER,
    section TEXT,
    text TEXT NOT NULL,
    source_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_inventory_batches_drug_id ON inventory_batches(drug_id);
CREATE INDEX IF NOT EXISTS idx_inventory_batches_expiry ON inventory_batches(expiry_date);
