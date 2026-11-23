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
import yaml

from src.ceo_gender_counts import DEFAULT_GENDER_CODING_PATH, FOUNDER, PROFESSIONAL, load_gender_coding
from src.eda import INTERIM_FILES, NEVER_LOADED
from src.eda_balance import (
    BLANK_VALUE,
    CEO_TYPE_FACTOR,
    GENDER_FACTOR,
    NOT_MATCHED,
    OTHER_GENDER_CODE,
    SECTOR_FACTOR,
    SIZE_FACTOR,
    UNREADABLE_SIZE,
)
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
from src.leader_master import MASTER_FILE
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
POST_TABLE = "posts"
CODED_VALUES = ("0", "1")
P_FORMAT = "{:.3g}"
SHARE_FORMAT = "{:.2f}"
ESTIMATE_FORMAT = "{:+.2f}"
NOT_AVAILABLE = "n/a"
SUMMARY_FIRST, SUMMARY_LAST = 3, 3 + len(SUMMARY_KEYS)  # slice of a summary row that holds the six statistics

WITHOUT_SECTOR = "without sector"
WITH_SECTOR = "with sector, small sectors pooled"
OTHER_SECTORS = "other sectors"
FACTORS_WITHOUT_SECTOR = tuple(factor for factor in FACTORS if factor != SECTOR_FACTOR)
FACTORS_BY_MODEL = {WITHOUT_SECTOR: FACTORS_WITHOUT_SECTOR, WITH_SECTOR: FACTORS}

KNOWN_CEO_TYPES = (FOUNDER, PROFESSIONAL)
MIN_HIDDEN_GROUPS = 2
UNKNOWN_GENDER = frozenset({BLANK_VALUE, NOT_MATCHED, OTHER_GENDER_CODE, NO_GROUP_LABEL})
UNKNOWN_SIZE = frozenset({BLANK_VALUE, UNREADABLE_SIZE, NOT_MATCHED, NO_GROUP_LABEL})
UNKNOWN_SECTOR = frozenset({BLANK_VALUE, NOT_MATCHED, NO_GROUP_LABEL})
CODED_PREFIX = "coded "  # a code the gender config has no word for: not a known gender

PREFERRED_PARTNERS = {GENDER_FACTOR: UNKNOWN_GENDER, SIZE_FACTOR: UNKNOWN_SIZE, SECTOR_FACTOR: UNKNOWN_SECTOR}


@dataclass(frozen=True)
class ModelRun:
    """One random-intercept model: a measure on a cell set, with the leader-level share of variance.

    `leaders` is the number actually fitted; `sample_leaders` is the analysis sample it is shown next to.
    """

    model: str
    measure: str
    cell_set: str
    leaders: int
    sample_leaders: int
    posts: int
    icc_empty: float
    icc_adjusted: float
    note: str


@dataclass(frozen=True)
class Comparison:
    """Joint Wald test of one factor in one model, with its Benjamini-Hochberg adjusted p.

    A two-group factor (df 1) also carries the signed difference with its interval; `contrast` names the direction.
    """

    model: str
    cell_set: str
    measure: str
    factor: str
    df: int
    p_value: float
    adjusted_p: float
    rejected: bool
    note: str
    contrast: str = ""
    estimate: float = float("nan")
    lower: float = float("nan")
    upper: float = float("nan")


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


def _groups_to_hide(counts: dict[str, int], minimum: int, preferred: frozenset[str]) -> set[str]:
    """Groups under the minimum, plus partners until the hidden groups together reach the minimum.

    A lone hidden group would be given away by subtraction from a printed total, so it always gets a partner. A partner
    is taken from the `preferred` groups (the unknown-value groups) first, then the smallest visible group.
    """
    hidden = {group for group, count in counts.items() if count < minimum}
    while hidden and (len(hidden) < MIN_HIDDEN_GROUPS or sum(counts[g] for g in hidden) < minimum):
        visible = [group for group in counts if group not in hidden]
        if not visible:
            break
        favoured = [group for group in visible if group in preferred] or visible
        hidden.add(min(favoured, key=lambda group: counts[group]))
    return hidden


