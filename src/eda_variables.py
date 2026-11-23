"""Variable map with fill rates (`make eda-variables`): every variable we hold, where it comes from, its study role.

Counts only: no names, post text, links, emails, company names or leader ids appear in the report. The raw manifest is
verified first. Fill is counted on three bases: leaders with at least 1 raw cell (post-workbook variables), leaders
with a clear Company_Data match (company variables), and cells (derived variables). "." and "-" are blank, a number
that `parse_quantity` cannot read counts as missing, and nothing is filled in or guessed. The study role of each
variable is a proposal from CLAUDE.md for the humans to confirm; "usable" means at least one value is filled, not that
the variable is adequate. The comparison with the numbers quoted in the write-up is a check: a difference is reported,
never fixed here. No network, no scraping, and no gate is signed off.
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.ceo_gender_counts import CODED_ONE, CODED_ZERO, load_gender_coding
from src.company_columns import RAW_KIND, leader_post_counts
from src.company_data import WATCHED_HEADERS, clean_cell
from src.eda_common import DEFAULT_THRESHOLDS_PATH, EdaSettings, load_eda_settings, show_count, show_share
from src.eda_gaps import (
    COMPANY_COLUMNS,
    COMPANY_SOURCE,
    LEADER,
    POST_COLUMNS,
    POST_SOURCE,
    PROPOSAL_COLUMNS,
    TEXT_KIND,
    _blank_flags,
    _company_rows,
    _post_rows,
    _require,
)
from src.eda_groups import classify_matches, proposal_lookup
from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _table
from src.name_key import name_key
from src.reaction_count_check import find_trailing_number
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/eda_variable_map.md")
DEFAULT_EXPECTED_PATH = Path("configs/writeup_numbers.yaml")

POST_TEXT = "post_text"
AGE_COLUMN = "age_months"
GENDER_COLUMN = "Gender"
DERIVED_SOURCE = "derived"
NO_RATE = "n/a"
YES, NO = "yes", "no"

ROLE_LEADER = "X leader block"
ROLE_FIRM = "X firm block"
ROLE_CONTROL = "control"
ROLE_OUTCOME = "outcome"
ROLE_NOT_USABLE = "not usable"

# Variable shown -> (row key, study role) for the post-workbook variables; the key is the name in eda_gaps.
POST_ROLES = {
    "ceo_type": ROLE_LEADER,
    "current_title": ROLE_LEADER,
    "role_start_year": ROLE_LEADER,
    "post_date": ROLE_CONTROL,
    "post_date_text": ROLE_CONTROL,
}
# Variable shown in eda_gaps.COMPANY_VARIABLES -> row key. Names not listed here become "revenue_2021" and so on.
COMPANY_KEYS = {
    "gender (as coded)": "gender_coded",
    "sector": "sector",
    "firm size (employees)": "firm_size",
    "firm age (founded year)": "founded_year",
    "LinkedIn followers": "followers",
}
COMPANY_ROLES = {"gender_coded": ROLE_LEADER, "followers": ROLE_CONTROL}
EXTRA_IPO_COLUMNS = frozenset({"StockTicker", "Exchange"})
UNVERIFIED_REASON = (
    "Unverified: what these trailing numbers are (reaction counts, years, ages) has not been hand-checked."
)
IPO_REASON = "Every firm in Company_Data is listed, so listed versus unlisted cannot be tested."
UNNAMED_REASON = "The column has no header and its meaning is unknown."
CONTACT_REASON = "Email and phone columns are dropped at load, before anything is written to disk, so they have no fill rate."
NO_VALUE_REASON = "No cell is filled."


@dataclass(frozen=True)
class VariableRow:
    """One variable: where it comes from, its proposed study role, and how many of N are filled (None = no rate)."""

    key: str
    variable: str
    source: str
    role: str
    filled: int | None
    total: int | None
    usable: str
    reason: str


@dataclass(frozen=True)
class Check:
    """A number from the write-up next to the number the data gives."""

    key: str
    expected: int
    observed: int
    matches: bool


def _row(
    key: str, variable: str, source: str, role: str, filled: int | None, total: int | None, usable: str = "", reason: str = ""
) -> VariableRow:
    """A row; unless told otherwise it is usable when at least one value is filled."""
    verdict = usable or (YES if filled else NO)
    why = reason or ("" if filled else NO_VALUE_REASON)
    return VariableRow(key, variable, source, role, filled, total, verdict, why)


# ---- post-workbook variables (leaders with at least 1 raw cell) -------------------------------


def _leader_rows(posts: pd.DataFrame, members: set[str]) -> tuple[VariableRow, ...]:
    raw = pd.DataFrame(posts.loc[posts[TEXT_KIND] == RAW_KIND])
    keys = pd.Series([name_key(name) for name in raw[LEADER]], index=raw.index, dtype=str)
    keep = keys != ""
    gaps = _post_rows(_blank_flags(pd.DataFrame(raw.loc[keep]), pd.Series(keys.loc[keep])), members)
    return tuple(
        _row(gap.variable, gap.variable, POST_SOURCE, POST_ROLES[gap.variable], gap.leaders - gap.missing, gap.leaders)
        for gap in gaps
    )


# ---- Company_Data variables (leaders with a clear match) --------------------------------------


def _gender_rows(
    company: pd.DataFrame,
    positions: list[int],
    coded: VariableRow,
    coding: Mapping[str, str] | None = None,
) -> tuple[VariableRow, ...]:
    if coding is None:
        coding = load_gender_coding()
    values = [clean_cell(company.iloc[position][GENDER_COLUMN]) for position in positions]
    total = len(positions)
    ones, zeros = values.count(CODED_ONE), values.count(CODED_ZERO)
    filled = sum(value is not None for value in values)
    label_1 = f"gender coded 1 ({coding['1']})" if "1" in coding else "gender coded 1"
    label_0 = f"gender coded 0 ({coding['0']})" if "0" in coding else "gender coded 0"
    parts = (
        ("gender_coded_1", label_1, ones),
        ("gender_coded_0", label_0, zeros),
        ("gender_coded_other", "gender coded as another value", filled - ones - zeros),
        ("gender_no_value", "gender with no value", total - filled),
    )
    return tuple(_row(key, name, COMPANY_SOURCE, coded.role, count, total) for key, name, count in parts)


def _company_variable_rows(company: pd.DataFrame, positions: list[int]) -> tuple[VariableRow, ...]:
    rows = []
    for gap in _company_rows(company, positions):
        key = COMPANY_KEYS.get(gap.variable, gap.variable.replace(" ", "_"))
        role = COMPANY_ROLES.get(key, ROLE_FIRM)
        rows.append(_row(key, gap.variable, COMPANY_SOURCE, role, gap.leaders - gap.missing, gap.leaders))
        if key == "gender_coded":
            rows.extend(_gender_rows(company, positions, rows[-1]))
    return tuple(rows)


# ---- columns that are not usable --------------------------------------------------------------


def ipo_columns(columns: Sequence[str]) -> tuple[str, ...]:
    """Company_Data columns about the IPO: any name containing "ipo", plus the ticker and the exchange."""
    return tuple(
        column
        for column in columns
        if column not in COMPANY_COLUMNS and ("ipo" in column.lower() or column in EXTRA_IPO_COLUMNS)
    )


def _any_filled(company: pd.DataFrame, positions: list[int], columns: Sequence[str]) -> int | None:
    """Leaders with at least one filled value in the columns; None when none of the columns exists."""
    present = [column for column in columns if column in company.columns]
    if not present:
        return None
    matched = company.iloc[positions]
    return int(sum(any(clean_cell(value) is not None for value in row) for row in matched[present].itertuples(index=False)))


def _not_usable_rows(company: pd.DataFrame, positions: list[int]) -> tuple[VariableRow, ...]:
    total = len(positions)
    specs = [("ipo_columns", "IPO columns", ipo_columns(list(company.columns)), IPO_REASON)]
    specs.extend(
        (f"unnamed_{header.lower()}", f"unnamed column {header}", (header,), UNNAMED_REASON) for header in WATCHED_HEADERS
    )
    rows = [
        _row(key, name, COMPANY_SOURCE, ROLE_NOT_USABLE, _any_filled(company, positions, columns), total, NO, reason)
        for key, name, columns, reason in specs
    ]
    rows.append(_row("contact_columns", "email and phone columns", COMPANY_SOURCE, ROLE_NOT_USABLE, None, None, NO, CONTACT_REASON))
    return tuple(rows)


# ---- cell-level variables ---------------------------------------------------------------------


def _cell_rows(posts: pd.DataFrame, clean: pd.DataFrame) -> tuple[VariableRow, ...]:
    ages = sum(clean_cell(value) is not None for value in clean[AGE_COLUMN])
    raw_texts = posts.loc[posts[TEXT_KIND] == RAW_KIND, POST_TEXT]
    trailing = sum(find_trailing_number(text) is not None for text in raw_texts)
    return (
        _row("age_parsed", "cells with a parsed relative age", DERIVED_SOURCE, ROLE_CONTROL, ages, len(clean)),
        _row(
            "ends_in_number", "cells ending in a number (unverified)", DERIVED_SOURCE, ROLE_OUTCOME, trailing, len(raw_texts), NO,
            UNVERIFIED_REASON,
        ),
    )


def variable_rows(
    posts: pd.DataFrame, proposal: pd.DataFrame, company: pd.DataFrame, clean: pd.DataFrame
) -> tuple[VariableRow, ...]:
    """The whole variable map; no input is changed."""
    _require(posts, [*POST_COLUMNS, POST_TEXT], "harmonised_posts")
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(company, COMPANY_COLUMNS, "company_data")
    _require(clean, [AGE_COLUMN], "posts_clean")
    members = {key for key, count in leader_post_counts(posts).items() if count >= 1}
    matched, _ = classify_matches(members, proposal_lookup(proposal), len(company))
    positions = list(matched.values())
    return (
        *_leader_rows(posts, members),
        *_company_variable_rows(company, positions),
        *_cell_rows(posts, clean),
        *_not_usable_rows(company, positions),
    )


# ---- comparison with the write-up -------------------------------------------------------------


def load_expected(path: Path) -> dict[str, int]:
    """Read the write-up numbers (row key -> whole number); a value that is not a whole number is named."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(values, dict):
        raise ValueError(f"{path}: expected a mapping of row key to number")
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{path}: {key} is not a whole number")
    return {str(key): int(value) for key, value in values.items()}


