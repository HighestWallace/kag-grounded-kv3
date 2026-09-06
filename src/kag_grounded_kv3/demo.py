"""Command-line demonstration using the original synthetic Japanese corpus."""

from __future__ import annotations

import argparse
import json

from .adapters.in_memory import load_fixture
from .conditional_path import ConditionalPathRetriever

DEFAULT_QUESTION = (
    "画像メタデータを更新した後も古いサムネイルキャッシュが表示される場合、"
    "どのような処理が必要ですか。"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Grounded KV3 synthetic demo")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    index, graph_store, _questions = load_fixture()
    result = ConditionalPathRetriever(index, graph_store).retrieve(args.question)
    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    print(f"質問: {result.query}")
    print("\n選択された根拠:")
    for chunk in result.chunks:
        components = ", ".join(
            f"{name}={value:.3f}" for name, value in chunk.component_scores.items() if value > 0
        )
        print(f"{chunk.rank}. [{chunk.id}] score={chunk.score:.3f} ({components})")
        print(f"   {chunk.content}")


if __name__ == "__main__":
    main()
