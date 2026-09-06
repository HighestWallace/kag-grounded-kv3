"""Data contracts shared by the retriever and its storage adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchHit:
    """One result from a single retrieval view."""

    id: str
    view: str
    score: float
    content: str = ""
    source_value_ids: tuple[str, ...] = ()
    source_quotes: tuple[str, ...] = ()
    path_id: str = ""


@dataclass(frozen=True)
class SourceValue:
    """An original source chunk that is safe to pass to a solver."""

    id: str
    content: str
    name: str = ""
    chapter: str = ""


@dataclass(frozen=True)
class PathHop:
    predicate: str
    source_quote: str


@dataclass(frozen=True)
class PathRecord:
    id: str
    anchor_entity: str
    target_entity: str
    source_value_ids: tuple[str, ...]
    hops: tuple[PathHop, ...]


@dataclass
class ScoreProfile:
    """Projected retrieval signals for one source value."""

    id: str
    direct: float = 0.0
    sentence: float = 0.0
    fact: float = 0.0
    path: float = 0.0
    key_ids: set[str] = field(default_factory=set)
    channels: set[str] = field(default_factory=set)
    source_quotes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class RetrievedChunk:
    """A ranked source value returned by the public API."""

    id: str
    content: str
    name: str
    chapter: str
    score: float
    rank: int
    component_scores: dict[str, float]
    key_ids: tuple[str, ...]
    channels: tuple[str, ...]
    source_quotes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResult:
    """Source-only retrieval output plus an inspectable decision trace."""

    query: str
    chunks: tuple[RetrievedChunk, ...]
    audit: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "audit": self.audit,
        }
