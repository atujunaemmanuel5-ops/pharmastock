"""Hybrid lexical and semantic retrieval with a safe lexical fallback.

The hosted API must remain usable without an embedding service. Lexical
retrieval is therefore always available, while semantic retrieval is enabled
when a precomputed embedding index and an OpenAI-compatible embedding endpoint
are configured.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import requests

from .ingest import load_corpus


logger = logging.getLogger(__name__)

STOPWORDS = {
    "what", "does", "the", "say", "about", "where", "is", "are", "how", "can",
    "this", "that", "for", "and", "from", "with", "into", "list", "listed",
    "please", "tell", "me", "you", "your", "our", "their",
}


def _terms(text: str) -> list[str]:
    """Tokenize text while retaining repeated terms for BM25 term frequency."""
    return [term for term in re.findall(r"[a-z0-9]+", text.lower()) if len(term) > 2 and term not in STOPWORDS]


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


def document_key(document: dict) -> str:
    """Return a stable key used to match chunks to precomputed vectors."""
    raw = "\x1f".join(
        str(document.get(field, ""))
        for field in ("doc_name", "page", "section", "source_url", "text")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EmbeddingClient:
    """Small OpenAI-compatible embedding client using requests."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None, model: str | None = None):
        self.provider = os.getenv("PHARMASTOCK_EMBEDDING_PROVIDER", "openai").strip().lower()
        self.model = (model or os.getenv("PHARMASTOCK_EMBEDDING_MODEL", "")).strip()
        if self.provider == "gemini":
            self.model = self.model or "gemini-embedding-001"
            self.endpoint = (endpoint or os.getenv(
                "PHARMASTOCK_EMBEDDING_API_URL",
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
            )).strip()
            self.api_key = (api_key or os.getenv("PHARMASTOCK_EMBEDDING_API_KEY", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("PHARMASTOCK_LLM_API_KEY", "")).strip()
        else:
            self.endpoint = (endpoint or os.getenv("PHARMASTOCK_EMBEDDING_API_URL", "")).strip()
            self.api_key = (api_key or os.getenv("PHARMASTOCK_EMBEDDING_API_KEY", "")).strip()

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.model)

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        if not self.configured:
            return []
        values = list(texts)
        if not values:
            return []
        if self.provider == "gemini":
            vectors = []
            for value in values:
                response = requests.post(
                    self.endpoint,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json={
                        "taskType": "SEMANTIC_SIMILARITY",
                        "content": {"parts": [{"text": value}]},
                        "outputDimensionality": int(os.getenv("PHARMASTOCK_EMBEDDING_DIMENSIONS", "768")),
                    },
                    timeout=float(os.getenv("PHARMASTOCK_EMBEDDING_TIMEOUT", "20")),
                )
                response.raise_for_status()
                vector = response.json().get("embedding", {}).get("values", [])
                if not vector:
                    raise ValueError("Gemini returned an empty embedding")
                vectors.append(_normalise_vector(vector))
            return vectors
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "input": values},
            timeout=float(os.getenv("PHARMASTOCK_EMBEDDING_TIMEOUT", "20")),
        )
        response.raise_for_status()
        payload = response.json()
        rows = sorted(payload.get("data", []), key=lambda row: row.get("index", 0))
        vectors = [row.get("embedding", []) for row in rows]
        if len(vectors) != len(values) or not all(vectors):
            raise ValueError("Embedding provider returned an incomplete response")
        return [_normalise_vector(vector) for vector in vectors]


