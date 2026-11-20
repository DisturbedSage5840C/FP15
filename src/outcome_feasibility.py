"""Which firm-outcome measures can Company_Data give us? (`make outcome-feasibility`)

Counts only. For leaders matched to a Company_Data row it shows which outcome columns are filled, which
same-year pairs can give a profit margin, an EBITDA margin and growth, and how many leaders that covers,
overall and by sector. It also lists the columns ROA and Tobin's q would need that the file does not have.

Nothing is built from a bare-number cell (no K/M/B suffix): its scale is not stated, so it is left alone.
The two Annual* columns hold a number followed by a bracket whose meaning is unknown, so they are counted as
filled and never read. No value, ratio, name or id is written; cells under the disclosure minimum show "<5".
Nothing here is fetched, filled or guessed, and no gate is signed off.

Claim limit: firm performance is not leader success; the study is about the image projected in public posts.
"""
from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.company_columns import CLEAR_STATUS, _company_position
from src.company_data import clean_cell, parse_quantity
from src.company_numeric import NOT_PARSED, _is_bare_number
from src.eda_common import EdaSettings, load_eda_settings, protect_cells, show_count
from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _table
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/outcome_feasibility.md")
SECTOR_COLUMN = "SectorPraticeAreaFeed"
PROFIT, EBITDA = "ProfitUSD2024", "EBITDAUSD2024"
REVENUE_2024, REVENUE_2023 = "RevenueUSD2024", "RevenueUSD2023"
FILL_COLUMNS: tuple[str, ...] = (
    "AnnualNetProfitUSD", PROFIT, EBITDA, "AnnualRevenueUSD", "LatestRevenueUSD", REVENUE_2024, REVENUE_2023,
    "RevenueCAGR1Year", "RevenueCAGR3Year", "RevenueCAGR5Year",
    "EmployeeCountLatest12monthgr", "LatestEmployeeGrowth12month",
)
NO_SECTOR = "(no sector listed)"
OTHER_GROUPS = "(other groups, each under the disclosure minimum)"
TOTAL_ROW = "All leaders in this group"
_LABEL_SEPARATOR = re.compile(r",\r?\n")
_GROUP_SEPARATOR = " > "
_SIMILAR_HEADER = re.compile(
    r"asset|equity|debt|borrow|liabil|valuation|marketcap|stockprice|networth|bookvalue", re.IGNORECASE
)
_PAST_END_ERROR = "leader_id_proposal.csv points past the end of company_data.csv"


@dataclass(frozen=True)
class Measure:
    """One outcome that could be built: a same-year ratio of two columns, or a growth column read as given."""

    label: str
    kind: str  # "ratio" or "given"
    top: str
    bottom: str | None = None


MEASURES: tuple[Measure, ...] = (
    Measure("Profit margin, 2024", "ratio", PROFIT, REVENUE_2024),
    Measure("EBITDA margin, 2024", "ratio", EBITDA, REVENUE_2024),
    Measure("Revenue growth, 2023 to 2024", "ratio", REVENUE_2024, REVENUE_2023),
    Measure("Revenue CAGR, 1 year", "given", "RevenueCAGR1Year"),
    Measure("Revenue CAGR, 3 years", "given", "RevenueCAGR3Year"),
    Measure("Revenue CAGR, 5 years", "given", "RevenueCAGR5Year"),
    Measure("Employee growth, 12 months", "given", "EmployeeCountLatest12monthgr"),
)

# (what the ROA / Tobin's q formula needs, why). None of these has a column in Company_Data.
MISSING_FOR_ROA_AND_Q: tuple[tuple[str, str], ...] = (
    ("Total assets", "the denominator of ROA (profit over assets) and the book value of assets in Tobin's q."),
    ("Market value of equity (current)",
     "the main part of the numerator of Tobin's q; the file has no current market value."),
    ("Total debt", "added to the market value of equity in the numerator of Tobin's q, and a leverage control."),
    ("Book equity", "gives return on equity as an alternative to ROA and a cross-check on total assets and debt."),
)
NOT_ACCEPTED_REASONS: dict[str, str] = {
    "MarketCapitalatIPOUSD": "market value at the IPO date only, not current",
    "StockPriceatIPOUSD": "a price at the IPO date only, with no share count",
    "LatestValuationUSD": "its meaning is not verified (it could be a private-round valuation)",
}
UNKNOWN_MEANING = "its meaning is not stated in the file"


