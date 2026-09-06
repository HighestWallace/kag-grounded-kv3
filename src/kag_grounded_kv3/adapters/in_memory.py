"""Dependency-free adapter used by the synthetic demo and unit tests."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from ..models import PathHop, PathRecord, SearchHit, SourceValue
from ..text import text_ngrams


@dataclass(frozen=True)
class IndexDocument:
    id: str
    view: str
    content: str
    source_value_ids: tuple[str, ...]
    source_quotes: tuple[str, ...] = ()
    path_id: str = ""


def _cosine_overlap(left: str, right: str) -> float:
    left_terms = text_ngrams(left)
    right_terms = text_ngrams(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / math.sqrt(len(left_terms) * len(right_terms))


class InMemoryIndex:
    """A deterministic character-ngram index for the public mini dataset."""

    def __init__(self, documents: Iterable[IndexDocument]) -> None:
        self._documents: dict[str, list[IndexDocument]] = {}
        for document in documents:
            self._documents.setdefault(document.view, []).append(document)

    def search(self, view: str, query: str, limit: int) -> Sequence[SearchHit]:
        rows = [
            SearchHit(
                id=document.id,
                view=view,
                score=_cosine_overlap(query, document.content),
                content=document.content,
                source_value_ids=document.source_value_ids,
                source_quotes=document.source_quotes,
                path_id=document.path_id,
            )
            for document in self._documents.get(view, [])
        ]
        rows.sort(key=lambda row: (-row.score, row.id))
        return rows[:limit]


class InMemoryGraphStore:
    def __init__(self, sources: Iterable[SourceValue], paths: Iterable[PathRecord]) -> None:
        self._sources = {source.id: source for source in sources}
        self._paths = {path.id: path for path in paths}

    def source_ids(self) -> Iterable[str]:
        return self._sources.keys()

    def get_source(self, source_id: str) -> SourceValue:
        return self._sources[source_id]

    def get_path(self, path_id: str) -> PathRecord | None:
        return self._paths.get(path_id)


def _default_fixture_path() -> Path:
    return Path(str(files("kag_grounded_kv3").joinpath("data/synthetic_ja.json")))


def load_fixture(
    path: str | Path | None = None,
) -> tuple[InMemoryIndex, InMemoryGraphStore, list[dict[str, object]]]:
    fixture_path = Path(path) if path else _default_fixture_path()
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    sources = [
        SourceValue(
            id=row["id"],
            content=row["content"],
            name=row.get("name", ""),
            chapter=row.get("chapter", ""),
        )
        for row in payload["source_values"]
    ]
    paths = [
        PathRecord(
            id=row["id"],
            anchor_entity=row["anchor_entity"],
            target_entity=row["target_entity"],
            source_value_ids=tuple(row["source_value_ids"]),
            hops=tuple(PathHop(**hop) for hop in row["hops"]),
        )
        for row in payload["paths"]
    ]
    documents = [
        IndexDocument(
            id=row["id"],
            view=row["view"],
            content=row["content"],
            source_value_ids=tuple(row["source_value_ids"]),
            source_quotes=tuple(row.get("source_quotes", [])),
            path_id=row.get("path_id", ""),
        )
        for row in payload["documents"]
    ]
    return InMemoryIndex(documents), InMemoryGraphStore(sources, paths), payload["questions"]
