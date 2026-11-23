"""Provisional group comparisons (step 14, part 3): `make provisional-compare`.

PROVISIONAL. G1 is unsigned, so raw cells stand in for posts; English-only pronoun counts; no gold-set check;
exploratory, not pre-registered. Claims are about the image projected in public posts. A p-value here says nothing
about causes. The singular rate is one signal, not a narcissism score.

For each of the five factors in `src.provisional_groups` the report gives leader counts and shrunk-rate summaries per
group (counts under the disclosure minimum show as "<5"), then one random-intercept model per measure and cell set
(posts nested in leaders, all factors together) with the leader-level share of variance, and joint Wald tests per
factor adjusted with Benjamini-Hochberg across every comparison. Sector groups need at least the existing
"too small to model" number of leaders to enter a model; no new cut is introduced. Leaders enter the models when they
meet the minimum posts in the all-cells set; the Hinglish-free set only removes flagged cells.

Leader ids exist only in memory. The name key is turned into an id in memory, and the tracked report holds aggregates.
"""
from __future__ import annotations

import logging
import math
import sys
from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.eda import INTERIM_FILES, NEVER_LOADED
from src.eda_balance import SECTOR_FACTOR
from src.eda_common import (
    DEFAULT_THRESHOLDS_PATH,
    SMALL,
    TOO_SMALL_TO_MODEL,
    EdaSettings,
    load_eda_settings,
    protect_cells,
    show_count,
)
from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import leader_id_for
from src.provisional_common import BANNER, DEFAULT_MEASURES_PATH, DEFAULT_REPORT_DIR, read_banner_csv
from src.provisional_groups import FACTORS, leader_groups
from src.provisional_leaders import (
    ALL_CELLS,
    CELL_SETS,
    MEASURE_LABELS,
    MEASURES,
    NO_HINGLISH,
    SUMMARY_KEYS,
    _table,
    build_leader_frame,
    summarise,
)
from src.provisional_models import FactorTest, factor_tests, variance_share
from src.stats_tools import benjamini_hochberg
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

__all__ = ["ALL_CELLS", "NO_HINGLISH"]

DEFAULT_REPORT_PATH = DEFAULT_REPORT_DIR / "provisional_comparisons.md"
NO_GROUP_LABEL = "no group label"
USED_TABLES = ("posts", "proposal", "company")
P_FORMAT = "{:.3g}"
SHARE_FORMAT = "{:.2f}"
NOT_AVAILABLE = "n/a"
SUMMARY_FIRST, SUMMARY_LAST = 3, 3 + len(SUMMARY_KEYS)  # slice of a summary row that holds the six statistics


@dataclass(frozen=True)
class ModelRun:
    """One random-intercept model: a measure on a cell set, with the leader-level share of variance."""

    measure: str
    cell_set: str
    leaders: int
    posts: int
    icc_empty: float
    icc_adjusted: float
    note: str


@dataclass(frozen=True)
class Comparison:
    """Joint Wald test of one factor in one model, with its Benjamini-Hochberg adjusted p."""

    cell_set: str
    measure: str
    factor: str
    df: int
    p_value: float
    adjusted_p: float
    rejected: bool
    note: str


def _labelled(labels: pd.DataFrame, leader_ids: Collection[str]) -> pd.DataFrame:
    """Labels for the given leaders; a leader with no label row gets its own group instead of vanishing."""
    base = pd.DataFrame({"leader_id": sorted(leader_ids)})
    merged = base.merge(labels, on="leader_id", how="left")
    return merged.fillna(dict.fromkeys(FACTORS, NO_GROUP_LABEL))


def _cell_subset(joined: pd.DataFrame, measure: str, cell_set: str) -> pd.DataFrame:
    return joined[(joined["measure"] == measure) & (joined["cell_set"] == cell_set)]


def _summary_row(
    joined: pd.DataFrame, factor: str, group: str, measure: str, cell_set: str, settings: EdaSettings
) -> list[str]:
    subset = _cell_subset(joined, measure, cell_set)
    values = subset.loc[subset[factor] == group, "shrunk_mean"]
    # The models use every leader who qualifies in the all-cells set, so the flag counts those leaders, whatever the row.
    modelled = _cell_subset(joined, measure, ALL_CELLS)
    modelled_count = int((modelled[factor] == group).sum())
    flag = TOO_SMALL_TO_MODEL if modelled_count < settings.model_min else ""
    summary = summarise(values, settings.disclosure_min)
    return [group, MEASURE_LABELS[measure], cell_set, *(summary[key] for key in SUMMARY_KEYS), flag]