@dataclass(frozen=True)
class Population:
    """Leaders in one group and the Company_Data rows (zero-based) the matched ones point to, in leader order."""

    leaders: int
    positions: tuple[int, ...]
    unmatched_by_match: dict[str, int]

    @property
    def unmatched(self) -> int:
        return self.leaders - len(self.positions)

    @property
    def firms(self) -> int:
        return len(set(self.positions))


@dataclass(frozen=True)
class FillRow:
    column: str
    filled: int
    readable: int | None  # None: the column is deliberately not read
    bare: int | None
    at_minimum: int
    with_posts: int


@dataclass(frozen=True)
class MeasureRow:
    label: str
    firms: int
    at_minimum: int
    with_posts: int


@dataclass(frozen=True)
class Analysis:
    settings: EdaSettings
    company_rows: int
    at_minimum: Population
    with_posts: Population
    fills: tuple[FillRow, ...]
    measures: tuple[MeasureRow, ...]
    sector_at_minimum: tuple[tuple[str, ...], ...]
    sector_with_posts: tuple[tuple[str, ...], ...]
    similar_headers: tuple[str, ...]


# ---- cells and measures ---------------------------------------------------------------------------


def _cells(company: pd.DataFrame, column: str) -> pd.Series:
    """The cleaned cells of a column ("." and "-" are None); a header that is not in the file gives all None."""
    if column not in company.columns:
        return pd.Series([None] * len(company), index=company.index, dtype=object)
    return company[column].map(clean_cell).astype(object)


def _numbers(company: pd.DataFrame, column: str) -> tuple[pd.Series, pd.Series]:
    """The number each cell reads as (NaN when it does not) and whether the cell is a bare number."""
    cells = _cells(company, column)
    numbers = pd.to_numeric(cells.map(parse_quantity), errors="coerce")
    bare = cells.map(lambda cell: cell is not None and _is_bare_number(cell)).astype(bool)
    return numbers, bare


def filled_flags(company: pd.DataFrame) -> pd.DataFrame:
    """One boolean column per FILL_COLUMNS entry: is the cell filled. Annual* count as filled though unread."""
    return pd.DataFrame({column: _cells(company, column).notna() for column in FILL_COLUMNS}, index=company.index)


def _usable_ratio(company: pd.DataFrame, top: str, bottom: str) -> pd.Series:
    """Both cells read, the base is positive, and neither cell is a bare number (scale unstated)."""
    top_numbers, top_bare = _numbers(company, top)
    bottom_numbers, bottom_bare = _numbers(company, bottom)
    return top_numbers.notna() & bottom_numbers.notna() & (bottom_numbers > 0) & ~top_bare & ~bottom_bare


def _usable_given(company: pd.DataFrame, column: str) -> pd.Series:
    numbers, bare = _numbers(company, column)
    return numbers.notna() & ~bare


def measure_flags(company: pd.DataFrame) -> pd.DataFrame:
    """One boolean column per measure in MEASURES: can this firm give it. Nothing is built from Annual* columns."""
    columns = {
        measure.label: _usable_ratio(company, measure.top, measure.bottom)
        if measure.kind == "ratio" and measure.bottom is not None
        else _usable_given(company, measure.top)
        for measure in MEASURES
    }
    return pd.DataFrame(columns, index=company.index)


# ---- who is counted -------------------------------------------------------------------------------


def _proposal_by_id(proposal: pd.DataFrame) -> dict[str, tuple[str, str]]:
    named = proposal[proposal["leader_id"] != ""]  # ambiguous rows carry a blank id; a blank id never joins
    if named["leader_id"].duplicated().any():
        raise ValueError("leader_id_proposal.csv lists a leader_id more than once")
    return {row.leader_id: (row.status, row.company) for row in named.itertuples(index=False)}


def _matched_position(entry: tuple[str, str] | None) -> int | None:
    """Only a clear proposal match with a company row counts; ambiguous or blank ones are never guessed at."""
    if entry is None or entry[0] != CLEAR_STATUS:
        return None
    return _company_position(entry[1])


