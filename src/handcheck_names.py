"""Step 2: hand-check file for Company_Data matches a human has to look at (`make handcheck`).

Three kinds of leader (from the post workbooks) are listed with their candidate Company_Data rows side by side:
  - ambiguous: the name key matched more than one Company_Data row, or the leader key is shared;
  - no_match: no Company_Data row has the same name key; the nearest rows (shared name tokens, or the
    same company) are offered as candidates, never chosen;
  - company_differs: one exact name match whose company disagrees with the company on the sheet.

The file holds names and company names, so it lives in data/derived (git-ignored) and is never committed.
Every cell is defused against spreadsheet formulas. The log reports counts only. The two human_* columns
are left empty: a person decides, code does not.
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.company_columns import _read
from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import AMBIGUOUS, EXACT, NONE, Entity, Match, leader_id_for, match_entities
from src.id_sources import COMPANY_FIRM_COLUMN, COMPANY_NAME_COLUMN, company_entities, sheet_entities
from src.name_key import name_key
from src.reaction_count_check import spreadsheet_safe
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_OUT_DIR = Path("data/derived")
OUTPUT_FILE = "handcheck_names.csv"
POST_COLUMNS = ("leader", "company", "workbook", "sheet_idx", "text_kind")
COMPANY_TITLE_COLUMN = "Current_Title"

CASE_AMBIGUOUS = "ambiguous"
CASE_NO_MATCH = "no_match"
CASE_COMPANY_DIFFERS = "company_differs"
CASE_ORDER = (CASE_AMBIGUOUS, CASE_NO_MATCH, CASE_COMPANY_DIFFERS)

BASIS_AMBIGUOUS = "ambiguous_match"
BASIS_NAME_TOKENS = "shared_name_tokens"
BASIS_SAME_COMPANY = "same_company"
BASIS_EXACT = "exact_match_company_differs"
BASIS_NONE_FOUND = "no_candidate_found"

MAX_NEAR_CANDIDATES = 5
OUTPUT_COLUMNS = (
    "case",
    "leader_id",
    "sheet_name",
    "sheet_company",
    "n_candidates",
    "candidate_rank",
    "company_row",
    "company_person_name",
    "company_firm",
    "company_current_title",
    "candidate_basis",
    "shared_tokens",
    "human_decision",
    "human_note",
)


@dataclass(frozen=True)
class HandcheckRow:
    """One candidate line (or one line saying there is none) for one leader."""

    case: str
    leader_id: str
    sheet_name: str
    sheet_company: str
    n_candidates: int
    candidate_rank: int
    company_row: str
    company_person_name: str
    company_firm: str
    company_current_title: str
    candidate_basis: str
    shared_tokens: int


@dataclass(frozen=True)
class _SheetLeader:
    name: str
    company: str


def _sheet_leaders(posts: pd.DataFrame) -> dict[str, _SheetLeader]:
    """Name and company as written on the sheets, per name key (first non-blank value wins)."""
    names: dict[str, str] = {}
    firms: dict[str, str] = {}
    for leader, company in zip(posts["leader"], posts["company"], strict=True):
        key = name_key(leader)
        if not key:
            continue
        names.setdefault(key, str(leader))
        if str(company).strip():
            firms.setdefault(key, str(company))
    return {key: _SheetLeader(names[key], firms.get(key, "")) for key in names}


def _company_fields(company: pd.DataFrame, ref: str) -> tuple[str, str, str]:
    """Person name, firm and current title of the Company_Data row a `row:<n>` ref points at."""
    record = company.iloc[int(ref.split(":")[1]) - 1]
    title = str(record[COMPANY_TITLE_COLUMN]) if COMPANY_TITLE_COLUMN in company.columns else ""
    firm = str(record[COMPANY_FIRM_COLUMN]) if COMPANY_FIRM_COLUMN in company.columns else ""
    return str(record[COMPANY_NAME_COLUMN]), firm, title


def _row(
    case: str,
    key: str,
    sheet: _SheetLeader,
    company: pd.DataFrame,
    *,
    n_candidates: int,
    rank: int,
    ref: str,
    basis: str,
    shared: int = 0,
) -> HandcheckRow:
    person, firm, title = _company_fields(company, ref) if ref else ("", "", "")
    return HandcheckRow(
        case, leader_id_for(key), sheet.name, sheet.company, n_candidates, rank, ref, person, firm, title,
        basis, shared,
    )


def _matches_by_key(matches: Sequence[Match], kind: str) -> dict[str, list[Match]]:
    grouped: dict[str, list[Match]] = {}
    for match in matches:
        if match.match_type == kind:
            grouped.setdefault(match.key_a, []).append(match)
    return grouped


def _near_candidates(leader: Entity, pool: Sequence[Entity]) -> list[tuple[Entity, int, str]]:
    """Company rows sharing a name token or the company with the leader, best first."""
    mine = frozenset(leader.key.split())
    found: list[tuple[Entity, int, str]] = []
    for entity in pool:
        shared = len(mine & frozenset(entity.key.split()))
        same_firm = bool(leader.company_key) and leader.company_key == entity.company_key
        if shared or same_firm:
            found.append((entity, shared, BASIS_NAME_TOKENS if shared else BASIS_SAME_COMPANY))
    found.sort(key=lambda item: (-item[1], item[2] != BASIS_NAME_TOKENS, int(item[0].ref.split(":")[1])))
    return found


def _ambiguous_rows(matches: Sequence[Match], sheets: dict[str, _SheetLeader], company: pd.DataFrame) -> list[HandcheckRow]:
    return [
        _row(CASE_AMBIGUOUS, key, sheets[key], company, n_candidates=group[0].n_candidates, rank=rank,
             ref=match.ref_b, basis=BASIS_AMBIGUOUS)
        for key, group in _matches_by_key(matches, AMBIGUOUS).items()
        for rank, match in enumerate(group, start=1)
    ]


def _no_match_rows(
    matches: Sequence[Match],
    leaders: dict[str, Entity],
    pool: Sequence[Entity],
    sheets: dict[str, _SheetLeader],
    company: pd.DataFrame,
) -> list[HandcheckRow]:
    rows: list[HandcheckRow] = []
    for key in _matches_by_key(matches, NONE):
        found = _near_candidates(leaders[key], pool)
        if not found:
            rows.append(_row(CASE_NO_MATCH, key, sheets[key], company, n_candidates=0, rank=1, ref="",
                             basis=BASIS_NONE_FOUND))
        rows.extend(
            _row(CASE_NO_MATCH, key, sheets[key], company, n_candidates=len(found), rank=rank,
                 ref=entity.ref, basis=basis, shared=shared)
            for rank, (entity, shared, basis) in enumerate(found[:MAX_NEAR_CANDIDATES], start=1)
        )
    return rows


def _company_differs_rows(matches: Sequence[Match], sheets: dict[str, _SheetLeader], company: pd.DataFrame) -> list[HandcheckRow]:
    return [
        _row(CASE_COMPANY_DIFFERS, key, sheets[key], company, n_candidates=1, rank=1, ref=group[0].ref_b,
             basis=BASIS_EXACT)
        for key, group in _matches_by_key(matches, EXACT).items()
        if group[0].company_agrees is False
    ]


def build_handcheck(posts: pd.DataFrame, company: pd.DataFrame) -> tuple[HandcheckRow, ...]:
    """Candidate rows for every ambiguous, unmatched and company-mismatched leader, grouped by case."""
    leaders = sheet_entities(posts)
    pool = company_entities(company)
    matches = match_entities(leaders, pool)
    sheets = _sheet_leaders(posts)
    by_key = {leader.key: leader for leader in leaders}
    rows = [
        *_ambiguous_rows(matches, sheets, company),
        *_no_match_rows(matches, by_key, pool, sheets, company),
        *_company_differs_rows(matches, sheets, company),
    ]
    rows.sort(key=lambda row: (CASE_ORDER.index(row.case), row.leader_id))
    return tuple(rows)


# ---- output -----------------------------------------------------------------------------------


def handcheck_frame(rows: Sequence[HandcheckRow]) -> pd.DataFrame:
    """The hand-check table; every cell is text and safe to open in a spreadsheet."""
    records = [
        [
            row.case, row.leader_id, row.sheet_name, row.sheet_company, row.n_candidates, row.candidate_rank,
            row.company_row, row.company_person_name, row.company_firm, row.company_current_title,
            row.candidate_basis, row.shared_tokens, "", "",
        ]
        for row in rows
    ]
    frame = pd.DataFrame(records, columns=list(OUTPUT_COLUMNS))
    return frame.astype(str).apply(lambda column: column.map(spreadsheet_safe))


def _log_counts(rows: Sequence[HandcheckRow]) -> None:
    leaders_by_case = Counter(case for case, _ in {(row.case, row.leader_id) for row in rows})
    for case in CASE_ORDER:
        logger.info("handcheck %s: %d leaders", case, leaders_by_case[case])
    logger.info("handcheck candidate lines: %d", len(rows))


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> int:
    """Verify the raw manifest and write the hand-check file; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        posts = _read(interim_dir / "harmonised_posts.csv", POST_COLUMNS)
        company = _read(interim_dir / "company_data.csv", (COMPANY_NAME_COLUMN,))
        rows = build_handcheck(posts, company)
        frame = handcheck_frame(rows)
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("handcheck FAILED: %s", error)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_dir / OUTPUT_FILE, index=False)
    _log_counts(rows)
    logger.info("wrote %s (git-ignored; holds names)", out_dir / OUTPUT_FILE)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
