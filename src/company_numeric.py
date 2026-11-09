"""Step 3: numeric versions of three named Company_Data columns (`make company-numeric`).

Only LatestRevenueUSD, NumberofEmployees and ProfitUSD2024 are read. The bracketed columns
(AnnualRevenueUSD, AnnualNetProfitUSD, TotalEmployeeCount) are deliberately not parsed.
Parsing reuses `parse_quantity`; blanks and unreadable cells stay missing, nothing is guessed.

A ProfitUSD2024 cell written as a bare number (no K/M/B/T suffix) has a scale the file does not state,
so it is flagged and kept exactly as written, never rescaled.

The table is keyed by `row:<n>` (1-based over all Company_Data rows) and carries no names. The report holds
counts and column headers only. Whether the three columns share a fiscal year is answered from headers only.
"""
from __future__ import annotations

import logging
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.company_data import clean_cell, parse_quantity
from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _table
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/company_numeric.md")
INPUT_FILE = "company_data.csv"
OUTPUT_FILE = "company_numeric.csv"
COLUMN_MAP: tuple[tuple[str, str], ...] = (
    ("revenue_usd_latest", "LatestRevenueUSD"),
    ("employees", "NumberofEmployees"),
    ("profit_usd_2024", "ProfitUSD2024"),
)
NUMERIC_COLUMNS = tuple(output for output, _ in COLUMN_MAP)
UNVERIFIED_SCALE = "profit_scale_unverified"
SCALE_UNVERIFIED_SOURCE = "ProfitUSD2024"
NOT_PARSED = ("AnnualRevenueUSD", "AnnualNetProfitUSD", "TotalEmployeeCount")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_BARE_NUMBER = re.compile(r"^-?[\d,]+(?:\.\d+)?$")


@dataclass(frozen=True)
class ColumnSummary:
    """Counts for one named column; never a cell value."""

    output_column: str
    source_column: str
    rows: int
    blank: int
    filled: int
    parsed: int
    unparsed: int
    unverified_scale: int


def _require_columns(company: pd.DataFrame) -> None:
    missing = [source for _, source in COLUMN_MAP if source not in company.columns]
    if missing:
        raise ValueError(f"Company_Data is missing column(s): {', '.join(missing)}")


def _is_bare_number(value: object) -> bool:
    text = clean_cell(value)
    return text is not None and _BARE_NUMBER.match(text) is not None


def build_numeric(company: pd.DataFrame) -> pd.DataFrame:
    """One row per Company_Data row: `company_row`, the three numbers, and the scale flag for profit."""
    _require_columns(company)
    refs = [f"row:{number}" for number in range(1, len(company) + 1)]
    columns: dict[str, list[object]] = {"company_row": list(refs)}
    for output, source in COLUMN_MAP:
        columns[output] = [parse_quantity(value) for value in company[source]]
    parsed_profit = columns["profit_usd_2024"]
    columns[UNVERIFIED_SCALE] = [
        number is not None and _is_bare_number(raw)
        for number, raw in zip(parsed_profit, company[SCALE_UNVERIFIED_SOURCE], strict=True)
    ]
    return pd.DataFrame(columns)


def _summarise(company: pd.DataFrame, output: str, source: str) -> ColumnSummary:
    cells = list(company[source])
    filled = [cell for cell in cells if clean_cell(cell) is not None]
    parsed = [cell for cell in filled if parse_quantity(cell) is not None]
    unverified = sum(_is_bare_number(cell) for cell in parsed) if source == SCALE_UNVERIFIED_SOURCE else 0
    return ColumnSummary(
        output, source, len(cells), len(cells) - len(filled), len(filled), len(parsed),
        len(filled) - len(parsed), unverified,
    )


def column_summaries(company: pd.DataFrame) -> tuple[ColumnSummary, ...]:
    _require_columns(company)
    return tuple(_summarise(company, output, source) for output, source in COLUMN_MAP)


# ---- report -----------------------------------------------------------------------------------


def _year_in_header(header: str) -> str:
    found = _YEAR.findall(header)
    return ", ".join(found) if found else "none"


def _fiscal_year_lines() -> list[str]:
    rows = [(source, _year_in_header(source), "Latest" if "latest" in source.lower() else "-") for _, source in COLUMN_MAP]
    return [
        "## Do the three columns share a fiscal year? (headers only)",
        "",
        *_table(("Column header", "Year named in the header", "Says latest"), rows),
        "",
        "Only ProfitUSD2024 names a year (2024). LatestRevenueUSD says latest without a year, and "
        "NumberofEmployees names no year. The headers therefore do not show that the three refer to the same "
        "fiscal year. This is not established and needs the owner or the mentors. The bracketed columns "
        f"({', '.join(NOT_PARSED)}) were not parsed and are not used to answer this.",
        "",
    ]


def render_report(summaries: Sequence[ColumnSummary]) -> str:
    """Counts-only Markdown: no names, no cell values."""
    body = [
        (s.source_column, s.output_column, _fmt(s.rows), _fmt(s.blank), _fmt(s.filled), _fmt(s.parsed),
         _fmt(s.unparsed), _fmt(s.unverified_scale))
        for s in summaries
    ]
    header = ("Source column", "Numeric column", "Rows", "Blank", "Filled", "Parsed", "Unparsed", "Scale unverified")
    lines = [
        "# Company_Data numbers (Step 3)",
        "",
        "Numeric versions of three named columns, read with the one `parse_quantity` function. "
        "Blank markers (empty, `.`, `-`) stay missing. Unreadable cells stay missing and are not guessed. "
        "The row-level table is `data/interim/company_numeric.csv` (git-ignored, keyed by `row:<n>`, no names).",
        "",
        "## Counts per column",
        "",
        *_table(header, body),
        "",
        f"Scale unverified: a {SCALE_UNVERIFIED_SOURCE} cell written as a bare number, without a K, M, B or T "
        "suffix. The file does not state its scale, so it is flagged and kept as written, never rescaled.",
        "",
        *_fiscal_year_lines(),
    ]
    return "\n".join(lines)


# ---- entry points -----------------------------------------------------------------------------


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> int:
    """Verify the raw manifest, write the numeric table and the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        company = pd.read_csv(interim_dir / INPUT_FILE, dtype=str, keep_default_na=False)
        numeric = build_numeric(company)
        summaries = column_summaries(company)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("company-numeric FAILED: %s", error)
        return 1
    numeric.to_csv(interim_dir / OUTPUT_FILE, index=False)
    logger.info("wrote %s (%d rows)", interim_dir / OUTPUT_FILE, len(numeric))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(summaries), encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
