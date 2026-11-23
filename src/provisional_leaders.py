"""Provisional leader-level measures (step 14, part 2): mean pronoun rates per leader, shrunk from post to leader.

PROVISIONAL. G1 is unsigned, so raw cells stand in for posts; English-only pronoun counts; no gold-set check;
exploratory, not pre-registered. Claims are about the image projected in public posts, never personality.
The singular rate is one signal, not a narcissism score.

Reads the git-ignored per-post file from `src.provisional_measures`, keeps leaders at or above the minimum posts in
configs/thresholds.yaml, and applies the existing shrinkage in `src.stats_tools`. Every summary is shown for all
cells and again without possible-Hinglish cells. The per-leader file is git-ignored (leader_id and numbers only);
the tracked report holds aggregates only, with counts under the disclosure minimum shown as "<5".
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Collection
from pathlib import Path

import pandas as pd

from src.eda_common import (
    DEFAULT_THRESHOLDS_PATH,
    SMALL,
    load_eda_settings,
    protect_cells,
    show_count,
    show_share,
)
from src.provisional_common import (
    BANNER,
    DEFAULT_DERIVED_DIR,
    DEFAULT_MEASURES_PATH,
    DEFAULT_REPORT_DIR,
    read_banner_csv,
    write_banner_csv,
)
from src.stats_tools import shrink_leader_scores
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

ALL_CELLS = "all cells"
NO_HINGLISH = "without possible-Hinglish cells"
CELL_SETS = ((ALL_CELLS, False), (NO_HINGLISH, True))
MEASURES = ("singular_per_100", "plural_per_100")
MEASURE_LABELS = {"singular_per_100": "first-person singular (I-rate)", "plural_per_100": "first-person plural (we-rate)"}
REQUIRED_COLUMNS = ("leader_id", "post_id", "word_count", *MEASURES, "hinglish_flag")
LEADER_COLUMNS = ("leader_id", "measure", "cell_set", "n_posts", "raw_mean", "weight", "shrunk_mean")
SUMMARY_KEYS = ("leaders", "min", "q1", "median", "q3", "max")
WITH_FLAG = "leaders with at least one flagged cell"
WITHOUT_FLAG = "leaders with no flagged cell"
DEFAULT_LEADER_PATH = DEFAULT_DERIVED_DIR / "provisional_leader_measures.csv"
DEFAULT_REPORT_PATH = DEFAULT_REPORT_DIR / "provisional_leader_measures.md"
RATE_FORMAT = "{:.2f}"


def _require(measures: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in measures.columns]
    if missing:
        raise ValueError(f"provisional measures file is missing columns {missing}")


def _shrunk_leaders(
    measures: pd.DataFrame, measure: str, cell_set: str, drop_flagged: bool, min_posts: int
) -> pd.DataFrame:
    """Shrinkage for one measure on one cell set; an empty frame when fewer than two leaders qualify (a data limit)."""
    cells = measures[measures["hinglish_flag"] == 0] if drop_flagged else measures
    posts = cells.loc[:, ["leader_id", measure]].rename(columns={measure: "score"})
    try:
        leaders = shrink_leader_scores(posts, min_posts=min_posts).leaders
    except ValueError as error:
        logger.warning("%s, %s: no shrinkage (%s)", measure, cell_set, error)
        return pd.DataFrame(columns=list(LEADER_COLUMNS))
    return leaders.assign(measure=measure, cell_set=cell_set).loc[:, list(LEADER_COLUMNS)]


def build_leader_frame(measures: pd.DataFrame, min_posts: int) -> pd.DataFrame:
    """One row per leader, measure and cell set: scored post count, raw mean, shrinkage weight and shrunk mean."""
    _require(measures)
    parts = [
        _shrunk_leaders(measures, measure, cell_set, drop_flagged, min_posts)
        for measure in MEASURES
        for cell_set, drop_flagged in CELL_SETS
    ]
    parts = [part for part in parts if not part.empty]
    if not parts:
        return pd.DataFrame(columns=list(LEADER_COLUMNS))
    return pd.concat(parts, ignore_index=True)


def summarise(values: pd.Series, disclosure_min: int) -> dict[str, str]:
    """Count, min, quartiles and max of leader-level values; everything is hidden under the disclosure minimum."""
    clean = values.dropna()
    count = show_count(len(clean), disclosure_min)
    if count == SMALL:
        return dict.fromkeys(SUMMARY_KEYS, SMALL)
    quartiles = clean.quantile([0.25, 0.5, 0.75])
    return {
        "leaders": count,
        "min": RATE_FORMAT.format(clean.min()),
        "q1": RATE_FORMAT.format(quartiles[0.25]),
        "median": RATE_FORMAT.format(quartiles[0.5]),
        "q3": RATE_FORMAT.format(quartiles[0.75]),
        "max": RATE_FORMAT.format(clean.max()),
    }


def _status_counts(measures: pd.DataFrame, leader_ids: Collection[str]) -> dict[str, int]:
    """Leaders with and without a possible-Hinglish cell. One flagged cell is enough to count as flagged."""
    flagged = measures[measures["leader_id"].isin(set(leader_ids))].groupby("leader_id")["hinglish_flag"].max()
    return {WITH_FLAG: int((flagged == 1).sum()), WITHOUT_FLAG: int((flagged == 0).sum())}


def hinglish_status_counts(measures: pd.DataFrame, leader_ids: Collection[str], disclosure_min: int) -> dict[str, str]:
    """The two status counts as shown text: small ones hidden, and a lone hidden one takes its partner with it."""
    return protect_cells(_status_counts(measures, leader_ids), disclosure_min)


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return lines + ["| " + " | ".join(row) + " |" for row in rows]


def _cell_counts_section(measures: pd.DataFrame, disclosure_min: int) -> list[str]:
    scored = int((measures["word_count"] > 0).sum())
    flagged = int((measures["hinglish_flag"] == 1).sum())
    rows = [
        ["cleaned cells", show_count(len(measures), disclosure_min)],
        ["cells with at least one word (scored)", show_count(scored, disclosure_min)],
        ["cells marked possible Hinglish", show_count(flagged, disclosure_min)],
    ]
    return ["## Cells", "", *_table(["", "count"], rows), ""]


def _summary_section(leaders: pd.DataFrame, disclosure_min: int) -> list[str]:
    header = ["measure", "cell set", "value", *SUMMARY_KEYS]
    rows: list[list[str]] = []
    for measure in MEASURES:
        for cell_set, _ in CELL_SETS:
            subset = leaders[(leaders["measure"] == measure) & (leaders["cell_set"] == cell_set)]
            for value_label, column in (("raw leader mean", "raw_mean"), ("shrunk leader mean", "shrunk_mean")):
                summary = summarise(subset[column], disclosure_min)
                rows.append([MEASURE_LABELS[measure], cell_set, value_label, *(summary[key] for key in SUMMARY_KEYS)])
    return ["## Leader-level rates per 100 words", "", *_table(header, rows), ""]


def _status_rows(measures: pd.DataFrame, ids: Collection[str], disclosure_min: int) -> list[list[str]]:
    counts = _status_counts(measures, ids)
    shown = protect_cells(counts, disclosure_min)
    total = sum(counts.values())
    return [
        [label, shown[label], "<5" if shown[label] == SMALL else show_share(counts[label], total, disclosure_min)]
        for label in (WITH_FLAG, WITHOUT_FLAG)
    ]


def _status_section(measures: pd.DataFrame, leaders: pd.DataFrame, disclosure_min: int) -> list[str]:
    ids = set(leaders[leaders["cell_set"] == ALL_CELLS]["leader_id"])
    note = (
        "A leader counts as having a flagged cell when at least one of their cells carries the possible-Hinglish "
        "mark. The mark comes from the language flag in post cleaning, whose precision check is still pending a human."
    )
    table = _table(["status", "leaders", "share of leaders"], _status_rows(measures, ids, disclosure_min))
    return ["## Leaders by possible-Hinglish status (all-cells set)", "", *table, "", note, ""]


def render_report(measures: pd.DataFrame, leaders: pd.DataFrame, min_posts: int, disclosure_min: int) -> str:
    """The tracked markdown report: banner first, then aggregates only."""
    intro = [
        f"> {BANNER}",
        "",
        "# Provisional leader-level measures",
        "",
        "Exploratory only. Nothing here is pre-registered and no gate is signed.",
        "",
        f"- Leaders are kept when they have at least {min_posts} scored cells (the minimum in configs/thresholds.yaml).",
        "- A cell with no words stays missing and is not scored.",
        "- Rates are per 100 words from the English-only word lists in the dictionary layer.",
        "- Shrunk means use the existing empirical Bayes shrinkage from cell to leader, run separately for each "
        "measure and each cell set.",
        f"- Counts under {disclosure_min} are shown as \"{SMALL}\", and a lone hidden count hides its next smallest too.",
        "",
    ]
    body = [
        *_cell_counts_section(measures, disclosure_min),
        *_summary_section(leaders, disclosure_min),
        *_status_section(measures, leaders, disclosure_min),
    ]
    return "\n".join(intro + body) + "\n"


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    measures_path: Path = DEFAULT_MEASURES_PATH,
    out_path: Path = DEFAULT_LEADER_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
) -> int:
    """Verify the raw manifest, build the leader file and the report; 0 on success, 1 on failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        settings = load_eda_settings(thresholds_path)
        measures = read_banner_csv(measures_path)
        leaders = build_leader_frame(measures, settings.min_posts)
        report = render_report(measures, leaders, settings.min_posts, settings.disclosure_min)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("provisional-leaders FAILED: %s", error)
        return 1
    write_banner_csv(leaders, out_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s (git-ignored) and %s (aggregates only)", out_path, report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
