"""Small retrieval-only evaluation for the distributable synthetic fixture."""

from __future__ import annotations

import json

from .adapters.in_memory import load_fixture
from .conditional_path import ConditionalPathRetriever


def evaluate_fixture() -> dict[str, object]:
    index, graph_store, questions = load_fixture()
    retriever = ConditionalPathRetriever(index, graph_store)
    rows = []
    for question in questions:
        result = retriever.retrieve(str(question["question"]))
        expected = set(question["expected_source_ids"])
        selected = [chunk.id for chunk in result.chunks]
        recall = len(expected & set(selected)) / len(expected) if expected else 1.0
        rows.append(
            {
                "id": question["id"],
                "selected_source_ids": selected,
                "expected_source_ids": sorted(expected),
                "source_recall_at_8": recall,
                "top1_hit": bool(selected and selected[0] in expected),
            }
        )
    return {
        "dataset": "synthetic_ja",
        "question_count": len(rows),
        "mean_source_recall_at_8": sum(row["source_recall_at_8"] for row in rows) / len(rows),
        "top1_accuracy": sum(row["top1_hit"] for row in rows) / len(rows),
        "rows": rows,
    }


def main() -> None:
    print(json.dumps(evaluate_fixture(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
