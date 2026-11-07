"""Offline RAG corpus loader with page/source metadata."""

from __future__ import annotations

import os
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

HOSTED_DOCUMENTS = [
    {
        "doc_name": "uganda_clinical_guidelines_2023.pdf",
        "page": 22,
        "section": "Preface",
        "source_url": "data/rag/uganda_clinical_guidelines_2023.pdf",
        "text": "The Uganda Clinical Guidelines 2023 manual is intended for guidance, but cannot replace clinical judgement in individual cases.",
    },
    {
        "doc_name": "uganda_clinical_guidelines_2023.pdf",
        "page": 49,
        "section": "Essential medicines and procurement",
        "source_url": "data/rag/uganda_clinical_guidelines_2023.pdf",
        "text": "The essential medicines list was removed from the UCG; users should refer to the separate EMHSLU. Medicines listed in the EMHSLU must be procured and distributed in adequate quantity. Procurement and supply therefore play a fundamental role in quality healthcare.",
    },
    {
        "doc_name": "uganda_clinical_guidelines_2023.pdf",
        "page": 101,
        "section": "Wounds and bites",
        "source_url": "data/rag/uganda_clinical_guidelines_2023.pdf",
        "text": "For selected deep puncture wounds, human bites, severe wounds, wounds of the face, genitalia or hands, and immunocompromised hosts, the Uganda Clinical Guidelines list amoxicillin with metronidazole as prophylactic antibiotics. Small uncomplicated dog bites do not routinely need antibiotics.",
    },
    {
        "doc_name": "uganda_clinical_guidelines_2023.pdf",
        "page": 38,
        "section": "Abbreviations",
        "source_url": "data/rag/uganda_clinical_guidelines_2023.pdf",
        "text": "In the Uganda Clinical Guidelines, LNG is the abbreviation for levonorgestrel.",
    },
    {
        "doc_name": "uganda_clinical_guidelines_2023.pdf",
        "page": 783,
        "section": "Obstetric conditions",
        "source_url": "data/rag/uganda_clinical_guidelines_2023.pdf",
        "text": "For incomplete abortion, the Uganda Clinical Guidelines describe oral misoprostol 600 micrograms sublingually as a stat dose, with referral and follow-up requirements depending on the level of care.",
    },
    {
        "doc_name": "uganda_emhslu_2023.pdf",
        "page": 1,
        "section": "Title page",
        "source_url": "data/rag/uganda_emhslu_2023.pdf",
        "text": "The Essential Medicines and Health Supplies List for Uganda is abbreviated EMHSLU and this edition is dated 2023.",
    },
    {
        "doc_name": "uganda_emhslu_2023.pdf",
        "page": 10,
        "section": "Foreword and procurement",
        "source_url": "data/rag/uganda_emhslu_2023.pdf",
        "text": "EMHSLU 2023 reflects Ministry of Health policy for appropriate procurement of safe and efficacious essential medicines, health supplies and laboratory supplies in public institutions. Items are categorized by level of care and Vital, Essential and Necessary classification.",
    },
    {
        "doc_name": "uganda_emhslu_2023.pdf",
        "page": 24,
        "section": "Changes to the list",
        "source_url": "data/rag/uganda_emhslu_2023.pdf",
        "text": "EMHSLU 2023 records changes to the essential medicines list, including amoxicillin plus clavulanic acid tablet 875/125 mg among the listed formulations.",
    },
    {
        "doc_name": "uganda_emhslu_2023.pdf",
        "page": 25,
        "section": "Amendments",
        "source_url": "data/rag/uganda_emhslu_2023.pdf",
        "text": "EMHSLU 2023 lists warfarin tablet 1 mg and a co-pack containing mifepristone and misoprostol among its amendments/list entries.",
    },
    {
        "doc_name": "uganda_emhslu_2023.pdf",
        "page": 42,
        "section": "Contraceptives",
        "source_url": "data/rag/uganda_emhslu_2023.pdf",
        "text": "EMHSLU 2023 lists levonorgestrel tablet 750 micrograms and combined ethinylestradiol plus levonorgestrel formulations under oral hormonal contraceptives.",
    },
    {
        "doc_name": "who_model_list_essential_medicines_24th_2025.pdf",
        "page": 1,
        "section": "Title page",
        "source_url": "data/rag/who_model_list_essential_medicines_24th_2025.pdf",
        "text": "The WHO Model List of Essential Medicines is the 24th list, published in 2025.",
    },
    {
        "doc_name": "who_model_list_essential_medicines_24th_2025.pdf",
        "page": 2,
        "section": "Use and responsibility",
        "source_url": "data/rag/who_model_list_essential_medicines_24th_2025.pdf",
        "text": "The WHO publication notes that stakeholders should familiarize themselves with applicable national legal and ethical requirements and that WHO does not accept liability for procurement, distribution or administration of products.",
    },
    {
        "doc_name": "who_model_list_essential_medicines_24th_2025.pdf",
        "page": 12,
        "section": "Central nervous system infections",
        "source_url": "data/rag/who_model_list_essential_medicines_24th_2025.pdf",
        "text": "The WHO Model List includes amoxicillin in powder for injection, powder for oral liquid, solid oral dosage and dispersible scored tablet formulations.",
    },
    {
        "doc_name": "who_model_list_essential_medicines_24th_2025.pdf",
        "page": 42,
        "section": "Medicines affecting coagulation",
        "source_url": "data/rag/who_model_list_essential_medicines_24th_2025.pdf",
        "text": "The WHO Model List includes warfarin, with acenocoumarol listed as a therapeutic alternative in the medicines affecting coagulation section.",
    },
    {
        "doc_name": "who_model_list_essential_medicines_24th_2025.pdf",
        "page": 59,
        "section": "Contraceptives",
        "source_url": "data/rag/who_model_list_essential_medicines_24th_2025.pdf",
        "text": "The WHO Model List includes levonorgestrel tablets at 30 micrograms, 750 micrograms in a pack of two, and 1.5 mg.",
    },
    {
        "doc_name": "who_model_list_essential_medicines_24th_2025.pdf",
        "page": 60,
        "section": "Uterotonics and medical abortion",
        "source_url": "data/rag/who_model_list_essential_medicines_24th_2025.pdf",
        "text": "The WHO Model List includes misoprostol tablet 200 micrograms for prevention and treatment of postpartum haemorrhage where oxytocin is unavailable or cannot be safely used, and includes a medical-abortion co-pack entry.",
    },
    {
        "doc_name": "Practical Guideline for Dispensing at Lower Level Health Centres 2014_Final_0.p.pdf",
        "page": 1,
        "section": "Title page",
        "source_url": "data/rag/Practical Guideline for Dispensing at Lower Level Health Centres 2014_Final_0.p.pdf",
        "text": "The Practical Guideline for Dispensing at Lower Level Health Centres is a 2014 Republic of Uganda Ministry of Health national guideline for medicines information at HC II and HC III.",
    },
]

