"""Load, clean and profile Company_Data.xlsx.

Contact columns (email and phone) are dropped at load, before anything reaches disk or a report.
"." and "-" are blank. Quantities such as "186.6M" and "2.5B" are read by one function,
`parse_quantity`. Gender is kept exactly as coded and only counted, never decoded.
The profile report carries counts and column headers only: no names, companies or cell values.
"""
from __future__ import annotations

import logging
import math
import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

COMPANY_FILE = "Company_Data.xlsx"
DEFAULT_INTERIM_DIR = Path("data/interim")
DEFAULT_REPORT_PATH = Path("reports/company_data_profile.md")
CONTACT_COLUMNS = frozenset({"Email", "KeyPeopleEmailIds", "CompanyEmails", "CompanyPhoneNumbers"})
WATCHED_HEADERS = ("Q", "V", "Z")  # single-letter headers whose meaning is unknown
GENDER_COLUMN = "Gender"
BLANK_MARKERS = frozenset({"", ".", "-"})
SUFFIX_FACTORS = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
EMAIL_COLUMN_SHARE = 0.5  # share of filled cells holding an email address that marks a contact column

_CONTACT_NAME = re.compile(r"e[-_ ]?mail|phone", re.IGNORECASE)
_QUANTITY = re.compile(r"^(-?\d+(?:\.\d+)?)([KMBT%]?)$", re.IGNORECASE)
_EMAIL_CELL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_CELL = re.compile(r"\+\d[\d\s().-]{8,}\d|\(?\d{2,5}\)?[\s.-]\d{3,5}[\s.-]\d{3,5}")


def is_contact_column(name: str) -> bool:
    """True for the four named contact columns and any header that names an email or phone."""
    return name in CONTACT_COLUMNS or bool(_CONTACT_NAME.search(name))


def clean_cell(value: object) -> str | None:
    """Cell text with "." and "-" (and empty or NaN) turned into None; nothing else is changed."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return None if text in BLANK_MARKERS else text


def parse_quantity(value: object) -> float | None:
    """Read '186.6M', '2.5B', '12K', '1,250', '14%' or a plain number; None if it is not one.

    A trailing % keeps the number as written ('14%' -> 14.0). '500+' and similar are not
    guessed at: they return None.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return None if isinstance(value, float) and math.isnan(value) else float(value)
    text = clean_cell(value)
    if text is None:
        return None
    match = _QUANTITY.match(text.replace(",", ""))
    if match is None:
        return None
    number, suffix = float(match.group(1)), match.group(2).upper()
    return number * SUFFIX_FACTORS.get(suffix, 1.0)


@dataclass(frozen=True)
class LoadedCompanyData:
    frame: pd.DataFrame
    dropped: tuple[str, ...]  # every dropped header: by name and by content
    columns_loaded: int
    dropped_by_content: tuple[str, ...] = ()  # subset of `dropped`: not named like contact columns


def _mostly_email(cells: Sequence[object]) -> bool:
    """True when email addresses make up at least EMAIL_COLUMN_SHARE of the filled cells."""
    filled = [text for text in (clean_cell(v) for v in cells) if text is not None]
    if not filled:
        return False
    hits = sum(1 for text in filled if _EMAIL_CELL.search(text))
    return hits / len(filled) >= EMAIL_COLUMN_SHARE


