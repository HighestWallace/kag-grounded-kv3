"""Deterministic provenance checks and strict two-hop path construction."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, replace

from .models import PathHop, PathRecord, SourceValue
from .text import compact, normalize


def stable_id(prefix: str, value: str, *, length: int = 24) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}{digest}"


@dataclass(frozen=True)
class GroundedFact:
    id: str
    subject: str
    predicate: str
    object: str
    source_quote: str
    source_value_ids: tuple[str, ...]
    chapter: str = ""
    condition: str = ""
    polarity: str = "positive"
    subject_type: str = "GeneralConcept"
    object_type: str = "GeneralConcept"
    subject_id: str = ""
    object_id: str = ""


def map_quote_to_sources(
    quote: str,
    sources: Iterable[SourceValue],
    *,
    chapter: str = "",
) -> tuple[str, ...]:
    """Projects an exact normalized quote back to every containing source."""

    normalized_quote = compact(quote)
    if not normalized_quote:
        return ()
    return tuple(
        source.id
        for source in sources
        if (not chapter or source.chapter == chapter)
        and normalized_quote in compact(source.content)
    )


def canonicalize_fact(fact: GroundedFact) -> GroundedFact:
    subject = normalize(fact.subject)
    obj = normalize(fact.object)
    subject_id = stable_id("E_", f"{fact.subject_type}\0{compact(subject)}")
    object_id = stable_id("E_", f"{fact.object_type}\0{compact(obj)}")
    return replace(
        fact,
        subject=subject,
        object=obj,
        subject_id=subject_id,
        object_id=object_id,
    )


def validate_fact_provenance(
    fact: GroundedFact,
    sources: Iterable[SourceValue],
) -> GroundedFact | None:
    """Rejects facts whose entities or quote cannot be located in source text."""

    quote = normalize(fact.source_quote)
    if not quote or compact(fact.subject) == compact(fact.object):
        return None
    if compact(fact.subject) not in compact(quote) or compact(fact.object) not in compact(quote):
        return None
    source_ids = map_quote_to_sources(quote, sources, chapter=fact.chapter)
    if not source_ids:
        return None
    return canonicalize_fact(replace(fact, source_quote=quote, source_value_ids=source_ids))


def build_two_hop_paths(
    facts: Iterable[GroundedFact],
    *,
    maximum: int = 1_000,
    per_anchor_limit: int = 8,
) -> list[PathRecord]:
    """Builds strict A->B->C paths backed by at least two source values."""

    prepared = [canonicalize_fact(fact) for fact in facts]
    outgoing: dict[str, list[GroundedFact]] = {}
    for fact in prepared:
        outgoing.setdefault(fact.subject_id, []).append(fact)

    candidates: list[tuple[float, PathRecord]] = []
    seen: set[tuple[str, str]] = set()
    for first in prepared:
        for second in outgoing.get(first.object_id, []):
            names = {compact(first.subject), compact(first.object), compact(second.object)}
            if len(names) != 3 or first.polarity != second.polarity:
                continue
            source_ids = tuple(sorted(set(first.source_value_ids + second.source_value_ids)))
            if len(source_ids) < 2:
                continue
            key = (first.id, second.id)
            if key in seen:
                continue
            seen.add(key)
            path = PathRecord(
                id=stable_id("PTH_", "\0".join(key)),
                anchor_entity=first.subject,
                target_entity=second.object,
                source_value_ids=source_ids,
                hops=(
                    PathHop(predicate=first.predicate, source_quote=first.source_quote),
                    PathHop(predicate=second.predicate, source_quote=second.source_quote),
                ),
            )
            score = 0.8 + 0.1 * min(2, len(source_ids))
            candidates.append((score, path))

    candidates.sort(key=lambda row: (-row[0], row[1].id))
    per_anchor: dict[str, int] = {}
    selected: list[PathRecord] = []
    for _score, path in candidates:
        anchor_key = compact(path.anchor_entity)
        if per_anchor.get(anchor_key, 0) >= per_anchor_limit:
            continue
        selected.append(path)
        per_anchor[anchor_key] = per_anchor.get(anchor_key, 0) + 1
        if len(selected) >= maximum:
            break
    return selected
