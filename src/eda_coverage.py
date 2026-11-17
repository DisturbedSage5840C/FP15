"""EDA section 1, coverage: leaders by source list, overlap of the lists, leaders with posts and with enough cells.

Counts only. The leader_id and the key columns are used to join the two tables and are never written out.
"Posts" here are raw text cells: no segmented per-cell table exists until gate G1 is signed, so the cut at
`min_posts_per_leader` is applied to raw cells and the segmented cut is reported as not computed.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.eda_common import EdaSettings, count_rows, show_count
from src.harmonise_report import _table

LEADER_ID = "leader_id"
CELL_COUNT = "n_raw_post_cells"
STATUS, AMBIGUOUS = "status", "ambiguous"
SHEETS = "sheets"
PROPOSAL_COLUMNS = (LEADER_ID, STATUS, SHEETS, "roster", "summaries", "company")
LEADER_COLUMNS = (LEADER_ID, CELL_COUNT)

# (column in leader_id_proposal, name shown in the report); "All_500" is the roster source.
THREE_LISTS = (("roster", "All_500"), ("summaries", "Summaries"), ("company", "Company_Data"))
NONE_OF_THREE = "none of the three lists"
LIST_LABELS = {
    "roster": "All_500 roster",
    "summaries": "Summaries",
    "company": "Company_Data",
    SHEETS: "Post workbooks",
}


@dataclass(frozen=True)
class ListCoverage:
    """One source list: its leaders, how many have a raw cell, and how many reach the cut."""

    name: str
    leaders: int
    with_cell: int
    at_cut: int


@dataclass(frozen=True)
class CoverageCounts:
    """Coverage of the people lists and the post workbooks; nothing here identifies a leader."""

    union: int
    ambiguous: int
    lists: tuple[ListCoverage, ...]
    overlap: tuple[tuple[str, int], ...]
    with_posts: int
    at_cut: int
    raw_cells: int
    min_posts: int


def _require(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name}: missing columns {', '.join(missing)}")


def _listed(column: pd.Series) -> pd.Series:
    """True where a source list has an entry for the leader (empty or missing means not listed)."""
    return column.fillna("").astype(str).str.strip() != ""


def _cell_count(value: object) -> int:
    """A leader's raw cell count; a blank or non-numeric entry counts as 0 (missing stays missing, not guessed)."""
    try:
        return int(float(str(value)))
    except ValueError:
        return 0


def _overlap_label(pattern: tuple[bool, ...]) -> str:
    names = [name for (_, name), listed in zip(THREE_LISTS, pattern, strict=True) if listed]
    if not names:
        return NONE_OF_THREE
    return f"{names[0]} only" if len(names) == 1 else " + ".join(names)


def _overlap(listed: dict[str, pd.Series]) -> tuple[tuple[str, int], ...]:
    """Leaders per membership pattern of the three people lists, all eight patterns in a fixed order."""
    keys = [key for key, _ in THREE_LISTS]
    members = pd.DataFrame({key: listed[key] for key in keys})
    patterns = [tuple(bool(bits >> shift & 1) for shift in (2, 1, 0)) for bits in range(7, -1, -1)]
    return tuple(
        (_overlap_label(pattern), int((members == pd.Series(pattern, index=keys)).all(axis=1).sum()))
        for pattern in patterns
    )


def coverage_counts(proposal: pd.DataFrame, leaders: pd.DataFrame, min_posts: int) -> CoverageCounts:
    """Count the lists, their overlap and the leaders with posts, cut on raw cells (cells stand in for posts)."""
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(leaders, LEADER_COLUMNS, "leader_table")
    unknown = set(leaders[LEADER_ID]) - set(proposal[LEADER_ID])
    if unknown:
        raise ValueError(f"leader_table: {len(unknown)} leader ids are not in the proposal")
    cell_map = {
        leader: _cell_count(value) for leader, value in zip(leaders[LEADER_ID], leaders[CELL_COUNT], strict=True)
    }
    cells = proposal[LEADER_ID].map(lambda leader: cell_map.get(leader, 0)).astype(int)
    listed = {key: _listed(proposal[key]) for key in (*(k for k, _ in THREE_LISTS), SHEETS)}
    lists = tuple(
        ListCoverage(
            name=LIST_LABELS[key],
            leaders=int(mask.sum()),
            with_cell=int((mask & (cells >= 1)).sum()),
            at_cut=int((mask & (cells >= min_posts)).sum()),
        )
        for key, mask in listed.items()
    )
    return CoverageCounts(
        union=len(proposal),
        ambiguous=int((proposal[STATUS] == AMBIGUOUS).sum()),
        lists=lists,
        overlap=_overlap(listed),
        with_posts=int((cells >= 1).sum()),
        at_cut=int((cells >= min_posts).sum()),
        raw_cells=int(cells.sum()),
        min_posts=min_posts,
    )


# ---- output -----------------------------------------------------------------------------------


def render_coverage(counts: CoverageCounts, settings: EdaSettings) -> list[str]:
    """Markdown lines for section 1; leader counts below the disclosure minimum show as "<5"."""
    low = settings.disclosure_min
    cut = f"At least {counts.min_posts} raw cells"
    list_rows = [
        (entry.name, show_count(entry.leaders, low), show_count(entry.with_cell, low), show_count(entry.at_cut, low))
        for entry in counts.lists
    ]
    overlap_rows = [row[:3] for row in count_rows(dict(counts.overlap), settings)]
    post_rows = [
        ("Leaders in any list (the union)", show_count(counts.union, low)),
        ("of which under an ambiguous name key", show_count(counts.ambiguous, low)),
        ("Leaders with at least 1 raw cell", show_count(counts.with_posts, low)),
        (f"Leaders with at least {counts.min_posts} raw cells", show_count(counts.at_cut, low)),
        (f"Leaders with at least {counts.min_posts} posts once segmented", "not computed"),
        ("Raw cells, all leaders (cells, not leaders)", f"{counts.raw_cells:,}"),
    ]
    return [
        "## 1. Coverage",
        "",
        "### Leaders by source list",
        "",
        "A leader is one entry in `leader_id_proposal`: a name key matched across the people lists. The lists overlap, "
        "so the rows below do not add up to the union.",
        "",
        *_table(("List", "Leaders", "With at least 1 raw cell", cut), list_rows),
        "",
        "### Overlap of the three people lists",
        "",
        "Each leader falls in exactly one row. \"none of the three lists\" are leaders found only in the post workbooks.",
        "",
        *_table(("Listed in", "Leaders", "Share"), overlap_rows),
        "",
        "### Leaders with posts",
        "",
        *_table(("Item", "Value"), post_rows),
        "",
        "Cells stand in for posts until G1 is signed. A raw cell can hold more than one post, or none, so the cut on "
        f"{counts.min_posts} raw cells can differ from the cut on {counts.min_posts} posts in either direction. "
        "The count once segmented is not computed: no per-cell segmented table exists and G1 is not signed. "
        "Full-cell segmentation was deliberately not run.",
        "",
    ]