def _hide_partners(
    rows: list[list[str]],
    joined: pd.DataFrame,
    factor: str,
    groups: list[str],
    settings: EdaSettings,
    preferred_partners: frozenset[str],
) -> list[list[str]]:
    """Per measure and cell set, hide the groups under the minimum and the partners that stop subtraction."""
    protected = [list(row) for row in rows]
    for measure in MEASURES:
        for cell_set, _ in CELL_SETS:
            subset = _cell_subset(joined, measure, cell_set)
            counts = {group: int(subset.loc[subset[factor] == group, "shrunk_mean"].notna().sum()) for group in groups}
            hidden = _groups_to_hide(counts, settings.disclosure_min, preferred_partners)
            for row in protected:
                if row[1] == MEASURE_LABELS[measure] and row[2] == cell_set and row[0] in hidden:
                    row[SUMMARY_FIRST:SUMMARY_LAST] = [SMALL] * len(SUMMARY_KEYS)
    return protected


def group_summary_rows(
    leaders: pd.DataFrame,
    labels: pd.DataFrame,
    factor: str,
    settings: EdaSettings,
    preferred_partners: frozenset[str] = frozenset(),
) -> list[list[str]]:
    """Rows [group, measure, cell set, leaders, min, q1, median, q3, max, modelling flag] for one factor.

    Groups under the disclosure minimum are hidden, and so is a partner group, so a hidden count cannot be worked out by
    subtraction from the printed totals. The partner is taken from `preferred_partners` first. The modelling flag is
    set from the true count, whether or not the number is shown.
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
    return _hide_partners(rows, joined, factor, groups, settings, preferred_partners)


def _pool_small_sectors(frame: pd.DataFrame, settings: EdaSettings) -> pd.DataFrame:
    """Sector groups below the too-small-to-model minimum are pooled into one group, not dropped."""
    sizes = frame.groupby(SECTOR_FACTOR)["leader_id"].nunique()
    small = set(sizes[sizes < settings.model_min].index)
    return frame.assign(**{SECTOR_FACTOR: frame[SECTOR_FACTOR].where(~frame[SECTOR_FACTOR].isin(small), OTHER_SECTORS)})


def _gender_known(values: pd.Series) -> pd.Series:
    return ~values.isin(UNKNOWN_GENDER) & ~values.str.startswith(CODED_PREFIX)


def _known_rows(frame: pd.DataFrame, with_sector: bool) -> pd.DataFrame:
    """Leaders with a known gender, a Founder-CEO or Professional CEO ceo_type and a size band (and sector if asked)."""
    keep = (
        _gender_known(frame[GENDER_FACTOR])
        & frame[CEO_TYPE_FACTOR].isin(KNOWN_CEO_TYPES)
        & ~frame[SIZE_FACTOR].isin(UNKNOWN_SIZE)
    )
    if with_sector:
        keep &= ~frame[SECTOR_FACTOR].isin(UNKNOWN_SECTOR)
    return frame[keep]


def model_frame(
    measures: pd.DataFrame,
    labels: pd.DataFrame,
    leaders: pd.DataFrame,
    measure: str,
    cell_set: str,
    settings: EdaSettings,
    with_sector: bool = False,
) -> pd.DataFrame:
    """Rows for one model: leader_id, the rate as y, and one column per factor. Missing rates are never filled.

    Every leader with the minimum posts and a known gender, ceo_type (Founder-CEO or Professional CEO only) and size band
    enters. With `with_sector`, leaders with no sector are left out (not filled) and sectors under the too-small-to-model
    minimum are pooled into one group.
    """
    drop_flagged = dict(CELL_SETS)[cell_set]
    qualifying = set(leaders.loc[(leaders["measure"] == measure) & (leaders["cell_set"] == ALL_CELLS), "leader_id"])
    cells = measures[measures["leader_id"].isin(qualifying)]
    if drop_flagged:
        cells = cells[cells["hinglish_flag"] == 0]
    scored = cells.loc[:, ["leader_id", measure]].rename(columns={measure: "y"}).dropna(subset=["y"])
    frame = _known_rows(scored.merge(_labelled(labels, qualifying), on="leader_id", how="left"), with_sector)
    return (_pool_small_sectors(frame, settings) if with_sector else frame).reset_index(drop=True)


def _qualifying_count(leaders: pd.DataFrame, measure: str) -> int:
    return int(leaders.loc[(leaders["measure"] == measure) & (leaders["cell_set"] == ALL_CELLS), "leader_id"].nunique())


def _fit_one(
    model: str, measure: str, cell_set: str, frame: pd.DataFrame, sample_leaders: int
) -> tuple[ModelRun, list[FactorTest]]:
    factors = FACTORS_BY_MODEL[model]
    empty, adjusted = variance_share(frame), variance_share(frame, factors)
    run_ = ModelRun(
        model, measure, cell_set, adjusted.leaders, sample_leaders, adjusted.posts, empty.icc, adjusted.icc, adjusted.note
    )
    return run_, factor_tests(frame, factors)


def run_models(
    measures: pd.DataFrame, labels: pd.DataFrame, leaders: pd.DataFrame, settings: EdaSettings
) -> tuple[list[ModelRun], list[Comparison]]:
    """Fit both models on each measure and cell set; Benjamini-Hochberg is applied once across every comparison."""
    models: list[ModelRun] = []
    pending: list[tuple[str, str, str, FactorTest]] = []
    for model in FACTORS_BY_MODEL:
        for measure in MEASURES:
            for cell_set, _ in CELL_SETS:
                frame = model_frame(measures, labels, leaders, measure, cell_set, settings, model == WITH_SECTOR)
                fitted, tests = _fit_one(model, measure, cell_set, frame, _qualifying_count(leaders, measure))
                models.append(fitted)
                pending.extend((model, cell_set, measure, test) for test in tests)
    outcome = benjamini_hochberg([test.p_value for *_, test in pending])
    comparisons = [
        Comparison(
            model, cell_set, measure, test.factor, test.df, test.p_value, adjusted_p, rejected, test.note,
            test.contrast, test.estimate, test.lower, test.upper,
        )
        for (model, cell_set, measure, test), adjusted_p, rejected in zip(
            pending, outcome.adjusted, outcome.rejected, strict=True
        )
    ]
    return models, comparisons


def show_fitted_counts(fitted: list[int], samples: list[int], minimum: int) -> list[str]:
    """Fitted-leader counts as printed, in the order given.

    A count under the minimum shows as "<5". A count within the minimum of an exact number already printed (an analysis
    sample or a larger fitted count) shows as a lower bound, so no gap under the minimum can be read off the table.
    Counts are settled from the largest down, so every exact number a smaller count is compared with is already fixed.
    """
    printed = {sample for sample in samples if sample >= minimum}
    shown = [SMALL] * len(fitted)
    for index in sorted(range(len(fitted)), key=lambda position: -fitted[position]):
        count = fitted[index]
        if count < minimum:
            continue
        near = [value for value in printed if 0 < value - count < minimum]
        if near:
            shown[index] = f"{max(near) - minimum + 1:,} or more"
        else:
            shown[index] = f"{count:,}"
            printed.add(count)
    return shown


def _number(value: float, template: str) -> str:
    return NOT_AVAILABLE if math.isnan(value) else template.format(value)


GENDER_NOTE = (
    "A group is hidden when it is under the disclosure minimum, and a group with at least the minimum is shown, so the "
    "woman group is shown when it has enough leaders. A group may still be hidden for another reason: when one group is "
    "under the minimum, the printed total would give its count away by subtraction, so a partner group is hidden with "
    "it. The partner is a group of unknown gender where there is one, otherwise the next smallest group, and the "
    "hidden groups together always reach the minimum."
)
MODEL_NOTE = (
    f'"leaders fitted" is the number of leaders in the model. A count under the minimum shows as "{SMALL}". A count within '
    "the minimum of another printed count (the analysis sample or another model's count) shows as a lower bound, so "
    "no small difference between two printed numbers is a hidden count."
)
INTERVAL_NOTE = (
    "The interval is a normal-approximation interval on the estimate; its level is one minus the Benjamini-Hochberg "
    "FDR level in configs/thresholds.yaml, so no new cut is introduced. Estimates are in pronoun uses per 100 words."
)


def _group_section(leaders: pd.DataFrame, labels: pd.DataFrame, settings: EdaSettings) -> list[str]:
    header = ["group", "measure", "cell set", *SUMMARY_KEYS, "modelling"]
    lines = ["## Leaders and shrunk rates per group (exploratory)", ""]
    for factor in FACTORS:
        rows = group_summary_rows(leaders, labels, factor, settings, PREFERRED_PARTNERS.get(factor, frozenset()))
        lines += [f"### {factor}", "", *_table(header, rows), ""]
        if factor == GENDER_FACTOR:
            lines += [GENDER_NOTE, ""]
    return lines


def _model_section(models: list[ModelRun], disclosure_min: int) -> list[str]:
    header = [
        "model",
        "measure",
        "cell set",
        "leaders fitted",
        "analysis sample",
        "cells",
        "leader-level share, no factors",
        "leader-level share, with factors",
        "note",
    ]
    fitted = show_fitted_counts([m.leaders for m in models], [m.sample_leaders for m in models], disclosure_min)
    rows = [
        [
            m.model,
            MEASURE_LABELS[m.measure],
            m.cell_set,
            fitted_text,
            show_count(m.sample_leaders, disclosure_min),
            show_count(m.posts, disclosure_min),
            _number(m.icc_empty, SHARE_FORMAT),
            _number(m.icc_adjusted, SHARE_FORMAT),
            m.note,
        ]
        for m, fitted_text in zip(models, fitted, strict=True)
    ]
    return ["## Random-intercept models (exploratory)", "", MODEL_NOTE, "", *_table(header, rows), ""]


def _interval(comparison: Comparison) -> str:
    if math.isnan(comparison.lower):
        return NOT_AVAILABLE
    return f"{comparison.lower:+.2f} to {comparison.upper:+.2f}"


def _comparison_row(c: Comparison) -> list[str]:
    return [
        c.model,
        MEASURE_LABELS[c.measure],
        c.cell_set,
        c.factor,
        str(c.df),
        c.contrast or NOT_AVAILABLE,
        _number(c.estimate, ESTIMATE_FORMAT),
        _interval(c),
        _number(c.p_value, P_FORMAT),
        _number(c.adjusted_p, P_FORMAT),
        "yes" if c.rejected else "no",
        c.note,
    ]


COMPARISON_HEADER = [
    "model",
    "measure",
    "cell set",
    "factor",
    "df",
    "contrast",
    "estimate",
    "interval",
    "p",
    "BH-adjusted p",
    "within the FDR level",
    "note",
]


def _founder_section(comparisons: list[Comparison]) -> list[str]:
    rows = [_comparison_row(c) for c in comparisons if c.factor == CEO_TYPE_FACTOR]
    intro = (
        "Founder-CEO against Professional CEO only, so the test has 1 degree of freedom: leaders whose ceo_type is "
        "blank or conflicting are left out of the models. Each row is the Professional CEO group's rate minus the "
        "Founder-CEO group's rate, adjusted for the other factors in that model. " + INTERVAL_NOTE
    )
    return ["## Founder-CEO and Professional CEO (exploratory)", "", intro, "", *_table(COMPARISON_HEADER, rows), ""]


def _comparison_section(comparisons: list[Comparison]) -> list[str]:
    rows = [_comparison_row(c) for c in comparisons]
    return ["## Joint tests per factor (exploratory)", "", *_table(COMPARISON_HEADER, rows), ""]


def _intro(settings: EdaSettings) -> list[str]:
    return [
        f"> {BANNER}",
        "",
        "# Provisional group comparisons",
        "",
        "Every result below is exploratory. Nothing is pre-registered, no gate is signed, and a p-value says nothing "
        "about causes.",
        "",
        "- Gender, sector and firm size come from the leader master (data/interim/leader_master.csv). ceo_type and "
        "title family come from the post sheets, because the master carries neither. Gender words come from "
        "configs/gender_coding.yaml; a blank stays missing and nothing is inferred from a name. Leaders with no usable "
        "company match are labelled as such.",
        f'- A count under {settings.disclosure_min} shows as "{SMALL}". A hidden group is paired with a partner group '
        "that is hidden too (an unknown-value group where there is one), so no hidden count can be worked out by "
        f'subtraction. Groups with fewer than {settings.model_min} leaders are marked "{TOO_SMALL_TO_MODEL}".',
        "- Models: one random intercept per leader, fitted by REML. The first model has ceo_type, title family, gender "
        "and firm size band, and takes every leader in the analysis sample with a known gender, a Founder-CEO or "
        "Professional CEO ceo_type and a size band. The second adds sector for the leaders whose sector is known, with "
        f'sectors under {settings.model_min} leaders pooled into one "{OTHER_SECTORS}" group instead of dropped. '
        "The leader-level share of variance is leader variance over leader plus cell variance. Tests are joint Wald "
        "tests per factor from one fit.",
        "- Benjamini-Hochberg is applied once across every comparison in the last table: both models, both measures "
        "and both cell sets together.",
        "- A factor column that repeats an earlier factor is dropped, and the lost degrees of freedom are in the note.",
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
        *_founder_section(comparisons),
        *_comparison_section(comparisons),
    ]
    return "\n".join([*_intro(settings), *body]) + "\n"


def _read_tables(interim_dir: Path) -> dict[str, pd.DataFrame]:
    """The posts and the leader master, as strings, without post text, links or profile urls."""
    files = {POST_TABLE: INTERIM_FILES[POST_TABLE], "master": MASTER_FILE}
    return {
        name: pd.read_csv(
            interim_dir / file,
            dtype=str,
            keep_default_na=False,
            usecols=lambda column: column not in NEVER_LOADED,
        )
        for name, file in files.items()
    }


def _check_some_ids_match(measures: pd.DataFrame, labels: pd.DataFrame) -> None:
    if not set(measures["leader_id"]) & set(labels["leader_id"]):
        raise ValueError("no leader id in the measures file matches a leader id built from the interim tables")


def _read_gender_coding(path: Path) -> dict[str, str]:
    """The confirmed words for 0 and 1; a missing, empty or incomplete file is an error, not a silent 'coded 1'."""
    try:
        coding = load_gender_coding(path)
    except yaml.YAMLError as error:
        raise ValueError(f"gender coding {path} is not valid YAML") from error
    missing = [code for code in CODED_VALUES if code not in coding]
    if missing:
        raise ValueError(f"gender coding {path} has no words for code(s) {', '.join(missing)}")
    return coding


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    measures_path: Path = DEFAULT_MEASURES_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH,
    id_of: Callable[[str], str] = leader_id_for,
    gender_coding_path: Path = DEFAULT_GENDER_CODING_PATH,
) -> int:
    """Verify the raw manifest, build the comparisons, write the report; 0 on success, 1 on failure (nothing written)."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        settings = load_eda_settings(thresholds_path)
        measures = read_banner_csv(measures_path)
        tables = _read_tables(interim_dir)
        labels = leader_groups(
            tables[POST_TABLE], tables["master"], settings.size_bands, id_of, _read_gender_coding(gender_coding_path)
        )
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
