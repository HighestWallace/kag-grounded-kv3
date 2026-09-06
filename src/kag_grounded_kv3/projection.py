"""Route fusion and grounded key-to-value projection."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .models import SearchHit


def normalized_scores(rows: Sequence[SearchHit]) -> dict[str, float]:
    if not rows:
        return {}
    scores = [float(row.score) for row in rows]
    low, high = min(scores), max(scores)
    if math.isclose(low, high):
        return {row.id: 1.0 for row in rows}
    return {row.id: (float(row.score) - low) / (high - low) for row in rows}


def accepted_route_scores(
    full: Sequence[SearchHit],
    stem: Sequence[SearchHit],
    *,
    full_gate: int = 16,
    improvement_margin: float = 0.05,
) -> tuple[dict[str, float], dict[str, set[str]], dict[str, SearchHit]]:
    """Fuse two routes by max score while admitting only useful stem hits."""

    full_scores = normalized_scores(full)
    stem_scores = normalized_scores(stem)
    full_top = {row.id for row in full[:full_gate]}
    scores = dict(full_scores)
    channels = {row_id: {"full"} for row_id in full_scores}
    items = {row.id: row for row in full}

    for row in stem:
        stem_score = stem_scores[row.id]
        full_score = full_scores.get(row.id, 0.0)
        if row.id not in full_top or stem_score >= full_score + improvement_margin:
            scores[row.id] = max(full_score, stem_score)
            channels.setdefault(row.id, set()).add("stem")
            items[row.id] = row
    return scores, channels, items