def compare_checks(rows: Sequence[VariableRow], expected: Mapping[str, int]) -> tuple[Check, ...]:
    """One check per write-up number; an unknown key or a row with no fill count is an error, not a guess."""
    by_key = {row.key: row for row in rows}
    checks = []
    for key, number in expected.items():
        if key not in by_key:
            raise ValueError(f"write-up numbers: no row for {key}")
        observed = by_key[key].filled
        if observed is None:
            raise ValueError(f"write-up numbers: {key} has no fill count to compare")
        checks.append(Check(key, number, observed, observed == number))
    return tuple(checks)


# ---- the report -------------------------------------------------------------------------------


def fill_texts(filled: int | None, total: int | None, minimum: int) -> tuple[str, str]:
    """"filled of N" and the share missing, with "<5" under the disclosure minimum.

    The share is hidden when either side is small, so a hidden count cannot be recovered from the other.
    """
    if filled is None or total is None:
        return NO_RATE, NO_RATE
    missing = total - filled
    share = show_share(missing, total, minimum) if min(filled, missing) >= minimum else show_count(0, minimum + 1)
    return f"{show_count(filled, minimum)} of {show_count(total, minimum)}", share


def _variable_table(rows: Sequence[VariableRow], settings: EdaSettings) -> list[str]:
    header = ("Variable", "Source", "Study role", "Filled n of N", "Share missing", "Usable?")
    body = []
    for row in rows:
        fill, share = fill_texts(row.filled, row.total, settings.disclosure_min)
        body.append((row.variable, row.source, row.role, fill, share, row.usable))
    return _table(header, body)


