-- Applied automatically by src.db.initialize_database for existing databases.
-- New databases can run this after sql/schema.sql as a documented migration.

ALTER TABLE dispensing_log ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT 'unknown-actor';

CREATE TABLE IF NOT EXISTS sales_uploads (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT NOT NULL,
    filename TEXT NOT NULL,
    rows INTEGER NOT NULL,
    first_date DATE NOT NULL,
    last_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_upload_rows (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES sales_uploads(id),
    sale_date DATE NOT NULL,
    product_group TEXT NOT NULL,
    quantity NUMERIC NOT NULL CHECK (quantity >= 0)
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id TEXT,
    detail_json JSONB
);