def load_company_data(path: Path) -> LoadedCompanyData:
    """Read the workbook, drop contact columns first, then clean the remaining cells.

    A column goes if its header names an email or phone, or if most of its cells are email
    addresses (a free-text column can carry them under an innocent header). Both checks run on
    the in-memory raw sheet, so no contact value reaches disk or a report.
    """
    raw = pd.read_excel(path, header=None, dtype=object)
    headers = [str(h).strip() for h in raw.iloc[0]]
    body_all = raw.iloc[1:]
    by_name = {i for i, name in enumerate(headers) if is_contact_column(name)}
    by_content = {
        i for i in range(len(headers))
        if i not in by_name and _mostly_email(body_all.iloc[:, i].tolist())
    }
    keep = [i for i in range(len(headers)) if i not in by_name | by_content]
    kept_names = [headers[i] for i in keep]
    if len(set(kept_names)) != len(kept_names):
        raise ValueError("duplicate column headers in Company_Data after dropping contact columns")
    body = body_all.iloc[:, keep]
    frame = pd.DataFrame(
        {name: [clean_cell(v) for v in body.iloc[:, pos]] for pos, name in enumerate(kept_names)},
        dtype=object,
    )
    return LoadedCompanyData(
        frame=frame,
        dropped=tuple(headers[i] for i in sorted(by_name | by_content)),
        columns_loaded=len(headers),
        dropped_by_content=tuple(headers[i] for i in sorted(by_content)),
    )


def with_numeric_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """A copy with a `<column>_num` companion for every column that carries K/M/B/T suffixes."""
    extra = {
        f"{column}_num": [parse_quantity(v) for v in frame[column]]
        for column in frame.columns
        if _suffixed_count(frame[column]) > 0
    }
    return frame.assign(**extra)


def _suffixed_count(column: pd.Series) -> int:
    return sum(
        1 for v in column
        if isinstance(v, str) and v[-1:].upper() in "KMBT" and parse_quantity(v) is not None
    )


@dataclass(frozen=True)
class WatchedColumn:
    name: str
    filled: int
    blank: int
    distinct: int
    percent_formatted: int
    negative: int
    zero: int
    positive: int


@dataclass(frozen=True)
class MagnitudeColumn:
    name: str
    filled: int
    parsed: int
    suffixed: int


@dataclass(frozen=True)
class CompanyProfile:
    rows: int
    columns_loaded: int
    columns_kept: int
    dropped: tuple[str, ...]
    dropped_by_content: tuple[str, ...]
    gender_counts: dict[str, int]
    watched: tuple[WatchedColumn, ...]
    magnitude_columns: tuple[MagnitudeColumn, ...]
    contact_like_cells: dict[str, int]
    empty_columns: tuple[str, ...]


def _watched(frame: pd.DataFrame, name: str) -> WatchedColumn:
    column = frame[name]
    filled = [v for v in column if v is not None]
    numbers = [n for n in (parse_quantity(v) for v in filled) if n is not None]
    return WatchedColumn(
        name=name,
        filled=len(filled),
        blank=len(column) - len(filled),
        distinct=len(set(filled)),
        percent_formatted=sum(1 for v in filled if v.endswith("%")),
        negative=sum(1 for n in numbers if n < 0),
        zero=sum(1 for n in numbers if n == 0),
        positive=sum(1 for n in numbers if n > 0),
    )


def _magnitude(frame: pd.DataFrame) -> tuple[MagnitudeColumn, ...]:
    found = []
    for name in frame.columns:
        suffixed = _suffixed_count(frame[name])
        if suffixed:
            filled = [v for v in frame[name] if v is not None]
            parsed = sum(1 for v in filled if parse_quantity(v) is not None)
            found.append(MagnitudeColumn(str(name), len(filled), parsed, suffixed))
    return tuple(found)


def _contact_like(frame: pd.DataFrame) -> dict[str, int]:
    counts = {}
    for name in frame.columns:
        hits = sum(
            1 for v in frame[name]
            if isinstance(v, str) and (_EMAIL_CELL.search(v) or _PHONE_CELL.search(v))
        )
        if hits:
            counts[str(name)] = hits
    return counts


def _gender_counts(frame: pd.DataFrame) -> dict[str, int]:
    if GENDER_COLUMN not in frame.columns:
        return {}
    coded = Counter(v for v in frame[GENDER_COLUMN] if v is not None)
    blank = int(frame[GENDER_COLUMN].isna().sum())
    return {**dict(coded.most_common()), "blank": blank}


