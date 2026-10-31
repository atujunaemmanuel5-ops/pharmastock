"""Offline RAG corpus loader with page/source metadata."""

from __future__ import annotations

from pathlib import Path

import fitz

from .chunk import chunk_text

DEFAULT_DOCUMENTS = [
    {
        "doc_name": "PharmaStock safety rules",
        "page": 1,
        "section": "Decision support boundary",
        "source_url": "notes/safety_rules.md",
        "text": "PharmaStock AI is decision support for a licensed dispenser. Rules decide whether a cart is blocked or warned. The assistant explains cited passages and never allows or blocks a sale. No interaction found does not mean safe.",
    },
    {
        "doc_name": "PharmaStock safety rules",
        "page": 2,
        "section": "Expiry and FEFO",
        "source_url": "src/expiry.py",
        "text": "Expired batches must never be sold. FEFO means earliest-expiry-first-out: select the earliest unexpired batch with positive stock. Units at risk of expiring are stock on hand minus expected daily demand multiplied by days until expiry, never below zero.",
    },
    {
        "doc_name": "PharmaStock inventory assumptions",
        "page": 1,
        "section": "Simulated data",
        "source_url": "data/raw/synthetic_data/README_synthetic.md",
        "text": "The Kaggle sales are real group-level observations. Drug-level sales, stock, batches, expiry dates and lead times in this demonstration are simulated with a fixed seed. They must not be described as real drug-level pharmacy records.",
    },
]


def ingest_directory(directory: Path) -> list[dict]:
    """Extract searchable page-level chunks from local PDFs and text files."""
    records = []
    for path in sorted(directory.glob("*.pdf")):
        with fitz.open(path) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                for text in chunk_text(page_text):
                    records.append({
                        "doc_name": path.name,
                        "page": page_number,
                        "section": "page text",
                        "source_url": str(path),
                        "text": text,
                    })
    for path in sorted(directory.glob("*.txt")):
        for index, text in enumerate(chunk_text(path.read_text(encoding="utf-8")), start=1):
            records.append({"doc_name": path.name, "page": index, "section": "text", "source_url": str(path), "text": text})
    return records or DEFAULT_DOCUMENTS.copy()


def load_corpus(directory: Path | None = None) -> list[dict]:
    """Load the local RAG corpus, falling back to built-in passages."""
    if directory is None:
        try:
            from ..config import PROJECT_ROOT
        except ImportError:
            from src.config import PROJECT_ROOT
        directory = PROJECT_ROOT / "data" / "rag"
    return ingest_directory(directory)
