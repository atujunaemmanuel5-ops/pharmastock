"""Grounded reference assistant with hybrid retrieval and safe fallback."""

from __future__ import annotations

import logging
from functools import lru_cache

from .llm import LLMError, generate_answer, provider_name
from .retrieve import retrieve


logger = logging.getLogger(__name__)

OUT_OF_SCOPE = ("diagnose", "self-medicate", "dosage for myself", "evade prescription", "how to abort")
REFERENCE_TERMS = (
    "drug", "medicine", "pharmacy", "prescription", "expiry", "interaction", "stock", "reorder",
    "dispens", "guideline", "ucg", "emhslu", "who", "health", "essential", "procurement",
    "treatment", "amoxicillin", "warfarin", "levonorgestrel", "misoprostol",
)
NOT_FOUND = "Not found in the PharmaStock reference documents or medicine catalogue."


@lru_cache(maxsize=1)
def _catalogue_terms() -> tuple[str, ...]:
    try:
        from ..simulate_drugs import load_drugs

        return tuple(sorted({str(name).strip().lower() for name in load_drugs()["generic_name"] if str(name).strip()}))
    except (ImportError, OSError, ValueError, KeyError):
        return ()


def _citations(hits: list[dict], selected_ids: list[str] | None = None) -> list[dict]:
    selected = set(selected_ids or [])
    unique_hits = []
    seen_pages = set()
    for index, hit in enumerate(hits, start=1):
        if selected and f"S{index}" not in selected:
            continue
        key = (hit.get("doc_name"), hit.get("page"))
        if key not in seen_pages:
            seen_pages.add(key)
            unique_hits.append(hit)
    return [
        {
            "doc_name": hit["doc_name"],
            "document": hit["doc_name"],
            "page": hit["page"],
            "section": hit["section"],
            "source_url": hit["source_url"],
        }
        for hit in unique_hits[:4]
    ]


def _extractive_answer(hits: list[dict]) -> tuple[str, list[dict]]:
    citations = _citations(hits)
    answer = " ".join(hit["text"] for hit in hits[:2])
    return answer, citations


def answer_question(question: str, documents=None) -> dict:
    question = (question or "").strip()
    lowered = question.lower()
    if not question:
        return {"answer": "Ask a question about stock, dispensing, expiry, or the safety rules.", "citations": [], "found": False}
    if any(phrase in lowered for phrase in OUT_OF_SCOPE):
        return {
            "answer": "I cannot provide personal treatment instructions or help bypass a prescription requirement. Ask a licensed dispenser or clinician.",
            "citations": [],
            "found": False,
            "refused": True,
            "answer_mode": "safety_refusal",
        }
    is_catalogue_query = any(term in lowered for term in _catalogue_terms())
    if not any(term in lowered for term in REFERENCE_TERMS) and not is_catalogue_query:
        return {"answer": NOT_FOUND, "citations": [], "found": False, "answer_mode": "not_found"}

    hits = retrieve(question, documents=documents, limit=8)
    if not hits:
        return {"answer": NOT_FOUND, "citations": [], "found": False, "answer_mode": "not_found"}

    retrieval_mode = hits[0].get("retrieval_mode", "lexical")
    if provider_name() not in {"", "none", "off", "disabled"}:
        try:
            generated = generate_answer(question, hits[:6])
            if generated:
                allowed_ids = {f"S{index}" for index in range(1, min(6, len(hits)) + 1)}
                citation_ids = [value for value in generated.get("citation_ids", []) if value in allowed_ids]
                citations = _citations(hits[:6], citation_ids)
                if generated["found"] and generated["answer"] and citations:
                    return {
                        "answer": generated["answer"],
                        "citations": citations,
                        "found": True,
                        "answer_mode": "llm",
                        "retrieval_mode": retrieval_mode,
                    }
                if not generated["found"]:
                    return {
                        "answer": generated["answer"] or NOT_FOUND,
                        "citations": citations,
                        "found": False,
                        "answer_mode": "llm",
                        "retrieval_mode": retrieval_mode,
                    }
        except LLMError as exc:
            logger.warning("LLM answer unavailable; using extractive fallback: %s", exc)
        except Exception:
            logger.exception("Unexpected LLM answer failure; using extractive fallback")

    answer, citations = _extractive_answer(hits)
    return {
        "answer": answer,
        "citations": citations,
        "found": True,
        "answer_mode": "extractive",
        "retrieval_mode": retrieval_mode,
        "llm_fallback": provider_name() not in {"", "none", "off", "disabled"},
    }
