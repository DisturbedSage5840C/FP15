"""Step 2: write reports/data_inventory.md from data/raw.

Verifies the raw-data manifest first, then reads everything in memory. Nothing in data/raw is
changed (the manifest is written only on the very first run, by verify_raw), and the report
carries counts and header labels only.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from src.inventory_report import (
    ZipMember,
    list_zip_members,
    render_report,
    summarise_company_data,
)
from src.loader import SheetRecord, load_workbook_sheets, load_zip_workbooks
from src.sheet_profile import profile_records
from src.verify_raw import DEFAULT_RAW_DIR, MANIFEST_NAME, ManifestMismatch, read_manifest, run

logger = logging.getLogger(__name__)

DEFAULT_REPORT = Path("reports/data_inventory.md")
COMPANY_DATA_NAME = "Company_Data.xlsx"
ZIP_SUFFIX = ".zip"


def _load_company_data(raw_dir: Path) -> SheetRecord:
    path = raw_dir / COMPANY_DATA_NAME
    if not path.exists():
        raise FileNotFoundError(f"{COMPANY_DATA_NAME} not found in {raw_dir}")
    loaded = [r for r in load_workbook_sheets(path, COMPANY_DATA_NAME) if r.frame is not None]
    if not loaded:
        raise ValueError(f"{COMPANY_DATA_NAME} has no readable sheet")
    return loaded[0]


def build_report(raw_dir: Path) -> str:
    """Render the inventory for an already-verified raw folder."""
    manifest = read_manifest(raw_dir)
    sizes = {name: (raw_dir / name).stat().st_size for name in manifest if (raw_dir / name).exists()}
    archives = sorted(raw_dir.glob(f"*{ZIP_SUFFIX}"))
    members: list[ZipMember] = [m for archive in archives for m in list_zip_members(archive)]
    records = [r for archive in archives for r in load_zip_workbooks(archive)]
    return render_report(
        manifest=manifest,
        sizes=sizes,
        members=members,
        profiles=profile_records(records),
        company=summarise_company_data(_load_company_data(raw_dir)),
    )


def main(raw_dir: Path = DEFAULT_RAW_DIR, report_path: Path = DEFAULT_REPORT) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        status = run(raw_dir)
        logger.info("manifest %s for %s (%s)", status, raw_dir, MANIFEST_NAME)
        text = build_report(raw_dir)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("inventory FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    logger.info("wrote %s", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
