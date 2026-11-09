"""Describe the groups the looser dedupe key collapsed although their texts differ (`make dedup-characterise`).

Counts only: group size, link type (from domain and path pattern, never fetched) and how the texts differ. No
names, links, ids or text are written.
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.dedup_check import classify_texts
from src.dedup_rules import LINK_TYPES, RELATIONS, link_type, relation
from src.harmonise import DEFAULT_RAW_DIR, _load_all, dedupe_keys, stack_records
from src.verify_raw import ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = Path("reports/dedup_characterisation.md")
SIZE_BUCKETS = ("2", "3", "4", "5 or more")
MAX_SINGLE_SIZE = 4


@dataclass(frozen=True)
class Characterisation:
    groups: int
    rows: int
    by_size: dict[str, int]
    by_link_type: dict[str, int]
    by_relation: dict[str, int]


def size_bucket(size: int) -> str:
    return str(size) if size <= MAX_SINGLE_SIZE else "5 or more"


def _link_of(key: str, frame: pd.DataFrame) -> str:
    """The group's link; a text-keyed group has none (its link cells are null or blank)."""
    return "" if "|T|" in key else str(frame["link"].iloc[0])


def characterise(stacked: pd.DataFrame) -> Characterisation:
    """Tally size, link type and text relation for every group whose texts differ in content."""
    keys = dedupe_keys(stacked)
    sizes = keys.value_counts()
    repeated = set(sizes[sizes > 1].index)
    grouped = stacked.assign(_key=keys).groupby("_key", sort=False)
    by_size: Counter[str] = Counter()
    by_link: Counter[str] = Counter()
    by_relation: Counter[str] = Counter()
    groups = rows = 0
    for key, frame in grouped:
        if key not in repeated:
            continue
        texts = [str(t) for t in frame["post_text"]]
        if classify_texts(texts) != "content":
            continue
        groups += 1
        rows += len(texts)
        by_size[size_bucket(len(texts))] += 1
        by_link[link_type(_link_of(key, frame))] += 1
        by_relation[relation(texts)] += 1
    return Characterisation(groups, rows, dict(by_size), dict(by_link), dict(by_relation))


def _table(counts: dict[str, int], order: Sequence[str]) -> str:
    return "\n".join(f"| {name} | {counts.get(name, 0)} |" for name in order)


def render_report(result: Characterisation) -> str:
    return f"""# Dedupe characterisation: groups whose texts differ in content

Counts only; no names, ids, links or text. These are the groups the looser harmonise key collapsed although the
raw texts are not the same after ignoring spacing, case and punctuation (see `reports/dedup_check.md`).

| Measure | Count |
|---|---|
| Content-different groups | {result.groups} |
| Rows those groups held | {result.rows} |

## Group size (rows per group)

| Rows in group | Groups |
|---|---|
{_table(result.by_size, SIZE_BUCKETS)}

## Link type

From the domain and path pattern only; no link is opened. No link means the group was keyed on the first 200
characters of text.

| Link type | Groups |
|---|---|
{_table(result.by_link_type, LINK_TYPES)}

## How the texts differ

Tried in this order, first match wins: only the trailing number or age line differs (trailing_only); the
shortest text is the start of every other (prefix); identical after removing the first N lines, N up to 5
(first_lines); anything else (other).

| Difference | Groups |
|---|---|
{_table(result.by_relation, RELATIONS)}
"""


def run(raw_dir: Path = DEFAULT_RAW_DIR, report_path: Path = DEFAULT_REPORT_PATH) -> int:
    """Verify the raw manifest, characterise the content-different groups, write the report; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        stacked, _ = stack_records(_load_all(raw_dir))
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("dedup-characterise FAILED: %s", error)
        return 1
    result = characterise(stacked)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result), encoding="utf-8")
    logger.info("wrote %s: %d content-different groups", report_path, result.groups)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