def _population(rows: pd.DataFrame, by_id: Mapping[str, tuple[str, str]]) -> Population:
    positions: list[int] = []
    unmatched: dict[str, int] = {}
    for row in rows.itertuples(index=False):
        position = _matched_position(by_id.get(row.leader_id))
        if position is None:
            unmatched[row.company_match] = unmatched.get(row.company_match, 0) + 1
        else:
            positions.append(position)
    return Population(len(rows), tuple(positions), unmatched)


def build_populations(leaders: pd.DataFrame, proposal: pd.DataFrame, min_posts: int) -> tuple[Population, Population]:
    """(leaders at the post minimum, leaders with any raw post cell), each joined to a Company_Data row."""
    posts = pd.to_numeric(leaders["n_raw_post_cells"]).astype(int)
    by_id = _proposal_by_id(proposal)
    return _population(leaders[posts >= min_posts], by_id), _population(leaders[posts > 0], by_id)


# ---- sector ---------------------------------------------------------------------------------------


def primary_group(cell: object) -> str | None:
    """The group (text before " > ") of the first label in a sector cell; None for a blank cell."""
    text = clean_cell(cell)
    if text is None:
        return None
    group = _LABEL_SEPARATOR.split(text)[0].split(_GROUP_SEPARATOR)[0].strip()
    return group or None


def _group_labels(groups: pd.Series, disclosure_min: int) -> pd.Series:
    """Groups under the disclosure minimum are pooled and never named; a missing sector has its own label."""
    sizes = groups.dropna().value_counts()
    named = set(sizes[sizes >= disclosure_min].index)
    return groups.map(lambda group: NO_SECTOR if pd.isna(group) else group if group in named else OTHER_GROUPS)


def sector_table(
    groups: pd.Series, flags: pd.DataFrame, positions: Sequence[int], settings: EdaSettings
) -> tuple[tuple[str, ...], ...]:
    """Rows of strings: sector, leaders, then one column per measure. Small cells show "<5"."""
    rows = list(positions)
    labels = _group_labels(groups.iloc[rows], settings.disclosure_min)
    counts = labels.value_counts()
    special = (OTHER_GROUPS, NO_SECTOR)
    named = sorted((label for label in counts.index if label not in special), key=lambda label: (-counts[label], label))
    present = [*named, *(label for label in special if label in counts.index)]
    masks = {label: (labels == label).to_numpy() for label in present}
    values = flags.iloc[rows].to_numpy()
    columns = [{label: int(mask.sum()) for label, mask in masks.items()}]
    columns += [
        {label: int(values[mask, index].sum()) for label, mask in masks.items()} for index in range(values.shape[1])
    ]
    shown = [protect_cells(column, settings.disclosure_min) for column in columns]
    totals = [len(rows), *(int(values[:, index].sum()) for index in range(values.shape[1]))]
    body = [(label, *(column[label] for column in shown)) for label in present]
    total = (TOTAL_ROW, *(show_count(count, settings.disclosure_min) for count in totals))
    return (*body, total)


# ---- analysis -------------------------------------------------------------------------------------


def _fill_row(company: pd.DataFrame, filled: pd.DataFrame, column: str, populations: Sequence[Population]) -> FillRow:
    cells = _cells(company, column).dropna()
    reads = column not in NOT_PARSED
    readable = sum(parse_quantity(cell) is not None for cell in cells) if reads else None
    bare = sum(_is_bare_number(cell) for cell in cells) if reads else None
    at_minimum, with_posts = (int(filled[column].iloc[list(pop.positions)].sum()) for pop in populations)
    return FillRow(column, int(filled[column].sum()), readable, bare, at_minimum, with_posts)


def _measure_row(measures: pd.DataFrame, label: str, populations: Sequence[Population]) -> MeasureRow:
    at_minimum, with_posts = (int(measures[label].iloc[list(pop.positions)].sum()) for pop in populations)
    return MeasureRow(label, int(measures[label].sum()), at_minimum, with_posts)


def _check_positions(company: pd.DataFrame, population: Population) -> None:
    if population.positions and max(population.positions) >= len(company):
        raise ValueError(_PAST_END_ERROR)


