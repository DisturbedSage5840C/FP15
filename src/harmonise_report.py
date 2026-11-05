"""Render reports/harmonise_summary.md from a harmonise run (counts, file names, sheet indexes).

The report never carries leader names, sheet names or post text. Sheets are identified by
workbook path and zero-based sheet index; the full list with sheet names stays in the
git-ignored data/interim/harmonise_skipped.csv.
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from typing import TYPE_CHECKING

import pandas as pd

from src.name_key import name_key

if TYPE_CHECKING:
    from src.harmonise import HarmonisedResult

SPOT_CHECK_SHEETS = 20  # sample size for the sheet-name-is-the-leader spot check
SPOT_CHECK_SEED = 15
LOG_COLUMNS = (
    "workbook", "sheet_idx", "sheet", "status", "reason", "is_combined", "method", "text_kind",
    "odd_reasons", "rows_with_text", "rows_kept", "dropped_no_leader", "filled_from_sheet",
    "sheet_name_conflict", "cell_leader_rows", "cell_matches_sheet",
)
OWNER_FIGURES = (
    ("Non-empty post_text rows", 32448),
    ("Sheets with post text", 705),
    ("Unique posts after dedupe", 22083),
    ("Leaders", 544),
)


def _fmt(number: int) -> str:
    return f"{number:,}"


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def _total(frame: pd.DataFrame, column: str) -> int:
    return sum(int(str(v)) for v in frame[column])


def _table(header: tuple[str, ...], rows: Iterable[tuple[object, ...]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return lines


def _grouped_lines(log: pd.DataFrame) -> list[str]:
    """One 'workbook: idx, idx' line per workbook."""
    lines = []
    for workbook, group in log.groupby("workbook", sort=True):
        indexes = ", ".join(str(int(i)) for i in sorted(group["sheet_idx"]))
        lines.append(f"- {workbook}: {indexes}")
    return lines


def _kind_figures(result: HarmonisedResult, log: pd.DataFrame, kind: str | None) -> tuple[int, int, int, int]:
    """Rows with text, sheets with text, unique posts and leaders for one text kind (None = all)."""
    posts = result.posts if kind is None else result.posts[result.posts["text_kind"] == kind]
    sheets = log if kind is None else log[log["text_kind"] == kind]
    rows = [int(str(v)) for v in sheets["rows_with_text"]]
    leaders = {key for key in (name_key(v) for v in posts["leader"]) if key}
    return sum(rows), sum(n > 0 for n in rows), len(posts), len(leaders)


def _headline(result: HarmonisedResult, log: pd.DataFrame) -> list[str]:
    raw = _kind_figures(result, log, "raw")
    cleaned = _kind_figures(result, log, "cleaned")
    everything = _kind_figures(result, log, None)
    rows = [
        (label, _fmt(theirs), _fmt(r), f"{r - theirs:+,}", _fmt(c), _fmt(a))
        for (label, theirs), r, c, a in zip(OWNER_FIGURES, raw, cleaned, everything)
    ]
    return [
        "## Headline figures against the owner's figures",
        "",
        *_table(
            ("Measure", "Owner's figure", "Raw post_text workbooks", "Difference", "Cleaned workbooks", "All"),
            rows,
        ),
        "",
        "The wordcount workbooks carry `cleaned_post_text`, a cleaned copy of posts that also sit in the "
        "raw `post_text` workbooks. The owner's figures are compared with the raw post_text workbooks only. "
        "Raw and cleaned rows are kept apart by `text_kind` and are not deduplicated against each other, "
        "so the All column counts the same post twice.",
        "",
        f"Rows lost at the leader step: {_fmt(result.rows_with_text - result.rows_after_leader)}. "
        f"Duplicates removed: {_fmt(result.rows_after_leader - len(result.posts))}. Differences are reported, "
        "not forced: they come from sheets skipped with a reason (below), rows dropped on the combined "
        "sheet for lack of a leader, and the dedupe rule.",
    ]


def _sheet_status(log: pd.DataFrame) -> list[str]:
    used = log[log["status"] == "used"]
    rows = [
        ("Sheets loaded", _fmt(len(log))),
        ("Sheets used", _fmt(len(used))),
        ("Sheets skipped", _fmt(len(log) - len(used))),
        ("Combined sheets (first post sheet of a workbook)", _fmt(int(used["is_combined"].astype(bool).sum()))),
    ]
    rows += [
        (f"Sheets mapped by {method}", _fmt(int((used["method"] == method).sum())))
        for method in sorted(used["method"].dropna().unique())
    ]
    rows += [
        (f"Sheets with {kind} text", _fmt(int((used["text_kind"] == kind).sum())))
        for kind in sorted(used["text_kind"].dropna().unique())
    ]
    return ["## Sheets", "", *_table(("Item", "Count"), rows)]


def _skipped_section(log: pd.DataFrame) -> list[str]:
    skipped = log[log["status"] == "skipped"]
    lines = ["## Skipped sheets and why (workbook: sheet index)", ""]
    if skipped.empty:
        return [*lines, "No sheet was skipped."]
    for reason, group in skipped.groupby("reason", sort=True):
        lines += [f"**{reason}** ({len(group)} sheets)", "", *_grouped_lines(group), ""]
    return lines


def _leader_section(log: pd.DataFrame) -> list[str]:
    rows = [
        ("Rows dropped (combined sheet, no leader)", _fmt(_total(log, "dropped_no_leader"))),
        ("Rows with a leader filled from the sheet name", _fmt(_total(log, "filled_from_sheet"))),
        ("  of which the sheet name disagrees with the other leader cells", _fmt(_total(log, "sheet_name_conflict"))),
    ]
    return [
        "## Leader assignment",
        "",
        "Rule (ASSUMPTION in docs/decisions.md): on the combined sheet rows with no leader are dropped; on "
        "every other sheet a blank leader cell takes the sheet name; nothing is forward-filled. Conflicts are "
        "flagged `sheet_name_conflict`, never auto-resolved. Excel truncates sheet names at 31 characters, "
        "so some conflicts may be truncation, not a real disagreement.",
        "",
        *_table(("Item", "Rows"), rows),
    ]


def _spot_check(log: pd.DataFrame) -> list[str]:
    heading = [f"## Spot check: is the sheet name the leader? ({SPOT_CHECK_SHEETS} random sheets)", ""]
    pool = log[(log["status"] == "used") & ~log["is_combined"].astype(bool)]
    pool = pool[pd.to_numeric(pool["cell_leader_rows"]) > 0].sort_values(["workbook", "sheet_idx"])
    if pool.empty:
        return [*heading, "No sheet has both a leader cell and a sheet name to compare."]
    chosen = random.Random(SPOT_CHECK_SEED).sample(range(len(pool)), min(SPOT_CHECK_SHEETS, len(pool)))
    sample = pool.iloc[sorted(chosen)]
    lines = [
        f"- {row.workbook}: {int(row.sheet_idx)} ({int(row.cell_matches_sheet)}/{int(row.cell_leader_rows)} "
        "leader cells agree with the sheet name)"
        for row in sample.itertuples()
    ]
    sample_agree, sample_rows = _total(sample, "cell_matches_sheet"), _total(sample, "cell_leader_rows")
    all_agree, all_rows = _total(pool, "cell_matches_sheet"), _total(pool, "cell_leader_rows")
    return [
        *heading,
        *lines,
        "",
        f"Agreement in the sample: {_fmt(sample_agree)}/{_fmt(sample_rows)} rows ({_pct(sample_agree, sample_rows)}). "
        f"Agreement on all {_fmt(len(pool))} comparable sheets: {_fmt(all_agree)}/{_fmt(all_rows)} rows "
        f"({_pct(all_agree, all_rows)}). A human still has to judge whether this supports the assumption.",
    ]


def _filled(series: pd.Series) -> int:
    return int(series.notna().sum())


def _column_fill(posts: pd.DataFrame) -> list[str]:
    total = len(posts)
    rows = [
        ("age_text", _filled(posts["age_text"])),
        ("post_date", _filled(posts["post_date"])),
        ("post_date holds post text", int(posts["post_date_is_text"].astype(bool).sum())),
        ("post_date_text", _filled(posts["post_date_text"])),
        ("role_start_year", _filled(posts["role_start_year"])),
    ]
    return [
        "## Date and tenure columns in the unique posts",
        "",
        "`age_text` is a relative age ('3mo'), not a date. Absolute dates stay missing; none are inferred.",
        "",
        *_table(("Column", "Filled", "Share"), [(name, _fmt(n), _pct(n, total)) for name, n in rows]),
    ]


def _odd_section(log: pd.DataFrame) -> list[str]:
    odd = log[log["odd_reasons"].fillna("") != ""]
    lines = ["## Sheets the profiler flagged as odd (workbook: sheet index)", ""]
    if odd.empty:
        return [*lines, "None."]
    return [*lines, *_grouped_lines(odd)]


def render_report(result: HarmonisedResult, roster: pd.DataFrame) -> str:
    """The full Markdown report; raises nothing on an empty run."""
    log = result.sheet_log.reindex(columns=list(LOG_COLUMNS))
    sections = [
        ["# Harmonise summary", "", "Counts, file paths and sheet indexes only; no names and no post text."],
        _headline(result, log),
        [f"Roster loaded once from seventh_100_leaders/All_500.xlsx: {_fmt(len(roster))} people."],
        _sheet_status(log),
        _skipped_section(log),
        _leader_section(log),
        _spot_check(log),
        _column_fill(result.posts),
        _odd_section(log),
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"
