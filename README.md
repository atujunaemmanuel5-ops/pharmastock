# PharmaStock AI

PharmaStock AI is a local-first decision-support demo for a small pharmacy. It
combines a 7-day ATC-group demand forecast, simulated stock/reorder and expiry
views, a deterministic dispense checker, and a small cited assistant.

> A licensed dispenser makes the final decision. The system does not verify a
> prescription, diagnose patients, or claim clinical accuracy.

## What is real and what is simulated

The Kaggle daily sales file is real historical sales at eight ATC product-group
levels. It ends in 2019 and contains sales volume, not necessarily unit counts.
Drug-level sales, drug allocation, stock, batches, expiry dates and lead times
are seeded simulated data. The dashboard and API label this with `SIMULATED`.
See [data/SOURCES.md](data/SOURCES.md) and [notes/scope.md](notes/scope.md).

## Run locally

PowerShell:

```powershell
\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.data_prep
python -m src.forecasting
uvicorn api.main:app --reload
```

In a second terminal, start the React frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. The API docs are at
`http://127.0.0.1:8000/docs`. The React app defaults to that API; set
`VITE_API_URL` if the API is hosted elsewhere. The original Streamlit dashboard
is retained under `dashboard/` as a legacy fallback, but React is the primary
presentation UI.

## Main workflows

- `POST /dispense/check` checks unknown drugs, sourced prescription gates,
  expiry/FEFO, interactions and therapeutic duplication. Rules decide; RAG
  never allows or blocks a sale.
- `GET /forecast/{code}`, `/stockout-risk/{code}`, `/reorder/{code}`, and
  `/recommendations` expose the forecast and reorder views.
- `GET /inventory/velocity` and `/inventory/expiry` expose simulated stock
  intelligence.
- `POST /inventory/medications` registers a new medicine, opening stock batch,
  and optional prescription rule without editing the source CSV files.
- `POST /ask` searches the downloaded Uganda Clinical Guidelines, EMHSLU, and
  WHO Essential Medicines List PDFs plus the local dispensing guideline,
  returning extractive answers with
  document/page citations or `Not found`.
- `POST /upload` validates a Kaggle-format CSV and persists it as the active
  product-group history while retaining the simulated drug-level sales rows.

## Tests

```powershell
python -m pytest -q
```

The tests cover validation failures, pack-rounded reorder calculations, FEFO
and expired-stock refusal, the misoprostol prescription example, interaction
severity and API behavior.

The local database is SQLite at `data/pharmastock.db`. It is seeded
idempotently from the CSV inputs, stores the RAG chunks, and records dispense
checks/confirmations. For PostgreSQL, set `PHARMASTOCK_DB_BACKEND=postgres` and
`DATABASE_URL` before starting the API.

Use the dashboard's **Data import → Add a medicine** form to extend the
catalogue. A prescription rule is only enforced when a source reference is
provided; otherwise it remains visible as a review rule.

To reproduce the small local RAG retrieval evaluation:

```powershell
python -m src.rag.evaluate
```

## Forecast limitation

The current evaluation uses identical chronological rolling 7-day windows. The
pipeline compares naive, moving-average, seasonal-naive, weekday-average and a
random forest candidate, selecting the lowest-MAE method per group. This is an
evaluation on historical group sales, not proof of current demand or real
stockout prediction.

## Safety limitation

Only prescription rules with a source reference are enforced by the demo. The
rest of the catalogue is explicitly proposed/unverified and needs pharmacist
review. The interaction import is development data and “no interaction found”
does not mean safe. Expired inventory is never offered, and major interaction
overrides require a reason in the request.
