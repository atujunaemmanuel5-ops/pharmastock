"""Optional grounded answer generation for the reference assistant.

The LLM is deliberately optional. If it is disabled, unavailable, or returns
an invalid response, the caller keeps the existing cited extractive answer.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


class LLMError(RuntimeError):
    """Raised when an optional answer provider cannot produce a safe response."""


def provider_name() -> str:
    return os.getenv("PHARMASTOCK_LLM_PROVIDER", "none").strip().lower()


def _model(provider: str) -> str:
    configured = os.getenv("PHARMASTOCK_LLM_MODEL", "").strip()
    if configured:
        return configured
    return "gemini-2.0-flash" if provider == "gemini" else "openrouter/free"


def _api_key(provider: str) -> str:
    provider_key = os.getenv("GEMINI_API_KEY" if provider == "gemini" else "OPENROUTER_API_KEY", "")
    return (provider_key or os.getenv("PHARMASTOCK_LLM_API_KEY", "")).strip()


def _system_prompt() -> str:
    return (
        "You are PharmaStock's grounded pharmacy-reference assistant. "
        "Use only the supplied evidence. Do not diagnose, prescribe, recommend "
        "personal treatment or dosage, verify prescriptions, or authorize a sale. "
        "If the evidence does not answer the question, return found=false. "
        "Return JSON only with exactly: answer (string), found (boolean), "
        "citation_ids (array of strings). Cite only supplied IDs such as S1."
    )


def _prompt(question: str, hits: list[dict]) -> str:
    evidence = []
    for index, hit in enumerate(hits, start=1):
        evidence.append(
            f"[S{index}] {hit.get('doc_name', 'Unknown document')} page {hit.get('page', '?')}\n"
            f"{hit.get('text', '')[:6000]}"
        )
    return f"Question: {question}\n\nEvidence:\n" + "\n\n".join(evidence)


def _request(provider: str, question: str, hits: list[dict]) -> str:
    key = _api_key(provider)
    if not key:
        raise LLMError(f"No API key configured for {provider}")
    model = _model(provider)
    prompt = _prompt(question, hits)
    timeout = float(os.getenv("PHARMASTOCK_LLM_TIMEOUT", "20"))

    if provider == "gemini":
        url = os.getenv(
            "PHARMASTOCK_GEMINI_API_URL",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        )
        response = requests.post(
            url,
            params={"key": key},
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": _system_prompt()}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500, "responseMimeType": "application/json"},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        candidates = response.json().get("candidates", [])
        try:
            return candidates[0]["content"]["parts"][0]["text"]
        except (IndexError, KeyError, TypeError) as exc:
            raise LLMError("Gemini returned no answer") from exc

    if provider == "openrouter":
        url = os.getenv("PHARMASTOCK_OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("PHARMASTOCK_PUBLIC_URL", "https://pharmastock.local"),
                "X-Title": "PharmaStock AI",
            },
            json={
                "model": model,
                "temperature": 0.1,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        choices = response.json().get("choices", [])
        try:
            content = choices[0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as exc:
            raise LLMError("OpenRouter returned no answer") from exc
        if isinstance(content, list):
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        return str(content)

    raise LLMError(f"Unsupported LLM provider: {provider}")


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError("LLM response was not valid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
        raise LLMError("LLM response did not contain an answer")
    citation_ids = payload.get("citation_ids", [])
    if not isinstance(citation_ids, list) or not all(isinstance(value, str) for value in citation_ids):
        raise LLMError("LLM response contained invalid citation IDs")
    return {
        "answer": payload["answer"].strip(),
        "found": bool(payload.get("found", True)),
        "citation_ids": citation_ids,
    }


def generate_answer(question: str, hits: list[dict]) -> dict[str, Any] | None:
    """Generate a grounded answer, or return ``None`` when LLM mode is disabled."""
    provider = provider_name()
    if provider in {"", "none", "off", "disabled"}:
        return None
    raw = _request(provider, question, hits)
    return _parse_json(raw)
