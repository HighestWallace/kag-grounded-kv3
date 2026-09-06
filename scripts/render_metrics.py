#!/usr/bin/env python3
"""Render dependency-free SVG charts from the public aggregate CSV."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "results" / "evolution_metrics.csv"
ASSET_DIR = ROOT / "docs" / "assets"

COLORS = {
    "off": "#2563eb",
    "legacy": "#c2410c",
    "guarded": "#15803d",
}


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def write_svg(path: Path, body: list[str], *, width: int, height: int) -> None:
    svg_open = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    path.write_text(
        "\n".join(
            [
                svg_open,
                '<rect width="100%" height="100%" fill="#ffffff"/>',
                "<style>text{font-family:Arial,sans-serif;fill:#202124}.small{font-size:11px}.label{font-size:12px}.title{font-size:18px;font-weight:700}.grid{stroke:#d1d5db;stroke-width:1}.axis{stroke:#374151;stroke-width:1.5}</style>",
                *body,
                "</svg>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def render_accuracy(rows: list[dict[str, str]]) -> None:
    width, height = 1160, 500
    left, right, top, bottom = 70, 30, 55, 125
    plot_w, plot_h = width - left - right, height - top - bottom
    ymin, ymax = 0.84, 0.895

    def x(index: int) -> float:
        return left + index * plot_w / max(1, len(rows) - 1)

    def y(value: float) -> float:
        return top + (ymax - value) * plot_h / (ymax - ymin)

    body = [
        '<text x="70" y="30" class="title">Accuracy evolution on the 229-question benchmark</text>'
    ]
    for tick in (0.84, 0.85, 0.86, 0.87, 0.88, 0.89):
        yy = y(tick)
        body.append(
            f'<line x1="{left}" y1="{yy:.1f}" x2="{width - right}" y2="{yy:.1f}" class="grid"/>'
        )
        body.append(
            f'<text x="{left - 10}" y="{yy + 4:.1f}" text-anchor="end" '
            f'class="small">{tick:.2f}</text>'
        )
    baseline = y(0.855895)
    body.append(
        f'<line x1="{left}" y1="{baseline:.1f}" x2="{width - right}" '
        f'y2="{baseline:.1f}" stroke="#7c3aed" stroke-width="2" '
        'stroke-dasharray="7 5"/>'
    )
    body.append(
        f'<text x="{width - right - 4}" y="{baseline - 7:.1f}" text-anchor="end" '
        'class="small">LightRAG 0.856</text>'
    )
    points = []
    for index, row in enumerate(rows):
        xx, yy = x(index), y(float(row["accuracy"]))
        color = COLORS.get(row["finalizer"], "#6b7280")
        points.append(f"{xx:.1f},{yy:.1f}")
        title = f"{escape(row['system'])}: {float(row['accuracy']):.3f}"
        body.append(
            f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="5" fill="{color}">'
            f"<title>{title}</title></circle>"
        )
        body.append(
            f'<text x="{xx:.1f}" y="{height - bottom + 20}" text-anchor="middle" class="small">'
            f"{escape(row['stage_order'])}</text>"
        )
    body.insert(
        1,
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#9ca3af" stroke-width="1.5"/>',
    )
    body.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" '
        f'y2="{top + plot_h}" class="axis"/>'
    )
    body.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - bottom + 48}" '
        'text-anchor="middle" class="label">'
        "Stage order (see the milestone table)</text>"
    )
    write_svg(ASSET_DIR / "accuracy_evolution.svg", body, width=width, height=height)


def render_tradeoff(rows: list[dict[str, str]]) -> None:
    chart_rows = [row for row in rows if row["mean_latency_seconds"]]
    width, height = 920, 540
    left, right, top, bottom = 80, 170, 55, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    xmax, ymin, ymax = 35.0, 0.84, 0.895

    def x(value: float) -> float:
        return left + value * plot_w / xmax

    def y(value: float) -> float:
        return top + (ymax - value) * plot_h / (ymax - ymin)

    body = [
        '<text x="80" y="30" class="title">Accuracy, evidence recall, and latency trade-off</text>'
    ]
    for tick in (0, 5, 10, 15, 20, 25, 30, 35):
        xx = x(tick)
        body.append(
            f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top + plot_h}" class="grid"/>'
        )
        body.append(
            f'<text x="{xx:.1f}" y="{top + plot_h + 22}" text-anchor="middle" '
            f'class="small">{tick}s</text>'
        )
    for tick in (0.84, 0.85, 0.86, 0.87, 0.88, 0.89):
        yy = y(tick)
        body.append(
            f'<line x1="{left}" y1="{yy:.1f}" x2="{left + plot_w}" y2="{yy:.1f}" class="grid"/>'
        )
        body.append(
            f'<text x="{left - 10}" y="{yy + 4:.1f}" text-anchor="end" '
            f'class="small">{tick:.2f}</text>'
        )
    for row in chart_rows:
        xx = x(float(row["mean_latency_seconds"]))
        yy = y(float(row["accuracy"]))
        evidence = float(row["evidence_recall"])
        radius = 4 + 7 * max(0.0, min(1.0, evidence))
        color = COLORS.get(row["finalizer"], "#6b7280")
        title = (
            f"{escape(row['system'])} | acc={float(row['accuracy']):.3f} "
            f"ev={evidence:.3f} latency={float(row['mean_latency_seconds']):.2f}s"
        )
        body.append(
            f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="{radius:.1f}" '
            f'fill="{color}" fill-opacity="0.70" stroke="#ffffff" '
            f'stroke-width="1"><title>{title}</title></circle>'
        )
    body.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" '
        f'y2="{top + plot_h}" class="axis"/>'
    )
    body.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>')
    body.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 18}" '
        'text-anchor="middle" class="label">Mean latency</text>'
    )
    body.append(
        f'<text x="20" y="{top + plot_h / 2:.1f}" '
        f'transform="rotate(-90 20 {top + plot_h / 2:.1f})" '
        'text-anchor="middle" class="label">Accuracy</text>'
    )
    legend_x = left + plot_w + 25
    body.append(f'<text x="{legend_x}" y="{top + 20}" class="label">Color: finalizer</text>')
    for offset, name in enumerate(("off", "legacy", "guarded"), start=1):
        yy = top + 20 + offset * 25
        body.append(f'<circle cx="{legend_x + 8}" cy="{yy}" r="6" fill="{COLORS[name]}"/>')
        body.append(f'<text x="{legend_x + 22}" y="{yy + 4}" class="small">{name}</text>')
    body.append(f'<text x="{legend_x}" y="{top + 125}" class="label">Size: evidence recall</text>')
    write_svg(ASSET_DIR / "accuracy_evidence_latency.svg", body, width=width, height=height)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    render_accuracy(rows)
    render_tradeoff(rows)


if __name__ == "__main__":
    main()
