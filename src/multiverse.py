"""Provisional Step 14D robustness multiverse (`make provisional-multiverse`).

This reruns the Step 14C *without-sector* model only.  It is exploratory,
does not replace the pre-registration, and reads no gold-set file.  The tracked
report contains aggregates only.
"""
from __future__ import annotations

import logging
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.ceo_gender_counts import DEFAULT_GENDER_CODING_PATH
from src.eda import INTERIM_FILES, NEVER_LOADED
from src.eda_balance import CEO_TYPE_FACTOR, SIZE_FACTOR, TITLE_FACTOR
from src.eda_common import DEFAULT_THRESHOLDS_PATH, SMALL, EdaSettings, load_eda_settings, show_count
from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import leader_id_for
from src.leader_master import MASTER_FILE
from src.provisional_common import BANNER, DEFAULT_MEASURES_PATH, DEFAULT_REPORT_DIR, read_banner_csv
from src.provisional_compare import (
    ESTIMATE_FORMAT,
    INTERVAL_NOTE,
    NOT_AVAILABLE,
    P_FORMAT,
    _check_some_ids_match,
    _number,
    _read_gender_coding,
    FACTORS_WITHOUT_SECTOR,
    show_fitted_counts,
)
from src.provisional_groups import FACTORS, leader_groups
from src.provisional_leaders import MEASURE_LABELS, MEASURES, _table
from src.provisional_models import FactorTest, factor_tests
from src.stats_tools import benjamini_hochberg
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = DEFAULT_REPORT_DIR / "provisional_multiverse.md"
ALL_CELLS = "all cells"
NO_HINGLISH = "without possible-Hinglish cells"
NO_REPOSTS = "without repost or embedded-post cells"
CELL_SETS = ((ALL_CELLS, None), (NO_HINGLISH, "hinglish_flag"), (NO_REPOSTS, "repost_flag"))
RAW = "raw rate"
LOG = "log(1 + rate)"
TRIMMED = "raw rate, top 1% leader means trimmed"
SCALES = (RAW, LOG, TRIMMED)
TESTED_FACTORS = (CEO_TYPE_FACTOR, TITLE_FACTOR, SIZE_FACTOR)
P_CUTOFF = 0.05


@dataclass(frozen=True)
class MultiverseSettings:
    min_posts_lower: int
    min_posts_higher: int
    trim_share: float
    log_offset: float


@dataclass(frozen=True)
class Variant:
    min_posts: int
    scale: str
    cells: str


@dataclass(frozen=True)
class MultiverseTest:
    variant: Variant
    measure: str
    factor: str
    leaders: int
    cells: int
    df: int
    p_value: float
    adjusted_p: float
    rejected: bool
    note: str
    contrast: str = ""
    estimate: float = float("nan")
    lower: float = float("nan")
    upper: float = float("nan")


