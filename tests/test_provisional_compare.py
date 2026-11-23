"""Provisional group comparisons (src/provisional_compare.py). Invented names, ids and numbers only: no real data.

Everything here is exploratory and about the image projected in public posts. A p-value says nothing about causes,
and nothing about personality.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.eda_balance import (
    BLANK_VALUE,
    CEO_TYPE_FACTOR,
    GENDER_FACTOR,
    NOT_MATCHED,
    OTHER_GENDER_CODE,
    SECTOR_FACTOR,
    SIZE_FACTOR,
    TITLE_FACTOR,
    UNREADABLE_SIZE,
)
from src.eda_common import TOO_SMALL_TO_MODEL, load_eda_settings
from src.leader_master import MASTER_FILE
from src.name_key import name_key
from src.provisional_common import BANNER, write_banner_csv
from src.provisional_compare import (
    FACTORS_WITHOUT_SECTOR,
    NO_HINGLISH,
    OTHER_SECTORS,
    UNKNOWN_GENDER,
    WITH_SECTOR,
    WITHOUT_SECTOR,
    Comparison,
    group_summary_rows,
    model_frame,
    render_report,
    run,
    run_models,
    show_fitted_counts,
)
from src.provisional_groups import FACTORS
from src.provisional_leaders import ALL_CELLS, MEASURE_LABELS, build_leader_frame

SETTINGS = load_eda_settings()
LEADERS = 73
POSTS_EACH = 16
RARE_FROM = 70
SINGULAR, PLURAL = "singular_per_100", "plural_per_100"


def _id(index: int) -> str:
    return f"L{index:03d}"


def invented_labels() -> pd.DataFrame:
    """Sector groups of 20, 20, 20, 10 and 3 leaders; ceo_type alternates; gender, title and size are unrelated."""
    rows = []
    for i in range(LEADERS):
        rows.append(
            {
                "leader_id": _id(i),
                CEO_TYPE_FACTOR: "Founder-CEO" if i % 2 == 0 else "Professional CEO",
                TITLE_FACTOR: ("CEO", "Managing director", "Chair")[(i * 7 + i // 3) % 3],
                GENDER_FACTOR: "man" if (i // 2) % 2 == 0 else "woman",
                SECTOR_FACTOR: "Rare" if i >= RARE_FROM else f"Sector {i // 20}",
                SIZE_FACTOR: f"size band {(i // 5) % 3 + 1}",
            }
        )
    return pd.DataFrame(rows)


def invented_measures(seed: int = 5, flagged_leaders: int = 4) -> pd.DataFrame:
    """Even leaders (Founder-CEO) say 'I' about 3 more per 100 words than odd ones; the plural rate has no group shift."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(LEADERS):
        leader_shift = rng.normal(0, 1.0)
        for post in range(POSTS_EACH):
            rows.append(
                {
                    "leader_id": _id(i),
                    "post_id": f"p{len(rows):06d}",
                    "word_count": 60,
                    SINGULAR: 5.0 + (3.0 if i % 2 == 0 else 0.0) + leader_shift + rng.normal(0, 1.0),
                    PLURAL: 4.0 + rng.normal(0, 1.5),
                    "hinglish_flag": int(i < flagged_leaders and post < 4),
                }
            )
    return pd.DataFrame(rows)


def _leaders(measures: pd.DataFrame) -> pd.DataFrame:
    return build_leader_frame(measures, SETTINGS.min_posts)


def _rows_for(group: str, rows: list[list[str]]) -> list[list[str]]:
    return [row for row in rows if row[0] == group]


def test_summary_rows_hide_small_groups_and_their_next_smallest_partner() -> None:
    rows = group_summary_rows(_leaders(invented_measures()), invented_labels(), SECTOR_FACTOR, SETTINGS)

    for group in ("Rare", "Sector 3"):
        for row in _rows_for(group, rows):
            assert row[3:9] == ["<5"] * 6
    big = _rows_for("Sector 0", rows)[0]
    assert big[3] == "20"