def _normalise_vector(vector: Iterable[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values] if norm else values


@lru_cache(maxsize=1)
def embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


def _embedding_path() -> Path:
    configured = os.getenv("PHARMASTOCK_RAG_EMBEDDINGS_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "processed" / "rag_embeddings.json"


@lru_cache(maxsize=1)
def _stored_embeddings() -> dict[str, list[float]]:
    path = _embedding_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = payload.get("embeddings", {})
        return {key: _normalise_vector(vector) for key, vector in values.items() if vector}
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("Ignoring invalid RAG embedding index %s: %s", path, exc)
        return {}


def _document_vectors(documents: list[dict]) -> dict[int, list[float]]:
    stored = _stored_embeddings()
    result = {}
    for index, document in enumerate(documents):
        vector = document.get("embedding") or stored.get(document_key(document))
        if vector:
            result[index] = _normalise_vector(vector)
    return result


def _bm25_scores(query_terms: list[str], documents: list[dict]) -> dict[int, float]:
    tokenized = [
        _terms(document.get("text", "") + " " + document.get("section", "") + " " + document.get("doc_name", ""))
        for document in documents
    ]
    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / max(1, len(lengths))
    document_frequency = {term: sum(term in tokens for tokens in tokenized) for term in set(query_terms)}
    scores: dict[int, float] = {}
    k1 = 1.2
    b = 0.75
    for index, tokens in enumerate(tokenized):
        if not tokens:
            continue
        term_frequency = {term: tokens.count(term) for term in set(tokens)}
        score = 0.0
        for term in query_terms:
            frequency = term_frequency.get(term, 0)
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + k1 * (1 - b + b * len(tokens) / max(1, average_length))
            score += inverse_frequency * (frequency * (k1 + 1)) / denominator
        if score:
            scores[index] = score
    return scores


def _semantic_scores(query: str, vectors: dict[int, list[float]]) -> dict[int, float]:
    if not vectors:
        return {}
    try:
        query_vectors = embedding_client().embed([query])
        if not query_vectors:
            return {}
        query_vector = query_vectors[0]
        return {
            index: sum(left * right for left, right in zip(query_vector, vector))
            for index, vector in vectors.items()
            if len(query_vector) == len(vector)
        }
    except Exception as exc:  # semantic search must never take down /ask
        logger.warning("Semantic RAG retrieval unavailable; using lexical results: %s", exc)
        return {}


def _ranked_indices(scores: dict[int, float]) -> list[int]:
    return [index for index, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)]


def retrieve(query: str, documents=None, limit: int = 3) -> list[dict]:
    """Retrieve chunks using BM25 plus optional dense-vector RRF fusion."""
    corpus = list(cached_corpus() if documents is None else documents)
    if not corpus or limit < 1:
        return []

    query_terms = _terms(query)
    lexical_scores = _bm25_scores(query_terms, corpus)
    vectors = _document_vectors(corpus)
    semantic_scores = _semantic_scores(query, vectors)
    lexical_rank = _ranked_indices(lexical_scores)
    semantic_rank = _ranked_indices(semantic_scores)
    mode = "hybrid" if semantic_rank else "lexical"

    rrf_k = int(os.getenv("PHARMASTOCK_RAG_RRF_K", "60"))
    lexical_weight = float(os.getenv("PHARMASTOCK_RAG_LEXICAL_WEIGHT", "1.0"))
    semantic_weight = float(os.getenv("PHARMASTOCK_RAG_SEMANTIC_WEIGHT", "1.0"))
    fused: dict[int, float] = {}
    for rank, index in enumerate(lexical_rank, start=1):
        fused[index] = fused.get(index, 0.0) + lexical_weight / (rrf_k + rank)
    for rank, index in enumerate(semantic_rank, start=1):
        fused[index] = fused.get(index, 0.0) + semantic_weight / (rrf_k + rank)

    preferred_document = _preferred_document(query)
    for index, document in enumerate(corpus):
        name = document.get("doc_name", "").lower()
        if preferred_document and preferred_document in name:
            fused[index] = fused.get(index, 0.0) + 0.05
        if "practical guideline" in name and int(document.get("page", 0)) <= 15:
            fused[index] = fused.get(index, 0.0) * 0.35

    ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    results = []
    for index, score in ranked[:limit]:
        document = corpus[index]
        results.append(document | {
            "score": score,
            "lexical_score": lexical_scores.get(index, 0.0),
            "semantic_score": semantic_scores.get(index, 0.0),
            "retrieval_mode": mode,
        })
    return results


@lru_cache(maxsize=1)
def cached_corpus() -> tuple[dict, ...]:
    return tuple(load_corpus())


def build_embedding_index(documents: list[dict] | None = None, output: str | Path | None = None) -> Path:
    """Create a reusable vector index using the configured embedding endpoint."""
    corpus = list(cached_corpus() if documents is None else documents)
    client = embedding_client()
    if not client.configured:
        raise RuntimeError(
            "Set PHARMASTOCK_EMBEDDING_API_URL, PHARMASTOCK_EMBEDDING_API_KEY, "
            "and PHARMASTOCK_EMBEDDING_MODEL before building the index."
        )
    destination = Path(output) if output else _embedding_path()
    batch_size = max(1, int(os.getenv("PHARMASTOCK_EMBEDDING_BATCH_SIZE", "32")))
    vectors: dict[str, list[float]] = {}
    for start in range(0, len(corpus), batch_size):
        batch = corpus[start:start + batch_size]
        for document, vector in zip(batch, client.embed([item.get("text", "") for item in batch])):
            vectors[document_key(document)] = vector
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"model": client.model, "embeddings": vectors}), encoding="utf-8")
    _stored_embeddings.cache_clear()
    return destination


if __name__ == "__main__":
    path = build_embedding_index()
    print(f"Wrote RAG embedding index to {path}")