def _intro(settings: EdaSettings) -> list[str]:
    return [
        "# EDA: variable map and fill rates",
        "",
        "Counts only: no names, post text, links, emails, company names or leader ids appear here. A count below "
        f'{settings.disclosure_min} shows as "<5" instead of its number, and a share is hidden when either the filled '
        "or the missing side is below that minimum. Every statement is about the image projected in public posts, "
        "never about personality. Nothing is filled in or guessed: missing stays missing. No gate is signed off by "
        "this report. No scraping and no network were used, and scraping_approved stays false.",
        "",
    ]


def _notes(rows: Sequence[VariableRow]) -> list[str]:
    lines = [
        "## Reading the table",
        "",
        "- N is the leaders with at least 1 raw post cell (post-workbook variables), the leaders with a clear "
        "Company_Data match (company variables), or the cells (derived variables).",
        '- "." and "-" count as blank. A number that cannot be read (for example "500+") counts as missing.',
        "- Gender is shown as coded in Company_Data, with labels from configs/gender_coding.yaml (confirmed "
        "2026-11-23 by the project team from the data owner and mentors: 1 = man, 0 = woman). Gender is never "
        "inferred from names.",
        "- Study role is a proposal for the humans to confirm. Usable yes means at least one value is filled; it is "
        "not a judgment that the variable is adequate for a model.",
        "- Cells ending in a number are unverified: they may be reaction counts, years or ages.",
        "",
    ]
    reasons = [f"- {row.variable}: {row.reason}" for row in rows if row.usable == NO and row.reason]
    return [*lines, "## Why a variable is not usable", "", *reasons, ""]


