from src.rag.answer import answer_question


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
