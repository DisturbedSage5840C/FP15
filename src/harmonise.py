"""Step 2b: map every post-bearing sheet onto one schema and write it to data/interim.

Rules (project owner, recorded in docs/decisions.md):
  * the FIRST post sheet of a workbook is the combined sheet: rows with no leader are dropped;
  * in every other sheet a blank leader cell means the sheet name is the leader (an ASSUMPTION,
    spot-checked in the report); a sheet whose filled cells hold two or more distinct leaders is
    treated like the combined sheet; nothing is forward-filled;
  * duplicates are removed on (leader, link if present else the first 200 characters of text).
Nothing is guessed: missing stays missing, skipped sheets carry a written reason.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

import pandas as pd

from src.harmonise_plan import SheetPlan, plan_sheet
from src.harmonise_report import render_report
from src.loader import SheetRecord, load_zip_workbooks
from src.name_key import name_key
from src.sheet_profile import SheetProfile, normalise_header, profile_records
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_INTERIM_DIR = Path("data/interim")
DEFAULT_REPORT_PATH = Path("reports/harmonise_summary.md")
ZIP_SUFFIX = ".zip"
ROSTER_SUFFIX = "seventh_100_leaders/All_500.xlsx"
ROSTER_SCAN_ROWS = 20
POST_DATE_TEXT_LEN = 40  # a "date" longer than this is post text that slipped into the column
DEDUPE_TEXT_CHARS = 200

ROLE_COLUMNS = (
    "leader", "company", "title", "ceo_type", "platform", "post_text", "link", "age_text",
    "profile_url", "role_start_year", "post_date", "post_date_text",
)
SCHEMA_COLUMNS = (
    *ROLE_COLUMNS[:9], "batch", "sheet", "workbook", "sheet_idx", "source_row",
    *ROLE_COLUMNS[9:], "post_date_is_text", "text_kind", "leader_source",
)
POST_COLUMNS = (*SCHEMA_COLUMNS, "n_copies")
ROSTER_BY_HEADER = {
    "companyname": "company", "person_name": "person_name", "current_title": "title",
    "linkedin_profile_link": "profile_url", "person_id": "person_id",
}
ROSTER_COLUMNS = ("company", "person_name", "title", "profile_url", "person_id")


@dataclass(frozen=True)
class FillResult:
    rows: pd.DataFrame
    dropped: int  # rows removed because no leader could be assigned
    filled: int  # blank leader cells set from the sheet name
    conflict: int  # of those, rows where the sheet name disagrees with the leader cells
    cell_leader_rows: int  # rows whose leader cell was filled (single-leader sheets only)
    cell_matches_sheet: int  # of those, rows whose leader cell agrees with the sheet name


@dataclass(frozen=True)
class HarmonisedResult:
    posts: pd.DataFrame
    sheet_log: pd.DataFrame
    rows_with_text: int
    rows_after_leader: int


def batch_of(workbook: str) -> str:
    """Batch = the folder that holds the workbook inside the archive."""
    return PurePosixPath(workbook).parent.name


def _clean(value: object) -> str | None:
    if value is None or cast(bool, pd.isna(value)):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _empty_rows() -> pd.DataFrame:
    return pd.DataFrame({column: [] for column in SCHEMA_COLUMNS}, dtype=object)


def extract_rows(record: SheetRecord, plan: SheetPlan, sheet_idx: int) -> pd.DataFrame:
    """Rows of one planned sheet that carry post text, on the common schema."""
    if plan.skip_reason is not None or record.frame is None:
        return _empty_rows()
    body = record.frame.iloc[plan.first_data_row :]
    positions = {role: position for position, role in plan.roles}
    values = {
        role: [_clean(v) for v in body.iloc[:, positions[role]]]
        if role in positions and positions[role] < body.shape[1]
        else [None] * len(body)
        for role in ROLE_COLUMNS
    }
    source_rows = [plan.first_data_row + i + 1 for i in range(len(body))]
    frame = pd.DataFrame(
        {
            **values,
            "batch": batch_of(record.workbook),
            "sheet": record.sheet,
            "workbook": record.workbook,
            "sheet_idx": sheet_idx,
            "source_row": source_rows,
            "post_date_is_text": [d is not None and len(d) > POST_DATE_TEXT_LEN for d in values["post_date"]],
            "text_kind": plan.text_kind,
            "leader_source": [None] * len(body),
        },
        dtype=object,
    )
    keep = [t is not None for t in values["post_text"]]
    return frame.loc[keep, list(SCHEMA_COLUMNS)].reset_index(drop=True)


def _filled_keys(rows: pd.DataFrame) -> set[str]:
    return {key for key in (name_key(v) for v in rows["leader"]) if key}


def _drop_blank_leaders(rows: pd.DataFrame) -> FillResult:
    has_leader = [name_key(v) != "" for v in rows["leader"]]
    kept = rows.loc[has_leader].reset_index(drop=True).assign(leader_source="cell")
    return FillResult(kept, int(len(rows) - sum(has_leader)), 0, 0, 0, 0)


def fill_leader(rows: pd.DataFrame, sheet_name: str, is_combined: bool) -> FillResult:
    """Assign a leader to every row, or drop the row; never forward-fills."""
    if is_combined or len(_filled_keys(rows)) >= 2:
        return _drop_blank_leaders(rows)
    cell_keys = _filled_keys(rows)
    sheet_key = name_key(sheet_name)
    disagrees = bool(cell_keys) and cell_keys != {sheet_key}
    blank = [name_key(v) == "" for v in rows["leader"]]
    fill_source = "sheet_name_conflict" if disagrees else "sheet_name"
    leaders = [sheet_name if is_blank else v for is_blank, v in zip(blank, rows["leader"])]
    sources = [fill_source if is_blank else "cell" for is_blank in blank]
    filled = rows.assign(leader=pd.Series(leaders, dtype=object), leader_source=pd.Series(sources, dtype=object))
    n_blank = sum(blank)
    n_cell = len(rows) - n_blank
    return FillResult(
        filled, 0, n_blank, n_blank if disagrees else 0, n_cell, 0 if disagrees else n_cell
    )


def dedupe_keys(posts: pd.DataFrame) -> pd.Series:
    """The looser key: (leader, link) when a link is present, else (leader, first 200 characters of text)."""
    return pd.Series(
        [
            f"{name_key(leader)}|L|{link}" if link else f"{name_key(leader)}|T|{str(text)[:DEDUPE_TEXT_CHARS]}"
            for leader, link, text in zip(posts["leader"], posts["link"], posts["post_text"])
        ],
        index=posts.index,
        dtype=object,
    )


def drop_duplicates(posts: pd.DataFrame) -> pd.DataFrame:
    """Keep the first copy of each (leader, link-or-text-head) post and count the copies."""
    keys = dedupe_keys(posts)
    counted = posts.assign(n_copies=keys.map(keys.value_counts()))
    return counted.loc[~keys.duplicated()].reset_index(drop=True)


def _log_entry(
    record: SheetRecord, profile: SheetProfile, plan: SheetPlan, is_combined: bool, fill: FillResult | None,
    n_text: int,
) -> dict[str, object]:
    skipped = plan.skip_reason is not None
    return {
        "workbook": record.workbook,
        "sheet_idx": profile.position,
        "sheet": record.sheet,
        "status": "skipped" if skipped else "used",
        "reason": plan.skip_reason or "",
        "is_combined": is_combined,
        "method": plan.method,
        "text_kind": plan.text_kind,
        "odd_reasons": "; ".join(profile.odd_reasons),
        "rows_with_text": n_text,
        "rows_kept": 0 if fill is None else len(fill.rows),
        "dropped_no_leader": 0 if fill is None else fill.dropped,
        "filled_from_sheet": 0 if fill is None else fill.filled,
        "sheet_name_conflict": 0 if fill is None else fill.conflict,
        "cell_leader_rows": 0 if fill is None else fill.cell_leader_rows,
        "cell_matches_sheet": 0 if fill is None else fill.cell_matches_sheet,
    }


def stack_records(records: list[SheetRecord]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Planning, extraction and leader assignment over every loaded sheet, before any dedupe: (rows, sheet log)."""
    frames: list[pd.DataFrame] = []
    log: list[dict[str, object]] = []
    seen_workbooks: set[str] = set()
    for record, profile in zip(records, profile_records(records)):
        plan = plan_sheet(record, profile)
        if plan.skip_reason is not None:
            log.append(_log_entry(record, profile, plan, False, None, 0))
            continue
        is_combined = record.workbook not in seen_workbooks
        seen_workbooks.add(record.workbook)
        rows = extract_rows(record, plan, profile.position)
        fill = fill_leader(rows, record.sheet, is_combined)
        frames.append(fill.rows)
        log.append(_log_entry(record, profile, plan, is_combined, fill, len(rows)))
    stacked = pd.concat(frames, ignore_index=True) if frames else _empty_rows()
    return stacked, pd.DataFrame(log)