def _hide_partners(
    rows: list[list[str]], joined: pd.DataFrame, factor: str, groups: list[str], settings: EdaSettings
) -> list[list[str]]:
    """Where exactly one group is hidden in a measure and cell set, its next smallest group is hidden too."""
    protected = [list(row) for row in rows]
    for measure in MEASURES:
        for cell_set, _ in CELL_SETS:
            subset = _cell_subset(joined, measure, cell_set)
            counts = {group: int(subset.loc[subset[factor] == group, "shrunk_mean"].notna().sum()) for group in groups}
            shown = protect_cells(counts, settings.disclosure_min)
            for row in protected:
                if row[1] == MEASURE_LABELS[measure] and row[2] == cell_set and shown[row[0]] == SMALL:
                    row[SUMMARY_FIRST:SUMMARY_LAST] = [SMALL] * len(SUMMARY_KEYS)
    return protected


def group_summary_rows(
    leaders: pd.DataFrame, labels: pd.DataFrame, factor: str, settings: EdaSettings
) -> list[list[str]]:
    """Rows [group, measure, cell set, leaders, min, q1, median, q3, max, modelling flag] for one factor.

    Small groups are hidden, and a lone hidden group takes its next smallest with it. The modelling flag is set from the
    true count, whether or not the number is shown.
    """
    labelled = _labelled(labels, set(leaders["leader_id"]))
    joined = leaders.merge(labelled.loc[:, ["leader_id", factor]], on="leader_id")
    groups = sorted(joined[factor].unique())
    rows = [
        _summary_row(joined, factor, group, measure, cell_set, settings)
        for group in groups
        for measure in MEASURES
        for cell_set, _ in CELL_SETS
    ]
    return _hide_partners(rows, joined, factor, groups, settings)


def _large_sectors_only(frame: pd.DataFrame, settings: EdaSettings) -> pd.DataFrame:
    """Sector groups below the existing too-small-to-model minimum stay out of the models."""
    sizes = frame.groupby(SECTOR_FACTOR)["leader_id"].nunique()
    kept = set(sizes[sizes >= settings.model_min].index)
    return frame[frame[SECTOR_FACTOR].isin(kept)]


def model_frame(
    measures: pd.DataFrame,
    labels: pd.DataFrame,
    leaders: pd.DataFrame,
    measure: str,
    cell_set: str,
    settings: EdaSettings,
) -> pd.DataFrame:
    """Rows for one model: leader_id, the rate as y, and one column per factor. Missing rates are never filled."""
    drop_flagged = dict(CELL_SETS)[cell_set]
    qualifying = set(leaders.loc[(leaders["measure"] == measure) & (leaders["cell_set"] == ALL_CELLS), "leader_id"])
    cells = measures[measures["leader_id"].isin(qualifying)]
    if drop_flagged:
        cells = cells[cells["hinglish_flag"] == 0]
    scored = cells.loc[:, ["leader_id", measure]].rename(columns={measure: "y"}).dropna(subset=["y"])
    frame = scored.merge(_labelled(labels, qualifying), on="leader_id", how="left")
    return _large_sectors_only(frame, settings).reset_index(drop=True)


def run_models(
    measures: pd.DataFrame, labels: pd.DataFrame, leaders: pd.DataFrame, settings: EdaSettings
) -> tuple[list[ModelRun], list[Comparison]]:
    """Fit each measure on each cell set; Benjamini-Hochberg is applied once across every comparison."""
    models: list[ModelRun] = []
    pending: list[tuple[str, str, FactorTest]] = []
    for measure in MEASURES:
        for cell_set, _ in CELL_SETS:
            frame = model_frame(measures, labels, leaders, measure, cell_set, settings)
            empty = variance_share(frame)
            adjusted = variance_share(frame, FACTORS)
            models.append(
                ModelRun(measure, cell_set, adjusted.leaders, adjusted.posts, empty.icc, adjusted.icc, adjusted.note)
            )
            pending.extend((cell_set, measure, test) for test in factor_tests(frame, FACTORS))
    outcome = benjamini_hochberg([test.p_value for _, _, test in pending])
    comparisons = [
        Comparison(cell_set, measure, test.factor, test.df, test.p_value, adjusted_p, rejected, test.note)
        for (cell_set, measure, test), adjusted_p, rejected in zip(pending, outcome.adjusted, outcome.rejected, strict=True)
    ]
    return models, comparisons


def _number(value: float, template: str) -> str:
    return NOT_AVAILABLE if math.isnan(value) else template.format(value)


def _group_section(leaders: pd.DataFrame, labels: pd.DataFrame, settings: EdaSettings) -> list[str]:
    header = ["group", "measure", "cell set", *SUMMARY_KEYS, "modelling"]
    lines = ["## Leaders and shrunk rates per group (exploratory)", ""]
    for factor in FACTORS:
        rows = group_summary_rows(leaders, labels, factor, settings)
        lines += [f"### {factor}", "", *_table(header, rows), ""]
    return lines


