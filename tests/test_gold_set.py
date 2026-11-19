"""Tests for src.gold_set: stratified gold-set sampler and coder assignment. Synthetic tables only.

Nothing here touches real data. Leader ids are invented labels (L001...), not keyed hashes; gender is a bare 1/0 code
used exactly as the file would code it, with no meaning attached.
"""
from __future__ import annotations

import itertools
import shutil
import subprocess
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.gold_set import (
    GOLD_SHEET_COLUMNS,
    GoldSettings,
    assign_coders,
    assignment_balance,
    load_gold_settings,
    sample_gold_set,
    stratum_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FOUNDER = "Founder-CEO"
PROFESSIONAL = "Professional CEO"

BASE = GoldSettings(size=40, max_posts_per_leader=3, seed=11, coders=4, coders_per_post=2)


def _posts(leaders: Sequence[tuple[str, str, object, int]]) -> pd.DataFrame:
    """One row per post from (leader_id, ceo_type, gender_as_coded, post_count) specs."""
    rows = []
    for leader_id, ceo_type, gender, count in leaders:
        for _ in range(count):
            rows.append({"post_id": f"p{len(rows):05d}", "ceo_type": ceo_type, "gender_as_coded": gender, "leader_id": leader_id})
    return pd.DataFrame(rows, columns=["post_id", "ceo_type", "gender_as_coded", "leader_id"])


def _even_table(posts_per_leader: int = 5, leaders_per_stratum: int = 10) -> pd.DataFrame:
    specs = []
    for index, (ceo_type, gender) in enumerate(itertools.product([FOUNDER, PROFESSIONAL], [1, 0])):
        for leader in range(leaders_per_stratum):
            specs.append((f"L{index}{leader:02d}", ceo_type, gender, posts_per_leader))
    return _posts(specs)


def _by_leader(posts: pd.DataFrame, chosen: tuple[str, ...]) -> Counter:
    leader_of = dict(zip(posts["post_id"], posts["leader_id"], strict=True))
    return Counter(leader_of[post_id] for post_id in chosen)


# ---- sampler: size, seed, cap -----------------------------------------------------------------------------------


def test_the_sample_has_exactly_the_requested_size_with_unique_ids_from_the_table() -> None:
    posts = _even_table()

    chosen = sample_gold_set(posts, BASE)

    assert len(chosen) == BASE.size
    assert len(set(chosen)) == BASE.size
    assert set(chosen) <= set(posts["post_id"])


def test_the_same_seed_gives_the_same_sample_twice() -> None:
    posts = _even_table()

    assert sample_gold_set(posts, BASE) == sample_gold_set(posts, BASE)


def test_a_different_seed_gives_a_different_sample() -> None:
    posts = _even_table()

    assert sample_gold_set(posts, BASE) != sample_gold_set(posts, replace(BASE, seed=BASE.seed + 1))


def test_the_row_order_of_the_input_does_not_change_the_sample() -> None:
    posts = _even_table()
    shuffled = posts.sample(frac=1.0, random_state=3).reset_index(drop=True)

    assert sample_gold_set(posts, BASE) == sample_gold_set(shuffled, BASE)


def test_no_leader_is_above_the_cap_even_when_one_leader_has_most_of_the_posts() -> None:
    posts = pd.concat([_even_table(), _posts([("DOMINANT", FOUNDER, 1, 80)])], ignore_index=True)
    posts["post_id"] = [f"p{i:05d}" for i in range(len(posts))]
    settings = replace(BASE, max_posts_per_leader=2)

    chosen = sample_gold_set(posts, settings)

    assert max(_by_leader(posts, chosen).values()) <= 2


def test_a_leader_with_fewer_posts_than_the_cap_can_still_be_drawn_in_full() -> None:
    posts = _posts([("A", FOUNDER, 1, 1), ("B", FOUNDER, 1, 1), ("C", PROFESSIONAL, 0, 1)])
    settings = replace(BASE, size=3, max_posts_per_leader=5)

    assert sorted(sample_gold_set(posts, settings)) == sorted(posts["post_id"])


# ---- sampler: strata --------------------------------------------------------------------------------------------


def test_equal_strata_each_get_an_equal_share() -> None:
    posts = _even_table()

    report = stratum_report(posts, sample_gold_set(posts, BASE))

    assert report["drawn"].tolist() == [10, 10, 10, 10]


def test_unequal_strata_get_a_share_within_one_post_of_proportional() -> None:
    specs = (
        [(f"F1_{i}", FOUNDER, 1, 4) for i in range(12)]
        + [(f"F0_{i}", FOUNDER, 0, 4) for i in range(6)]
        + [(f"P1_{i}", PROFESSIONAL, 1, 4) for i in range(9)]
        + [(f"P0_{i}", PROFESSIONAL, 0, 4) for i in range(3)]
    )
    posts = _posts(specs)
    settings = replace(BASE, size=30, max_posts_per_leader=3)
    pool = {"F1": 36, "F0": 18, "P1": 27, "P0": 9}  # min(4 posts, cap 3) per leader
    total = sum(pool.values())

    report = stratum_report(posts, sample_gold_set(posts, settings))

    for row in report.itertuples():
        key = ("F" if row.ceo_type == FOUNDER else "P") + str(row.gender_as_coded)
        assert abs(row.drawn - settings.size * pool[key] / total) < 1


def test_a_tiny_stratum_that_draws_nothing_still_appears_in_the_report_with_zero() -> None:
    specs = [(f"L{i}", FOUNDER, 1, 3) for i in range(40)] + [("TINY", PROFESSIONAL, 0, 1)]
    posts = _posts(specs)
    settings = replace(BASE, size=20, max_posts_per_leader=3)

    report = stratum_report(posts, sample_gold_set(posts, settings))

    tiny = report[(report["ceo_type"] == PROFESSIONAL) & (report["gender_as_coded"] == "0")]
    assert tiny["available"].tolist() == [1]
    assert tiny["drawn"].tolist() == [0]


def test_missing_values_form_their_own_stratum_and_are_never_filled_in() -> None:
    specs = [(f"L{i}", FOUNDER, 1, 3) for i in range(10)] + [(f"M{i}", FOUNDER, float("nan"), 3) for i in range(10)]
    posts = _posts(specs)
    before = posts.copy(deep=True)

    report = stratum_report(posts, sample_gold_set(posts, replace(BASE, size=20)))

    assert "(missing)" in report["gender_as_coded"].tolist()
    assert report["drawn"].sum() == 20
    pd.testing.assert_frame_equal(posts, before)  # the input table is not modified


def test_gender_is_used_as_coded_so_a_value_outside_one_and_zero_is_its_own_stratum() -> None:
    specs = [(f"A{i}", FOUNDER, 1, 3) for i in range(5)] + [(f"B{i}", FOUNDER, 2, 3) for i in range(5)]
    posts = _posts(specs)

    report = stratum_report(posts, sample_gold_set(posts, replace(BASE, size=10)))

    assert sorted(report["gender_as_coded"].tolist()) == ["1", "2"]


# ---- sampler: refusals ------------------------------------------------------------------------------------------


def test_asking_for_more_posts_than_remain_after_the_cap_is_an_error_with_counts() -> None:
    posts = _posts([("A", FOUNDER, 1, 50), ("B", PROFESSIONAL, 0, 50)])
    settings = replace(BASE, size=10, max_posts_per_leader=3)

    with pytest.raises(ValueError, match=r"only 6 posts remain after the per-leader cap of 3; 10 are needed"):
        sample_gold_set(posts, settings)


def test_a_duplicate_post_id_is_refused_without_echoing_the_id() -> None:
    posts = _even_table()
    posts.loc[1, "post_id"] = posts.loc[0, "post_id"]

    with pytest.raises(ValueError, match="duplicate post_id") as raised:
        sample_gold_set(posts, BASE)
    assert str(posts.loc[0, "post_id"]) not in str(raised.value)


def test_a_missing_column_is_named() -> None:
    posts = _even_table().drop(columns=["leader_id"])

    with pytest.raises(ValueError, match="leader_id"):
        sample_gold_set(posts, BASE)


def test_a_post_with_no_leader_id_is_refused_because_the_cap_cannot_be_applied() -> None:
    posts = _even_table()
    posts.loc[0, "leader_id"] = None

    with pytest.raises(ValueError, match="1 post has no leader_id"):
        sample_gold_set(posts, BASE)


def test_a_leader_whose_rows_sit_in_two_strata_is_refused_because_the_cap_would_not_hold() -> None:
    posts = _even_table()
    posts.loc[0, "gender_as_coded"] = 2  # leader L000 now has rows in two strata

    with pytest.raises(ValueError, match="1 leader appears in more than one"):
        sample_gold_set(posts, BASE)


# ---- coder assignment -------------------------------------------------------------------------------------------


def _ids(count: int) -> tuple[str, ...]:
    return tuple(f"p{i:05d}" for i in range(count))


def test_every_post_goes_to_two_different_coders_never_the_same_coder_twice() -> None:
    assignments = assign_coders(_ids(300), BASE)

    by_post: dict[str, list[str]] = {}
    for row in assignments:
        by_post.setdefault(row.post_id, []).append(row.coder)
    assert len(by_post) == 300
    assert all(len(coders) == 2 and len(set(coders)) == 2 for coders in by_post.values())


def test_three_hundred_posts_give_each_coder_150_and_each_pair_50() -> None:
    coder_counts, pair_counts = assignment_balance(assign_coders(_ids(300), BASE))

    assert set(coder_counts.values()) == {150}
    assert len(pair_counts) == 6
    assert set(pair_counts.values()) == {50}


@pytest.mark.parametrize("count", [100, 101, 103, 7])
def test_a_count_that_does_not_divide_evenly_stays_within_one_post_per_coder_and_per_pair(count: int) -> None:
    coder_counts, pair_counts = assignment_balance(assign_coders(_ids(count), BASE))

    assert max(coder_counts.values()) - min(coder_counts.values()) <= 1
    assert max(pair_counts.values()) - min(pair_counts.values()) <= 1
    assert sum(coder_counts.values()) == 2 * count


def test_the_same_seed_gives_the_same_assignment_and_a_new_seed_a_different_one() -> None:
    first = assign_coders(_ids(60), BASE)

    assert first == assign_coders(_ids(60), BASE)
    assert first != assign_coders(_ids(60), replace(BASE, seed=BASE.seed + 1))


def test_the_input_order_of_the_ids_does_not_change_the_assignment() -> None:
    ids = _ids(60)

    assert assign_coders(ids, BASE) == assign_coders(tuple(reversed(ids)), BASE)


def test_coder_names_are_neutral_labels_not_people() -> None:
    coders = {row.coder for row in assign_coders(_ids(12), BASE)}

    assert coders == {"coder_1", "coder_2", "coder_3", "coder_4"}


def test_three_coders_per_post_is_supported_and_balanced() -> None:
    settings = replace(BASE, coders=4, coders_per_post=3)

    coder_counts, group_counts = assignment_balance(assign_coders(_ids(120), settings))

    assert set(coder_counts.values()) == {90}
    assert set(group_counts.values()) == {30}


def test_a_duplicate_post_id_in_the_assignment_input_is_refused() -> None:
    with pytest.raises(ValueError, match="duplicate post_id"):
        assign_coders(("p1", "p2", "p1"), BASE)


# ---- settings from the thresholds file --------------------------------------------------------------------------


def _config(tmp_path: Path, **overrides: object) -> Path:
    values: dict[str, object] = {
        "gold_set_size": 300,
        "gold_set_max_posts_per_leader": 3,
        "gold_set_seed": 7,
        "gold_set_coders": 4,
        "gold_set_coders_per_post": 2,
    }
    values.update(overrides)
    path = tmp_path / "thresholds.yaml"
    path.write_text(yaml.safe_dump(values), encoding="utf-8")
    return path


def test_settings_are_read_from_the_thresholds_file(tmp_path: Path) -> None:
    settings = load_gold_settings(_config(tmp_path))

    assert settings == GoldSettings(size=300, max_posts_per_leader=3, seed=7, coders=4, coders_per_post=2)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"gold_set_max_posts_per_leader": 0}, "gold_set_max_posts_per_leader"),
        ({"gold_set_size": 0}, "gold_set_size"),
        ({"gold_set_coders_per_post": 1}, "at least two"),
        ({"gold_set_coders_per_post": 5}, "more coders per post than coders"),
    ],
)
def test_impossible_settings_are_refused(tmp_path: Path, override: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_gold_settings(_config(tmp_path, **override))


def test_a_missing_setting_is_named(tmp_path: Path) -> None:
    path = _config(tmp_path)
    path.write_text("gold_set_size: 300\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing key gold_set_max_posts_per_leader"):
        load_gold_settings(path)


def test_the_real_thresholds_file_has_every_gold_set_key_and_marks_the_cap_as_a_proposal() -> None:
    path = REPO_ROOT / "configs" / "thresholds.yaml"

    settings = load_gold_settings(path)

    assert settings.size == 300 and settings.coders == 4 and settings.coders_per_post == 2
    assert settings.max_posts_per_leader >= 1
    text = path.read_text(encoding="utf-8")
    before_cap = text.split("gold_set_max_posts_per_leader:")[0].splitlines()[-3:]
    assert any("PROPOSAL" in line for line in before_cap), "the cap must be flagged as a proposal, not a decision"


# ---- coding sheet template and where the real sheet may go ------------------------------------------------------


def test_the_coding_sheet_template_is_a_header_only_file_with_the_agreed_columns() -> None:
    template = REPO_ROOT / "templates" / "gold_coding_sheet.csv"

    lines = template.read_text(encoding="utf-8").splitlines()

    assert lines == ["post_id,coder,label,second_label,is_reshare,note"]
    assert tuple(lines[0].split(",")) == GOLD_SHEET_COLUMNS


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_the_private_interim_folder_for_the_real_sheet_is_git_ignored() -> None:
    done = subprocess.run(
        ["git", "check-ignore", "-q", "data/interim/gold_coding_sheet.csv"], cwd=REPO_ROOT, capture_output=True, check=False
    )

    assert done.returncode == 0, "the real coding sheet (with post text) must be written to a git-ignored folder"


def test_the_sampler_module_never_reads_files_and_uses_no_global_random_state() -> None:
    source = (REPO_ROOT / "src" / "gold_set.py").read_text(encoding="utf-8")

    for forbidden in ("read_excel", "read_csv", "open(", "data/raw", "np.random.seed", "random.seed"):
        assert forbidden not in source, forbidden