def harmonise_records(records: list[SheetRecord]) -> HarmonisedResult:
    """Run planning, extraction, leader assignment and dedupe over every loaded sheet."""
    stacked, sheet_log = stack_records(records)
    return HarmonisedResult(
        posts=drop_duplicates(stacked),
        sheet_log=sheet_log,
        rows_with_text=int(sheet_log["rows_with_text"].sum()) if len(sheet_log) else 0,
        rows_after_leader=len(stacked),
    )


def _roster_header_row(frame: pd.DataFrame) -> int | None:
    for index in range(min(ROSTER_SCAN_ROWS, len(frame))):
        cells = {normalise_header(c) for c in (_clean(v) for v in frame.iloc[index]) if c is not None}
        if "person_id" in cells:
            return index
    return None


def load_roster(records: list[SheetRecord]) -> pd.DataFrame:
    """The roster, loaded ONCE from seventh_100_leaders/All_500.xlsx (never the other copies)."""
    for record in records:
        if record.frame is None or not record.workbook.endswith(ROSTER_SUFFIX):
            continue
        header_row = _roster_header_row(record.frame)
        if header_row is None:
            continue
        header = [normalise_header(c) if (c := _clean(v)) is not None else "" for v in record.frame.iloc[header_row]]
        position = {ROSTER_BY_HEADER[h]: i for i, h in enumerate(header) if h in ROSTER_BY_HEADER}
        body = record.frame.iloc[header_row + 1 :]
        roster = pd.DataFrame(
            {col: [_clean(v) for v in body.iloc[:, position[col]]] if col in position else [None] * len(body)
             for col in ROSTER_COLUMNS},
            dtype=object,
        )
        keep = roster["person_id"].notna() | roster["person_name"].notna()
        return roster.loc[keep].reset_index(drop=True)
    raise ValueError(f"roster workbook {ROSTER_SUFFIX} not found or it has no person_id header")


