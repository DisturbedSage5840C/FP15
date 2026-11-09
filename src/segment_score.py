"""Score the segmenter against the human post counts in the 200-cell check (`make segmentation-score`).

A human fills `human_post_count` in data/derived/segmentation_check_200.csv. This script compares each filled
count with the number of posts the segmenter finds in the same raw cell and reports exact matches against the
`segmentation_accuracy` threshold. It states whether the threshold was reached as a fact. It does NOT sign off
gate G1: that is a human sign-off line in docs/decisions.md.

The committed report holds counts only. Row-level detail (sample row number, human count, machine count) goes
to a git-ignored file. Neither file holds a name or any post text.
"""
from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.harmonise import DEFAULT_INTERIM_DIR
from src.reaction_count_check import _read_posts
from src.segment import DEFAULT_SAMPLE_PATH, DEFAULT_THRESHOLDS_PATH, raw_cell_frame, segment_cell
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/segmentation_check.md")
DEFAULT_DETAIL_PATH = Path("data/derived/segmentation_score_detail.csv")
SAMPLE_COLUMNS = ("n", "ref", "human_post_count")
DETAIL_COLUMNS = ["n", "human", "machine", "match"]
MAX_SEPARATE_BUCKET = 2
_WHOLE_NUMBER = re.compile(r"^\d+$")


@dataclass(frozen=True)
class HumanCount:
    """One sample row: its number, the raw-cell ref and the human's post count (None when not filled in)."""

    n: int
    ref: str
    count: int | None


@dataclass(frozen=True)
class Detail:
    """Human and machine post counts for one scored row. Holds no text."""

    n: int
    human: int
    machine: int


@dataclass(frozen=True)
class ScoreResult:
    """Counts from comparing the human and machine post counts."""

    n_rows: int
    scored: int
    unscored: int
    exact: int
    accuracy: float | None
    threshold: float
    at_or_above_threshold: bool | None
    machine_fewer: int
    machine_more: int
    by_machine_count: tuple[tuple[str, int, int], ...]
    details: tuple[Detail, ...]


def load_threshold(path: Path = DEFAULT_THRESHOLDS_PATH) -> float:
    """The segmentation accuracy threshold; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "segmentation_accuracy" not in values:
        raise ValueError(f"{path}: missing key segmentation_accuracy")
    return float(values["segmentation_accuracy"])


def load_required_cells(path: Path = DEFAULT_THRESHOLDS_PATH) -> int:
    """How many hand-checked cells the gate asks for; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "segmentation_check_cells" not in values:
        raise ValueError(f"{path}: missing key segmentation_check_cells")
    return int(values["segmentation_check_cells"])


def _parse_count(value: str, n: int) -> int | None:
    text = value.strip()
    if not text:
        return None
    if not _WHOLE_NUMBER.match(text):
        raise ValueError(f"row {n}: human_post_count must be a whole number, not a decimal, negative or text")
    return int(text)


