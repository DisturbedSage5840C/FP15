#!/usr/bin/env python3
"""Counts-only report for the git-ignored AI-1 gold-set coding file."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

from scripts.code_goldset_ai import AI_COLUMNS, DEFAULT_AI_PATH, TRAITS
from src.eda_common import DEFAULT_THRESHOLDS_PATH, load_eda_settings, protect_cells, show_count
from src.provisional_leaders import _table

DEFAULT_REPORT_PATH = Path("reports/goldset_ai_coding.md")
BANNER = "AI-assisted, PROVISIONAL. Single AI coder. Krippendorff alpha cannot be computed with one coder. G2 NOT passed."


def _read(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if tuple(frame.columns) != AI_COLUMNS:
        raise ValueError("AI-1 coding file has an unexpected schema")
    return frame


def _distribution(frame: pd.DataFrame, trait: str, minimum: int) -> list[list[str]]:
    values = frame[trait]
    counts = {"not enough evidence": int(values.eq("").sum()), **{str(score): int(values.eq(str(score)).sum()) for score in range(1, 6)}}
    shown = protect_cells(counts, minimum)
    return [[trait.replace("_", " "), label, shown[label]] for label in counts]


def _agreement(frame: pd.DataFrame, trait: str, minimum: int) -> list[str]:
    agreement = int(frame[f"agree_{trait}"].str.lower().eq("true").sum())
    return [trait.replace("_", " "), show_count(agreement, minimum)]


def render_report(frame: pd.DataFrame, disclosure_min: int) -> str:
    """A tracked report with aggregate score counts and no ids, names, text or free reasons."""
    distribution = [row for trait in TRAITS for row in _distribution(frame, trait, disclosure_min)]
    agreement = [_agreement(frame, trait, disclosure_min) for trait in TRAITS]
    outstanding = [
        ["Human coding", "Coders H1--H3 must code the same posts using the human template."],
        ["Guidelines", "Human coding guidelines and their review are still needed."],
        ["Reliability", "The 0.67 Krippendorff alpha check needs at least two human coders."],
        ["Dictionary check", "The dictionary-to-human correlation check (about 0.4) is Step 17 and was not computed here."],
    ]
    lines = [
        f"> {BANNER}", "", "# AI-1 gold-set coding", "",
        "Counts only: no names, ids, links, post text, reason text or source references. AI-1 is not a human coder, "
        "and this output does not validate a measure.", "",
        f"- Posts coded: {show_count(len(frame), disclosure_min)}.",
        "- Scores are the first of two fixed-setting runs; blank means the model returned not enough evidence. "
        "No score was filled or guessed.",
        "- The tables use the disclosure minimum and existing secondary suppression where a table has a lone small cell.",
        "",
        "## Scores and not-enough-evidence counts", "",
        *_table(["trait", "response", "posts"], distribution), "",
        "## Run-to-run exact agreement", "",
        *_table(["trait", "posts with exactly matching scores in both runs"], agreement), "",
        "## Still needed before G2", "",
        *_table(["item", "status"], outstanding), "",
    ]
    return "\n".join(lines)


def run(ai_path: Path = DEFAULT_AI_PATH, report_path: Path = DEFAULT_REPORT_PATH, thresholds_path: Path = DEFAULT_THRESHOLDS_PATH) -> int:
    try:
        settings = load_eda_settings(thresholds_path)
        report = render_report(_read(ai_path), settings.disclosure_min)
    except (FileNotFoundError, ValueError) as error:
        print(f"report-goldset-ai FAILED: {error}", file=sys.stderr)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
