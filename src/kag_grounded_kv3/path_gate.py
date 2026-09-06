"""Strict provenance and relevance checks for conditional graph paths."""

from __future__ import annotations

from .interfaces import GraphStore
from .models import SearchHit
from .text import compact


def path_allowed(
    item: SearchHit,
    query: str,
    cutoff: float,
    graph_store: GraphStore,
    *,
    score_margin: float = 0.03,
) -> bool:
    if float(item.score) < cutoff:
        return False

    path_id = item.path_id or item.id.removeprefix("KVP_")
    path = graph_store.get_path(path_id)
    if path is None or len(set(path.source_value_ids)) < 2:
        return False
    if not path.hops or any(not hop.source_quote.strip() for hop in path.hops):
        return False

    endpoint_names = [path.anchor_entity, path.target_entity]
    endpoints = {compact(name) for name in endpoint_names if compact(name)}
    if len(endpoints) != 2:
        return False

    query_text = compact(query)
    endpoint_hit = sum(1 for name in endpoint_names if compact(name) in query_text)
    predicate_hit = any(
        compact(hop.predicate) and compact(hop.predicate) in query_text for hop in path.hops
    )
    return endpoint_hit >= 1 and (
        endpoint_hit >= 2 or predicate_hit or float(item.score) >= cutoff + score_margin
    )