def load_multiverse_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> MultiverseSettings:
    """Load every multiverse setting; there are deliberately no code defaults."""
    try:
        values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise ValueError(f"{path}: invalid YAML") from error
    section = values.get("multiverse")
    required = ("min_posts_lower", "min_posts_higher", "trim_share", "log_offset")
    if not isinstance(section, dict) or any(key not in section for key in required):
        raise ValueError(f"{path}: multiverse needs {', '.join(required)}")
    try:
        settings = MultiverseSettings(
            int(section["min_posts_lower"]), int(section["min_posts_higher"]),
            float(section["trim_share"]), float(section["log_offset"]),
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{path}: invalid multiverse setting") from error
    if settings.min_posts_lower <= 0 or settings.min_posts_higher <= 0:
        raise ValueError(f"{path}: multiverse post minimums must be positive")
    if not 0 < settings.trim_share < 1 or settings.log_offset <= 0:
        raise ValueError(f"{path}: multiverse trim_share must be between zero and one and log_offset positive")
    try:
        main_minimum = int(values["min_posts_per_leader"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{path}: missing or invalid min_posts_per_leader") from error
    if not settings.min_posts_lower < main_minimum < settings.min_posts_higher:
        raise ValueError(f"{path}: multiverse minimums must bracket min_posts_per_leader")
    return settings


def build_variants(main_min_posts: int, settings: MultiverseSettings) -> list[Variant]:
    minimums = (settings.min_posts_lower, main_min_posts, settings.min_posts_higher)
    if not settings.min_posts_lower < main_min_posts < settings.min_posts_higher:
        raise ValueError("multiverse post minimums must be lower and higher than min_posts_per_leader")
    return [Variant(minimum, scale, cells) for minimum in minimums for scale in SCALES for cells, _ in CELL_SETS]


def _selected_cells(measures: pd.DataFrame, cells: str) -> pd.DataFrame:
    flags = dict(CELL_SETS)
    if cells not in flags:
        raise ValueError(f"unknown multiverse cell set {cells}")
    flag = flags[cells]
    return measures.copy() if flag is None else measures[measures[flag] == 0].copy()


def _trim_top_leader_means(frame: pd.DataFrame, share: float) -> pd.DataFrame:
    means = frame.groupby("leader_id", as_index=False)["y"].mean().sort_values(["y", "leader_id"])
    n_drop = math.ceil(len(means) * share)
    dropped = set(means.tail(n_drop)["leader_id"])
    return frame[~frame["leader_id"].isin(dropped)].copy()


def variant_frame(
    measures: pd.DataFrame,
    labels: pd.DataFrame,
    measure: str,
    variant: Variant,
    settings: MultiverseSettings,
    eda_settings: EdaSettings,
) -> pd.DataFrame:
    """Post-level model frame for one variant, with selection before any transformation."""
    needed = {"leader_id", measure, "hinglish_flag", "repost_flag"}
    missing = needed - set(measures.columns)
    if missing:
        raise ValueError(f"provisional measures file is missing columns {sorted(missing)}")
    cells = _selected_cells(measures, variant.cells)
    counts = cells.groupby("leader_id").size()
    qualifying = set(counts[counts >= variant.min_posts].index)
    scored = cells[cells["leader_id"].isin(qualifying)].loc[:, ["leader_id", measure]].rename(columns={measure: "y"})
    scored = scored.dropna(subset=["y"])
    if scored.empty:
        return pd.DataFrame(columns=["leader_id", "y", *FACTORS])
    merged = scored.merge(labels, on="leader_id", how="left")
    merged = merged.dropna(subset=list(FACTORS))
    # Step 14C's without-sector model: no sector column is passed to the fit.
    merged = merged[merged[CEO_TYPE_FACTOR].isin(("Founder-CEO", "Professional CEO"))].copy()
    if variant.scale == LOG:
        merged["y"] = np.log(settings.log_offset + merged["y"].astype(float))
    elif variant.scale == TRIMMED:
        merged = _trim_top_leader_means(merged, settings.trim_share)
    elif variant.scale != RAW:
        raise ValueError(f"unknown multiverse scale {variant.scale}")
    return merged.reset_index(drop=True)


def run_multiverse(
    measures: pd.DataFrame, labels: pd.DataFrame, eda_settings: EdaSettings, settings: MultiverseSettings
) -> list[MultiverseTest]:
    """Fit the requested terms for both rates and all 27 combinations; BH is one pass over all tests."""
    pending: list[tuple[Variant, str, int, int, FactorTest]] = []
    for variant in build_variants(eda_settings.min_posts, settings):
        for measure in MEASURES:
            frame = variant_frame(measures, labels, measure, variant, settings, eda_settings)
            tests = factor_tests(frame, FACTORS_WITHOUT_SECTOR)
            wanted = {test.factor: test for test in tests}
            for factor in TESTED_FACTORS:
                pending.append((variant, measure, int(frame["leader_id"].nunique()), len(frame), wanted[factor]))
    outcome = benjamini_hochberg([test.p_value for *_, test in pending])
    return [
        MultiverseTest(
            variant, measure, test.factor, leaders, cells, test.df, test.p_value, adjusted, rejected, test.note,
            test.contrast, test.estimate, test.lower, test.upper,
        )
        for (variant, measure, leaders, cells, test), adjusted, rejected in zip(
            pending, outcome.adjusted, outcome.rejected, strict=True
        )
    ]


def _value(value: float, template: str) -> str:
    return NOT_AVAILABLE if math.isnan(value) else template.format(value)


def _interval(test: MultiverseTest) -> str:
    return NOT_AVAILABLE if math.isnan(test.lower) else f"{test.lower:+.2f} to {test.upper:+.2f}"


def _direction_line(results: list[MultiverseTest], measure: str) -> str:
    rows = [row for row in results if row.measure == measure and row.factor == CEO_TYPE_FACTOR and not math.isnan(row.estimate)]
    main = next((row for row in rows if row.variant == Variant(15, RAW, ALL_CELLS)), None)
    if main is None or main.estimate == 0:
        return f"- {MEASURE_LABELS[measure]}: n/a direction; {sum(row.p_value < P_CUTOFF for row in rows)} of {len(rows)} raw p below 0.05."
    same = sum(math.copysign(1, row.estimate) == math.copysign(1, main.estimate) for row in rows)
    raw_below = sum(row.p_value < P_CUTOFF for row in rows)
    return (
        f"- {MEASURE_LABELS[measure]}: {same} of {len(rows)} fitted variants have the same direction as the main "
        f"variant; {raw_below} of {len(rows)} raw p below 0.05."
    )


def _rows(results: list[MultiverseTest], factor: str, shown_leaders: list[str]) -> list[list[str]]:
    selected = [row for row in results if row.factor == factor]
    return [
        [
            str(row.variant.min_posts), row.variant.scale, row.variant.cells, MEASURE_LABELS[row.measure], leaders,
            row.contrast or NOT_AVAILABLE, _value(row.estimate, ESTIMATE_FORMAT), _interval(row),
            _value(row.p_value, P_FORMAT), _value(row.adjusted_p, P_FORMAT), row.note,
        ]
        for row, leaders in zip(selected, shown_leaders, strict=True)
    ]


def render_report(results: list[MultiverseTest], eda_settings: EdaSettings, settings: MultiverseSettings) -> str:
    """Counts-only tracked report for the 27-variant robustness grid."""
    header = ["post minimum", "outcome scale", "cells", "measure", "leaders fitted", "contrast", "estimate", "interval", "raw p", "BH-adjusted p", "note"]
    lines = [
        f"> {BANNER}", "", "# Provisional robustness multiverse", "",
        "Exploratory only. This multiverse does not replace the pre-registration and no gate is signed.", "",
        "- The without-sector Step 14C model is rerun for every combination of the configured post minimum, outcome "
        "scale and cell set. Founder-CEO and Professional CEO are the only ceo_type groups in every fit.",
        f'- Counts under {eda_settings.disclosure_min} show as "{SMALL}"; fitted-leader counts use the existing '
        "secondary-suppression rule.",
        "- Raw p is shown alongside one Benjamini-Hochberg pass across every displayed comparison. " + INTERVAL_NOTE,
        "",
        "## Founder-CEO versus Professional CEO", "",
        *_table(header, _rows(results, CEO_TYPE_FACTOR, show_fitted_counts(
            [row.leaders for row in results if row.factor == CEO_TYPE_FACTOR], [], eda_settings.disclosure_min
        ))), "",
        "## Title-family joint test", "",
        *_table(header, _rows(results, TITLE_FACTOR, show_fitted_counts(
            [row.leaders for row in results if row.factor == TITLE_FACTOR], [], eda_settings.disclosure_min
        ))), "",
        "## Firm-size joint test", "",
        *_table(header, _rows(results, SIZE_FACTOR, show_fitted_counts(
            [row.leaders for row in results if row.factor == SIZE_FACTOR], [], eda_settings.disclosure_min
        ))), "",
        "## Direction and raw-p count", "",
        _direction_line(results, MEASURES[0]), _direction_line(results, MEASURES[1]), "",
    ]
    return "\n".join(lines)


def _read_tables(interim_dir: Path) -> dict[str, pd.DataFrame]:
    files = {"posts": INTERIM_FILES["posts"], "master": MASTER_FILE}
    return {
        name: pd.read_csv(interim_dir / file, dtype=str, keep_default_na=False, usecols=lambda column: column not in NEVER_LOADED)
        for name, file in files.items()
    }


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    measures_path: Path = DEFAULT_MEASURES_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
    id_of: Callable[[str], str] = leader_id_for,
    gender_coding_path: Path = DEFAULT_GENDER_CODING_PATH,
) -> int:
    """Verify inputs then write the aggregates-only report, or leave no report on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        eda_settings = load_eda_settings(thresholds_path)
        settings = load_multiverse_settings(thresholds_path)
        measures = read_banner_csv(measures_path)
        tables = _read_tables(interim_dir)
        labels = leader_groups(tables["posts"], tables["master"], eda_settings.size_bands, id_of, _read_gender_coding(gender_coding_path))
        _check_some_ids_match(measures, labels)
        results = run_multiverse(measures, labels, eda_settings, settings)
        report = render_report(results, eda_settings, settings)
    except (ManifestMismatch, FileNotFoundError, ValueError, KeyError, MissingIdKey) as error:
        logger.error("provisional-multiverse FAILED: %s", error)
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info("wrote %s (aggregates only)", report_path)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
