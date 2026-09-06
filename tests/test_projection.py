from kag_grounded_kv3.models import SearchHit
from kag_grounded_kv3.projection import accepted_route_scores, normalized_scores
from kag_grounded_kv3.text import question_stem_only


def hit(identifier: str, score: float) -> SearchHit:
    return SearchHit(id=identifier, view="source", score=score, source_value_ids=(identifier,))


def test_minmax_normalization() -> None:
    assert normalized_scores([hit("a", 0.9), hit("b", 0.8)]) == {"a": 1.0, "b": 0.0}


def test_full_and_stem_use_max_not_sum() -> None:
    full = [hit("a", 0.9), hit("b", 0.8)]
    stem = [hit("a", 0.95), hit("c", 0.7)]
    scores, channels, _items = accepted_route_scores(full, stem)

    assert scores["a"] == 1.0
    assert scores["a"] <= 1.0
    assert channels["a"] == {"full"}
    assert "stem" in channels["c"]


def test_stem_route_is_extracted_from_multiple_choice_prompt() -> None:
    question = "更新後に必要な処理は何ですか。\n選択肢: 1. 放置 2. 無効化"
    assert question_stem_only(question) == "更新後に必要な処理は何ですか。"