def analyse(
    company: pd.DataFrame,
    leaders: pd.DataFrame,
    proposal: pd.DataFrame,
    settings: EdaSettings,
    headers: Sequence[str],
) -> Analysis:
    """Counts of fills, measures and sectors for leaders at the post minimum and for all leaders with posts."""
    at_minimum, with_posts = build_populations(leaders, proposal, settings.min_posts)
    _check_positions(company, with_posts)
    populations = (at_minimum, with_posts)
    filled, measures = filled_flags(company), measure_flags(company)
    groups = _cells(company, SECTOR_COLUMN).map(primary_group)
    return Analysis(
        settings=settings,
        company_rows=len(company),
        at_minimum=at_minimum,
        with_posts=with_posts,
        fills=tuple(_fill_row(company, filled, column, populations) for column in FILL_COLUMNS),
        measures=tuple(_measure_row(measures, measure.label, populations) for measure in MEASURES),
        sector_at_minimum=sector_table(groups, measures, at_minimum.positions, settings),
        sector_with_posts=sector_table(groups, measures, with_posts.positions, settings),
        similar_headers=tuple(header for header in headers if _SIMILAR_HEADER.search(header)),
    )


# ---- report ---------------------------------------------------------------------------------------


def _who_section(analysis: Analysis) -> list[str]:
    minimum = analysis.settings.disclosure_min
    groups = (analysis.at_minimum, analysis.with_posts)
    rows = [
        ("Leaders in the group", *(show_count(pop.leaders, minimum) for pop in groups)),
        ("Matched to one Company_Data row", *(show_count(len(pop.positions), minimum) for pop in groups)),
        ("Distinct firms among those matched", *(show_count(pop.firms, minimum) for pop in groups)),
    ]
    labels = sorted({label for pop in groups for label in pop.unmatched_by_match})
    protected = [
        protect_cells({label: pop.unmatched_by_match.get(label, 0) for label in labels}, minimum) for pop in groups
    ]
    rows += [
        (f"Not matched; the leader table says: {label or '(blank)'}", *(column[label] for column in protected))
        for label in labels
    ]
    head = ("Group", f"{analysis.settings.min_posts}+ raw post cells", "Any raw post cells")
    return [
        "## Who is counted", "",
        "Leaders are joined to a Company_Data row only on a clear proposal match with a company row. Ambiguous, "
        "blank and missing matches are counted as not matched and never guessed. Two leaders at one firm both count.",
        "",
        *_table(head, rows), "",
    ]


def _readable(value: int | None, minimum: int) -> str:
    return "not read" if value is None else show_count(value, minimum)


def _fill_section(analysis: Analysis) -> list[str]:
    minimum = analysis.settings.disclosure_min
    head = ("Column", "Filled (file)", "Reads as a number (file)", "Bare number, scale unstated (file)",
            f"Leaders, {analysis.settings.min_posts}+ posts", "Leaders, any posts")
    rows = [
        (fill.column, show_count(fill.filled, minimum), _readable(fill.readable, minimum),
         _readable(fill.bare, minimum), show_count(fill.at_minimum, minimum), show_count(fill.with_posts, minimum))
        for fill in analysis.fills
    ]
    return [
        "## Fill counts", "",
        f"The file has {analysis.company_rows:,} firm rows. The two leader columns count leaders matched to a row. "
        "AnnualRevenueUSD and AnnualNetProfitUSD hold a comma-grouped number followed by a bracket whose meaning is "
        "unknown, so they are counted as filled and not read. A bare-number cell has no K, M or B suffix, so its scale "
        "and unit are not stated; it is left as written, never rescaled, and used in no measure. "
        "LatestRevenueUSD and LatestEmployeeGrowth12month are bare numbers throughout, so they give no measure here.",
        "",
        *_table(head, rows), "",
    ]


def _measure_section(analysis: Analysis) -> list[str]:
    minimum = analysis.settings.disclosure_min
    head = ("Measure", "Firm rows (file)", f"Leaders, {analysis.settings.min_posts}+ posts", "Leaders, any posts")
    rows = [
        (row.label, show_count(row.firms, minimum), show_count(row.at_minimum, minimum),
         show_count(row.with_posts, minimum))
        for row in analysis.measures
    ]
    return [
        "## Which measures can be built", "",
        "A margin or a growth ratio needs both columns of a same-year pair to read as numbers, a positive base, and "
        "no bare-number cell. The 2023 and 2024 columns are paired by name; that they share a fiscal year is not "
        "verified. The three CAGR columns and the employee growth column are used as given when they read as numbers. "
        "No ratio or value is shown here.", "",
        *_table(head, rows), "",
    ]


