#!/usr/bin/env python3
"""Fail on files or literals that must not enter the public repository."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "__pycache__",
    "build",
    "dist",
}
BINARY_SUFFIXES = {".db", ".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".pyc"}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*['\"][^'\"]{4,}['\"]"
)
PRIVATE_PATH = re.compile(r"/(Users|home)/[^/\s]+/(Documents|Desktop|Downloads|projects)/")
PRIVATE_NETWORK = re.compile(
    r"\b(?:10\.|192\.168\.|100\.(?:6[4-9]|[78]\d|9\d|1[01]\d|12[0-7])\.)"
    r"(?:\d{1,3}\.){1,2}\d{1,3}\b"
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
JAPAN_PHONE = re.compile(r"\b0\d{1,4}[- ]?\d{1,4}[- ]?\d{4}\b")
JAPAN_POSTAL_CODE = re.compile(r"\b\d{3}-\d{4}\b")
BLOCKED_CJK_VARIANTS = re.compile(
    r"[\u8fd9\u8be5\u4e2a\u4e3a\u4e0e\u5e76\u4ece\u8bc1\u636e\u8bf4"
    r"\u95ee\u8fc7\u8fd8\u8f83\u4ec5\u8ba9\u8fdb\u5bf9\u56fe\u6001\u8bef"
    r"\u6d4b\u7ebf\u8bcd\u7c7b\u8054\u8d44\u5904\u52a1\u5458\u8bc4\u8fc1"
    r"\u5386\u590d\u4ea7\u7b80\u6444\u5c06\u53d1\u672f\u7edf\u5c42\u5219"
    r"\u65f6\u95f4\u5f00\u5b9e\u9a8c]"
)
FORBIDDEN_DIGESTS = (
    (9, "5388bc10736a0eff09be2ab9c8369a9c1cd14ef7916dafe4e177da6903aefdec"),
    (8, "07a9fa0d51dee596c4803f7772ec492f88e35ad5b75884a6c02dc9f55bb5c7d7"),
    (13, "c303234ea4a55fc320890425a0f8f927cc5b97b68e819ac925b898b65fa72d84"),
    (8, "713ec46512c8f37127281f0e10c5eecb7f41e493c29aaebfc3105e919131cc43"),
    (17, "58b61a1634a7ac23328a231b3c689325b9d63301ed6bbc741689427f5b520c67"),
    (7, "5a513575437c43f6ae2700e33f61bbd8f991fbfa111fd1161ff98372784b1c81"),
    (7, "6ce178d69c9c2c374be74b1658b35a5d4ab241866b6cbf9365e2b6ac82fbeea4"),
    (2, "72726d8818f693066ceb69afa364218b692e62ea92b385782363780f47529c21"),
    (2, "cdbcca581b850626ad081ab5be557cec772bb02bf8a84addb132d797d9311c92"),
    (2, "205f3859abe469be388577ef8118a33bebb96430b7c792b7eb6afed36007ea80"),
    (2, "dab2fb440d86e0d1219de50193a92698629e4736e4da2cc8d9f05df3826f1b44"),
    (2, "245b763117e942f07e7e5b1a5046d109c37a72cb9960f616c3d42dd52232bb1d"),
    (2, "8c7756a41aa53a5d29c7f4dcb1e0345b47ecfd02178b9c114b3f68e1a28bc65f"),
    (4, "5d39d83a04f94d1c4a359be2ecb0a67bd5c012d5bc4d91cbab2393a343f63336"),
    (3, "d2b3cdae5d7ee1bd6c798af7a16dcedf4d78e84fdb14ccc6649fdd2df220ee39"),
    (7, "21c357ea47a71e116e2352e516e752c3f4f04abc2c38706df49ca81d899aff59"),
    (9, "0e6a8e0b849ed9b064c5a25e1ee5592f427e3eb9d250e42069ce46147d00e8d4"),
    (9, "02540942346fdfbf21a94f8b823af2ae315f20cb71721c2cc6e205097d560840"),
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def ignored(path: Path) -> bool:
    return any(part in SKIP_PARTS or part.endswith(".egg-info") for part in path.parts)


def contains_forbidden_term(text: str) -> bool:
    normalized = text.casefold()
    for length, expected in FORBIDDEN_DIGESTS:
        for start in range(len(normalized) - length + 1):
            value = normalized[start : start + length]
            if hashlib.sha256(value.encode()).hexdigest() == expected:
                return True
    return False


def main() -> None:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ignored(path.relative_to(ROOT)):
            continue
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in BINARY_SUFFIXES:
            failures.append(f"blocked binary extension: {relative}")
            continue
        if path.stat().st_size > 1_000_000:
            failures.append(f"file exceeds 1 MB: {relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"non-text file: {relative}")
            continue
        if PRIVATE_PATH.search(text):
            failures.append(f"private absolute path in {relative}")
        if PRIVATE_NETWORK.search(text):
            failures.append(f"private network address in {relative}")
        if EMAIL.search(text):
            failures.append(f"email address in {relative}")
        if JAPAN_PHONE.search(text):
            failures.append(f"phone number in {relative}")
        if JAPAN_POSTAL_CODE.search(text):
            failures.append(f"postal code in {relative}")
        if BLOCKED_CJK_VARIANTS.search(text):
            failures.append(f"blocked CJK variant in {relative}")
        if contains_forbidden_term(text) or contains_forbidden_term(relative.as_posix()):
            failures.append(f"restricted context term in {relative}")
        if SECRET_ASSIGNMENT.search(text):
            failures.append(f"possible hard-coded credential in {relative}")
        if path.suffix.lower() == ".md":
            for target in MARKDOWN_LINK.findall(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                local_target = unquote(target.split("#", 1)[0])
                if local_target and not (path.parent / local_target).resolve().exists():
                    failures.append(f"broken Markdown link in {relative}: {target}")

    metrics_path = ROOT / "results" / "evolution_metrics.csv"
    with metrics_path.open(encoding="utf-8", newline="") as handle:
        metrics = list(csv.DictReader(handle))
    for row in metrics:
        exact_accuracy = int(row["correct"]) / int(row["total"])
        if abs(float(row["accuracy"]) - exact_accuracy) > 0.000001:
            failures.append(f"accuracy mismatch in evolution_metrics.csv: {row['system']}")

    gate_path = ROOT / "results" / "kv_conditional_path_gate_summary.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    selected = [row for row in gate["candidates"] if row["status"] == "selected"]
    if [row["id"] for row in selected] != ["kv_conditional_path"]:
        failures.append("the selected candidate is not uniquely kv_conditional_path")

    if failures:
        raise SystemExit("\n".join(failures))
    print("publication check passed")


if __name__ == "__main__":
    main()