def profile_company_data(loaded: LoadedCompanyData) -> CompanyProfile:
    """Counts only: shape, dropped headers, Gender as coded, Q/V/Z, magnitude columns."""
    frame = loaded.frame
    return CompanyProfile(
        rows=len(frame),
        columns_loaded=loaded.columns_loaded,
        columns_kept=len(frame.columns),
        dropped=loaded.dropped,
        dropped_by_content=loaded.dropped_by_content,
        gender_counts=_gender_counts(frame),
        watched=tuple(_watched(frame, h) for h in WATCHED_HEADERS if h in frame.columns),
        magnitude_columns=_magnitude(frame),
        contact_like_cells=_contact_like(frame),
        empty_columns=tuple(str(c) for c in frame.columns if frame[c].isna().all()),
    )


def _table(header: tuple[str, ...], rows: Sequence[tuple[object, ...]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]


def render_profile(profile: CompanyProfile) -> str:
    """Markdown for reports/company_data_profile.md: counts and column headers only."""
    gender = [(k, f"{v:,}") for k, v in profile.gender_counts.items()]
    watched = [
        (w.name, w.filled, w.blank, w.distinct, w.percent_formatted, w.negative, w.zero, w.positive)
        for w in profile.watched
    ]
    magnitude = [(m.name, m.filled, m.suffixed, m.parsed) for m in profile.magnitude_columns]
    contact = [(name, n) for name, n in profile.contact_like_cells.items()]
    sections = [
        ["# Company_Data profile", "",
         "Counts and column headers only: no names, companies or cell values. Contact columns were "
         "dropped at load, before anything was written."],
        ["## Shape", "", *_table(("Item", "Count"), [
            ("Data rows", f"{profile.rows:,}"),
            ("Columns in the file", profile.columns_loaded),
            ("Contact columns dropped at load", len(profile.dropped)),
            ("Columns kept", profile.columns_kept),
        ])],
        ["## Contact columns dropped (headers)", "",
         *[f"- {name}" for name in profile.dropped if name not in profile.dropped_by_content]],
        ["## Columns dropped because their cells are mostly email addresses (headers)", "",
         f"Rule: email addresses in at least {EMAIL_COLUMN_SHARE:.0%} of a column's filled cells. "
         "The header does not say contact, the content does.", "",
         *([f"- {name}" for name in profile.dropped_by_content] or ["None."])],
        ["## Gender (counts as coded; not decoded)", "",
         "Gender is used exactly as coded in the file. What 1 and 0 mean is an open question for the "
         "mentors; nothing here decodes it, and no gender is inferred from names.", "",
         *_table(("Value as coded", "Rows"), gender)],
        ["## Columns with the headers Q, V and Z", "",
         "These are the columns whose header text is the single letter (not the Excel columns "
         "lettered Q, V, Z). Counts only; what they measure is not decided here.", "",
         *_table(("Header", "Filled", "Blank", "Distinct", "Ends in %", "Negative", "Zero", "Positive"),
                 watched)],
        ["## Columns carrying K/M/B/T suffixes (parsed by one function)", "",
         *_table(("Column", "Filled", "With suffix", "Parsed"), magnitude)],
        ["## Contact-like text left in kept columns (heuristic)", "",
         "Cells in kept columns that look like an email address or a phone number. Reported, not "
         "scrubbed.", "",
         *(_table(("Column", "Cells"), contact) if contact else ["None found."])],
        ["## Columns with no value at all", "", *([f"- {name}" for name in profile.empty_columns]
                                                  or ["None."])],
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"


def write_interim(frame: pd.DataFrame, interim_dir: Path) -> Path:
    """Write the cleaned frame (no contact columns) to data/interim/company_data.csv."""
    interim_dir.mkdir(parents=True, exist_ok=True)
    target = interim_dir / "company_data.csv"
    frame.to_csv(target, index=False, encoding="utf-8")
    return target


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> int:
    """Verify the raw manifest, load Company_Data, write the interim CSV and the profile; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        loaded = load_company_data(raw_dir / COMPANY_FILE)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("company_data FAILED: %s", error)
        return 1
    logger.info("wrote %s", write_interim(with_numeric_columns(loaded.frame), interim_dir))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_profile(profile_company_data(loaded)), encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
