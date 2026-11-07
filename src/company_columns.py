"""Step C: which Company_Data columns are most useful, and how filled are they? (`make company-columns`)

For the leaders who reach the post minimum, this counts how many have a value in each candidate
column of Company_Data ("." and "-" are blank) and proposes the best columns for the leader and firm
analysis. It uses only tables already in data/interim (no network, no scraping). The report holds
column headers, counts and shares; it never holds leader names, company names or cell values.

Claim limit: the columns describe the leader's profile and firm, and the analysis is about the image
projected in public posts. The 15-post rule is applied to raw post cells here (a cell-level proxy),
because author blocks are not segmented yet.
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.company_data import clean_cell, parse_quantity
from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _pct, _table
from src.name_key import name_key
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
DEFAULT_REPORT_PATH = Path("reports/company_columns.md")
POST_COLUMNS = ("leader", "text_kind")
PROPOSAL_COLUMNS = ("key", "status", "company")
RAW_KIND = "raw"
CLEAR_STATUS = "clear"
AMBIGUOUS_STATUS = "ambiguous"
COMPANY_REF_PREFIX = "row:"
PER_VARIABLE_CAP = 2


@dataclass(frozen=True)
class ColumnSettings:
    min_posts: int
    top_n: int


@dataclass(frozen=True)
class Candidate:
    """A Company_Data column that could serve one study variable."""

    column: str
    variable: str
    numeric: bool = False


@dataclass(frozen=True)
class ColumnFill:
    """How many of the counted leaders have a value in one column."""

    column: str
    variable: str
    numeric: bool
    present: bool
    filled: int
    parsed: int
    total: int

    @property
    def share(self) -> float:
        return self.filled / self.total if self.total else 0.0


@dataclass(frozen=True)
class Eligibility:
    """Who passes the post minimum and how they join to Company_Data."""

    leaders_with_posts: int
    eligible: int
    matched_positions: tuple[int, ...]
    ambiguous: int
    no_company: int
    not_in_proposal: int


# Ordered by usefulness for the study, so ties in fill share keep this order. At most
# PER_VARIABLE_CAP columns are taken per study variable so one topic cannot fill the list.
CANDIDATES: tuple[Candidate, ...] = (
    Candidate("Gender", "gender"),
    Candidate("Current_Title", "title family"),
    Candidate("SectorPraticeAreaFeed", "sector"),
    Candidate("BusinessModels", "sector"),
    Candidate("TotalEmployeeCount", "firm size (employees)", numeric=True),
    Candidate("NumberofEmployees", "firm size (employees)", numeric=True),
    Candidate("LatestEmployeeCount", "firm size (employees)", numeric=True),
    Candidate("EmployeeCount2024", "firm size (employees)", numeric=True),
    Candidate("RevenueUSD2024", "firm size", numeric=True),
    Candidate("AnnualRevenueUSD", "firm size", numeric=True),
    Candidate("LatestRevenueUSD", "firm size", numeric=True),
    Candidate("RevenueUSD2023", "firm size", numeric=True),
    Candidate("ProfitUSD2024", "profitability", numeric=True),
    Candidate("EBITDAUSD2024", "profitability", numeric=True),
    Candidate("AnnualNetProfitUSD", "profitability", numeric=True),
    Candidate("RevenueCAGR3Year", "firm growth", numeric=True),
    Candidate("RevenueCAGR1Year", "firm growth", numeric=True),
    Candidate("EmployeeCountLatest12monthgr", "firm growth", numeric=True),
    Candidate("LatestEmployeeGrowth12month", "firm growth", numeric=True),
    Candidate("FoundedYear", "firm age", numeric=True),
    Candidate("CompanyStage", "firm stage"),
    Candidate("Country", "location"),
    Candidate("Current_City", "location"),
    Candidate("Current_State", "location"),
    Candidate("City", "location"),
    Candidate("LinkedIn_Followers", "audience size", numeric=True),
    Candidate("LinkedIn_Connections", "audience size", numeric=True),
    Candidate("LinkedIn_Recommendations_Count", "profile richness", numeric=True),
    Candidate("Honors_Awards_Count", "profile richness", numeric=True),
    Candidate("LinkedIn_Skills", "profile richness"),
    Candidate("Languages_Spoken", "profile richness"),
    Candidate("LinkedIn_Publications_Count", "profile richness", numeric=True),
    Candidate("Licenses_Certifications", "profile richness"),
    Candidate("IsFunded", "funding"),
    Candidate("TotalFundingUSD", "funding", numeric=True),
    Candidate("NewsArticlesAllTime", "firm visibility", numeric=True),
)

EXCLUDED_GROUPS: tuple[tuple[str, str], ...] = (
    ("CompanyName, Person_Name", "identifiers; analysis files carry leader_id only"),
    ("Website, LinkedIn, LinkedIn_Profile_Link, Twitter, Facebook, BlogUrl, TracxnURL, DomainName",
     "links and identifiers, not analysis variables"),
    ("Overview, Description, AdditionalComment, TeamBackground", "free text, not a structured variable"),
    ("IsIPO, StockTicker, Exchange, IPODate and the other IPO columns",
     "every firm in the file is listed, so listed versus unlisted cannot be tested"),
    ("Q, V, Z", "unnamed columns with no known meaning; not used until the owner says what they hold"),
    ("the *_num columns", "derived by this project from the columns above; not a source column"),
    ("email and phone columns", "dropped when the file is loaded, before anything is written to disk"),
)


# ---- reading ----------------------------------------------------------------------------------


def load_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> ColumnSettings:
    """Read the post minimum and the list length; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keys = ("min_posts_per_leader", "company_columns_top_n")
    for key in keys:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return ColumnSettings(*(int(values[key]) for key in keys))