def _sector_section(analysis: Analysis) -> list[str]:
    head = ("Sector (first listed label's group)", "Leaders", *(measure.label for measure in MEASURES))
    minimum = analysis.settings.disclosure_min
    lines = [
        "## Measures by sector", "",
        f"Groups with fewer than {minimum} leaders are pooled and not named. A cell under {minimum} shows "
        f"\"<5\", and a neighbouring cell is also hidden where the total would give a hidden one away. "
        "A firm that lists several labels is placed by its first.", "",
    ]
    for title, table in (
        (f"Leaders with {analysis.settings.min_posts}+ raw post cells", analysis.sector_at_minimum),
        ("Leaders with any raw post cell", analysis.sector_with_posts),
    ):
        lines += [f"### {title}", "", *_table(head, table), ""]
    return lines


def _missing_section(analysis: Analysis) -> list[str]:
    lines = [
        "## Not in the file", "",
        "ROA and Tobin's q need the columns below. None has a header in Company_Data. Nothing is guessed or filled.",
        "",
        *(f"- **{name}**: {why}" for name, why in MISSING_FOR_ROA_AND_Q), "",
    ]
    if analysis.similar_headers:
        lines += ["Headers with a similar look were found and are not accepted as substitutes:", ""]
        lines += [
            f"- {header}: not accepted; {NOT_ACCEPTED_REASONS.get(header, UNKNOWN_MEANING)}."
            for header in analysis.similar_headers
        ]
    else:
        lines += ["No header with a similar look was found."]
    return [*lines, ""]


def _caveat_section() -> list[str]:
    return [
        "## Caveats", "",
        "- **Firm performance is not leader success.** A firm's margin or growth reflects its market, history and "
        "capital as much as one leader.",
        "- **No tenure.** role_start_year is filled for fewer than 5 leaders in the workbooks seen so far, so a "
        "leader's time in the role cannot be matched to a performance year.",
        "- **No movers.** Each leader is seen at one firm, so leader and firm cannot be told apart by who moved where.",
        "- **Reverse causation.** Performance may shape how and whether a leader posts, as much as the reverse. "
        "Any link is descriptive.",
        "- **Fiscal years.** Whether the Latest columns and the 2023 and 2024 columns share a fiscal year is unverified.",
        "- **Sector.** The sector label is the first listed one; a firm can list several.", "",
        "## Open for the team and the mentors", "",
        "- Which outcome measure (ROA, Tobin's q, or the margins and growth above), which year window, and whether to "
        "adjust for sector. Recorded as open in docs/decisions.md; nothing is decided here.",
        "- The meeting with the data owners about specific columns is planned for 2026-11-23.",
    ]


def render_report(analysis: Analysis) -> str:
    intro = [
        "# Outcome feasibility from Company_Data", "",
        "Claims here are about the image projected in public posts, not about the person. This report holds column "
        "headers and counts only: no names, ids, cell values or ratios.", "",
    ]
    sections = [
        *intro, *_who_section(analysis), *_fill_section(analysis), *_measure_section(analysis),
        *_sector_section(analysis), *_missing_section(analysis), *_caveat_section(),
    ]
    return "\n".join(sections) + "\n"


# ---- entry points ---------------------------------------------------------------------------------


def _read(path: Path, needed: Sequence[str]) -> pd.DataFrame:
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [name for name in needed if name not in table.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {', '.join(missing)}")
    return table


def _build(interim_dir: Path, settings: EdaSettings) -> str:
    company = pd.read_csv(interim_dir / "company_data.csv", dtype=str, keep_default_na=False)
    leaders = _read(interim_dir / "leader_table.csv", ("leader_id", "company_match", "n_raw_post_cells"))
    proposal = _read(interim_dir / "leader_id_proposal.csv", ("leader_id", "status", "company"))
    headers = [column for column in company.columns if not column.endswith("_num")]
    return render_report(analyse(company, leaders, proposal, settings, headers))


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    settings: EdaSettings | None = None,
) -> int:
    """Verify the raw manifest, count, write the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        text = _build(interim_dir, settings or load_eda_settings())
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("outcome-feasibility FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
