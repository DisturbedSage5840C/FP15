"""Step 14A: the widened leader master table (`make leader-master`).

The study universe is every distinct leader key across the four sources:
- post sheets (harmonised_posts.csv)
- roster (roster.csv)
- wordcount summaries (Company_Data summary sheets)
- Company_Data (company_data.csv)

data/interim/leader_master.csv (git-ignored) has one row per leader; it carries leader_id only,
never a name. The report holds counts only: no names, no ids, no workbook or sheet references.

Matching ladder (applied to Company_Data person rows):
  1. name_exact  - sorted-token key matches 1:1
  2. name_loose  - the existing loose rule (token subset, MIN_LOOSE_TOKENS, claimed by one)
  3. company_name - still-unmatched leaders: match on company-name key (name_key of CompanyName)
  4. domain       - still-unmatched leaders: match on the registrable domain label
  Steps 3 and 4 are accepted only when they point to exactly one firm row; otherwise ambiguous.

A firm row reached by step 3 or 4 for two or more leaders is recorded in firm_row_claims for each.

An internally shared roster or summary key is not a reason to exclude a leader.  Its
source-specific fields are not used as a match input and the output records that fact.
Internally shared post-sheet and Company_Data keys are not merged: each source entry
gets an opaque, distinct leader id and a source-specific shared-key flag.
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.company_data import clean_cell
from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey, load_id_key
from src.id_matching import (
    AMBIGUOUS,
    EXACT,
    LOOSE,
    NONE,
    Entity,
    make_entity,
    match_entities,
)
from src.id_sources import SOURCE_COMPANY, SOURCE_ROSTER, SOURCE_SHEETS, SOURCE_SUMMARIES
from src.leader_ladder import (
    AMBIGUOUS as _LAD_AMBIGUOUS,
    COMPANY_NAME,
    DOMAIN,
    NAME_EXACT,
    NAME_LOOSE,
    NONE as _LAD_NONE,
    FirmIndex,
    FirmStep,
    build_firm_index,
    resolve_by_firm,
)
from src.name_key import name_key
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/leader_master.md")
MASTER_FILE = "leader_master.csv"

# Columns carried from Company_Data when a name match (exact or loose) is found:
# the person-level columns (person-specific, not firm-level).
PERSON_COLUMNS: tuple[str, ...] = (
    "Current_Title",
    "Gender",
)

# Columns carried from Company_Data when any step finds a firm row (name, company, domain):
# firm-level columns that belong to the company, not specifically to the person.
FIRM_COLUMNS: tuple[str, ...] = (
    "TotalEmployeeCount",
    "SectorPraticeAreaFeed",
    "FoundedYear",
    "LatestRevenueUSD",
    "NumberofEmployees",
    "ProfitUSD2024",
    "CompanyStage",
    "Country",
    "State",
    "IsFunded",
    "TotalFundingUSD",
)

# Columns that are NEVER written to the output (they are identifying):
_BLOCKED_COLUMNS = frozenset({
    "Person_Name", "CompanyName", "DomainName",
    "LinkedIn_Profile_Link", "Website", "LinkedIn", "Twitter", "Facebook",
    "BlogUrl", "TracxnURL", "LinkstoKeyPeopleProfiles",
})

# Match-method labels (the unified ladder vocabulary):
_NAME_EXACT = NAME_EXACT
_NAME_LOOSE = NAME_LOOSE
_COMPANY_NAME = COMPANY_NAME
_DOMAIN = DOMAIN
_AMBIGUOUS = AMBIGUOUS   # re-use from id_matching for step-1/2 ambiguous
_NONE = NONE

# columns_scope values
SCOPE_PERSON_AND_FIRM = "person_and_firm"
SCOPE_FIRM_ONLY = "firm_only"
SCOPE_NONE = "none"

POST_COLUMNS = ("leader", "company", "workbook", "sheet_idx", "text_kind")


@dataclass(frozen=True)
class MasterResult:
    frame: pd.DataFrame
    excluded_ambiguous_keys: int  # retained for report-call compatibility; always zero


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path, columns: Sequence[str] | None = None) -> pd.DataFrame:
    usecols = list(columns) if columns else None
    return pd.read_csv(path, dtype=str, keep_default_na=False, usecols=usecols)


def _safe_columns(df: pd.DataFrame, wanted: Sequence[str]) -> list[str]:
    """Return wanted columns that actually exist in df."""
    return [c for c in wanted if c in df.columns]


def _assert_columns(df: pd.DataFrame, required: Sequence[str], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: missing column(s): {missing!r}")


# ---------------------------------------------------------------------------
# universe: union of all four sources
# ---------------------------------------------------------------------------


def _all_entities(sources: Mapping[str, Sequence[Entity]]) -> dict[str, Entity]:
    """One entity per distinct name key across all sources; first occurrence wins for the ref."""
    seen: dict[str, Entity] = {}
    # process in stable order: sheets, roster, summaries, company
    order = (SOURCE_SHEETS, SOURCE_ROSTER, SOURCE_SUMMARIES, SOURCE_COMPANY)
    for src in order:
        for entity in sources.get(src, ()):
            if entity.key not in seen:
                seen[entity.key] = entity
    return seen


# ---------------------------------------------------------------------------
# step-1/2 name matching (delegated to existing id_matching logic)
# ---------------------------------------------------------------------------


def _name_match_method(match_type: str) -> str:
    """Convert id_matching match types to our ladder vocabulary."""
    return {EXACT: NAME_EXACT, LOOSE: NAME_LOOSE, AMBIGUOUS: AMBIGUOUS, NONE: NONE}[match_type]


def _build_name_matches(
    leaders: Sequence[Entity],
    company_entities: Sequence[Entity],
) -> dict[str, tuple[str, list[int]]]:
    """
    Returns {leader_key: (match_method, [company_row_indices])}.
    Row indices are 0-based positions in company_entities.
    """
    if not company_entities:
        return {}

    matches = match_entities(list(leaders), list(company_entities))
    # group by leader key
    result: dict[str, tuple[str, list[int]]] = {}
    for m in matches:
        key = m.key_a
        if not key:
            continue
        method = _name_match_method(m.match_type)
        # get the index of the matched company entity
        if m.match_type in (NONE,):
            if key not in result:
                result[key] = (method, [])
        else:
            # find the position of the matched ref in company_entities
            if m.ref_b:
                # ref format is "row:N" (1-based)
                try:
                    idx = int(m.ref_b.split("row:")[-1]) - 1
                except (ValueError, IndexError):
                    idx = -1
            else:
                idx = -1

            if key not in result:
                result[key] = (method, [idx] if idx >= 0 else [])
            else:
                existing_method, existing_idxs = result[key]
                # keep the same method; add more candidate rows
                if idx >= 0 and idx not in existing_idxs:
                    existing_idxs.append(idx)
    return result


# ---------------------------------------------------------------------------
# step-3: company name and domain matching
# ---------------------------------------------------------------------------


def _company_key_for_entity(entity: Entity) -> str:
    """The company name as a name_key (sorted-token), already on the entity."""
    return entity.company_key


# ---------------------------------------------------------------------------
# pull firm rows
# ---------------------------------------------------------------------------


def _firm_row(company: pd.DataFrame, row_idx: int) -> pd.Series:
    return company.iloc[row_idx]


def _copy_columns(
    company: pd.DataFrame,
    row_idx: int,
    columns: Sequence[str],
) -> dict[str, str]:
    row = company.iloc[row_idx]
    out: dict[str, str] = {}
    for col in columns:
        if col in company.columns:
            val = clean_cell(row[col])
            out[col] = "" if val is None else val
        else:
            out[col] = ""
    return out


# ---------------------------------------------------------------------------
# in_<source> flags
# ---------------------------------------------------------------------------


def _source_flags(key: str, sources: Mapping[str, Sequence[Entity]]) -> dict[str, bool]:
    return {
        "in_posts": any(e.key == key for e in sources.get(SOURCE_SHEETS, ())),
        "in_roster": any(e.key == key for e in sources.get(SOURCE_ROSTER, ())),
        "in_summaries": any(e.key == key for e in sources.get(SOURCE_SUMMARIES, ())),
        "in_company": any(e.key == key for e in sources.get(SOURCE_COMPANY, ())),
    }


def _entities_by_key(entities: Sequence[Entity]) -> dict[str, list[Entity]]:
    grouped: dict[str, list[Entity]] = {}
    for entity in entities:
        grouped.setdefault(entity.key, []).append(entity)
    return grouped


def _entry_id_key(key: str, source: str, ordinal: int) -> str:
    """A non-reversible HMAC input for an entry that may not be merged by key."""
    return f"{key}|{source}|{ordinal}"


# ---------------------------------------------------------------------------
# main build function
# ---------------------------------------------------------------------------


def build_master(
    sources: Mapping[str, Sequence[Entity]],
    company: pd.DataFrame,
    post_counts: Mapping[str, int],
    id_of: Callable[[str], str],
) -> MasterResult:
    """
    Build the master frame: one row per distinct leader key across all four sources.

    Parameters
    ----------
    sources:       entities per source (sheets, roster, summaries, company)
    company:       the full cleaned Company_Data frame (must have PERSON_COLUMNS and FIRM_COLUMNS)
    post_counts:   {name_key: raw_post_cell_count}
    id_of:         callable from name_key -> leader_id string

    Returns
    -------
    MasterResult with the frame and the count of excluded ambiguous keys.
    """
    # validate required columns
    required_person = list(PERSON_COLUMNS)
    required_firm = [c for c in FIRM_COLUMNS if c in company.columns]
    _assert_columns(company, required_person, "Company_Data (PERSON_COLUMNS)")

    # --- entities by source/key, and Company_Data row positions ---
    # Company entities have ref="row:N" (1-based); preserve every position rather
    # than silently choosing one for a duplicated Company_Data key.
    comp_entities = list(sources.get(SOURCE_COMPANY, ()))
    grouped = {src: _entities_by_key(ents) for src, ents in sources.items()}
    _comp_key_to_rows: dict[str, list[int]] = {}
    for ent in comp_entities:
        try:
            idx = int(ent.ref.split("row:")[-1]) - 1
            _comp_key_to_rows.setdefault(ent.key, []).append(idx)
        except (ValueError, IndexError):
            pass

    # --- build the full universe and the physical records to retain ---
    universe = _all_entities(sources)
    universe_keys = sorted(universe.keys())
    records: list[tuple[str, Entity, str, dict[str, bool], int]] = []
    for key in universe_keys:
        per_source = {src: grouped.get(src, {}).get(key, []) for src in (
            SOURCE_SHEETS, SOURCE_ROSTER, SOURCE_SUMMARIES, SOURCE_COMPANY
        )}
        post_shared = len(per_source[SOURCE_SHEETS]) > 1
        company_shared = len(per_source[SOURCE_COMPANY]) > 1
        roster_shared = len(per_source[SOURCE_ROSTER]) > 1
        summary_shared = len(per_source[SOURCE_SUMMARIES]) > 1

        # A shared post or Company_Data key is not one person that can safely be
        # merged. Keep each relevant source entry separately. Roster/summary rows
        # are enrichment only and therefore never create extra master records.
        if post_shared or company_shared:
            physical = [
                *( (SOURCE_SHEETS, entity) for entity in per_source[SOURCE_SHEETS] ),
                *( (SOURCE_COMPANY, entity) for entity in per_source[SOURCE_COMPANY] ),
            ]
            for ordinal, (source, entity) in enumerate(physical, start=1):
                flags = {
                    "in_posts": source == SOURCE_SHEETS,
                    "in_roster": bool(per_source[SOURCE_ROSTER]) and not roster_shared,
                    "in_summaries": bool(per_source[SOURCE_SUMMARIES]) and not summary_shared,
                    "in_company": source == SOURCE_COMPANY,
                    "roster_key_shared": roster_shared,
                    "summary_key_shared": summary_shared,
                    "post_key_shared": post_shared,
                    "company_key_shared": company_shared,
                }
                # post_counts is keyed only by name key. Never duplicate its cells
                # across separately retained ambiguous post entries.
                raw_cells = post_counts.get(key, 0) if source == SOURCE_SHEETS and ordinal == 1 else 0
                records.append((_entry_id_key(key, source, ordinal), entity, key, flags, raw_cells))
        else:
            # A unique post-sheet key is the preferred match input; otherwise use
            # the unique Company_Data row. Shared roster/summary values cannot
            # supply an entity or company value for matching.
            entity = (
                per_source[SOURCE_SHEETS][0] if per_source[SOURCE_SHEETS]
                else per_source[SOURCE_COMPANY][0] if per_source[SOURCE_COMPANY]
                else per_source[SOURCE_ROSTER][0] if len(per_source[SOURCE_ROSTER]) == 1
                else per_source[SOURCE_SUMMARIES][0]
            )
            flags = {
                "in_posts": bool(per_source[SOURCE_SHEETS]),
                "in_roster": bool(per_source[SOURCE_ROSTER]) and not roster_shared,
                "in_summaries": bool(per_source[SOURCE_SUMMARIES]) and not summary_shared,
                "in_company": bool(per_source[SOURCE_COMPANY]),
                "roster_key_shared": roster_shared,
                "summary_key_shared": summary_shared,
                "post_key_shared": False,
                "company_key_shared": False,
            }
            records.append((key, entity, key, flags, post_counts.get(key, 0)))

    # --- build firm index for step 3 ---
    if "CompanyName" in company.columns and "DomainName" in company.columns:
        firm_index = build_firm_index(company)
    else:
        firm_index = None

    # --- step 1 & 2: name matching ---
    # Only match non-company-source leaders against company entities.
    # Leaders that live IN Company_Data already know their row directly.
    # For leaders in non-company sources, run the full ladder.
    non_company_entities = [entity for _, entity, key, flags, _ in records if entity.source != SOURCE_COMPANY]
    name_matches = _build_name_matches(non_company_entities, comp_entities)

    # --- build firm_row_claims counter ---
    # Counts all leaders that resolve to each firm row (via any step).
    # firm_row_claims[row_idx] = all retained record ids that point there
    all_row_claimants: dict[int, list[str]] = {}

    # Pre-compute: for all leaders, which firm row do they resolve to?
    # We need a dry-run of the full matching to gather claimants.
    for record_id, entity, key, flags, _ in records:
        firm_row_idx_dry: int | None = None

        if entity.source == SOURCE_COMPANY:
            firm_row_idx_dry = int(entity.ref.split("row:")[-1]) - 1
        else:
            nm_result_dry = name_matches.get(key, (NONE, []))
            nm_method_dry, nm_idxs_dry = nm_result_dry
            if nm_method_dry in (NAME_EXACT, NAME_LOOSE) and nm_idxs_dry:
                firm_row_idx_dry = nm_idxs_dry[0]
            elif nm_method_dry in (NONE, AMBIGUOUS) and firm_index is not None:
                ck_dry = _company_key_for_entity(entity)
                if ck_dry:
                    step_dry = resolve_by_firm(ck_dry, firm_index)
                    if step_dry.method in (COMPANY_NAME, DOMAIN) and step_dry.rows:
                        firm_row_idx_dry = step_dry.rows[0]

        if firm_row_idx_dry is not None:
            all_row_claimants.setdefault(firm_row_idx_dry, []).append(record_id)

    # --- now build one row per leader ---
    rows: list[dict] = []
    for record_id, entity, key, flags, raw_cells in records:
        leader_id = id_of(record_id)

        match_method: str
        person_data: dict[str, str] = {}
        firm_data: dict[str, str] = {}
        scope: str
        n_candidates: int = 0
        firm_row_idx: int | None = None

        # Leaders that are IN Company_Data get their row directly (name_exact by definition)
        if entity.source == SOURCE_COMPANY:
            firm_row_idx = int(entity.ref.split("row:")[-1]) - 1
            person_data = _copy_columns(company, firm_row_idx, PERSON_COLUMNS)
            firm_data = _copy_columns(company, firm_row_idx, required_firm)
            scope = SCOPE_PERSON_AND_FIRM
            match_method = NAME_EXACT
            n_candidates = 1

        else:
            # apply the name ladder
            nm_result = name_matches.get(key, (NONE, []))
            nm_method, nm_row_idxs = nm_result

            if nm_method == NAME_EXACT:
                if nm_row_idxs:
                    firm_row_idx = nm_row_idxs[0]
                    person_data = _copy_columns(company, firm_row_idx, PERSON_COLUMNS)
                    firm_data = _copy_columns(company, firm_row_idx, required_firm)
                    scope = SCOPE_PERSON_AND_FIRM
                    n_candidates = 1
                else:
                    scope = SCOPE_NONE
                match_method = NAME_EXACT

            elif nm_method == NAME_LOOSE:
                if nm_row_idxs:
                    firm_row_idx = nm_row_idxs[0]
                    person_data = _copy_columns(company, firm_row_idx, PERSON_COLUMNS)
                    firm_data = _copy_columns(company, firm_row_idx, required_firm)
                    scope = SCOPE_PERSON_AND_FIRM
                    n_candidates = 1
                else:
                    scope = SCOPE_NONE
                match_method = NAME_LOOSE

            elif nm_method == AMBIGUOUS:
                # ambiguous name match – try step 3 (company name, then domain)
                if firm_index is not None:
                    ck = _company_key_for_entity(entity)
                    step = resolve_by_firm(ck, firm_index) if ck else FirmStep(_LAD_NONE, ())
                else:
                    step = FirmStep(_LAD_NONE, ())

                if step.method in (COMPANY_NAME, DOMAIN):
                    firm_row_idx = step.rows[0]
                    firm_data = _copy_columns(company, firm_row_idx, required_firm)
                    scope = SCOPE_FIRM_ONLY
                    match_method = step.method
                    n_candidates = 1
                else:
                    # step 3 did not resolve to exactly one counterpart; stays ambiguous
                    match_method = AMBIGUOUS
                    scope = SCOPE_NONE
                    n_candidates = len(step.rows) if step.method == _LAD_AMBIGUOUS else len(nm_row_idxs)

            else:
                # NONE → try step 3 (company name, then domain)
                if firm_index is not None:
                    ck = _company_key_for_entity(entity)
                    step = resolve_by_firm(ck, firm_index) if ck else FirmStep(_LAD_NONE, ())
                else:
                    step = FirmStep(_LAD_NONE, ())

                if step.method == COMPANY_NAME:
                    firm_row_idx = step.rows[0]
                    firm_data = _copy_columns(company, firm_row_idx, required_firm)
                    scope = SCOPE_FIRM_ONLY
                    match_method = COMPANY_NAME
                    n_candidates = 1

                elif step.method == DOMAIN:
                    firm_row_idx = step.rows[0]
                    firm_data = _copy_columns(company, firm_row_idx, required_firm)
                    scope = SCOPE_FIRM_ONLY
                    match_method = DOMAIN
                    n_candidates = 1

                elif step.method == _LAD_AMBIGUOUS:
                    match_method = AMBIGUOUS
                    scope = SCOPE_NONE
                    n_candidates = len(step.rows)

                else:
                    match_method = NONE
                    scope = SCOPE_NONE

        # firm_row_claims
        if firm_row_idx is not None:
            firm_row_claims = len(all_row_claimants.get(firm_row_idx, []))
        else:
            firm_row_claims = 0

        # has_company_name: the leader's own company key is non-blank
        has_company_name = bool(entity.company_key)

        # has_domain: check domain in the matched firm row (or for in-company leaders, their row)
        has_domain = False
        if firm_row_idx is not None and "DomainName" in company.columns:
            dom_val = clean_cell(company.iloc[firm_row_idx]["DomainName"])
            has_domain = dom_val is not None and dom_val != ""
        elif firm_index is not None and entity.company_key:
            from src.leader_ladder import squash
            sq = squash(entity.company_key)
            has_domain = sq in firm_index.by_domain if sq else False

        # gender_as_coded: from person or firm columns
        gender_raw = person_data.get("Gender", firm_data.get("Gender", ""))

        all_person = {col: person_data.get(col, "") for col in PERSON_COLUMNS}
        all_firm = {col: firm_data.get(col, "") for col in required_firm}
        for col in FIRM_COLUMNS:
            if col not in all_firm:
                all_firm[col] = ""

        row = {
            "leader_id": leader_id,
            "in_posts": flags["in_posts"],
            "in_roster": flags["in_roster"],
            "in_summaries": flags["in_summaries"],
            "in_company": flags["in_company"],
            "roster_key_shared": flags["roster_key_shared"],
            "summary_key_shared": flags["summary_key_shared"],
            "post_key_shared": flags["post_key_shared"],
            "company_key_shared": flags["company_key_shared"],
            "raw_post_cells": raw_cells,
            "match_method": match_method,
            "gender_as_coded": gender_raw,
            "columns_scope": scope,
            "n_candidates": n_candidates,
            "firm_row_claims": firm_row_claims,
            "has_company_name": has_company_name,
            "has_domain": has_domain,
            **all_person,
            **all_firm,
        }
        rows.append(row)

    # Remove any blocked columns from output
    frame = pd.DataFrame(rows).sort_values("leader_id").reset_index(drop=True)
    for col in _BLOCKED_COLUMNS:
        if col in frame.columns:
            frame = frame.drop(columns=[col])

    return MasterResult(frame=frame, excluded_ambiguous_keys=0)


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------


def _load_sources(raw_dir: Path, interim_dir: Path) -> tuple[
    dict[str, tuple[Entity, ...]],
    pd.DataFrame,
    dict[str, int],
]:
    """Load all four sources; return (sources, company_frame, post_counts)."""
    from src.company_columns import leader_post_counts
    from src.harmonise import _load_all
    from src.id_sources import (
        company_entities,
        roster_entities,
        sheet_entities,
        summary_entities,
    )

    posts = _read_csv(interim_dir / "harmonised_posts.csv")
    roster = _read_csv(interim_dir / "roster.csv")
    company = _read_csv(interim_dir / "company_data.csv")

    try:
        summaries, _ = summary_entities(_load_all(raw_dir))
    except FileNotFoundError:
        summaries = ()

    sources: dict[str, tuple[Entity, ...]] = {
        SOURCE_SHEETS: sheet_entities(posts),
        SOURCE_ROSTER: roster_entities(roster),
        SOURCE_SUMMARIES: summaries,
        SOURCE_COMPANY: company_entities(company),
    }
    post_counts = leader_post_counts(posts)
    return sources, company, post_counts


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    out_path: Path | None = None,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path | None = None,
    id_of: Callable[[str], str] | None = None,
) -> int:
    """Build the master table and report; 0 on success, 1 on a clean failure (nothing written)."""
    from src.eda_common import load_eda_settings
    from src.id_matching import leader_id_for
    from src.leader_master_report import render_report

    if out_path is None:
        out_path = interim_dir / MASTER_FILE
    if id_of is None:
        id_of = leader_id_for
    if thresholds_path is None:
        thresholds_path = Path("configs/thresholds.yaml")

    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        sources, company, post_counts = _load_sources(raw_dir, interim_dir)
        settings = load_eda_settings(thresholds_path)
        result = build_master(sources, company, post_counts, id_of)
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey, KeyError) as error:
        logger.error("leader-master FAILED: %s", error)
        return 1

    # write table (git-ignored)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.frame.to_csv(out_path, index=False)
    logger.info("wrote %s (%d rows)", out_path, len(result.frame))

    # write report
    report = render_report(result.frame, result.excluded_ambiguous_keys, settings)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