def write_interim(result: HarmonisedResult, roster: pd.DataFrame, interim_dir: Path) -> list[Path]:
    """Write the git-ignored interim tables; they may hold names, analysis files must not."""
    interim_dir.mkdir(parents=True, exist_ok=True)
    skipped = result.sheet_log.loc[result.sheet_log["status"] == "skipped"]
    outputs = {
        "harmonised_posts.csv": result.posts.loc[:, list(POST_COLUMNS)],
        "harmonise_sheet_log.csv": result.sheet_log,
        "harmonise_skipped.csv": skipped,
        "roster.csv": roster,
    }
    paths = []
    for name, table in outputs.items():
        path = interim_dir / name
        table.to_csv(path, index=False)
        paths.append(path)
    return paths


def _load_all(raw_dir: Path) -> list[SheetRecord]:
    archives = sorted(raw_dir.glob(f"*{ZIP_SUFFIX}"))
    if not archives:
        raise FileNotFoundError(f"no {ZIP_SUFFIX} archive in {raw_dir}")
    return [record for archive in archives for record in load_zip_workbooks(archive)]


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> int:
    """Verify the raw manifest, harmonise, write interim tables and the report; 0 on success."""
    try:
        status = verify_raw(raw_dir)
        logger.info("manifest %s for %s", status, raw_dir)
        records = _load_all(raw_dir)
        result = harmonise_records(records)
        roster = load_roster(records)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("harmonise FAILED: %s", error)
        return 1
    for path in write_interim(result, roster, interim_dir):
        logger.info("wrote %s", path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result, roster), encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
