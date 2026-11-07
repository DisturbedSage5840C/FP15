"""Step 4: propose leader_id matches across the four people lists (`make ids`).

Reads the harmonised interim tables plus the wordcount summary sheets, matches with the sorted-token
name key, writes row-level tables to data/interim (git-ignored) and a counts-only report.
Ambiguous names are listed and never resolved.
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from src.harmonise import DEFAULT_INTERIM_DIR, _load_all
from src.id_matching import (
    AMBIGUOUS,
    Entity,
    Match,
    PairSummary,
    ProposalRow,
    match_entities,
    propose_leader_ids,
    summarise_pair,
)
from src.id_report import render_id_report
from src.id_sources import (
    SOURCE_COMPANY,
    SOURCE_ROSTER,
    SOURCE_SHEETS,
    SOURCE_SUMMARIES,
    SummarySheet,
    company_entities,
    roster_entities,
    sheet_entities,
    summary_entities,
)
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/id_matching.md")
PairKey = tuple[str, str]
PAIRS: tuple[PairKey, ...] = (
    (SOURCE_SHEETS, SOURCE_COMPANY),
    (SOURCE_SHEETS, SOURCE_ROSTER),
    (SOURCE_SHEETS, SOURCE_SUMMARIES),
    (SOURCE_ROSTER, SOURCE_SUMMARIES),
    (SOURCE_ROSTER, SOURCE_COMPANY),
    (SOURCE_SUMMARIES, SOURCE_COMPANY),
)
SOURCE_ORDER = (SOURCE_SHEETS, SOURCE_ROSTER, SOURCE_SUMMARIES, SOURCE_COMPANY)
MATCH_COLUMNS = ["source_a", "ref_a", "source_b", "ref_b", "match_type", "n_candidates", "company_agrees"]
AMBIGUOUS_COLUMNS = ["key", "reason", "source_a", "ref_a", "source_b", "ref_b", "n_candidates"]
REF_SEPARATOR = ";"
COMPANY_COLUMNS = frozenset({"CompanyName", "Person_Name"})


def _read_csv(path: Path, columns: frozenset[str] | None = None) -> pd.DataFrame:
    """Read as strings with blanks kept as ''; only `columns` when given (others are never loaded)."""
    usecols = (lambda name: name in columns) if columns is not None else None
    return pd.read_csv(path, dtype=str, keep_default_na=False, usecols=usecols)


def _build_sources(
    raw_dir: Path, interim_dir: Path
) -> tuple[dict[str, tuple[Entity, ...]], tuple[SummarySheet, ...]]:
    summaries, summary_sheets = summary_entities(_load_all(raw_dir))
    sources = {
        SOURCE_SHEETS: sheet_entities(_read_csv(interim_dir / "harmonised_posts.csv")),
        SOURCE_ROSTER: roster_entities(_read_csv(interim_dir / "roster.csv")),
        SOURCE_SUMMARIES: summaries,
        SOURCE_COMPANY: company_entities(_read_csv(interim_dir / "company_data.csv", COMPANY_COLUMNS)),
    }
    return sources, summary_sheets


def _match_pairs(sources: Mapping[str, Sequence[Entity]]) -> dict[PairKey, tuple[Match, ...]]:
    return {(a, b): match_entities(sources[a], sources[b]) for a, b in PAIRS}


def _agrees_text(value: bool | None) -> str:
    return "" if value is None else str(value).lower()


def _matches_frame(matches: Mapping[PairKey, Sequence[Match]]) -> pd.DataFrame:
    rows = [
        [m.source_a, m.ref_a, m.source_b, m.ref_b, m.match_type, m.n_candidates, _agrees_text(m.company_agrees)]
        for pair in matches.values()
        for m in pair
    ]
    return pd.DataFrame(rows, columns=MATCH_COLUMNS)


def _ambiguous_frame(
    sources: Mapping[str, Sequence[Entity]],
    matches: Mapping[PairKey, Sequence[Match]],
    proposal: Sequence[ProposalRow],
) -> pd.DataFrame:
    key_of = {(e.source, e.ref): e.key for items in sources.values() for e in items}
    rows = [
        [key_of[(m.source_a, m.ref_a)], "ambiguous_match", m.source_a, m.ref_a, m.source_b, m.ref_b, m.n_candidates]
        for pair in matches.values()
        for m in pair
        if m.match_type == AMBIGUOUS
    ]
    rows += [
        [row.key, "shared_key", source, ref, "", "", len(refs)]
        for row in proposal
        if row.status == AMBIGUOUS
        for source, refs in row.refs.items()
        if len(refs) > 1
        for ref in refs
    ]
    return pd.DataFrame(rows, columns=AMBIGUOUS_COLUMNS)


def _proposal_frame(proposal: Sequence[ProposalRow]) -> pd.DataFrame:
    rows = [
        [row.leader_id, row.key, row.status, *(REF_SEPARATOR.join(row.refs.get(s, ())) for s in SOURCE_ORDER)]
        for row in proposal
    ]
    return pd.DataFrame(rows, columns=["leader_id", "key", "status", *SOURCE_ORDER])


def _pair_summaries(
    sources: Mapping[str, Sequence[Entity]], matches: Mapping[PairKey, Sequence[Match]]
) -> tuple[PairSummary, ...]:
    return tuple(summarise_pair(sources[a], sources[b], matches[(a, b)]) for a, b in PAIRS)


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> int:
    """Verify the raw manifest, match the lists, write interim tables and the report; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        sources, summary_sheets = _build_sources(raw_dir, interim_dir)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("ids FAILED: %s", error)
        return 1
    matches = _match_pairs(sources)
    proposal = propose_leader_ids(sources)
    tables = {
        "id_matches.csv": _matches_frame(matches),
        "id_ambiguous.csv": _ambiguous_frame(sources, matches, proposal),
        "leader_id_proposal.csv": _proposal_frame(proposal),
    }
    for name, frame in tables.items():
        frame.to_csv(interim_dir / name, index=False)
        logger.info("wrote %s (%d rows)", interim_dir / name, len(frame))
    report = render_id_report(sources, summary_sheets, _pair_summaries(sources, matches), matches, proposal)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
