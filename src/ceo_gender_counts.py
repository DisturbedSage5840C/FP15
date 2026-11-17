"""The ceo_type split per leader and the Company_Data Gender counts (`make ceo-gender-counts`).

Counts only: no names, no ids, no cell values. ceo_type is counted per leader (pooled by `name_key`), and also per
post cell. Gender is counted exactly as coded in the file; what 1 and 0 mean is not interpreted here.
"""
from __future__ import annotations

import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.company_data import BLANK_MARKERS, GENDER_COLUMN
from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _table
from src.name_key import name_key
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/ceo_type_gender_counts.md")
POSTS_FILE = "harmonised_posts.csv"
COMPANY_FILE = "company_data.csv"
LEADER_COLUMN = "leader"
CEO_TYPE_COLUMN = "ceo_type"
PROFESSIONAL = "Professional CEO"
FOUNDER = "Founder-CEO"
KNOWN_LABELS = frozenset({PROFESSIONAL, FOUNDER})
CODED_ONE, CODED_ZERO = "1", "0"

_BLANK, _UNRECOGNISED, _CONFLICTING = "blank", "unrecognised", "conflicting"


@dataclass(frozen=True)
class CeoTypeCounts:
    """ceo_type per leader (pooled by name_key) and per post cell; no values are kept."""

    leaders: int
    professional: int
    founder: int
    blank: int
    unrecognised_only: int
    conflicting: int
    cells_professional: int
    cells_founder: int
    cells_blank: int
    cells_unrecognised: int
    cells_without_leader: int


@dataclass(frozen=True)
class GenderCounts:
    """Gender exactly as coded: the strings 1 and 0, blank, and anything else counted apart."""

    rows: int
    coded_1: int
    coded_0: int
    blank: int
    other: int


def _text(value: object) -> str:
    """A cell as stripped text; anything that is not text, and the blank markers, become ''."""
    if not isinstance(value, str):
        return ""
    stripped = value.strip()
    return "" if stripped in BLANK_MARKERS else stripped


def _require(frame: pd.DataFrame, column: str) -> None:
    if column not in frame.columns:
        raise ValueError(f"missing column {column!r}")


def _leader_class(values: set[str]) -> str:
    """One leader's class from the distinct non-blank ceo_type values on their rows."""
    labels = values & KNOWN_LABELS
    if len(labels) > 1:
        return _CONFLICTING
    if labels:
        return next(iter(labels))
    return _UNRECOGNISED if values else _BLANK


def ceo_type_counts(posts: pd.DataFrame) -> CeoTypeCounts:
    """Split ceo_type per leader and per cell; rows with no leader name are counted apart."""
    _require(posts, LEADER_COLUMN)
    _require(posts, CEO_TYPE_COLUMN)
    by_leader: dict[str, set[str]] = defaultdict(set)
    cell_values: list[str] = []
    without_leader = 0
    for leader, raw in zip(posts[LEADER_COLUMN], posts[CEO_TYPE_COLUMN], strict=True):
        key = name_key(leader)
        if not key:
            without_leader += 1
            continue
        value = _text(raw)
        cell_values.append(value)
        by_leader[key].update({value} - {""})
    classes = [_leader_class(values) for values in by_leader.values()]
    return CeoTypeCounts(
        leaders=len(classes),
        professional=classes.count(PROFESSIONAL),
        founder=classes.count(FOUNDER),
        blank=classes.count(_BLANK),
        unrecognised_only=classes.count(_UNRECOGNISED),
        conflicting=classes.count(_CONFLICTING),
        cells_professional=cell_values.count(PROFESSIONAL),
        cells_founder=cell_values.count(FOUNDER),
        cells_blank=cell_values.count(""),
        cells_unrecognised=sum(1 for v in cell_values if v and v not in KNOWN_LABELS),
        cells_without_leader=without_leader,
    )


def gender_counts(company: pd.DataFrame) -> GenderCounts:
    """Count the Gender column as coded; '.', '-' and empty cells are blank, other values are not coerced."""
    _require(company, GENDER_COLUMN)
    values = [_text(v) for v in company[GENDER_COLUMN]]
    return GenderCounts(
        rows=len(values),
        coded_1=values.count(CODED_ONE),
        coded_0=values.count(CODED_ZERO),
        blank=values.count(""),
        other=sum(1 for v in values if v and v not in {CODED_ONE, CODED_ZERO}),
    )


# ---- output -----------------------------------------------------------------------------------


def render_report(ceo: CeoTypeCounts, gender: GenderCounts) -> str:
    """Counts-only Markdown: no names, no ids, no cell values."""
    leader_rows = [
        (PROFESSIONAL, _fmt(ceo.professional)),
        (FOUNDER, _fmt(ceo.founder)),
        ("blank on every row", _fmt(ceo.blank)),
        ("only a value that is neither label", _fmt(ceo.unrecognised_only)),
        ("both labels (conflicting)", _fmt(ceo.conflicting)),
        ("all leaders", _fmt(ceo.leaders)),
    ]
    cell_rows = [
        (PROFESSIONAL, _fmt(ceo.cells_professional)),
        (FOUNDER, _fmt(ceo.cells_founder)),
        ("blank", _fmt(ceo.cells_blank)),
        ("a value that is neither label", _fmt(ceo.cells_unrecognised)),
        ("rows with no leader name (not counted above)", _fmt(ceo.cells_without_leader)),
    ]
    gender_rows = [
        ("coded 1", _fmt(gender.coded_1)),
        ("coded 0", _fmt(gender.coded_0)),
        ("blank", _fmt(gender.blank)),
        ("any other value", _fmt(gender.other)),
        ("all rows", _fmt(gender.rows)),
    ]
    lines = [
        "# ceo_type and Gender counts",
        "",
        "Counts only: no names, no ids, no cell values. Inputs are `data/interim/harmonised_posts.csv` and "
        "`data/interim/company_data.csv` (both git-ignored).",
        "",
        "## ceo_type, per leader",
        "",
        "A leader is one `name_key` in the post workbooks. The column is blank on many rows, so a leader with a "
        "label on some rows counts once under that label. A leader with both labels is counted as conflicting, "
        "not assigned.",
        "",
        *_table(("ceo_type", "Leaders"), leader_rows),
        "",
        "## ceo_type, per post cell",
        "",
        *_table(("ceo_type", "Cells"), cell_rows),
        "",
        "## Company_Data Gender, exactly as coded",
        "",
        "Counted as the strings 1 and 0, with '.', '-' and empty cells treated as blank. What 1 and 0 mean is "
        "not interpreted here: it is an open question for the mentors, and no gender is inferred from names.",
        "",
        *_table(("Value as coded", "Rows"), gender_rows),
        "",
    ]
    return "\n".join(lines)


# ---- entry points -----------------------------------------------------------------------------


def _read(path: Path, columns: list[str]) -> pd.DataFrame:
    return pd.read_csv(path, usecols=columns, dtype=str, keep_default_na=False)


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> int:
    """Verify the raw manifest, count, and write the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        posts = _read(interim_dir / POSTS_FILE, [LEADER_COLUMN, CEO_TYPE_COLUMN])
        company = _read(interim_dir / COMPANY_FILE, [GENDER_COLUMN])
        report = render_report(ceo_type_counts(posts), gender_counts(company))
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("ceo-gender-counts FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