def test_summary_rows_flag_groups_below_the_modelling_minimum_even_when_shown() -> None:
    rows = group_summary_rows(_leaders(invented_measures()), invented_labels(), SECTOR_FACTOR, SETTINGS)

    assert all(row[9] == TOO_SMALL_TO_MODEL for row in _rows_for("Sector 3", rows))
    assert all(row[9] == "" for row in _rows_for("Sector 0", rows))


def test_summary_rows_cover_both_measures_and_both_cell_sets_per_group() -> None:
    rows = group_summary_rows(_leaders(invented_measures()), invented_labels(), CEO_TYPE_FACTOR, SETTINGS)

    seen = {(row[1], row[2]) for row in _rows_for("Founder-CEO", rows)}
    assert seen == {(label, cell_set) for label in MEASURE_LABELS.values() for cell_set in (ALL_CELLS, NO_HINGLISH)}


def test_a_leader_with_no_label_row_gets_its_own_group_instead_of_vanishing() -> None:
    labels = invented_labels().iloc[:-5]

    rows = group_summary_rows(_leaders(invented_measures()), labels, CEO_TYPE_FACTOR, SETTINGS)

    assert any(row[0] == "no group label" for row in rows)


def _frame(
    measures: pd.DataFrame,
    labels: pd.DataFrame,
    cell_set: str = ALL_CELLS,
    with_sector: bool = False,
) -> pd.DataFrame:
    return model_frame(measures, labels, _leaders(measures), SINGULAR, cell_set, SETTINGS, with_sector=with_sector)


def test_model_frame_without_sector_keeps_every_qualifying_leader_and_drops_flagged_cells_only_when_asked() -> None:
    measures, labels = invented_measures(), invented_labels()

    all_cells = _frame(measures, labels)
    no_hinglish = _frame(measures, labels, NO_HINGLISH)

    assert all_cells["leader_id"].nunique() == LEADERS
    assert len(all_cells) == LEADERS * POSTS_EACH
    assert len(no_hinglish) == LEADERS * POSTS_EACH - 4 * 4
    assert no_hinglish["y"].notna().all()
    assert {"leader_id", "y", *FACTORS} <= set(all_cells.columns)


def test_model_frame_with_sector_pools_small_sectors_into_one_group_instead_of_dropping_them() -> None:
    measures, labels = invented_measures(), invented_labels()

    frame = _frame(measures, labels, with_sector=True)

    assert set(frame[SECTOR_FACTOR]) == {"Sector 0", "Sector 1", "Sector 2", OTHER_SECTORS}
    assert frame["leader_id"].nunique() == LEADERS
    pooled = frame.loc[frame[SECTOR_FACTOR] == OTHER_SECTORS, "leader_id"].nunique()
    assert pooled == 13


def test_a_sector_at_the_modelling_minimum_is_not_pooled() -> None:
    measures, labels = invented_measures(), invented_labels()

    sizes = _frame(measures, labels, with_sector=True).groupby(SECTOR_FACTOR)["leader_id"].nunique()

    assert sizes["Sector 0"] == SETTINGS.model_min
    assert sizes[OTHER_SECTORS] < SETTINGS.model_min


def _with_label(labels: pd.DataFrame, positions: range, factor: str, value: str) -> pd.DataFrame:
    changed = labels.copy()
    changed.loc[list(positions), factor] = value
    return changed


