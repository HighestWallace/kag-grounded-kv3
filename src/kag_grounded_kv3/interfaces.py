"""Minimal storage interfaces used by the standalone retriever."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from .models import PathRecord, SearchHit, SourceValue


class MultiViewIndex(Protocol):
    """Searches source, sentence, fact, and path views."""

    def search(self, view: str, query: str, limit: int) -> Sequence[SearchHit]: ...


class GraphStore(Protocol):
    """Resolves retrieval keys back to grounded source values."""

    def source_ids(self) -> Iterable[str]: ...

    def get_source(self, source_id: str) -> SourceValue: ...

    def get_path(self, path_id: str) -> PathRecord | None: ...
