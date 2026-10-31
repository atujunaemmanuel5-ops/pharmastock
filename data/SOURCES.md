# Data sources and status

| Source | Use | Status |
|---|---|---|
| Kaggle Pharma sales data (milanzdravkovic) | Daily sales for eight ATC groups | Real source data; raw files are local and must remain out of a public repository unless the licence permits it |
| DDInter 2.0 development downloads | Interaction lookup development data | Imported development data; verify current licence, coverage, and pharmacist interpretation before use |
| National Drug Authority statement as linked in `rx_rules.csv` | Misoprostol prescription-gate reference | Source found; pharmacist confirmation still required |
| `data/raw/synthetic_data/` | Drug catalogue, drug allocation, batches, lead times, demo carts | Simulated, seed 2026; never real inventory or drug-level sales |

The real Kaggle file is group-level sales only. The drug-level sales and stock
views are simulated allocations and are visibly labelled in the API/dashboard.
Licence text and deployment terms must be rechecked before submission because
they can change.

Downloaded RAG documents:

- Uganda Clinical Guidelines 2023 — Ministry of Health portal:
  https://library.health.go.ug/node/1511
- EMHSLU 2023 — Ministry of Health portal:
  https://library.health.go.ug/medical-products-technologies/pharmaceuticals-and-drugs/essential-medicines-and-health-supplies
- WHO Model List of Essential Medicines, 24th list (2025):
  https://www.who.int/publications/i/item/B09474

The PDFs are stored locally under `data/rag/` and excluded from Git by the
existing `data/rag/*.pdf` rule. Retrieval citations identify the local filename
and page number.