@pytest.mark.parametrize(
    ("factor", "value"),
    [
        (GENDER_FACTOR, BLANK_VALUE),
        (GENDER_FACTOR, NOT_MATCHED),
        (GENDER_FACTOR, OTHER_GENDER_CODE),
        (CEO_TYPE_FACTOR, BLANK_VALUE),
        (CEO_TYPE_FACTOR, "conflicting"),
        (SIZE_FACTOR, BLANK_VALUE),
        (SIZE_FACTOR, UNREADABLE_SIZE),
        (SIZE_FACTOR, NOT_MATCHED),
    ],
)
def test_a_leader_without_a_known_gender_ceo_type_or_size_band_is_left_out_not_filled(
    factor: str, value: str
) -> None:
    measures = invented_measures()
    labels = _with_label(invented_labels(), range(0, 6), factor, value)

    frame = _frame(measures, labels)

    assert frame["leader_id"].nunique() == LEADERS - 6
    assert not set(frame["leader_id"]) & {_id(i) for i in range(6)}


def test_a_leader_with_no_label_row_is_left_out_of_the_models() -> None:
    measures, labels = invented_measures(), invented_labels().iloc[:-5]

    frame = _frame(measures, labels)

    assert frame["leader_id"].nunique() == LEADERS - 5


@pytest.mark.parametrize("value", [BLANK_VALUE, NOT_MATCHED])
def test_a_leader_with_no_sector_is_left_out_of_the_with_sector_model_only(value: str) -> None:
    measures = invented_measures()
    labels = _with_label(invented_labels(), range(0, 6), SECTOR_FACTOR, value)

    without = _frame(measures, labels)
    with_sector = _frame(measures, labels, with_sector=True)

    assert without["leader_id"].nunique() == LEADERS
    assert with_sector["leader_id"].nunique() == LEADERS - 6
    assert value not in set(with_sector[SECTOR_FACTOR])


def test_model_frame_keeps_flagged_cells_in_the_all_cells_set() -> None:
    measures, labels = invented_measures(), invented_labels()

    frame = _frame(measures, labels)

    assert len(frame) == LEADERS * POSTS_EACH


def _comparisons() -> list[Comparison]:
    measures, labels = invented_measures(), invented_labels()
    return run_models(measures, labels, _leaders(measures), SETTINGS)[1]


def test_a_real_group_shift_is_found_and_noise_is_not_and_bh_never_lowers_a_p() -> None:
    comparisons = _comparisons()

    found = {(c.model, c.cell_set, c.measure, c.factor): c for c in comparisons}
    for model in (WITHOUT_SECTOR, WITH_SECTOR):
        shifted = found[(model, ALL_CELLS, SINGULAR, CEO_TYPE_FACTOR)]
        assert shifted.p_value < 0.01
        assert shifted.rejected
        assert found[(model, ALL_CELLS, PLURAL, CEO_TYPE_FACTOR)].p_value > 0.05
    assert all(c.adjusted_p >= c.p_value for c in comparisons if not math.isnan(c.p_value))


def test_bh_runs_once_across_both_models_every_measure_and_cell_set() -> None:
    comparisons = _comparisons()

    without = [c for c in comparisons if c.model == WITHOUT_SECTOR]
    with_sector = [c for c in comparisons if c.model == WITH_SECTOR]
    assert len(without) == 2 * 2 * len(FACTORS_WITHOUT_SECTOR)
    assert len(with_sector) == 2 * 2 * len(FACTORS)
    assert SECTOR_FACTOR not in {c.factor for c in without}
    assert len(comparisons) == len(without) + len(with_sector)


def test_founder_vs_professional_has_one_degree_of_freedom_and_a_signed_estimate_with_an_interval() -> None:
    comparisons = [c for c in _comparisons() if c.factor == CEO_TYPE_FACTOR]

    assert len(comparisons) == 2 * 2 * 2
    assert all(c.df == 1 for c in comparisons)
    assert {c.contrast for c in comparisons} == {"Professional CEO minus Founder-CEO"}
    singular = [c for c in comparisons if c.measure == SINGULAR]
    assert all(-4.0 < c.estimate < -2.0 and c.lower < c.estimate < c.upper for c in singular)
    plural = [c for c in comparisons if c.measure == PLURAL]
    assert all(c.lower < 0.0 < c.upper for c in plural)


