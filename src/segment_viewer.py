"""Make the G1 hand count practical (`make segmentation-viewer`): a private name lookup and a local counting page.

Writes two files into data/derived, both git-ignored because the first holds names:
- segmentation_check_200_names.csv: n, leader_name, company_name. The name comes from the same leader_id -> name
  mapping the pipeline already uses (src.handcheck_names._sheet_leaders). Every row is checked: the cell's raw
  post must exist and its leader's keyed id must equal the sample's leader_id, or nothing is written.
- segmentation_counter.html: a copy of src/templates/segmentation_counter.html (one file, no network).

It never touches the live sample (segmentation_check_200.csv), holds no segmenter count and counts nothing. The
log and every error report counts only, never a name, a ref, an id or any text.
"""
from __future__ import annotations

import logging
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from src.handcheck_names import _sheet_leaders
from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.reaction_count_check import FORMULA_TRIGGERS, RAW_KIND, _read_posts, spreadsheet_safe
from src.segment import DEFAULT_SAMPLE_PATH, ref_for
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

NAMES_COLUMNS = ("n", "leader_name", "company_name")
DEFAULT_NAMES_PATH = Path("data/derived/segmentation_check_200_names.csv")
DEFAULT_VIEWER_PATH = Path("data/derived/segmentation_counter.html")
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "segmentation_counter.html"
DEFUSING_PREFIX = "'"
SAMPLE_NEEDS = ("n", "leader_id", "ref")


def _undefused(ref: str) -> str:
    """The sample prefixes an apostrophe to a ref a spreadsheet would run as a formula; undo exactly that."""
    if ref.startswith(DEFUSING_PREFIX) and ref[len(DEFUSING_PREFIX):].startswith(FORMULA_TRIGGERS):
        return ref[len(DEFUSING_PREFIX):]
    return ref


def _leader_by_ref(posts: pd.DataFrame) -> dict[str, str]:
    """Raw cell ref -> the leader name written on that row."""
    raw = posts[posts["text_kind"] == RAW_KIND]
    return {
        ref_for(row.workbook, row.sheet_idx, row.source_row): str(row.leader)
        for row in raw.itertuples(index=False)
    }


def names_frame(sample: pd.DataFrame, posts: pd.DataFrame) -> pd.DataFrame:
    """n, leader_name, company_name for every sample row, or ValueError that says how many rows failed (no names).

    A row fails when its raw cell is not in the posts, or when the keyed id of that cell's leader differs from the
    sample's leader_id. Nothing is guessed: either every row is confirmed or no lookup is produced.
    """
    missing = [column for column in SAMPLE_NEEDS if column not in sample.columns]
    if missing:
        raise ValueError(f"sample is missing columns {missing}")
    if "company" not in posts.columns:
        raise ValueError("harmonised posts have no company column")
    leaders, by_ref = _sheet_leaders(posts), _leader_by_ref(posts)
    rows: list[tuple[int, str, str]] = []
    failed = 0
    for row in sample.itertuples(index=False):
        leader = by_ref.get(_undefused(str(row.ref)))
        key = name_key(leader) if leader is not None else ""
        if not key or leader_id_for(key) != row.leader_id:
            failed += 1
            continue
        sheet = leaders[key]
        rows.append((int(row.n), spreadsheet_safe(sheet.name), spreadsheet_safe(sheet.company)))
    if failed:
        raise ValueError(f"{failed} of {len(sample)} sample rows could not be matched to a leader by ref and id")
    return pd.DataFrame(rows, columns=list(NAMES_COLUMNS))


def _read_sample(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    sample_path: Path = DEFAULT_SAMPLE_PATH,
    names_path: Path = DEFAULT_NAMES_PATH,
    viewer_path: Path = DEFAULT_VIEWER_PATH,
) -> int:
    """Verify the raw manifest, write the names lookup, install the viewer. 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        names = names_frame(_read_sample(sample_path), _read_posts(interim_dir))
        if not TEMPLATE_PATH.is_file():
            raise FileNotFoundError(f"viewer template missing: {TEMPLATE_PATH}")
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("segmentation-viewer FAILED: %s", error)
        return 1
    names_path.parent.mkdir(parents=True, exist_ok=True)
    names.to_csv(names_path, index=False)
    viewer_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE_PATH, viewer_path)
    logger.info("wrote %s (%d rows; git-ignored; holds names)", names_path, len(names))
    logger.info("wrote %s (git-ignored; open it in a browser and pick the two CSVs)", viewer_path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
