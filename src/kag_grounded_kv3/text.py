"""Text normalization shared by retrieval routes and MMR."""

from __future__ import annotations

import re
import unicodedata


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip()


def compact(value: object) -> str:
    return re.sub(r"\s+", "", normalize(value).lower())


def question_stem_only(question: str) -> str:
    stem = re.split(r"(?m)^\s*選択肢\s*[:：]?", str(question or ""), maxsplit=1)[0]
    stem = re.sub(
        r"教材根拠だけに基づき、最も適切な選択肢番号と短い理由を答えてください。?\s*$",
        "",
        stem,
    )
    return stem.strip() or str(question or "").strip()


def text_ngrams(value: str) -> set[str]:
    normalized = compact(value)
    grams = {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}
    grams.update(re.findall(r"[a-z0-9]{2,}", normalized))
    return grams


def jaccard(left: str, right: str) -> float:
    left_terms = text_ngrams(left)
    right_terms = text_ngrams(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)