def test_model_runs_report_both_models_with_leader_counts_next_to_the_analysis_sample() -> None:
    measures, labels = invented_measures(), invented_labels()

    models, _ = run_models(measures, labels, _leaders(measures), SETTINGS)

    assert len(models) == 2 * 2 * 2
    assert {m.model for m in models} == {WITHOUT_SECTOR, WITH_SECTOR}
    singular = next(m for m in models if m.measure == SINGULAR and m.cell_set == ALL_CELLS and m.model == WITHOUT_SECTOR)
    assert 0.2 < singular.icc_adjusted < 0.8
    assert singular.leaders == LEADERS
    assert singular.sample_leaders == LEADERS


def test_model_runs_count_the_leaders_actually_fitted_when_some_are_left_out() -> None:
    measures = invented_measures()
    labels = _with_label(invented_labels(), range(0, 6), SECTOR_FACTOR, BLANK_VALUE)

    models, _ = run_models(measures, labels, _leaders(measures), SETTINGS)

    by_model = {m.model: m for m in models if m.measure == SINGULAR and m.cell_set == ALL_CELLS}
    assert by_model[WITHOUT_SECTOR].leaders == LEADERS
    assert by_model[WITH_SECTOR].leaders == LEADERS - 6
    assert by_model[WITH_SECTOR].sample_leaders == LEADERS


# --- disclosure control for the model counts and the gender table --------------------------------------------------


@pytest.mark.parametrize(
    ("fitted", "sample", "expected"),
    [(60, 73, "60"), (73, 73, "73"), (70, 73, "69 or more"), (72, 73, "69 or more"), (2, 73, "<5")],
)
def test_a_model_count_never_lets_a_gap_under_the_minimum_be_read_off_the_sample(
    fitted: int, sample: int, expected: str
) -> None:
    assert show_fitted_counts([fitted], [sample], SETTINGS.disclosure_min) == [expected]


def test_two_model_counts_close_to_each_other_do_not_reveal_the_small_difference_between_them() -> None:
    shown = show_fitted_counts([380, 377], [400, 400], SETTINGS.disclosure_min)

    assert shown == ["380", "376 or more"]


def test_model_counts_keep_the_order_given_and_far_apart_counts_stay_exact() -> None:
    shown = show_fitted_counts([377, 380, 250], [400, 400, 400], SETTINGS.disclosure_min)

    assert shown == ["376 or more", "380", "250"]


def _gender_labels(man: int, woman: int, other: int, blank: int = 0) -> pd.DataFrame:
    labels = invented_labels()
    values = ["man"] * man + ["woman"] * woman + [OTHER_GENDER_CODE] * other + [BLANK_VALUE] * blank
    assert len(values) == LEADERS
    labels[GENDER_FACTOR] = values
    return labels


def _gender_rows(labels: pd.DataFrame) -> dict[str, list[str]]:
    rows = group_summary_rows(_leaders(invented_measures()), labels, GENDER_FACTOR, SETTINGS, preferred_partners=UNKNOWN_GENDER)
    return {row[0]: row for row in rows if row[1] == MEASURE_LABELS[SINGULAR] and row[2] == ALL_CELLS}


def test_the_partner_of_a_hidden_gender_group_is_an_unknown_group_so_the_woman_group_stays_shown() -> None:
    rows = _gender_rows(_gender_labels(45, 20, 3, blank=5))

    assert rows["man"][3] == "45"
    assert rows["woman"][3] == "20"
    assert rows[OTHER_GENDER_CODE][3:9] == ["<5"] * 6
    assert rows[BLANK_VALUE][3:9] == ["<5"] * 6


def test_the_hidden_gender_groups_never_leave_a_remainder_under_the_minimum_against_the_total() -> None:
    rows = _gender_rows(_gender_labels(45, 20, 3, blank=5))

    printed = sum(int(row[3]) for row in rows.values() if row[3] != "<5")
    remainder = LEADERS - printed
    assert remainder >= SETTINGS.disclosure_min


