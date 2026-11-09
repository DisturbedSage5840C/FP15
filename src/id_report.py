"""Counts-only markdown report for ID matching (reports/id_matching.md).

Privacy: only file paths, sheet indexes and counts appear. No names, company names or row refs.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from src.harmonise_report import SUPERSEDED_LEADER_NOTE, _fmt, _pct, _table
from src.id_matching import AMBIGUOUS, CLEAR, EXACT, Entity, Match, PairSummary, ProposalRow, duplicate_keys
from src.id_sources import SOURCE_COMPANY, SOURCE_ROSTER, SOURCE_SHEETS, SOURCE_SUMMARIES, SummarySheet

SOURCE_FILES: dict[str, str] = {
    SOURCE_SHEETS: "harmonised posts table (git-ignored, data/interim)",
    SOURCE_ROSTER: "roster table (git-ignored, data/interim; the roster workbook is loaded once)",
    SOURCE_SUMMARIES: "the summary sheet of every wordcount workbook (counted below)",
    SOURCE_COMPANY: "company table (git-ignored, data/interim; contact columns dropped at load)",
}

# Figures stated by the project owner, compared with ours. They are targets to explain, not inputs.
OWNER_SHEET_LEADERS = 544
OWNER_SHEETS_COMPANY_EXACT = 541
OWNER_SHEETS_COMPANY_AMBIGUOUS = 5
OWNER_SHEETS_COMPANY_LOOSE_TOTAL = 543
OWNER_ROSTER_SUMMARY_BOTH = 383
OWNER_ROSTER_ONLY = 265
OWNER_SUMMARY_ONLY = 148
OWNER_COMPANY_ROWS = 852
OWNER_SUMMARY_NAMES = 532

PairKey = tuple[str, str]


def _keys(entities: Sequence[Entity]) -> frozenset[str]:
    return frozenset(entity.key for entity in entities)


def _source_section(sources: Mapping[str, Sequence[Entity]]) -> list[str]:
    rows = [
        (name, SOURCE_FILES.get(name, ""), _fmt(len(items)), _fmt(len(_keys(items))), _fmt(len(duplicate_keys(items))))
        for name, items in sources.items()
    ]
    header = ("source", "file", "entities", "distinct keys", "keys held by 2+ entities")
    return ["## Sources", "", *_table(header, rows), ""]


def _summary_sheet_section(sheets: Sequence[SummarySheet]) -> list[str]:
    total = sum(s.names_filled for s in sheets)
    return ["## Summary sheets read", "",
            f"{_fmt(len(sheets))} summary sheets read. Workbook names and sheet indexes are not listed. "
            f"Total name cells filled: {_fmt(total)}.", ""]


def _agreement(matches: Sequence[Match]) -> tuple[int, int, int]:
    exact = [m.company_agrees for m in matches if m.match_type == EXACT]
    return exact.count(True), exact.count(False), exact.count(None)


def _pair_section(pairs: Sequence[PairSummary], matches: Mapping[PairKey, Sequence[Match]]) -> list[str]:
    rows = []
    for p in pairs:
        agrees, differs, unknown = _agreement(matches.get((p.source_a, p.source_b), ()))
        rows.append((f"{p.source_a} -> {p.source_b}", _fmt(p.n_a), _fmt(p.n_b), _fmt(p.exact), _fmt(p.loose),
                     _fmt(p.ambiguous), _fmt(p.none), _fmt(p.b_unreferenced), f"{agrees} / {differs} / {unknown}"))
    header = ("pair (a -> b)", "a entities", "b entities", "exact", "loose", "ambiguous", "none",
              "b never named", "exact: company agrees / differs / unknown")
    note = ("Outcomes are counted per entity of side a. Ambiguous names are listed in "
            "data/interim/id_ambiguous.csv and are not resolved.")
    return ["## Pair outcomes", "", *_table(header, rows), "", note, ""]


def _overlap_section(sources: Mapping[str, Sequence[Entity]], pair_keys: Sequence[PairKey]) -> list[str]:
    rows = []
    for a, b in pair_keys:
        ka, kb = _keys(sources[a]), _keys(sources[b])
        rows.append((f"{a} / {b}", _fmt(len(ka & kb)), _fmt(len(ka - kb)), _fmt(len(kb - ka))))
    return ["## Distinct-key overlap", "", *_table(("pair", "in both", "only in first", "only in second"), rows), ""]


def _find(pairs: Sequence[PairSummary], a: str, b: str) -> PairSummary | None:
    return next((p for p in pairs if (p.source_a, p.source_b) == (a, b)), None)


def _compare_row(label: str, owner: int, ours: int | None) -> tuple[object, ...]:
    if ours is None:
        return (label, owner, "n/a", "n/a")
    return (label, owner, ours, f"{ours - owner:+d}")


def _owner_section(sources: Mapping[str, Sequence[Entity]], pairs: Sequence[PairSummary]) -> list[str]:
    sheet_company = _find(pairs, SOURCE_SHEETS, SOURCE_COMPANY)
    roster, summaries = _keys(sources[SOURCE_ROSTER]), _keys(sources[SOURCE_SUMMARIES])
    rows = [
        _compare_row("sheet leaders (distinct keys)", OWNER_SHEET_LEADERS, len(_keys(sources[SOURCE_SHEETS]))),
        _compare_row("sheets -> company exact", OWNER_SHEETS_COMPANY_EXACT, sheet_company.exact if sheet_company else None),
        _compare_row("sheets -> company ambiguous", OWNER_SHEETS_COMPANY_AMBIGUOUS,
                     sheet_company.ambiguous if sheet_company else None),
        _compare_row("sheets -> company exact + loose", OWNER_SHEETS_COMPANY_LOOSE_TOTAL,
                     sheet_company.exact + sheet_company.loose if sheet_company else None),
        _compare_row("roster and summaries both", OWNER_ROSTER_SUMMARY_BOTH, len(roster & summaries)),
        _compare_row("roster only", OWNER_ROSTER_ONLY, len(roster - summaries)),
        _compare_row("summaries only", OWNER_SUMMARY_ONLY, len(summaries - roster)),
        _compare_row("Company_Data rows", OWNER_COMPANY_ROWS, len(sources[SOURCE_COMPANY])),
        _compare_row("summary names (distinct keys)", OWNER_SUMMARY_NAMES, len(summaries)),
    ]
    note = "A non-zero difference is a finding to explain with the owner, not something fixed by this step."
    return [
        "## Owner figures versus ours",
        "",
        *_table(("measure", "owner", "ours", "difference"), rows),
        "",
        SUPERSEDED_LEADER_NOTE,
        "",
        note,
        "",
    ]


def _proposal_section(proposal: Sequence[ProposalRow]) -> list[str]:
    clear = [row for row in proposal if row.status == CLEAR]
    ambiguous = [row for row in proposal if row.status == AMBIGUOUS]
    coverage = Counter(len(row.refs) for row in clear)
    rows = [(f"{n} source(s)", _fmt(count), _pct(count, len(clear))) for n, count in sorted(coverage.items())]
    return ["## leader_id proposal", "",
            f"Keys: {_fmt(len(proposal))}. Clear (proposed id): {_fmt(len(clear))}. "
            f"Ambiguous (no id, left for a human): {_fmt(len(ambiguous))}.", "",
            *_table(("clear keys present in", "keys", "share of clear"), rows), ""]


def render_id_report(
    sources: Mapping[str, Sequence[Entity]],
    summary_sheets: Sequence[SummarySheet],
    pairs: Sequence[PairSummary],
    matches: Mapping[PairKey, Sequence[Match]],
    proposal: Sequence[ProposalRow],
) -> str:
    """Render the counts-only report; `matches` is keyed by (source_a, source_b)."""
    header = [
        "# ID matching", "",
        "Sorted-token name keys, matched across four lists. Loose = all tokens of the shorter name sit inside "
        "the longer one (at least 2 tokens), with one unclaimed candidate. Company agreement is shown for a "
        "human and never changes a match. Row-level tables are in data/interim (git-ignored); this file holds "
        "counts, file paths and sheet indexes only.", "",
    ]
    body = [
        *_source_section(sources),
        *_summary_sheet_section(summary_sheets),
        *_pair_section(pairs, matches),
        *_overlap_section(sources, list(matches)),
        *_owner_section(sources, pairs),
        *_proposal_section(proposal),
    ]
    return "\n".join([*header, *body])
