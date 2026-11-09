"""What the harmonise step's looser dedupe key collapsed, as counts only (`make dedup-check`).

The key is (leader, link) when a link is present, else (leader, first 200 characters of text). For each group
that held more than one row this compares the full raw texts and labels the group by its largest difference:
identical, spacing, case, punctuation or content. It changes nothing; it prints and writes counts, never text.
"""
from __future__ import annotations

import logging
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.harmonise import DEFAULT_RAW_DIR, _load_all, dedupe_keys, stack_records
from src.verify_raw import ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/dedup_check.md")
LABELS = ("identical", "spacing", "case", "punctuation", "content")
_NON_WORD = re.compile(r"[\W_]+")


@dataclass(frozen=True)
class CollapsedCounts:
    groups: int
    rows_collapsed: int
    by_label: dict[str, int]
    rows_by_label: dict[str, int]
    content_by_key: dict[str, int]
    content_extends: int


def classify_texts(texts: Sequence[str]) -> str:
    """The largest difference among the raw texts of one group."""
    levels = (
        ("identical", lambda t: t),
        ("spacing", lambda t: " ".join(t.split())),
        ("case", lambda t: " ".join(t.split()).casefold()),
        ("punctuation", lambda t: _NON_WORD.sub("", t.casefold())),
    )
    for label, normalise in levels:
        if len({normalise(t) for t in texts}) == 1:
            return label
    return "content"


def _extends(texts: Sequence[str]) -> bool:
    """True when the shortest text, spacing-normalised, is the start of every other text."""
    flat = sorted((" ".join(t.split()) for t in texts), key=len)
    return all(other.startswith(flat[0]) for other in flat[1:])


def count_collapsed(stacked: pd.DataFrame) -> CollapsedCounts:
    """Compare the raw texts inside every group the looser key collapsed."""
    keys = dedupe_keys(stacked)
    by_label = dict.fromkeys(LABELS, 0)
    rows_by_label = dict.fromkeys(LABELS, 0)
    content_by_key = {"link": 0, "text_head": 0}
    extends = 0
    sizes = keys.value_counts()
    repeated = set(sizes[sizes > 1].index)
    texts_by_key = stacked.groupby(keys, sort=False)["post_text"].apply(list)
    for key in repeated:
        texts = [str(t) for t in texts_by_key[key]]
        label = classify_texts(texts)
        by_label[label] += 1
        rows_by_label[label] += len(texts) - 1
        if label == "content":
            content_by_key["link" if "|L|" in key else "text_head"] += 1
            extends += int(_extends(texts))
    return CollapsedCounts(
        groups=len(repeated),
        rows_collapsed=sum(rows_by_label.values()),
        by_label=by_label,
        rows_by_label=rows_by_label,
        content_by_key=content_by_key,
        content_extends=extends,
    )


def render_report(counts: CollapsedCounts, rows_before: int) -> str:
    rows = "\n".join(
        f"| {label} | {counts.by_label[label]} | {counts.rows_by_label[label]} |" for label in LABELS
    )
    return f"""# Dedupe check: what the looser key collapsed

Counts only; no names, ids or text. The harmonise step keeps the first row of each group that shares
(leader, link) or, with no link, (leader, first 200 characters of text). This compares the full raw texts inside
each group of two or more rows. Nothing is changed by this check.

| Measure | Count |
|---|---|
| Rows before the looser key | {rows_before} |
| Groups with more than one row | {counts.groups} |
| Rows collapsed by the looser key | {counts.rows_collapsed} |

Groups are labelled by their largest difference: identical (same raw text), spacing (same after collapsing
whitespace), case (same after also ignoring case), punctuation (same after also ignoring punctuation), content
(anything else).

| Label | Groups | Rows collapsed |
|---|---|---|
{rows}

Groups labelled content, by key type: link {counts.content_by_key["link"]}, text head {counts.content_by_key["text_head"]}.
Of the content groups, {counts.content_extends} are cases where the shorter text is the start of the longer one.
"""


def run(raw_dir: Path = DEFAULT_RAW_DIR, report_path: Path = DEFAULT_REPORT_PATH) -> int:
    """Verify the raw manifest, count what the looser key collapsed, write the report; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        stacked, _ = stack_records(_load_all(raw_dir))
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("dedup-check FAILED: %s", error)
        return 1
    counts = count_collapsed(stacked)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(counts, len(stacked)), encoding="utf-8")
    logger.info("wrote %s: %d groups, %d rows collapsed", report_path, counts.groups, counts.rows_collapsed)
    logger.info("groups with different content: %d", counts.by_label["content"])
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
