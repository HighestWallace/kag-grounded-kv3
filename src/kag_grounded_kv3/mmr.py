"""Small deterministic MMR selector used by the public demo."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from .text import jaccard

T = TypeVar("T")


def select_mmr(
    rows: Sequence[T],
    *,
    top_k: int,
    score: Callable[[T], float],
    content: Callable[[T], str],
    relevance_weight: float = 0.85,
    redundancy_weight: float = 0.15,
) -> list[T]:
    pool = list(rows)
    selected: list[T] = []
    maximum = max((score(row) for row in pool), default=1.0) or 1.0

    while pool and len(selected) < top_k:
        best_index = 0
        best_score = float("-inf")
        for index, row in enumerate(pool):
            redundancy = max(
                (jaccard(content(row), content(prior)) for prior in selected),
                default=0.0,
            )
            mmr_score = relevance_weight * score(row) / maximum - redundancy_weight * redundancy
            if mmr_score > best_score:
                best_index = index
                best_score = mmr_score
        selected.append(pool.pop(best_index))
    return selected
