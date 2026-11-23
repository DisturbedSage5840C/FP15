"""Gold-set draw (step 16, part 2): `make gold-set-draw`.

PROVISIONAL (AI-assisted, not a human sign-off). The draw uses Option A: every leader with a cleaned post is in the
pool, with no minimum number of posts per leader, so no stratum is empty. The owner confirms or changes that choice.
The per-leader cap is the proposal in configs/thresholds.yaml that still awaits mentor approval.

It reuses the sampler in src/gold_set.py unchanged. Post ids are the ones src/provisional_measures.py assigns (a
sequence over ALL cleaned cells in a fixed order), so a drawn id means the same cell in both files. An empty cell
cannot be drawn, but it keeps its place in the numbering.

The text file holds post text, so it is written to git-ignored data/derived only. The tracked report holds counts: no
ids, no names, no text. Strata use the frozen leader labels of src/gold_set_groups.py: ceo_type as coded in the posts and
gender exactly as coded in Company_Data (nothing inferred from names; a missing value is its own stratum).
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from src.eda import INTERIM_FILES, NEVER_LOADED
from src.eda_balance import CEO_TYPE_FACTOR, GENDER_FACTOR
from src.eda_common import DEFAULT_THRESHOLDS_PATH, load_eda_settings
from src.gold_set import GoldDraw, GoldSettings, load_gold_settings, sample_gold_set, stratum_report
from src.gold_set_groups import leader_groups
from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import leader_id_for
from src.post_cleaning import DEFAULT_CLEAN_PATH
from src.provisional_common import COMMENT_PREFIX, DEFAULT_DERIVED_DIR, DEFAULT_REPORT_DIR
from src.provisional_measures import INPUT_COLUMNS, _post_id, _sorted_cells
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_OUT_PATH = DEFAULT_DERIVED_DIR / "gold_set_300.csv"
DEFAULT_REPORT_PATH = DEFAULT_REPORT_DIR / "gold_set_draw.md"
LABEL_TABLES = ("posts", "proposal", "company")
GOLD_COLUMNS = ("post_id", "leader_id", "post_text")
POOL_COLUMNS = ("post_id", "leader_id", "ceo_type", "gender_as_coded", "post_text")
GENDER_CODE_PREFIX = "coded "
FILE_MARKER = (
    "PROVISIONAL, AI-assisted draw, not a human sign-off. Option A: all leaders with posts, no minimum per leader. "
    "Holds post text: git-ignored, never to be committed or pasted."
)
REPORT_BANNER = (
    "PROVISIONAL (AI-assisted, not a human sign-off). The draw choices below are pending confirmation by the owner. "
    "Counts only: no ids, no names, no text."
)
MARKER_LINES = 1


def _group_labels(labels: pd.DataFrame) -> pd.DataFrame:
    """leader_id with the two stratum labels; gender keeps its code, with the word 'coded' removed."""
    gender = labels[GENDER_FACTOR].str.removeprefix(GENDER_CODE_PREFIX)
    return pd.DataFrame(
        {
            "leader_id": labels["leader_id"],
            "ceo_type": labels[CEO_TYPE_FACTOR],
            "gender_as_coded": gender,
        }
    )


def build_pool(cells: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Drawable cells: the provisional-measures post_id, leader, the two stratum labels and the text.

    Ids are assigned over every cell first, then empty cells are dropped, so numbering matches the measures file.
    A leader with cells but no group label is refused, never dropped.
    """
    ordered = _sorted_cells(cells)
    numbered = ordered.assign(post_id=[_post_id(position) for position in range(1, len(ordered) + 1)])
    drawable = numbered[numbered["post_text_clean"].str.strip() != ""]
    groups = _group_labels(labels)
    unlabelled = set(drawable["leader_id"]) - set(groups["leader_id"])
    if unlabelled:
        raise ValueError(f"{len(unlabelled)} leader(s) with posts have no group label")
    joined = drawable.merge(groups, on="leader_id", how="left", validate="many_to_one")
    pool = joined.rename(columns={"post_text_clean": "post_text"})
    return pool[list(POOL_COLUMNS)].reset_index(drop=True)


def draw_gold_set(pool: pd.DataFrame, settings: GoldSettings) -> GoldDraw:
    """Run the existing sampler on the pool (no reference table: Option A)."""
    return sample_gold_set(pool[["post_id", "ceo_type", "gender_as_coded", "leader_id"]], settings)


