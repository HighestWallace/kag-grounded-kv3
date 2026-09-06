"""Final Grounded KV3 candidate: source projection with gated paths."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .interfaces import GraphStore, MultiViewIndex
from .mmr import select_mmr
from .models import RetrievalResult, RetrievedChunk, ScoreProfile, SearchHit
from .path_gate import path_allowed
from .projection import accepted_route_scores
from .text import normalize, question_stem_only


@dataclass(frozen=True)
class RetrieverConfig:
    top_k: int = 8
    source_overfetch: int = 32
    key_overfetch: int = 16
    candidate_pool_size: int = 48
    full_gate: int = 16
    stem_improvement_margin: float = 0.05
    path_score_margin: float = 0.03
    direct_weight: float = 0.64
    sentence_weight: float = 0.16
    fact_weight: float = 0.10
    path_weight: float = 0.10
    mmr_relevance_weight: float = 0.85
    mmr_redundancy_weight: float = 0.15

    def __post_init__(self) -> None:
        weights = (
            self.direct_weight,
            self.sentence_weight,
            self.fact_weight,
            self.path_weight,
        )
        if self.top_k <= 0 or self.source_overfetch <= 0 or self.key_overfetch <= 0:
            raise ValueError("retrieval limits must be positive")
        if not 0.999 <= sum(weights) <= 1.001:
            raise ValueError("retrieval weights must sum to 1.0")


class ConditionalPathRetriever:
    """Ranks fine-grained keys but returns only original source values."""

    views = ("source", "sentence", "fact", "path")

    def __init__(
        self,
        index: MultiViewIndex,
        graph_store: GraphStore,
        config: RetrieverConfig | None = None,
    ) -> None:
        self.index = index
        self.graph_store = graph_store
        self.config = config or RetrieverConfig()

    def _route_searches(
        self, query: str
    ) -> tuple[dict[str, dict[str, list[SearchHit]]], dict[str, float]]:
        routes = {"full": query}
        stem = question_stem_only(query)
        if normalize(stem) != normalize(query):
            routes["stem"] = stem

        searches: dict[str, dict[str, list[SearchHit]]] = {}
        route_latency: dict[str, float] = {}
        for route_name, route_query in routes.items():
            started = time.perf_counter()
            searches[route_name] = {
                "source": list(
                    self.index.search("source", route_query, self.config.source_overfetch)
                ),
                "sentence": list(
                    self.index.search("sentence", route_query, self.config.key_overfetch)
                ),
                "fact": list(self.index.search("fact", route_query, self.config.key_overfetch)),
                "path": list(self.index.search("path", route_query, self.config.key_overfetch)),
            }
            route_latency[route_name] = time.perf_counter() - started
        return searches, route_latency

    def _project(
        self,
        searches: dict[str, dict[str, list[SearchHit]]],
        query: str,
    ) -> dict[str, ScoreProfile]:
        full = searches.get("full", {})
        stem = searches.get("stem", {})
        profiles = {
            source_id: ScoreProfile(id=source_id) for source_id in self.graph_store.source_ids()
        }

        source_rows = full.get("source", [])
        cutoff_index = min(7, len(source_rows) - 1)
        source_cutoff = float(source_rows[cutoff_index].score) if source_rows else 0.0

        for view in self.views:
            if view not in full:
                continue
            scores, channels, items = accepted_route_scores(
                full.get(view, []),
                stem.get(view, []),
                full_gate=self.config.full_gate,
                improvement_margin=self.config.stem_improvement_margin,
            )
            for item_id, score in scores.items():
                item = items[item_id]
                if view == "path" and not path_allowed(
                    item,
                    query,
                    source_cutoff,
                    self.graph_store,
                    score_margin=self.config.path_score_margin,
                ):
                    continue
                for source_id in item.source_value_ids:
                    profile = profiles.get(source_id)
                    if profile is None:
                        continue
                    target = "direct" if view == "source" else view
                    setattr(profile, target, max(float(getattr(profile, target)), float(score)))
                    profile.key_ids.add(item_id)
                    profile.channels.update(f"{channel}:{view}" for channel in channels[item_id])
                    profile.source_quotes.update(item.source_quotes)
        return profiles

    def retrieve(self, query: str) -> RetrievalResult:
        if not query.strip():
            raise ValueError("query must not be empty")

        started = time.perf_counter()
        searches, route_latency = self._route_searches(query)
        profiles = self._project(searches, query)
        ranked: list[tuple[float, ScoreProfile]] = []
        for profile in profiles.values():
            final_score = (
                self.config.direct_weight * profile.direct
                + self.config.sentence_weight * profile.sentence
                + self.config.fact_weight * profile.fact
                + self.config.path_weight * profile.path
            )
            if final_score > 0:
                ranked.append((final_score, profile))
        ranked.sort(key=lambda row: (-row[0], row[1].id))

        pool = ranked[: max(self.config.candidate_pool_size, self.config.source_overfetch)]
        selected = select_mmr(
            pool,
            top_k=self.config.top_k,
            score=lambda row: row[0],
            content=lambda row: self.graph_store.get_source(row[1].id).content,
            relevance_weight=self.config.mmr_relevance_weight,
            redundancy_weight=self.config.mmr_redundancy_weight,
        )

        chunks: list[RetrievedChunk] = []
        for rank, (final_score, profile) in enumerate(selected, start=1):
            source = self.graph_store.get_source(profile.id)
            chunks.append(
                RetrievedChunk(
                    id=source.id,
                    content=source.content,
                    name=source.name,
                    chapter=source.chapter,
                    score=final_score,
                    rank=rank,
                    component_scores={
                        "direct": profile.direct,
                        "sentence": profile.sentence,
                        "fact": profile.fact,
                        "path": profile.path,
                    },
                    key_ids=tuple(sorted(profile.key_ids)),
                    channels=tuple(sorted(profile.channels)),
                    source_quotes=tuple(sorted(profile.source_quotes)),
                )
            )

        audit = {
            "candidate": "kv_conditional_path",
            "routes": sorted(searches),
            "route_latency_seconds": {key: round(value, 6) for key, value in route_latency.items()},
            "retrieval_latency_seconds": round(time.perf_counter() - started, 6),
            "candidate_pool_count": len(ranked),
            "selected_source_ids": [chunk.id for chunk in chunks],
            "solver_output_policy": "source_value_only",
            "weights": {
                "direct": self.config.direct_weight,
                "sentence": self.config.sentence_weight,
                "fact": self.config.fact_weight,
                "path": self.config.path_weight,
            },
        }
        return RetrievalResult(query=query, chunks=tuple(chunks), audit=audit)
