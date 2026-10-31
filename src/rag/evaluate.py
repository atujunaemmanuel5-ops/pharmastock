"""Evaluate page-level retrieval against the committed golden questions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .retrieve import retrieve


def evaluate_golden(path: Path | None = None, top_k: int = 5) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "data" / "rag" / "golden_questions.csv"
    questions = pd.read_csv(path)
    rows = []
    for row in questions.itertuples():
        hits = retrieve(row.question, limit=top_k)
        document_hit = any(hit["doc_name"] == row.expected_document for hit in hits)
        page_hit = any(hit["doc_name"] == row.expected_document and int(hit["page"]) == int(row.expected_page) for hit in hits)
        rows.append({"question": row.question, "document_hit": document_hit, "page_hit": page_hit, "top_documents": [hit["doc_name"] for hit in hits]})
    result = pd.DataFrame(rows)
    return {"questions": len(result), "document_hit_rate": float(result["document_hit"].mean()), "page_hit_rate": float(result["page_hit"].mean()), "results": result}


if __name__ == "__main__":
    report = evaluate_golden()
    print(f"document_hit_rate={report['document_hit_rate']:.3f} page_hit_rate={report['page_hit_rate']:.3f}")
    print(report["results"].to_string(index=False))
