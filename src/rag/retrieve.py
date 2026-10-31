"""Dependency-free lexical retrieval used by the local/API runtime."""

from __future__ import annotations

import re
from functools import lru_cache
import math

from .ingest import load_corpus


STOPWORDS = {
    "what", "does", "the", "say", "about", "where", "is", "are", "how", "can",
    "the", "this", "that", "for", "and", "from", "with", "into", "list", "listed",
}


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", text.lower()) if len(term) > 2 and term not in STOPWORDS}


def _preferred_document(query: str) -> str | None:
    lowered = query.lower()
    if "emhslu" in lowered:
        return "emhslu"
    if "essential medicines list" in lowered and "uganda" in lowered:
        return "emhslu"
    if "who" in lowered or "model list" in lowered or "essential medicines list" in lowered:
        return "who_model"
    if "practical guideline" in lowered or "lower level" in lowered or "dispensing guideline" in lowered:
        return "practical guideline"
    if "ucg" in lowered or "clinical guidelines" in lowered or "uganda clinical" in lowered or "uganda guideline" in lowered:
        return "uganda_clinical"
    return None


def retrieve(query: str, documents=None, limit: int = 3) -> list[dict]:
    documents = cached_corpus() if documents is None else documents
    query_terms = _terms(query)
    preferred_document = _preferred_document(query)
    document_terms = [_terms(document["text"] + " " + document.get("section", "") + " " + document.get("doc_name", "")) for document in documents]
    document_frequency = {term: sum(term in terms for terms in document_terms) for term in query_terms}
    scored = []
    for document, doc_terms in zip(documents, document_terms):
        score = sum((1.0 + math.log((len(documents) + 1) / (document_frequency[term] + 1))) for term in query_terms if term in doc_terms)
        if preferred_document and preferred_document in document.get("doc_name", "").lower():
            score += 10.0
        # The added dispensing guideline has a cover, contents and glossary
        # before the useful medicine guidance. Keep title-heavy front matter
        # available for direct page questions, but do not let it outrank the
        # actual guidance for a general dispensing question.
        if "practical guideline" in document.get("doc_name", "").lower() and int(document.get("page", 0)) <= 15:
            score *= 0.35
        if score:
            scored.append((score, document))
    return [document | {"score": score} for score, document in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


@lru_cache(maxsize=1)
def cached_corpus() -> tuple[dict, ...]:
    return tuple(load_corpus())
