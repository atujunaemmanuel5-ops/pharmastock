from src.rag.answer import answer_question
from src.rag import retrieve as retrieve_module
from src.rag.retrieve import retrieve


def test_rag_returns_citations_or_not_found():
    answer = answer_question("What happens to expired stock?")
    assert answer["found"] is True
    assert answer["citations"]
    assert answer["citations"][0]["page"]


def test_rag_does_not_invent_out_of_scope_advice():
    answer = answer_question("How do I diagnose and self-medicate?")
    assert answer["refused"] is True
    assert "cannot" in answer["answer"].lower()


def test_rag_not_found_is_explicit():
    answer = answer_question("What is the weather tomorrow?")
    assert answer["found"] is False
    assert "not found" in answer["answer"].lower()


def test_hybrid_retrieval_fuses_dense_vectors(monkeypatch):
    class FakeEmbeddingClient:
        def embed(self, texts):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(retrieve_module, "embedding_client", lambda: FakeEmbeddingClient())
    documents = [
        {"doc_name": "semantic-a", "page": 1, "section": "", "source_url": "a", "text": "unrelated wording", "embedding": [1.0, 0.0]},
        {"doc_name": "semantic-b", "page": 2, "section": "", "source_url": "b", "text": "different wording", "embedding": [0.0, 1.0]},
    ]
    hits = retrieve("paraphrased request", documents=documents, limit=1)
    assert hits[0]["doc_name"] == "semantic-a"
    assert hits[0]["retrieval_mode"] == "hybrid"
    assert hits[0]["semantic_score"] > 0


def test_llm_answer_keeps_citations(monkeypatch):
    monkeypatch.setenv("PHARMASTOCK_LLM_PROVIDER", "test")
    monkeypatch.setattr(
        "src.rag.answer.generate_answer",
        lambda question, hits: {"answer": "Use the cited guidance.", "found": True, "citation_ids": ["S1"]},
    )
    documents = [{
        "doc_name": "reference.pdf", "page": 4, "section": "Safety", "source_url": "reference.pdf",
        "text": "The guidance explains expiry and safe stock handling.",
    }]
    answer = answer_question("What does the guidance say about expiry?", documents=documents)
    assert answer["answer_mode"] == "llm"
    assert answer["citations"][0]["page"] == 4
