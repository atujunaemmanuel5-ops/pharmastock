"""Cited extractive assistant with safe scope and not-found behavior."""

from __future__ import annotations

from .retrieve import retrieve

OUT_OF_SCOPE = ("diagnose", "self-medicate", "dosage for myself", "evade prescription", "how to abort")
REFERENCE_TERMS = ("drug", "medicine", "pharmacy", "prescription", "expiry", "interaction", "stock", "reorder", "dispens", "guideline", "health", "essential", "procurement", "treatment", "amoxicillin", "warfarin", "misoprostol")


def answer_question(question: str, documents=None) -> dict:
    question = (question or "").strip()
    lowered = question.lower()
    if not question:
        return {"answer": "Ask a question about stock, dispensing, expiry, or the safety rules.", "citations": [], "found": False}
    if any(phrase in lowered for phrase in OUT_OF_SCOPE):
        return {"answer": "I cannot provide personal treatment instructions or help bypass a prescription requirement. Ask a licensed dispenser or clinician.", "citations": [], "found": False, "refused": True}
    if not any(term in lowered for term in REFERENCE_TERMS):
        return {"answer": "Not found in the PharmaStock reference documents.", "citations": [], "found": False}
    hits = retrieve(question, documents=documents, limit=6)
    if not hits:
        return {"answer": "Not found in the PharmaStock reference documents.", "citations": [], "found": False}
    unique_hits = []
    seen_pages = set()
    for hit in hits:
        key = (hit["doc_name"], hit["page"])
        if key not in seen_pages:
            seen_pages.add(key)
            unique_hits.append(hit)
    citations = [{"doc_name": hit["doc_name"], "document": hit["doc_name"], "page": hit["page"], "section": hit["section"], "source_url": hit["source_url"]} for hit in unique_hits[:4]]
    answer = " ".join(hit["text"] for hit in unique_hits[:2])
    return {"answer": answer, "citations": citations, "found": True, "is_extractively_generated": True}
