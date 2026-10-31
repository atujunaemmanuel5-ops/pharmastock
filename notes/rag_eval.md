# RAG evaluation and boundary

The local assistant uses the downloaded Uganda Clinical Guidelines 2023,
EMHSLU 2023, WHO Model List of Essential Medicines 24th list, and Practical
Guideline for Dispensing at Lower Level Health Centres PDFs as a page-level
extractive corpus with document, page, section, and source metadata. Any PDF
added to `data/rag/` is ingested automatically.
It does not need an LLM or an embedding service to work.
Each answer either returns cited passages or says `Not found in the PharmaStock
reference documents.` Out-of-scope requests for personal treatment instructions
or bypassing prescription rules are refused.

The committed 20-question golden set is `data/rag/golden_questions.csv` and can
be scored with:

```powershell
python -m src.rag.evaluate
```

The source-aware lexical retriever scores 100% document hit rate and 90%
exact-page hit rate at top-5 on that set. This is a retrieval smoke test, not a
clinical accuracy claim. Questions that need a specific passage should still
be checked by a pharmacist or reviewer.