def write_gold_file(frame: pd.DataFrame, path: Path) -> None:
    """Write ids and text under a one-line provisional marker. The parent folder is created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"{COMMENT_PREFIX}{FILE_MARKER}\n")
        frame[list(GOLD_COLUMNS)].to_csv(handle, index=False)


def read_gold_file(path: Path) -> pd.DataFrame:
    """Read a file written by `write_gold_file`. The marker line is skipped by position, so text is never mistaken for it."""
    return pd.read_csv(path, skiprows=MARKER_LINES, dtype=str, keep_default_na=False)


def _table(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(frame.columns) + " |"
    divider = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, divider, *rows])


def _strata_table(pool: pd.DataFrame, draw: GoldDraw) -> pd.DataFrame:
    available = stratum_report(pool, draw.post_ids)[["ceo_type", "gender_as_coded", "available"]]
    merged = draw.strata.merge(available, on=["ceo_type", "gender_as_coded"], how="outer").fillna(0)
    columns = ["ceo_type", "gender_as_coded", "available", "target", "drawn", "shortfall"]
    counts = merged[columns[2:]].astype(int)
    return pd.concat([merged[columns[:2]], counts], axis=1)


def _posts_per_leader(pool: pd.DataFrame, draw: GoldDraw) -> pd.DataFrame:
    chosen = pool[pool["post_id"].isin(draw.post_ids)]
    sizes = Counter(chosen.groupby("leader_id").size())
    rows = [{"posts drawn from the leader": count, "leaders": sizes[count]} for count in sorted(sizes)]
    return pd.DataFrame(rows, columns=["posts drawn from the leader", "leaders"])


def render_report(pool: pd.DataFrame, draw: GoldDraw, settings: GoldSettings, empty_cells: int = 0) -> str:
    """Markdown for reports/gold_set_draw.md: counts only."""
    leaders_in_pool = pool["leader_id"].nunique()
    leaders_drawn = pool[pool["post_id"].isin(draw.post_ids)]["leader_id"].nunique()
    lines = [
        f"# Gold-set draw: {REPORT_BANNER}",
        "",
        "Command: `make gold-set-draw` (`python -m src.gold_set_draw`). Settings come from configs/thresholds.yaml: "
        f"gold_set_size {settings.size}, per-leader cap {settings.max_posts_per_leader} (a proposal awaiting mentor "
        f"approval), seed {settings.seed}.",
        "",
        "**Option A (provisional choice):** the pool is every leader with at least one cleaned post, with no minimum "
        "number of posts per leader, so no stratum is empty. Option B (only leaders at or above min_posts_per_leader) "
        "is not used. The owner confirms or changes this.",
        "",
        "Strata are ceo_type as coded in the posts by gender exactly as coded in Company_Data (nothing inferred from "
        "names; a missing value is its own stratum). 'available' counts posts before the cap.",
        "",
        "## Pool and draw",
        "",
        f"- Cells in the pool: {len(pool)} (empty cells left out: {empty_cells}).",
        f"- Leaders in the pool: {leaders_in_pool}.",
        f"- Posts drawn: {len(draw.post_ids)}. Leaders drawn from: {leaders_drawn}.",
        "",
        "## Strata",
        "",
        _table(_strata_table(pool, draw)),
        "",
        "## Posts drawn per leader",
        "",
        _table(_posts_per_leader(pool, draw)),
        "",
        "Post ids and post text are in the git-ignored data/derived file only.",
    ]
    return "\n".join(lines) + "\n"


def _read_tables(interim_dir: Path) -> dict[str, pd.DataFrame]:
    """The interim tables the frozen labels need, as strings, without post text, links or profile urls."""
    return {
        name: pd.read_csv(
            interim_dir / INTERIM_FILES[name],
            dtype=str,
            keep_default_na=False,
            usecols=lambda column: column not in NEVER_LOADED,
        )
        for name in LABEL_TABLES
    }


def _read_cells(clean_path: Path) -> pd.DataFrame:
    return pd.read_csv(clean_path, dtype=str, keep_default_na=False, usecols=list(INPUT_COLUMNS))


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    clean_path: Path = DEFAULT_CLEAN_PATH,
    out_path: Path = DEFAULT_OUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
    id_of: Callable[[str], str] = leader_id_for,
) -> int:
    """Verify the raw manifest, draw the gold set, write the text file and the report; 0 on success, 1 (nothing written)."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        settings = load_gold_settings(thresholds_path)
        eda = load_eda_settings(thresholds_path)
        cells = _read_cells(clean_path)
        tables = _read_tables(interim_dir)
        labels = leader_groups(tables["posts"], tables["proposal"], tables["company"], eda.size_bands, id_of)
        pool = build_pool(cells, labels)
        draw = draw_gold_set(pool, settings)
        report = render_report(pool, draw, settings, empty_cells=len(cells) - len(pool))
    except (ManifestMismatch, FileNotFoundError, ValueError, KeyError, MissingIdKey) as error:
        logger.error("gold-set-draw FAILED: %s", error)
        return 1
    chosen = pool[pool["post_id"].isin(draw.post_ids)].sort_values("post_id")
    write_gold_file(chosen, out_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s (git-ignored; ids and text) and %s (counts only)", out_path, report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
