"""Step 1: the base list of leaders who have posts (`make leader-table`).

The study's base list is the leaders found in the post workbooks. The roster, the wordcount summaries and
Company_Data are enrichment sources: each leader is looked up in them, and names that appear only in an
enrichment source are counted, never reconciled by hand.

data/interim/leader_table.csv (git-ignored) has one row per leader and carries leader_id only, never a name.
The report holds counts only: no names, no ids, no workbook or sheet references.
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.company_columns import _read, leader_post_counts, load_settings
from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _pct, _table
from src.id_key import MissingIdKey
from src.id_matching import AMBIGUOUS, EXACT, LOOSE, NONE, Entity, Match, leader_id_for, match_entities
from src.id_sources import SOURCE_COMPANY, SOURCE_ROSTER, SOURCE_SUMMARIES, sheet_entities
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/leader_table.md")
TABLE_FILE = "leader_table.csv"
POST_COLUMNS = ("leader", "company", "workbook", "sheet_idx", "text_kind")
TABLE_COLUMNS = ("leader_id", "company_match", "in_roster", "in_summaries", "n_raw_post_cells")
ENRICHMENT_SOURCES = (SOURCE_COMPANY, SOURCE_ROSTER, SOURCE_SUMMARIES)
MATCH_ORDER = (EXACT, LOOSE, AMBIGUOUS, NONE)
YES, NO = "yes", "no"


@dataclass(frozen=True)
class LeaderRow:
    """One leader from the post workbooks, with where else the leader was found."""

    leader_id: str
    company_match: str
    in_roster: bool
    in_summaries: bool
    n_raw_post_cells: int


@dataclass(frozen=True)
class LeaderTable:
    rows: tuple[LeaderRow, ...]
    enrichment_only: Mapping[str, int]


EntityId = tuple[str, str]


def _entity_id(entity: Entity) -> EntityId:
    """Sheet refs (workbook#index) are shared by many leaders, so the key is part of the identity."""
    return (entity.ref, entity.key)


def _type_by_entity(matches: Sequence[Match]) -> dict[EntityId, str]:
    """Match type per side-A entity; an ambiguous entity has several rows, all of one type."""
    found: dict[EntityId, str] = {}
    for match in matches:
        found.setdefault((match.ref_a, match.key_a), match.match_type)
    return found


def _count_only_in_source(source: Sequence[Entity], leaders: Sequence[Entity]) -> int:
    """Names in an enrichment source that match no leader with posts (counted, never resolved)."""
    types = _type_by_entity(match_entities(source, leaders))
    return sum(1 for kind in types.values() if kind == NONE)


def build_leader_table(posts: pd.DataFrame, enrichment: Mapping[str, Sequence[Entity]]) -> LeaderTable:
    """One row per distinct leader in `posts`; a source missing from `enrichment` counts as no match."""
    leaders = sheet_entities(posts)
    raw_cells = leader_post_counts(posts)
    types = {
        source: _type_by_entity(match_entities(leaders, enrichment.get(source, ())))
        for source in ENRICHMENT_SOURCES
    }
    rows = tuple(
        sorted(
            (
                LeaderRow(
                    leader_id=leader_id_for(leader.key),
                    company_match=types[SOURCE_COMPANY].get(_entity_id(leader), NONE),
                    in_roster=types[SOURCE_ROSTER].get(_entity_id(leader), NONE) != NONE,
                    in_summaries=types[SOURCE_SUMMARIES].get(_entity_id(leader), NONE) != NONE,
                    n_raw_post_cells=raw_cells.get(leader.key, 0),
                )
                for leader in leaders
            ),
            key=lambda row: row.leader_id,
        )
    )
    only = {source: _count_only_in_source(enrichment.get(source, ()), leaders) for source in ENRICHMENT_SOURCES}
    return LeaderTable(rows, only)


# ---- output -----------------------------------------------------------------------------------


def table_frame(table: LeaderTable) -> pd.DataFrame:
    records = [
        [
            row.leader_id,
            row.company_match,
            YES if row.in_roster else NO,
            YES if row.in_summaries else NO,
            row.n_raw_post_cells,
        ]
        for row in table.rows
    ]
    return pd.DataFrame(records, columns=list(TABLE_COLUMNS))


def _match_lines(rows: Sequence[LeaderRow], min_posts: int) -> list[str]:
    total_by_type = Counter(row.company_match for row in rows)
    eligible_by_type = Counter(row.company_match for row in rows if row.n_raw_post_cells >= min_posts)
    body = [
        (kind, _fmt(total_by_type[kind]), _fmt(eligible_by_type[kind]))
        for kind in MATCH_ORDER
    ]
    header = ("Company_Data match", "Leaders", f"With at least {min_posts} raw post cells")
    return _table(header, body)


def _flag_lines(rows: Sequence[LeaderRow]) -> list[str]:
    total = len(rows)
    roster = sum(row.in_roster for row in rows)
    summaries = sum(row.in_summaries for row in rows)
    body = [
        ("In the roster", _fmt(roster), _fmt(total - roster), _pct(roster, total)),
        ("In the summaries", _fmt(summaries), _fmt(total - summaries), _pct(summaries, total)),
    ]
    return _table(("Enrichment source", "Yes", "No", "Share yes"), body)


def render_report(table: LeaderTable, min_posts: int) -> str:
    """Counts-only Markdown: nothing here can identify a leader, a firm or a workbook."""
    rows = table.rows
    with_raw = sum(1 for row in rows if row.n_raw_post_cells > 0)
    lines = [
        "# Leader table (Step 1)",
        "",
        "The base list is the leaders who have posts. The roster, the summaries and Company_Data only enrich it.",
        "Counts only: no names, no ids, no workbook or sheet references. The row-level table is "
        "`data/interim/leader_table.csv` (git-ignored).",
        "",
        f"- Leaders in the base list: {_fmt(len(rows))}",
        f"- With at least 1 raw post cell: {_fmt(with_raw)}",
        f"- With no raw post cell (cleaned text only): {_fmt(len(rows) - with_raw)}",
        f"- Raw post cells, all leaders: {_fmt(sum(row.n_raw_post_cells for row in rows))}",
        "",
        "## Company_Data match",
        "",
        *_match_lines(rows, min_posts),
        "",
        "The post minimum is read from `configs/thresholds.yaml`. Raw post cells are a cell-level proxy "
        "until author blocks are segmented.",
        "",
        "## Roster and summaries",
        "",
        *_flag_lines(rows),
        "",
        "Yes means at least one candidate was found (exact, loose or ambiguous). Ambiguous matches are "
        "never resolved by hand.",
        "",
        "## Names in an enrichment source with no leader in the base list",
        "",
        *_table(
            ("Source", "Names counted, not resolved"),
            [(source, _fmt(table.enrichment_only.get(source, 0))) for source in ENRICHMENT_SOURCES],
        ),
        "",
    ]
    return "\n".join(lines)


# ---- entry points -----------------------------------------------------------------------------


def _build_enrichment(raw_dir: Path, interim_dir: Path) -> dict[str, tuple[Entity, ...]]:
    from src.ids import _build_sources  # local import: src.ids pulls in the whole matching stack

    sources, _ = _build_sources(raw_dir, interim_dir)
    return {source: sources[source] for source in ENRICHMENT_SOURCES}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    min_posts: int | None = None,
) -> int:
    """Verify the raw manifest, build the table and the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        posts = _read(interim_dir / "harmonised_posts.csv", POST_COLUMNS)
        table = build_leader_table(posts, _build_enrichment(raw_dir, interim_dir))
        floor = load_settings().min_posts if min_posts is None else min_posts
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("leader-table FAILED: %s", error)
        return 1
    table_frame(table).to_csv(interim_dir / TABLE_FILE, index=False)
    logger.info("wrote %s (%d rows)", interim_dir / TABLE_FILE, len(table.rows))
    _write(report_path, render_report(table, floor))
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
