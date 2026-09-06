from kag_grounded_kv3 import ConditionalPathRetriever, RetrieverConfig
from kag_grounded_kv3.adapters.in_memory import load_fixture


def test_synthetic_demo_returns_only_source_values() -> None:
    index, store, questions = load_fixture()
    result = ConditionalPathRetriever(index, store).retrieve(questions[0]["question"])

    assert result.chunks
    assert all(chunk.id.startswith("SRC_") for chunk in result.chunks)
    assert all(not chunk.id.startswith(("FACT_", "SENT_", "KVP_")) for chunk in result.chunks)
    assert result.audit["candidate"] == "kv_conditional_path"
    assert result.audit["solver_output_policy"] == "source_value_only"


def test_conditional_path_signal_reaches_grounded_values() -> None:
    index, store, questions = load_fixture()
    result = ConditionalPathRetriever(index, store).retrieve(questions[0]["question"])
    by_id = {chunk.id: chunk for chunk in result.chunks}

    assert by_id["SRC_002"].component_scores["path"] > 0
    assert by_id["SRC_003"].component_scores["path"] > 0


def test_public_weights_match_final_candidate() -> None:
    config = RetrieverConfig()
    assert config.direct_weight == 0.64
    assert config.sentence_weight == 0.16
    assert config.fact_weight == 0.10
    assert config.path_weight == 0.10
    assert config.top_k == 8
    assert config.source_overfetch == 32
    assert config.key_overfetch == 16


def test_empty_query_is_rejected() -> None:
    index, store, _questions = load_fixture()
    retriever = ConditionalPathRetriever(index, store)

    try:
        retriever.retrieve("  ")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty query should fail")


def test_retriever_configuration_contains_no_evaluation_labels() -> None:
    text = repr(RetrieverConfig()).lower()
    forbidden = ("official_answer", "expected_terms", "evidence_terms", "lightrag")
    assert not any(token in text for token in forbidden)
