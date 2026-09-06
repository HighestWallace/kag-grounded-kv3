from kag_grounded_kv3.grounding import (
    GroundedFact,
    build_two_hop_paths,
    map_quote_to_sources,
    validate_fact_provenance,
)
from kag_grounded_kv3.models import SourceValue

SOURCES = [
    SourceValue(
        id="s1",
        chapter="c1",
        content="画像メタデータを更新すると、キャッシュを無効化する。",
    ),
    SourceValue(
        id="s2",
        chapter="c1",
        content="キャッシュミス時には新しいサムネイルを生成する。",
    ),
]


def test_exact_quote_projects_to_original_source() -> None:
    assert map_quote_to_sources("キャッシュを無効化する。", SOURCES, chapter="c1") == ("s1",)


def test_fact_requires_entities_and_quote_in_source() -> None:
    fact = GroundedFact(
        id="f1",
        subject="画像メタデータ",
        predicate="INVALIDATES",
        object="キャッシュ",
        source_quote="画像メタデータを更新すると、キャッシュを無効化する。",
        source_value_ids=(),
        chapter="c1",
    )
    checked = validate_fact_provenance(fact, SOURCES)
    assert checked is not None
    assert checked.source_value_ids == ("s1",)
    assert checked.subject_id.startswith("E_")


def test_fact_without_grounded_object_is_rejected() -> None:
    fact = GroundedFact(
        id="f_bad",
        subject="画像メタデータ",
        predicate="INVALIDATES",
        object="CDN",
        source_quote="画像メタデータを更新すると、キャッシュを無効化する。",
        source_value_ids=(),
        chapter="c1",
    )
    assert validate_fact_provenance(fact, SOURCES) is None


def test_two_hop_path_requires_two_grounded_sources() -> None:
    facts = [
        GroundedFact(
            id="f1",
            subject="画像メタデータ",
            predicate="INVALIDATES",
            object="キャッシュ",
            source_quote=SOURCES[0].content,
            source_value_ids=("s1",),
        ),
        GroundedFact(
            id="f2",
            subject="キャッシュ",
            predicate="MISSES_TO_GENERATE",
            object="サムネイル",
            source_quote=SOURCES[1].content,
            source_value_ids=("s2",),
        ),
    ]
    paths = build_two_hop_paths(facts)
    assert len(paths) == 1
    assert paths[0].source_value_ids == ("s1", "s2")
    assert len(paths[0].hops) == 2