def _model_section(models: list[ModelRun], disclosure_min: int) -> list[str]:
    header = [
        "measure",
        "cell set",
        "leaders",
        "cells",
        "leader-level share, no factors",
        "leader-level share, with factors",
        "note",
    ]
    rows = [
        [
            MEASURE_LABELS[m.measure],
            m.cell_set,
            show_count(m.leaders, disclosure_min),
            show_count(m.posts, disclosure_min),
            _number(m.icc_empty, SHARE_FORMAT),
            _number(m.icc_adjusted, SHARE_FORMAT),
            m.note,
        ]
        for m in models
    ]
    return ["## Random-intercept models (exploratory)", "", *_table(header, rows), ""]


def _comparison_section(comparisons: list[Comparison]) -> list[str]:
    header = ["measure", "cell set", "factor", "df", "p", "BH-adjusted p", "within the FDR level", "note"]
    rows = [
        [
            MEASURE_LABELS[c.measure],
            c.cell_set,
            c.factor,
            str(c.df),
            _number(c.p_value, P_FORMAT),
            _number(c.adjusted_p, P_FORMAT),
            "yes" if c.rejected else "no",
            c.note,
        ]
        for c in comparisons
    ]
    return ["## Joint tests per factor (exploratory)", "", *_table(header, rows), ""]


def _intro(settings: EdaSettings) -> list[str]:
    return [
        f"> {BANNER}",
        "",
        "# Provisional group comparisons",
        "",
        "Every result below is exploratory. Nothing is pre-registered, no gate is signed, and a p-value says nothing "
        "about causes.",
        "",
        "- Groups come from the same labels as the EDA balance counts. Gender is used exactly as coded (1 and 0), "
        "with no meaning attached.",
        f'- A count under {settings.disclosure_min} shows as "{SMALL}", and a lone hidden group hides its next smallest '
        f'too. Groups with fewer than {settings.model_min} leaders are marked "{TOO_SMALL_TO_MODEL}"; sector groups '
        "that small are left out of the models.",
        "- Models: one random intercept per leader, all five factors together, fitted by REML. The leader-level share of "
        "variance is leader variance over leader plus cell variance. Tests are joint Wald tests per factor from one fit.",
        "- Benjamini-Hochberg is applied once across every comparison in the last table, both measures and both cell "
        "sets together.",
        "- A factor column that repeats an earlier factor (for example leaders with no usable company match, which "
        "form the same set in gender, sector and size) is dropped, and the lost degrees of freedom are in the note.",
        "",
    ]


def render_report(
    leaders: pd.DataFrame,
    labels: pd.DataFrame,
    models: list[ModelRun],
    comparisons: list[Comparison],
    settings: EdaSettings,
) -> str:
    """The tracked markdown report: banner first, then aggregates only."""
    body = [
        *_group_section(leaders, labels, settings),
        *_model_section(models, settings.disclosure_min),
        *_comparison_section(comparisons),
    ]
    return "\n".join([*_intro(settings), *body]) + "\n"


def _read_tables(interim_dir: Path) -> dict[str, pd.DataFrame]:
    """The interim tables this stage needs, as strings, without post text, links or profile urls."""
    return {
        name: pd.read_csv(
            interim_dir / INTERIM_FILES[name],
            dtype=str,
            keep_default_na=False,
            usecols=lambda column: column not in NEVER_LOADED,
        )
        for name in USED_TABLES
    }


def _check_some_ids_match(measures: pd.DataFrame, labels: pd.DataFrame) -> None:
    if not set(measures["leader_id"]) & set(labels["leader_id"]):
        raise ValueError("no leader id in the measures file matches a leader id built from the interim tables")


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    measures_path: Path = DEFAULT_MEASURES_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
    id_of: Callable[[str], str] = leader_id_for,
) -> int:
    """Verify the raw manifest, build the comparisons, write the report; 0 on success, 1 on failure (nothing written)."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        settings = load_eda_settings(thresholds_path)
        measures = read_banner_csv(measures_path)
        tables = _read_tables(interim_dir)
        labels = leader_groups(tables["posts"], tables["proposal"], tables["company"], settings.size_bands, id_of)
        _check_some_ids_match(measures, labels)
        leaders = build_leader_frame(measures, settings.min_posts)
        models, comparisons = run_models(measures, labels, leaders, settings)
        report = render_report(leaders, labels, models, comparisons, settings)
    except (ManifestMismatch, FileNotFoundError, ValueError, KeyError, MissingIdKey) as error:
        logger.error("provisional-compare FAILED: %s", error)
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
