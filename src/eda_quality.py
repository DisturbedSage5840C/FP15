"""EDA section 5: quality issues already found, as counts only (`make eda`).

Shifted and blank ceo_type, repeated names, company mismatches and Hinglish rows. Nothing is corrected, filled in or
dropped here: the issues are only counted so later stages can handle them on purpose. No names, values, ids or
references reach the output. A count below the disclosure minimum (zero included) is shown as "<5".
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pandas as pd

from src.ceo_gender_counts import CEO_TYPE_COLUMN, CeoTypeCounts, ceo_type_counts
from src.eda_common import SMALL, TOTAL_LABEL, EdaSettings, show_count
from src.eda_gaps import LEADER, _require
from src.harmonise_report import _table

SOURCE_COLUMNS = ("sheets", "roster", "summaries", "company")
REPEAT_SEPARATOR = ";"
AMBIGUOUS_STATUS = "ambiguous"
COMPANY_DISAGREES = "false"
BLANK_LABEL = "blank"
AMBIGUOUS_LABEL = "keys flagged ambiguous"
POST_COLUMNS = (LEADER, CEO_TYPE_COLUMN)
PROPOSAL_COLUMNS = ("status", *SOURCE_COLUMNS)
MATCH_COLUMNS = ("source_a", "source_b", "company_agrees")


@dataclass(frozen=True)
class QualityCounts:
    """Counts of the quality issues already found; every pair is (label, count)."""

    ceo_type: CeoTypeCounts
    repeated_keys: tuple[tuple[str, int], ...]
    ambiguous_keys: int
    company_match: tuple[tuple[str, int], ...]
    company_differs: tuple[tuple[str, int], ...]
    languages: tuple[tuple[str, int], ...]
    language_rows: int


def _text(value: object) -> str:
    return str(value).strip()


def _labelled_counts(values: Iterable[object]) -> tuple[tuple[str, int], ...]:
    """Counts per label, largest first (ties by label); an empty value gets the "blank" label."""
    counts = Counter(_text(value) or BLANK_LABEL for value in values)
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _repeated_keys(proposal: pd.DataFrame) -> tuple[tuple[str, int], ...]:
    """Keys whose cell lists two or more entities in a source list (the cells are ";"-joined)."""
    return tuple(
        (column, sum(REPEAT_SEPARATOR in _text(cell) for cell in proposal[column])) for column in SOURCE_COLUMNS
    )


def _company_differs(matches: pd.DataFrame) -> tuple[tuple[str, int], ...]:
    """Match rows where the company differs, per source pair in order of first appearance (zero kept)."""
    differs: dict[str, int] = {}
    for source_a, source_b, agrees in zip(
        matches["source_a"], matches["source_b"], matches["company_agrees"], strict=True
    ):
        pair = f"{_text(source_a)} to {_text(source_b)}"
        differs[pair] = differs.get(pair, 0) + int(_text(agrees) == COMPANY_DISAGREES)
    return tuple(differs.items())


def quality_counts(
    posts: pd.DataFrame, leaders: pd.DataFrame, proposal: pd.DataFrame, matches: pd.DataFrame, clean: pd.DataFrame
) -> QualityCounts:
    """Count the quality issues already found, from the existing interim tables (none is changed)."""
    _require(posts, POST_COLUMNS, "harmonised_posts")
    _require(leaders, ("company_match",), "leader_table")
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(matches, MATCH_COLUMNS, "id_matches")
    _require(clean, ("language",), "posts_clean")
    return QualityCounts(
        ceo_type=ceo_type_counts(posts),
        repeated_keys=_repeated_keys(proposal),
        ambiguous_keys=sum(_text(status) == AMBIGUOUS_STATUS for status in proposal["status"]),
        company_match=_labelled_counts(leaders["company_match"]),
        company_differs=_company_differs(matches),
        languages=_labelled_counts(clean["language"]),
        language_rows=len(clean),
    )


# ---- output -----------------------------------------------------------------------------------


def _count_table(header: tuple[str, str], pairs: Sequence[tuple[str, int]], minimum: int) -> list[str]:
    return [*_table(header, [(label, show_count(count, minimum)) for label, count in pairs]), ""]


def _ceo_type_table(counts: CeoTypeCounts, minimum: int) -> list[str]:
    """Leaders and rows per issue; a row count is hidden with its leader count, so it never stands for one leader."""
    issues = (
        ("ceo_type blank", counts.blank, counts.cells_blank),
        ("ceo_type neither label (shifted)", counts.unrecognised_only, counts.cells_unrecognised),
    )
    rows = []
    for label, leaders, cells in issues:
        if leaders < minimum:
            rows.append((label, SMALL, SMALL))
        else:
            rows.append((label, show_count(leaders, minimum), show_count(cells, minimum)))
    return [*_table(("Issue", "Leaders", "Rows"), rows), ""]


def render_quality(counts: QualityCounts, settings: EdaSettings) -> list[str]:
    """Markdown lines for section 5; counts below the disclosure minimum show as "<5"."""
    minimum = settings.disclosure_min
    key_rows = [*counts.repeated_keys, (AMBIGUOUS_LABEL, counts.ambiguous_keys)]
    language_rows = [*counts.languages, (TOTAL_LABEL, counts.language_rows)]
    return [
        "## 5. Quality issues already found",
        "",
        "Counts only: no names, values, ids or references. Nothing here was corrected, filled in or dropped; the issues "
        f"are listed so later stages can handle them on purpose. A count below {minimum} (zero included) shows as "
        '"<5". ceo_type counts are over every row of the harmonised table (raw and cleaned text rows), as in '
        "reports/ceo_type_gender_counts.md; a value that is neither label is counted, not inspected.",
        "",
        "### ceo_type",
        "",
        *_ceo_type_table(counts.ceo_type, minimum),
        "### Repeated names",
        "",
        "Keys (a normalised name) held by two or more entities in one source list, and keys the id proposal flagged "
        "ambiguous.",
        "",
        *_count_table(("Check", "Keys"), key_rows, minimum),
        "### Company mismatches",
        "",
        "Match kind of each leader against Company_Data (one row per leader), then match rows where the company named "
        "in one source differs from the other, per source pair (a leader can appear in more than one row).",
        "",
        *_count_table(("Company_Data match kind", "Leaders"), counts.company_match, minimum),
        *_count_table(("Source pair", "Match rows where the company differs"), counts.company_differs, minimum),
        "### Language (Hinglish rows)",
        "",
        "Language tag of each cleaned post. Hinglish and other non-English rows are only counted here; nothing is "
        "translated or dropped in this section.",
        "",
        *_count_table(("Language", "Cleaned posts"), language_rows, minimum),
    ]
