"""Tests for src.eda_common: the "<5" rule for small groups and the settings the EDA reads."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.eda_common import (
    SMALL,
    EdaSettings,
    count_rows,
    load_eda_settings,
    protect_cells,
    show_count,
    show_share,
)

SETTINGS = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)


# ---- show_count / show_share ------------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1, 4])
def test_counts_below_the_disclosure_minimum_show_as_small(value: int) -> None:
    assert show_count(value, 5) == SMALL == "<5"


def test_counts_at_or_above_the_minimum_are_shown_with_thousands_separators() -> None:
    assert show_count(5, 5) == "5"
    assert show_count(1234, 5) == "1,234"


def test_share_is_a_percentage_with_one_decimal() -> None:
    assert show_share(25, 200, 5) == "12.5%"


def test_share_is_hidden_when_the_part_is_small() -> None:
    assert show_share(3, 200, 5) == SMALL


def test_share_is_hidden_when_the_whole_is_small() -> None:
    assert show_share(4, 4, 5) == SMALL


def test_share_of_an_empty_whole_is_not_a_division_error() -> None:
    assert show_share(0, 0, 5) == SMALL


# ---- protect_cells ----------------------------------------------------------------------------


def test_cells_at_or_above_the_minimum_pass_through() -> None:
    assert protect_cells({"a": 10, "b": 20}, 5) == {"a": "10", "b": "20"}


def test_two_small_cells_are_both_hidden_and_nothing_else_changes() -> None:
    shown = protect_cells({"a": 2, "b": 3, "c": 50}, 5)

    assert shown == {"a": SMALL, "b": SMALL, "c": "50"}


def test_a_single_small_cell_hides_the_next_smallest_too_so_a_total_cannot_reveal_it() -> None:
    shown = protect_cells({"a": 2, "b": 30, "c": 50}, 5, total_shown=True)

    assert shown == {"a": SMALL, "b": SMALL, "c": "50"}


def test_a_single_small_cell_is_left_alone_when_no_total_is_shown() -> None:
    shown = protect_cells({"a": 2, "b": 30, "c": 50}, 5, total_shown=False)

    assert shown == {"a": SMALL, "b": "30", "c": "50"}


def test_a_single_small_cell_in_a_one_cell_table_does_not_fail() -> None:
    assert protect_cells({"a": 2}, 5, total_shown=True) == {"a": SMALL}


def test_the_input_mapping_is_not_changed() -> None:
    counts = {"a": 2, "b": 30}

    protect_cells(counts, 5)

    assert counts == {"a": 2, "b": 30}


# ---- count_rows -------------------------------------------------------------------------------


def test_rows_carry_the_label_the_protected_count_the_share_and_a_modelling_flag() -> None:
    rows = count_rows({"big": 100, "mid": 10, "tiny": 1, "tiny2": 2}, SETTINGS)
    by_label = {row[0]: row for row in rows}

    assert by_label["big"] == ("big", "100", "88.5%", "")
    assert by_label["mid"][3] == "too small to model"
    assert by_label["tiny"][1:3] == (SMALL, SMALL)
    assert by_label["tiny"][3] == "too small to model"


def test_rows_end_with_a_total_that_is_always_shown() -> None:
    rows = count_rows({"a": 100, "b": 1, "c": 2}, SETTINGS)

    assert rows[-1] == ("all", "103", "100.0%", "")


# ---- settings ---------------------------------------------------------------------------------


def _yaml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "thresholds.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_settings_are_read_from_the_thresholds_file(tmp_path: Path) -> None:
    path = _yaml(
        tmp_path,
        "min_posts_per_leader: 15\neda_disclosure_min_leaders: 5\neda_model_min_leaders: 20\neda_size_bands: 4\n",
    )

    assert load_eda_settings(path) == EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)


def test_a_missing_key_is_named_in_the_error(tmp_path: Path) -> None:
    path = _yaml(tmp_path, "min_posts_per_leader: 15\neda_disclosure_min_leaders: 5\n")

    with pytest.raises(ValueError, match="eda_model_min_leaders"):
        load_eda_settings(path)


def test_a_missing_size_band_key_is_named_in_the_error(tmp_path: Path) -> None:
    path = _yaml(
        tmp_path, "min_posts_per_leader: 15\neda_disclosure_min_leaders: 5\neda_model_min_leaders: 20\n"
    )

    with pytest.raises(ValueError, match="eda_size_bands"):
        load_eda_settings(path)


def test_the_repo_thresholds_file_has_the_eda_settings() -> None:
    settings = load_eda_settings()

    assert settings.min_posts == 15
    assert settings.disclosure_min == 5
    assert settings.size_bands == 4