def test_with_no_unknown_group_to_pair_the_next_smallest_group_is_hidden_beside_a_lone_hidden_one() -> None:
    rows = _gender_rows(_gender_labels(50, 20, 3))

    assert rows["woman"][3:9] == ["<5"] * 6
    assert rows["man"][3] == "50"


def test_a_count_under_the_minimum_is_never_printed_for_any_group_in_the_gender_rows() -> None:
    rows = _gender_rows(_gender_labels(68, 2, 3))

    assert rows["woman"][3:9] == ["<5"] * 6
    assert rows[OTHER_GENDER_CODE][3:9] == ["<5"] * 6


def _report() -> str:
    measures, labels = invented_measures(), invented_labels()
    leaders = _leaders(measures)
    models, comparisons = run_models(measures, labels, leaders, SETTINGS)
    return render_report(leaders, labels, models, comparisons, SETTINGS)


def test_report_starts_with_the_banner_and_labels_every_result_exploratory() -> None:
    report = _report()

    assert report.splitlines()[0] == f"> {BANNER}"
    assert "exploratory" in report.lower()
    assert "Benjamini-Hochberg" in report
    assert TOO_SMALL_TO_MODEL in report


def test_report_names_both_models_and_shows_fitted_leaders_next_to_the_analysis_sample() -> None:
    report = _report()

    assert WITHOUT_SECTOR in report
    assert WITH_SECTOR in report
    assert "analysis sample" in report
    assert f"| {LEADERS} | {LEADERS} |" in report


def test_report_gives_the_founder_vs_professional_difference_with_its_interval_for_both_measures() -> None:
    report = _report()
    lines = [line for line in report.splitlines() if "Professional CEO minus Founder-CEO" in line]

    assert {MEASURE_LABELS[SINGULAR], MEASURE_LABELS[PLURAL]} <= {label for line in lines for label in MEASURE_LABELS.values() if label in line}
    assert any(re.search(r"[+-]\d+\.\d\d", line) for line in lines)
    assert "interval" in report.lower()


def test_report_explains_why_a_gender_group_may_still_be_hidden() -> None:
    report = _report()

    assert "may still be hidden" in report
    assert "Who the models leave out" not in report


def test_report_has_no_leader_id_and_no_personality_or_narcissism_wording() -> None:
    report = _report()
    body = report.replace(BANNER, "")

    assert "L000" not in report
    assert "p000" not in report
    assert "personality" not in body.lower()
    assert "narcissis" not in body.lower()
    assert "<5" in report


# --- run(): files in, one report out ---------------------------------------------------------------------------

NAMES = [f"Sentinel Person{i:02d}" for i in range(LEADERS)]


def fake_id(key: str) -> str:
    return "L" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


def _write_interim(interim: Path) -> None:
    interim.mkdir()
    labels = invented_labels()
    posts = pd.DataFrame(
        [
            {
                "leader": name,
                "text_kind": "raw",
                "title": "CEO",
                "ceo_type": labels.loc[i, CEO_TYPE_FACTOR],
            }
            for i, name in enumerate(NAMES)
        ]
    )
    posts.to_csv(interim / "harmonised_posts.csv", index=False)
    master = pd.DataFrame(
        {
            "leader_id": [fake_id(name_key(n)) for n in NAMES],
            "columns_scope": "person_and_firm",
            "Gender": ["1" if i % 2 == 0 else "0" for i in range(LEADERS)],
            "SectorPraticeAreaFeed": [f"Sector {i // 20}" for i in range(LEADERS)],
            "NumberofEmployees": [str(100 * (i + 1)) for i in range(LEADERS)],
        }
    )
    master.to_csv(interim / MASTER_FILE, index=False)