def load_human_counts(path: Path) -> list[HumanCount]:
    """Read the sample file. Blank counts stay unscored; a bad count is an error naming the row."""
    sample = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [column for column in SAMPLE_COLUMNS if column not in sample.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    rows = []
    for row in sample.itertuples(index=False):
        n = int(row.n)
        rows.append(HumanCount(n, row.ref, _parse_count(row.human_post_count, n)))
    return rows


def _bucket(machine: int) -> str:
    return str(machine) if machine <= MAX_SEPARATE_BUCKET else f"{MAX_SEPARATE_BUCKET + 1} or more"


def _by_bucket(details: Sequence[Detail]) -> tuple[tuple[str, int, int], ...]:
    labels = [str(i) for i in range(MAX_SEPARATE_BUCKET + 1)] + [f"{MAX_SEPARATE_BUCKET + 1} or more"]
    cells = {label: 0 for label in labels}
    exact = {label: 0 for label in labels}
    for detail in details:
        label = _bucket(detail.machine)
        cells[label] += 1
        exact[label] += detail.human == detail.machine
    return tuple((label, cells[label], exact[label]) for label in labels if cells[label])


def score_cells(rows: Sequence[HumanCount], texts: Mapping[str, str], threshold: float) -> ScoreResult:
    """Compare each filled human count with the segmenter's count for the same raw cell."""
    details: list[Detail] = []
    for row in rows:
        if row.ref not in texts:
            raise ValueError(f"row {row.n}: ref not found in the harmonised posts")
        if row.count is not None:
            details.append(Detail(row.n, row.count, len(segment_cell(texts[row.ref]).segments)))
    exact = sum(d.human == d.machine for d in details)
    accuracy = exact / len(details) if details else None
    return ScoreResult(
        n_rows=len(rows),
        scored=len(details),
        unscored=len(rows) - len(details),
        exact=exact,
        accuracy=accuracy,
        threshold=threshold,
        at_or_above_threshold=None if accuracy is None else accuracy >= threshold,
        machine_fewer=sum(d.machine < d.human for d in details),
        machine_more=sum(d.machine > d.human for d in details),
        by_machine_count=_by_bucket(details),
        details=tuple(details),
    )


def _verdict(result: ScoreResult) -> str:
    if result.at_or_above_threshold is None:
        return "not scored"
    return "yes" if result.at_or_above_threshold else "no"


def render_report(result: ScoreResult, required_cells: int) -> str:
    """The counts-only report. States the threshold comparison as a fact and leaves G1 to a human."""
    accuracy = "n/a" if result.accuracy is None else f"{result.accuracy:.3f}"
    lines = [
        "# Segmentation check (counts only)",
        "",
        "Machine post count per raw cell versus the human count, on the hand-checked sample. "
        "Row detail is in a git-ignored file, by sample row number.",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Rows in the sample file | {result.n_rows} |",
        f"| Cells with a human count | {result.scored} |",
        f"| Rows without a human count | {result.unscored} |",
        f"| Exact matches | {result.exact} |",
        f"| Accuracy (exact matches / cells with a human count) | {accuracy} |",
        f"| Threshold (configs/thresholds.yaml) | {result.threshold} |",
        f"| At or above threshold | {_verdict(result)} |",
        f"| Machine found lower count than human | {result.machine_fewer} |",
        f"| Machine found higher count than human | {result.machine_more} |",
        "",
        "## By the machine's post count",
        "",
        "| Machine posts | Cells | Exact matches |",
        "|---|---|---|",
        *[f"| {label} | {cells} | {exact} |" for label, cells, exact in result.by_machine_count],
        "",
    ]
    if result.scored < required_cells:
        lines += [f"Only {result.scored} cells were scored, fewer than the {required_cells} the gate asks for.", ""]
    lines += [
        "This report does not sign off G1. G1 needs a human sign-off line in docs/decisions.md.",
        "",
    ]
    return "\n".join(lines)


def _detail_frame(result: ScoreResult) -> pd.DataFrame:
    return pd.DataFrame(
        [(d.n, d.human, d.machine, "yes" if d.human == d.machine else "no") for d in result.details],
        columns=DETAIL_COLUMNS,
    )


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    sample_path: Path = DEFAULT_SAMPLE_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    detail_path: Path = DEFAULT_DETAIL_PATH,
    threshold: float | None = None,
) -> int:
    """Verify the raw manifest, score the filled-in counts and write the report. 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        active = load_threshold() if threshold is None else threshold
        required = load_required_cells()
        rows = load_human_counts(sample_path)
        if all(row.count is None for row in rows):
            raise ValueError(f"{sample_path}: no human_post_count is filled in yet")
        texts = dict(zip(*(raw_cell_frame(_read_posts(interim_dir))[c] for c in ("ref", "text"))))
        result = score_cells(rows, texts, active)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("segmentation-score FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result, required), encoding="utf-8")
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    _detail_frame(result).to_csv(detail_path, index=False)
    logger.info("scored %d cells; wrote %s and %s", result.scored, report_path, detail_path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