def _checks_section(checks: Sequence[Check], settings: EdaSettings) -> list[str]:
    differing = [check for check in checks if not check.matches]
    head = ["## Checks", "", "Numbers quoted in the write-up (configs/writeup_numbers.yaml) against the data.", ""]
    if not differing:
        return [*head, f"No difference from the write-up numbers ({len(checks)} compared).", ""]
    rows = [
        (check.key, f"{check.expected:,}", show_count(check.observed, settings.disclosure_min), "differs")
        for check in differing
    ]
    summary = f"{len(differing)} of {len(checks)} write-up numbers differ. Each one is a finding for docs/decisions.md."
    return [*head, summary, "", *_table(("Row", "Write-up", "Data", "Result"), rows), ""]


def render_variable_map(rows: Sequence[VariableRow], checks: Sequence[Check], settings: EdaSettings) -> str:
    """The whole report as Markdown text, ending in one newline."""
    lines = [
        *_intro(settings),
        "## Variable map",
        "",
        *_variable_table(rows, settings),
        "",
        *_notes(rows),
        *_checks_section(checks, settings),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# ---- run --------------------------------------------------------------------------------------


def _company_wanted(column: str) -> bool:
    """Only the columns this report counts; names, emails and company names are never loaded."""
    return column in COMPANY_COLUMNS or column in WATCHED_HEADERS or bool(ipo_columns([column]))


def _read(path: Path, wanted: set[str] | None = None) -> pd.DataFrame:
    usecols = _company_wanted if wanted is None else (lambda column: column in wanted)
    return pd.read_csv(path, dtype=str, keep_default_na=False, usecols=usecols)


def _read_inputs(interim_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    posts = _read(interim_dir / "harmonised_posts.csv", {*POST_COLUMNS, POST_TEXT})
    proposal = _read(interim_dir / "leader_id_proposal.csv", set(PROPOSAL_COLUMNS))
    company = _read(interim_dir / "company_data.csv")
    clean = _read(interim_dir / "posts_clean.csv", {AGE_COLUMN})
    return posts, proposal, company, clean


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
    expected_path: Path = DEFAULT_EXPECTED_PATH,
) -> int:
    """Verify the raw manifest, build the report, write it; 0 on success, 1 on a clean failure (nothing written)."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        settings = load_eda_settings(thresholds_path)
        expected = load_expected(expected_path)
        rows = variable_rows(*_read_inputs(interim_dir))
        text = render_variable_map(rows, compare_checks(rows, expected), settings)
    except (ManifestMismatch, FileNotFoundError, ValueError, KeyError) as error:
        logger.error("eda-variables FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
