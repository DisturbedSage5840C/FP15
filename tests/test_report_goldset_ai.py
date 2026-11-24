"""Counts-only AI gold-set report tests using synthetic scores only."""
from __future__ import annotations

import pandas as pd

from scripts.code_goldset_ai import AI_COLUMNS, TRAITS
from scripts.report_goldset_ai import BANNER, render_report


def _frame(count: int = 10) -> pd.DataFrame:
    rows = []
    for index in range(count):
        row = dict.fromkeys(AI_COLUMNS, "")
        row.update({"leader_id": f"L{index}", "post_id": f"P{index}", "coder_id": "AI-1", "model_name": "fixed", "prompt_hash": "a"})
        for trait in TRAITS:
            row[trait] = "" if index == 0 else str((index % 5) + 1)
            row[f"agree_{trait}"] = "true" if index else "false"
        rows.append(row)
    return pd.DataFrame(rows, columns=AI_COLUMNS)


def test_report_has_required_banner_aggregate_counts_and_outstanding_work() -> None:
    report = render_report(_frame(), 5)

    assert report.startswith(f"> {BANNER}")
    assert "Krippendorff alpha" in report and "Step 17" in report
    assert "Posts coded: 10." in report
    assert "not enough evidence" in report
    assert "L0" not in report and "P0" not in report


def test_report_suppresses_small_cells() -> None:
    report = render_report(_frame(), 5)

    assert "<5" in report