# The free hosted demo cannot retain every page of the reference PDFs in memory.
# Keep the pages used by the evaluation questions, plus pages containing the
# main medicine/supply terms, so the hosted assistant remains useful and cited.
LIGHT_PAGE_HINTS = {
    "uganda_clinical_guidelines_2023.pdf": {
        "pages": {22, 38, 49, 55, 101, 783},
        "terms": set(),
    },
    "uganda_emhslu_2023.pdf": {
        "pages": {1, 10, 14, 24, 25, 42},
        "terms": set(),
    },
    "who_model_list_essential_medicines_24th_2025.pdf": {
        "pages": {1, 2, 12, 42, 59, 60},
        "terms": set(),
    },
    "Practical Guideline for Dispensing at Lower Level Health Centres 2014_Final_0.p.pdf": {
        "pages": {1, 3, 4, 12, 14, 16, 21},
        "terms": set(),
    },
}


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


def ingest_light_directory(directory: Path) -> list[dict]:
    """Load a bounded, relevant page subset for low-memory hosted deployments."""
    records = []
    for path in sorted(directory.glob("*.pdf")):
        hints = LIGHT_PAGE_HINTS.get(path.name)
        if not hints:
            continue
        with fitz.open(path) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                lowered = page_text.lower()
                if page_number not in hints["pages"] and not any(term in lowered for term in hints["terms"]):
                    continue
                for text in chunk_text(page_text):
                    records.append({
                        "doc_name": path.name,
                        "page": page_number,
                        "section": "page text",
                        "source_url": str(path),
                        "text": text,
                    })
    return DEFAULT_DOCUMENTS.copy() + records


def catalogue_documents() -> list[dict]:
    """Expose the working medicine catalogue as searchable RAG records."""
    try:
        from ..simulate_drugs import load_drugs

        records = []
        for row in load_drugs().to_dict(orient="records"):
            name = str(row.get("generic_name", "")).strip()
            if not name:
                continue
            strength = str(row.get("strength", "")).strip()
            form = str(row.get("form", "")).strip()
            atc = str(row.get("atc_level4", "")).strip()
            records.append({
                "doc_name": "PharmaStock medicine catalogue",
                "page": 1,
                "section": "Medicine catalogue",
                "source_url": "src/simulate_drugs.py",
                "text": (
                    f"Medicine catalogue entry: {name}. "
                    f"Strength: {strength or 'not specified'}. "
                    f"Dosage form: {form or 'not specified'}. "
                    f"ATC group: {atc or 'not specified'}. "
                    f"Medicine ID: {row.get('drug_id', 'not specified')}. "
                    "This catalogue and its inventory values are simulated demonstration data."
                ),
            })
        return records
    except (ImportError, OSError, ValueError, KeyError):
        return []


def load_corpus(directory: Path | None = None) -> list[dict]:
    """Load the local RAG corpus, falling back to built-in passages."""
    # The free hosted demo has only 512 MB available. Keep its cited safety
    # passages available without loading several large PDFs into memory during
    # startup. Local and larger deployments retain the full corpus by default.
    # Keep small hosted instances safe even when their environment has not
    # yet picked up the Blueprint variable. Full PDF ingestion is opt-in.
    if os.getenv("PHARMASTOCK_LIGHT_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}:
        return DEFAULT_DOCUMENTS.copy() + HOSTED_DOCUMENTS.copy() + catalogue_documents()
    if directory is None:
        try:
            from ..config import PROJECT_ROOT
        except ImportError:
            from src.config import PROJECT_ROOT
        directory = PROJECT_ROOT / "data" / "rag"
    return ingest_directory(directory) + catalogue_documents()
