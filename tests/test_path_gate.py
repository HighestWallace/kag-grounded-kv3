from kag_grounded_kv3.adapters.in_memory import InMemoryGraphStore
from kag_grounded_kv3.models import PathHop, PathRecord, SearchHit, SourceValue
from kag_grounded_kv3.path_gate import path_allowed


def store_with_path(*, quote: str = "更新時にキャッシュを無効化する") -> InMemoryGraphStore:
    sources = [
        SourceValue(id="s1", content="更新時にキャッシュを無効化する"),
        SourceValue(id="s2", content="ミス時に再生成する"),
    ]
    paths = [
        PathRecord(
            id="p1",
            anchor_entity="メタデータ",
            target_entity="キャッシュ",
            source_value_ids=("s1", "s2"),
            hops=(PathHop(predicate="無効化", source_quote=quote),),
        )
    ]
    return InMemoryGraphStore(sources, paths)


def path_hit(score: float = 0.8) -> SearchHit:
    return SearchHit(
        id="KVP_p1",
        view="path",
        score=score,
        path_id="p1",
        source_value_ids=("s1", "s2"),
    )


def test_path_is_allowed_with_provenance_and_query_endpoint() -> None:
    assert path_allowed(
        path_hit(),
        "メタデータ更新時にキャッシュをどう扱うか",
        0.75,
        store_with_path(),
    )


def test_path_is_rejected_below_source_cutoff() -> None:
    assert not path_allowed(
        path_hit(0.7),
        "メタデータ更新時にキャッシュをどう扱うか",
        0.75,
        store_with_path(),
    )


def test_path_is_rejected_without_source_quote() -> None:
    assert not path_allowed(
        path_hit(),
        "メタデータ更新時にキャッシュをどう扱うか",
        0.75,
        store_with_path(quote=""),
    )
