"""Tests for src.eda_distribution: cells per leader (cells stand in for posts until G1 is signed)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.eda_common import SMALL, EdaSettings
from src.eda_distribution import (
    TOP_SHARE,
    CellDistribution,
    DistributionCounts,
    cell_distribution,
    distribution_counts,
    render_distribution,
)
from src.name_key import name_key

LOOSE = EdaSettings(min_posts=3, disclosure_min=1, model_min=1, size_bands=2)
STRICT = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
SENTINELS = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel", "Wil Sentinel", "Vic Sentinel", "Uma Sentinel")
RAW_CELLS_PER_LEADER = (1, 2, 3, 4, 10)  # leaders A to E; F has a cleaned row only


def _posts() -> pd.DataFrame:
    rows = [(name, "raw") for name, cells in zip(SENTINELS, RAW_CELLS_PER_LEADER) for _ in range(cells)]
    rows.append((SENTINELS[5], "cleaned"))
    return pd.DataFrame(rows, columns=["leader", "text_kind"])


@pytest.fixture
def counts() -> DistributionCounts:
    return distribution_counts(_posts(), min_posts=3)


def _text(counts: DistributionCounts, settings: EdaSettings) -> str:
    return "\n".join(render_distribution(counts, settings))


def _line(text: str, label: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| {label} |"))


# ---- cell_distribution ------------------------------------------------------------------------


def test_the_summary_has_min_quartiles_max_and_the_top_decile_share() -> None:
    summary = cell_distribution("x", [1, 2, 3, 4, 10], TOP_SHARE)

    assert (summary.leaders, summary.total_cells) == (5, 20)
    assert (summary.minimum, summary.q1, summary.median, summary.q3, summary.maximum) == (1, 2.0, 3.0, 4.0, 10)
    assert (summary.top_leaders, summary.top_cells) == (1, 10)  # ceil(10% of 5 leaders) = 1


def test_the_top_group_rounds_up_so_it_always_holds_a_leader() -> None:
    assert cell_distribution("x", [7], TOP_SHARE).top_leaders == 1
    assert cell_distribution("x", list(range(1, 21)), TOP_SHARE).top_leaders == 2


def test_the_order_of_the_input_does_not_matter() -> None:
    assert cell_distribution("x", [10, 1, 4, 2, 3], TOP_SHARE) == cell_distribution("x", [1, 2, 3, 4, 10], TOP_SHARE)


def test_an_empty_group_is_summarised_without_a_division_error() -> None:
    summary = cell_distribution("x", [], TOP_SHARE)

    assert (summary.leaders, summary.total_cells, summary.top_leaders, summary.top_cells) == (0, 0, 0, 0)


@pytest.mark.parametrize("share", [0.0, -0.1, 1.5])
def test_a_top_share_outside_zero_to_one_is_refused(share: float) -> None:
    with pytest.raises(ValueError, match="top_share"):
        cell_distribution("x", [1, 2], share)


# ---- distribution_counts ----------------------------------------------------------------------


def test_leaders_are_summarised_over_raw_cells_only_with_and_without_the_cut(counts: DistributionCounts) -> None:
    everyone, at_cut = counts.distributions

    assert (everyone.leaders, everyone.total_cells, everyone.minimum, everyone.maximum) == (5, 20, 1, 10)
    assert (at_cut.leaders, at_cut.total_cells, at_cut.minimum, at_cut.maximum) == (3, 17, 3, 10)
    assert (at_cut.q1, at_cut.median, at_cut.q3) == (3.5, 4.0, 7.0)
    assert (at_cut.top_leaders, at_cut.top_cells) == (1, 10)


def test_the_cut_and_the_top_share_are_recorded(counts: DistributionCounts) -> None:
    assert (counts.min_posts, counts.top_share) == (3, TOP_SHARE)


def test_a_cut_nobody_reaches_gives_an_empty_group() -> None:
    result = distribution_counts(_posts(), min_posts=99)

    assert result.distributions[1].leaders == 0


@pytest.mark.parametrize("column", ["leader", "text_kind"])
def test_a_missing_posts_column_is_named(column: str) -> None:
    with pytest.raises(ValueError, match=column):
        distribution_counts(_posts().drop(columns=[column]), min_posts=3)


def test_the_counts_are_frozen(counts: DistributionCounts) -> None:
    with pytest.raises(AttributeError):
        counts.min_posts = 99  # type: ignore[misc]
    assert isinstance(counts.distributions[0], CellDistribution)


def test_the_input_is_not_changed() -> None:
    posts = _posts()
    before = posts.copy()

    distribution_counts(posts, min_posts=3)

    pd.testing.assert_frame_equal(posts, before)


# ---- rendering --------------------------------------------------------------------------------


def test_rendering_shows_every_statistic_for_a_group_large_enough_to_disclose(counts: DistributionCounts) -> None:
    line = _line(_text(counts, LOOSE), "1 or more raw cells")

    assert "| 5 | 20 | 1 | 2.0 | 3.0 | 4.0 | 10 | 1 | 50.0% |" in line


def test_rendering_hides_a_whole_row_when_the_group_is_below_the_disclosure_minimum(
    counts: DistributionCounts,
) -> None:
    text = _text(counts, STRICT)

    assert "| 3 or more raw cells | " + " | ".join([SMALL] * 9) + " |" in text
    assert SMALL not in _line(text, "1 or more raw cells")  # 5 leaders is enough


def test_an_empty_group_renders_as_hidden_not_as_zero_statistics() -> None:
    text = _text(distribution_counts(_posts(), min_posts=99), LOOSE)

    assert "| 99 or more raw cells | " + " | ".join([SMALL] * 9) + " |" in text


def test_rendering_names_the_section_the_quartile_method_and_the_caveat(counts: DistributionCounts) -> None:
    text = _text(counts, LOOSE).lower()

    assert "## 4. distribution of cells per leader" in text
    assert "top 10%" in text
    assert "stand in for posts until g1" in text
    assert "linear" in text  # how the quartiles are interpolated


def test_rendering_has_no_names_or_keys(counts: DistributionCounts) -> None:
    text = _text(counts, LOOSE)

    for forbidden in (*SENTINELS, name_key(SENTINELS[0])):
        assert forbidden not in text
