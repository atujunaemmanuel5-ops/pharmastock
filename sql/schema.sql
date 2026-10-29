-- Active: 1783955623418@@127.0.0.1@3306@db
-- PharmaStock database schema
-- Run this against the pharmastock database.

CREATE TABLE IF NOT EXISTS drugs (
    drug_id VARCHAR(50) PRIMARY KEY,
    generic_name VARCHAR(255) NOT NULL,
    strength VARCHAR(100),
    form VARCHAR(100),
    atc_code VARCHAR(50),
    atc_level4 VARCHAR(100),
    dataset_group VARCHAR(100),
    sim_base_daily_units NUMERIC(12, 3),
    pack_size INTEGER NOT NULL CHECK (pack_size > 0),
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    is_simulated BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS inventory_batches (
    batch_id VARCHAR(50) PRIMARY KEY,
    drug_id VARCHAR(50) NOT NULL REFERENCES drugs(drug_id),
    batch_no VARCHAR(100) NOT NULL,
    qty_on_hand INTEGER NOT NULL CHECK (qty_on_hand >= 0),
    expiry_date DATE NOT NULL,
    received_date DATE NOT NULL,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    pack_size INTEGER NOT NULL CHECK (pack_size > 0),
    as_of_date DATE NOT NULL,
    is_simulated BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_inventory_batches_drug_id
    ON inventory_batches(drug_id);

CREATE INDEX IF NOT EXISTS idx_inventory_batches_expiry_date
    ON inventory_batches(expiry_date);