def _write_measures(path: Path) -> None:
    measures = invented_measures()
    measures["leader_id"] = [fake_id(name_key(NAMES[int(v[1:])])) for v in measures["leader_id"]]
    write_banner_csv(measures, path)


def _write_coding(tmp_path: Path, text: str = '"1": man\n"0": woman\n') -> Path:
    path = tmp_path / "gender_coding.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _empty_manifest_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "MANIFEST.sha256").write_text("", encoding="utf-8")
    return raw


def test_run_writes_a_report_with_no_name_in_it(tmp_path: Path) -> None:
    _write_interim(tmp_path / "interim")
    _write_measures(tmp_path / "measures.csv")
    report_path = tmp_path / "out" / "report.md"

    code = run(
        raw_dir=_empty_manifest_dir(tmp_path),
        interim_dir=tmp_path / "interim",
        measures_path=tmp_path / "measures.csv",
        report_path=report_path,
        id_of=fake_id,
        gender_coding_path=_write_coding(tmp_path),
    )

    text = report_path.read_text(encoding="utf-8")
    assert code == 0
    assert text.startswith(f"> {BANNER}")
    assert "Sentinel" not in text
    assert name_key(NAMES[0]) not in text
    assert "gender_coding.yaml" in text
    assert "exactly as coded" not in text
    assert "coded 1" not in text


def test_run_fails_clearly_when_the_leader_master_is_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_interim(tmp_path / "interim")
    (tmp_path / "interim" / MASTER_FILE).unlink()
    _write_measures(tmp_path / "measures.csv")

    code = run(
        raw_dir=_empty_manifest_dir(tmp_path),
        interim_dir=tmp_path / "interim",
        measures_path=tmp_path / "measures.csv",
        report_path=tmp_path / "report.md",
        id_of=fake_id,
        gender_coding_path=_write_coding(tmp_path),
    )

    assert code == 1
    assert not (tmp_path / "report.md").exists()
    assert "leader_master" in caplog.text


def test_run_fails_without_writing_when_no_leader_id_matches(tmp_path: Path) -> None:
    _write_interim(tmp_path / "interim")
    _write_measures(tmp_path / "measures.csv")
    report_path = tmp_path / "report.md"

    code = run(
        raw_dir=_empty_manifest_dir(tmp_path),
        interim_dir=tmp_path / "interim",
        measures_path=tmp_path / "measures.csv",
        report_path=report_path,
        id_of=lambda key: "X" + key,
    )

    assert code == 1
    assert not report_path.exists()


def test_run_fails_clearly_when_the_id_key_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    _write_interim(tmp_path / "interim")
    _write_measures(tmp_path / "measures.csv")

    code = run(
        raw_dir=_empty_manifest_dir(tmp_path),
        interim_dir=tmp_path / "interim",
        measures_path=tmp_path / "measures.csv",
        report_path=tmp_path / "report.md",
    )

    assert code == 1
    assert not (tmp_path / "report.md").exists()


@pytest.mark.parametrize(
    "coding_text",
    [None, "", '"1": man\n', "just: [unclosed\n"],
    ids=["file missing", "empty file", "no code for 0", "malformed yaml"],
)
def test_run_fails_without_writing_when_the_gender_coding_is_missing_incomplete_or_unreadable(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, coding_text: str | None
) -> None:
    _write_interim(tmp_path / "interim")
    _write_measures(tmp_path / "measures.csv")
    path = tmp_path / "absent.yaml" if coding_text is None else _write_coding(tmp_path, coding_text)

    code = run(
        raw_dir=_empty_manifest_dir(tmp_path),
        interim_dir=tmp_path / "interim",
        measures_path=tmp_path / "measures.csv",
        report_path=tmp_path / "report.md",
        id_of=fake_id,
        gender_coding_path=path,
    )

    assert code == 1
    assert not (tmp_path / "report.md").exists()
    assert "gender" in caplog.text.lower()