def _read(path: Path, needed: Sequence[str]) -> pd.DataFrame:
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [name for name in needed if name not in table.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {', '.join(missing)}")
    return table


def leader_post_counts(posts: pd.DataFrame) -> dict[str, int]:
    """Raw post cells per leader name key; cells without a leader are skipped."""
    counts: dict[str, int] = {}
    for leader in posts.loc[posts["text_kind"] == RAW_KIND, "leader"]:
        key = name_key(leader)
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


# ---- who is counted ---------------------------------------------------------------------------


def _company_position(ref: str) -> int | None:
    """Zero-based row position from a 'row:<n>' reference (n is 1-based); None if there is none."""
    if not ref.startswith(COMPANY_REF_PREFIX):
        return None
    number = ref[len(COMPANY_REF_PREFIX):]
    return int(number) - 1 if number.isdigit() and int(number) >= 1 else None


def find_eligible(counts: dict[str, int], proposal: pd.DataFrame, min_posts: int) -> Eligibility:
    """Leaders with at least min_posts raw cells, joined to a Company_Data row.

    Only a clear proposal match with a company row is used. An ambiguous match is counted and left
    alone: nothing here decides which person a name belongs to.
    """
    by_key = {row.key: row for row in proposal.itertuples(index=False)}
    eligible_keys = sorted(key for key, count in counts.items() if count >= min_posts)
    positions: list[int] = []
    ambiguous = no_company = not_in_proposal = 0
    for key in eligible_keys:
        row = by_key.get(key)
        if row is None:
            not_in_proposal += 1
        elif row.status == AMBIGUOUS_STATUS:
            ambiguous += 1
        else:
            position = _company_position(row.company) if row.status == CLEAR_STATUS else None
            if position is None:
                no_company += 1
            else:
                positions.append(position)
    return Eligibility(
        leaders_with_posts=len(counts),
        eligible=len(eligible_keys),
        matched_positions=tuple(positions),
        ambiguous=ambiguous,
        no_company=no_company,
        not_in_proposal=not_in_proposal,
    )


# ---- fill shares ------------------------------------------------------------------------------


def fill_rows(
    company: pd.DataFrame, positions: Sequence[int], candidates: Sequence[Candidate]
) -> tuple[ColumnFill, ...]:
    """Filled (and, for numeric columns, parseable) counts for each candidate over the given rows."""
    rows = company.iloc[list(positions)]
    fills = []
    for candidate in candidates:
        present = candidate.column in company.columns
        values = [clean_cell(v) for v in rows[candidate.column]] if present else []
        filled = [v for v in values if v is not None]
        parsed = sum(1 for v in filled if candidate.numeric and parse_quantity(v) is not None)
        fills.append(
            ColumnFill(candidate.column, candidate.variable, candidate.numeric, present,
                       len(filled), parsed, len(positions))
        )
    return tuple(fills)


def select_top(fills: Sequence[ColumnFill], top_n: int) -> list[ColumnFill]:
    """Best-filled columns first (ties keep candidate order), at most PER_VARIABLE_CAP per variable."""
    ranked = sorted((fill for fill in fills if fill.present), key=lambda fill: -fill.share)
    taken: dict[str, int] = {}
    chosen: list[ColumnFill] = []
    for fill in ranked:
        if len(chosen) == top_n:
            break
        if taken.get(fill.variable, 0) < PER_VARIABLE_CAP:
            taken[fill.variable] = taken.get(fill.variable, 0) + 1
            chosen.append(fill)
    return chosen


# ---- report -----------------------------------------------------------------------------------


def _fill_line(fill: ColumnFill) -> tuple[str, ...]:
    parsed = f"{_fmt(fill.parsed)} of {_fmt(fill.filled)}" if fill.numeric else "n/a"
    return (fill.column, fill.variable, f"{_fmt(fill.filled)} of {_fmt(fill.total)}",
            _pct(fill.filled, fill.total), parsed)


def _who_section(settings: ColumnSettings, who: Eligibility) -> list[str]:
    rows = [
        ("Leaders with at least one raw post cell", _fmt(who.leaders_with_posts)),
        (f"Leaders with {settings.min_posts} or more raw post cells", _fmt(who.eligible)),
        ("Matched to exactly one Company_Data row", _fmt(len(who.matched_positions))),
        ("Left out: ambiguous name match, not resolved", _fmt(who.ambiguous)),
        ("Left out: clear match but no Company_Data row", _fmt(who.no_company)),
        ("Left out: not in the leader_id proposal", _fmt(who.not_in_proposal)),
    ]
    return ["## Who is counted", "", *_table(("Group", "Leaders"), rows), ""]


def _top_section(settings: ColumnSettings, chosen: Sequence[ColumnFill]) -> list[str]:
    head = ("Column", "Study variable", "Filled", "Share", "Reads as a number")
    return [
        f"## The {settings.top_n} columns proposed", "",
        f"Ranked by the share of counted leaders with a value; at most {PER_VARIABLE_CAP} per study "
        f"variable. {_fmt(len(chosen))} columns listed.", "",
        *_table(head, [_fill_line(fill) for fill in chosen]), "",
    ]


def _other_section(fills: Sequence[ColumnFill], chosen: Sequence[ColumnFill]) -> list[str]:
    taken = {fill.column for fill in chosen}
    others = [fill for fill in fills if fill.present and fill.column not in taken]
    absent = [fill.column for fill in fills if not fill.present]
    lines = ["## Other candidate columns considered", ""]
    if others:
        lines += [*_table(("Column", "Study variable", "Filled", "Share", "Reads as a number"),
                          [_fill_line(fill) for fill in others]), ""]
    else:
        lines += ["None.", ""]
    if absent:
        lines += [f"Candidates not found in the file: {', '.join(absent)}.", ""]
    lines += ["Columns left out on purpose:", ""]
    lines += [f"- {names}: {reason}." for names, reason in EXCLUDED_GROUPS]
    return [*lines, ""]


def _decision_section(settings: ColumnSettings) -> list[str]:
    return [
        "## Needs a human decision", "",
        "- The choice of columns and the study variable each one serves is a proposal for the mentors, "
        "not a decision.",
        "- Gender is used as coded in the file; what 1 and 0 mean is not confirmed, and gender is never "
        "inferred from a name.",
        "- Tenure is not in Company_Data (it has no role start year), and role_start_year is empty in the "
        "post workbooks, so tenure cannot be filled from here.",
        "- LinkedIn_Followers and LinkedIn_Connections already exist in the file. Scraping new reaction "
        "or follower counts is not approved, so these file values are the only source.",
        f"- The {settings.min_posts}-post rule is applied to raw post cells, a cell-level proxy. "
        "It will change once author blocks are segmented.",
        "- Ambiguous name matches are left out, not resolved. Resolving them is a human job.",
    ]


def render_report(
    settings: ColumnSettings, who: Eligibility, fills: Sequence[ColumnFill], chosen: Sequence[ColumnFill]
) -> str:
    intro = [
        "# Company_Data columns for the leader and firm analysis", "",
        "Claims here are about the image projected in public posts, not about the person. This report "
        "lists column headers, counts and shares only: no names, companies or cell values.",
        "Counts are cell-level: the post minimum is applied to raw post cells, not yet to author blocks.", "",
    ]
    lines = [*intro, *_who_section(settings, who), *_top_section(settings, chosen),
             *_other_section(fills, chosen), *_decision_section(settings)]
    return "\n".join(lines) + "\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---- entry points -----------------------------------------------------------------------------


def _build(interim_dir: Path, settings: ColumnSettings) -> str:
    posts = _read(interim_dir / "harmonised_posts.csv", POST_COLUMNS)
    proposal = _read(interim_dir / "leader_id_proposal.csv", PROPOSAL_COLUMNS)
    company = pd.read_csv(interim_dir / "company_data.csv", dtype=str, keep_default_na=False)
    who = find_eligible(leader_post_counts(posts), proposal, settings.min_posts)
    if who.matched_positions and max(who.matched_positions) >= len(company):
        raise ValueError("leader_id_proposal.csv points past the end of company_data.csv")
    fills = fill_rows(company, who.matched_positions, CANDIDATES)
    return render_report(settings, who, fills, select_top(fills, settings.top_n))


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    settings: ColumnSettings | None = None,
) -> int:
    """Verify the raw manifest, count the fills, write the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        text = _build(interim_dir, settings or load_settings())
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("company-columns FAILED: %s", error)
        return 1
    _write(report_path, text)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
