from kag_grounded_kv3.evaluation import evaluate_fixture


def test_synthetic_evaluation_is_complete() -> None:
    summary = evaluate_fixture()

    assert summary["question_count"] == 3
    assert summary["mean_source_recall_at_8"] == 1.0
    assert 0.0 <= summary["top1_accuracy"] <= 1.0
