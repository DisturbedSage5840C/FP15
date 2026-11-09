"""Tests for Step A (src.reaction_count_check): what a trailing number in raw post text looks like.

Synthetic data only. The report holds counts and rules, never post text, names or links. The sample
file holds leader ids, links and refs, and never a parsed number.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.reaction_count_check import (
    CONTROL,
    OWN_LINE,
    CheckSettings,
    count_trailing,
    ends_in_age_token,
    find_trailing_number,
    load_settings,
    run,
    select_sample,
    spreadsheet_safe,
)

POST_COLUMNS = ["leader", "company", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]
SAMPLE_COLUMNS = ["n", "group", "leader_id", "link", "ref", "last_line"]
NAMES = ("Ann Rao", "Bo Lee", "Cy Dunn", "Di Fox", "Ed Gray", "Fay Ito", "Gus Roe")


def _position(text: str) -> str:
    found = find_trailing_number(text)
    assert found is not None
    return found.position


# ---- finding the trailing number --------------------------------------------------------------


def test_returns_none_when_text_does_not_end_in_a_number() -> None:
    assert find_trailing_number("Great news today") is None
    assert find_trailing_number("") is None


def test_number_alone_on_its_own_line_is_own_line() -> None:
    assert _position("Great news today\n123") == "own_line"


def test_trailing_whitespace_after_the_number_is_ignored() -> None:
    assert _position("Great news\n45  \n") == "own_line"


def test_spaces_before_a_number_on_its_own_line_still_count_as_own_line() -> None:
    assert _position("Great news\n   45") == "own_line"


def test_a_text_that_is_only_a_number_is_own_line() -> None:
    assert _position("77") == "own_line"


def test_thousand_separators_and_k_suffix_stay_on_their_own_line() -> None:
    assert _position("Post\n1,234") == "own_line"
    assert _position("Post\n2.5K") == "own_line"


@pytest.mark.parametrize(
    ("text", "position"),
    [
        ("Joined in 2019", "after_space"),
        ("Covid19", "glued_to_word"),
        ("Loving the #Top10", "in_hashtag"),
        ("Summit #2024", "in_hashtag"),
        ("Score:7", "after_punct"),
    ],
)
def test_position_describes_what_sits_before_the_number(text: str, position: str) -> None:
    assert _position(text) == position


def test_a_decimal_is_read_whole_not_as_its_fraction() -> None:
    found = find_trailing_number("Margin\n2.5")

    assert found is not None
    assert found.position == "own_line"
    assert found.year_like is False


@pytest.mark.parametrize(("text", "year_like"), [
    ("Founded in 1999", True),
    ("Great news\n2024", True),
    ("Great news\n1899", False),
    ("Great news\n2036", False),
    ("Great news\n1,999", False),
    ("Great news\n2024K", False),
    ("Great news\n123", False),
])
def test_year_like_means_four_plain_digits_between_1900_and_2035(text: str, year_like: bool) -> None:
    found = find_trailing_number(text)

    assert found is not None
    assert found.year_like is year_like


@pytest.mark.parametrize(("text", "expected"), [
    ("Nice\n3mo\n45", True),
    ("Nice\n\n5yr\n\n45", True),
    ("Nice\n45", False),
    ("Nice 3mo 45", False),
])
def test_age_before_number_needs_a_relative_age_line_right_before_an_own_line_number(
    text: str, expected: bool
) -> None:
    found = find_trailing_number(text)

    assert found is not None
    assert found.age_before_number is expected


# ---- relative age tokens ----------------------------------------------------------------------


@pytest.mark.parametrize("text", ["Lovely day\n5yr", "Lovely day\n3mo", "Lovely day 2w", "Lovely day\n1d\n"])
def test_text_ending_in_a_relative_age_token_is_detected(text: str) -> None:
    assert ends_in_age_token(text) is True


@pytest.mark.parametrize("text", ["Lovely day", "Lovely day\n123", "A 5 year plan", "", "Version 2w3"])
def test_ordinary_text_does_not_look_like_it_ends_in_an_age_token(text: str) -> None:
    assert ends_in_age_token(text) is False


# ---- counting ---------------------------------------------------------------------------------


def test_count_trailing_tallies_each_pattern() -> None:
    texts = [
        "Hiring\n120",
        "Results\n2024",
        "Loving the #Top10",
        "Started in 2019",
        "Nice\n3mo\n45",
        "Day\n5yr",
        "No number",
        "Margin\n2.5K",
    ]

    counts = count_trailing(texts)

    assert counts.cells == 8
    assert counts.ends_in_number == 6
    assert counts.own_line == 4
    assert counts.in_hashtag == 1
    assert counts.after_space == 1
    assert counts.year_like == 2
    assert counts.year_like_own_line == 1
    assert counts.age_before_number == 1
    assert counts.ends_in_age_token == 1
    assert counts.with_suffix == 1


def test_count_trailing_on_nothing_is_all_zero() -> None:
    counts = count_trailing([])

    assert (counts.cells, counts.ends_in_number, counts.own_line) == (0, 0, 0)


# ---- sampling ---------------------------------------------------------------------------------


def _frame(n_own: int, n_control: int, overlap: int = 0) -> pd.DataFrame:
    """Leaders k00.. each with one own-line cell; control leaders follow (`overlap` shared)."""
    rows = [{"leader_key": f"k{i:02d}", "group": OWN_LINE, "ref": f"w#{i}:r1"} for i in range(n_own)]
    start = n_own - overlap
    rows += [{"leader_key": f"k{i:02d}", "group": CONTROL, "ref": f"w#{i}:r2"} for i in range(start, start + n_control)]
    return pd.DataFrame(rows)


def test_select_sample_takes_the_requested_number_from_each_group() -> None:
    chosen = select_sample(_frame(10, 6), n_own_line=4, n_control=2, seed=1)

    assert chosen["group"].value_counts().to_dict() == {OWN_LINE: 4, CONTROL: 2}


def test_select_sample_uses_each_leader_once_even_when_leaders_are_in_both_groups() -> None:
    chosen = select_sample(_frame(5, 5, overlap=5), n_own_line=5, n_control=0, seed=1)
    both = select_sample(_frame(6, 6, overlap=6), n_own_line=3, n_control=3, seed=1)

    assert chosen["leader_key"].is_unique
    assert both["leader_key"].is_unique
    assert len(both) == 6


def test_select_sample_is_deterministic_for_a_seed_and_changes_with_it() -> None:
    frame = _frame(20, 20)

    first = select_sample(frame, 5, 3, seed=1)["ref"].tolist()
    again = select_sample(frame, 5, 3, seed=1)["ref"].tolist()
    other = select_sample(frame, 5, 3, seed=2)["ref"].tolist()

    assert first == again
    assert first != other


def test_select_sample_does_not_depend_on_row_order() -> None:
    frame = _frame(20, 20)

    straight = select_sample(frame, 5, 3, seed=1)["ref"].tolist()
    shuffled = select_sample(frame.sample(frac=1, random_state=7), 5, 3, seed=1)["ref"].tolist()

    assert straight == shuffled


def test_select_sample_returns_what_exists_when_a_group_is_short() -> None:
    chosen = select_sample(_frame(3, 1), n_own_line=50, n_control=10, seed=1)

    assert chosen["group"].value_counts().to_dict() == {OWN_LINE: 3, CONTROL: 1}


# ---- settings ---------------------------------------------------------------------------------


def test_load_settings_reads_the_keys_from_the_yaml(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text(
        "reaction_check_number_on_own_line: 7\nreaction_check_control: 2\nreaction_check_seed: 3\nother: 1\n",
        encoding="utf-8",
    )

    assert load_settings(path) == CheckSettings(n_number_on_own_line=7, n_control=2, seed=3)


def test_load_settings_names_the_missing_key(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("reaction_check_control: 2\nreaction_check_seed: 3\n", encoding="utf-8")

    with pytest.raises(ValueError, match="reaction_check_number_on_own_line"):
        load_settings(path)


def test_real_thresholds_file_asks_for_forty_plus_ten_with_the_owner_seed() -> None:
    settings = load_settings(Path("configs/thresholds.yaml"))

    assert (settings.n_number_on_own_line, settings.n_control, settings.seed) == (40, 10, 20261107)


# ---- end to end -------------------------------------------------------------------------------


def _post(leader: str, row: int, text: str, link: str, kind: str = "raw") -> list[object]:
    return [leader, "Acme", "b/w1.xlsx", 1, row, text, link, kind]


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "dummy.bin").write_bytes(b"x")
    interim = tmp_path / "interim"
    interim.mkdir()
    rows = [
        _post("Ann Rao", 1, "Hiring engineers for our Bangalore office\n120", "https://www.linkedin.com/posts/p1"),
        _post("Ann Rao", 2, "No number here", "https://www.linkedin.com/posts/p2"),
        _post("Ann Rao", 3, "hiring engineers bangalore office", "", "cleaned"),
        _post("Bo Lee", 1, "Quarterly results were strong\n2024", "https://www.linkedin.com/posts/p3"),
        _post("Cy Dunn", 1, "Loving the #Top10", "https://www.linkedin.com/posts/p4"),
        _post("Di Fox", 1, "Great day\n5yr", "https://www.linkedin.com/posts/p5"),
        _post("Ed Gray", 1, "We started this in 2019", ""),
        _post("Fay Ito", 1, "Proud moment\n3mo\n45", "https://www.linkedin.com/posts/p6"),
        _post("Gus Roe", 1, "All good", "https://www.linkedin.com/posts/p7"),
        _post("Gus Roe", 2, "Unlinked note\n88", ""),
    ]
    pd.DataFrame(rows, columns=POST_COLUMNS).to_csv(interim / "harmonised_posts.csv", index=False)
    return {
        "raw": raw,
        "interim": interim,
        "report": tmp_path / "reports" / "reaction_count_check.md",
        "sample": tmp_path / "derived" / "reaction_sample.csv",
    }


def _go(workspace: dict[str, Path], own: int = 2, control: int = 1) -> int:
    return run(
        raw_dir=workspace["raw"],
        interim_dir=workspace["interim"],
        report_path=workspace["report"],
        sample_path=workspace["sample"],
        settings=CheckSettings(n_number_on_own_line=own, n_control=control, seed=1),
    )


def _report(workspace: dict[str, Path]) -> str:
    return workspace["report"].read_text(encoding="utf-8")


def _sample(workspace: dict[str, Path]) -> pd.DataFrame:
    return pd.read_csv(workspace["sample"], dtype=str, keep_default_na=False)


def test_run_writes_the_report_and_the_sample(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    assert _report(workspace).startswith("# Reaction-count check")
    assert workspace["sample"].exists()


def test_report_counts_match_the_synthetic_posts(workspace: dict[str, Path]) -> None:
    _go(workspace)

    text = _report(workspace)
    for line in (
        "| Raw cells | 9 |",
        "| End in a number | 6 |",
        "| Number alone on its own line | 4 |",
        "| Number inside a hashtag | 1 |",
        "| Year-like (4 digits, 1900 to 2035) | 2 |",
        "| Year-like and alone on its own line | 1 |",
        "| Relative-age line right before the number (like 5yr) | 1 |",
        "| Text ends in a relative-age token (like 5yr) | 1 |",
    ):
        assert line in text


def test_report_counts_cleaned_text_that_ends_in_a_number(workspace: dict[str, Path]) -> None:
    _go(workspace)

    assert "| Cleaned cells that end in a number | 0 of 1 |" in _report(workspace)


def test_report_gives_the_sampling_frame_and_the_rules(workspace: dict[str, Path]) -> None:
    _go(workspace)

    text = _report(workspace)
    assert "Seed: 1" in text
    assert "one cell per leader" in text.lower()
    assert "Eligible: has a LinkedIn post link" in text
    assert "| Own-line cells with a LinkedIn link | 3 |" in text


def test_report_has_no_names_no_post_text_and_no_links(workspace: dict[str, Path]) -> None:
    _go(workspace)

    text = _report(workspace)
    for name in NAMES:
        assert name not in text
    for fragment in ("Bangalore", "Quarterly", "engineers", "#Top10", "linkedin.com/", "http"):
        assert fragment not in text


def test_report_never_claims_the_number_is_a_reaction_count(workspace: dict[str, Path]) -> None:
    _go(workspace)

    assert "is a reaction count" not in _report(workspace).lower()


def test_sample_has_one_linked_cell_per_leader_in_the_requested_groups(workspace: dict[str, Path]) -> None:
    _go(workspace)

    sample = _sample(workspace)
    assert list(sample.columns) == SAMPLE_COLUMNS
    assert sample["group"].value_counts().to_dict() == {OWN_LINE: 2, CONTROL: 1}
    assert sample["leader_id"].str.fullmatch(r"L[0-9a-f]{10}").all()
    assert sample["leader_id"].is_unique
    assert sample["link"].str.startswith("https://www.linkedin.com/posts/").all()


def test_sample_own_line_cells_end_in_a_number_and_controls_do_not(workspace: dict[str, Path]) -> None:
    _go(workspace)

    sample = _sample(workspace)
    own = sample[sample["group"] == OWN_LINE]
    control = sample[sample["group"] == CONTROL]
    assert own["last_line"].str.fullmatch(r"[\d.,KkMm]+").all()
    assert not control["last_line"].str.fullmatch(r"[\d.,KkMm]+").any()


def _rewrite_posts(workspace: dict[str, Path], rows: list[list[object]]) -> None:
    pd.DataFrame(rows, columns=POST_COLUMNS).to_csv(workspace["interim"] / "harmonised_posts.csv", index=False)


def test_sample_neutralises_cells_a_spreadsheet_would_run_as_formulas(workspace: dict[str, Path]) -> None:
    good = "https://www.linkedin.com/posts/p1"
    _rewrite_posts(
        workspace,
        [
            _post("Ann Rao", 1, 'Intro\n=HYPERLINK("http://evil.test","x")', good),
            _post("Bo Lee", 1, "Intro\n@SUM(A1)", good),
            _post("Cy Dunn", 1, "Intro\n+cmd|calc", good),
            _post("Di Fox", 1, "Intro\n-note", good),
        ],
    )

    assert _go(workspace, own=0, control=4) == 0

    last_lines = _sample(workspace)["last_line"]
    assert len(last_lines) == 4
    assert last_lines.str.startswith("'").all()


def test_spreadsheet_safe_prefixes_every_formula_trigger_and_leaves_other_text() -> None:
    for risky in ("=1+1", "+1", "-1", "@a", "\tx", "\rx"):
        assert spreadsheet_safe(risky) == "'" + risky
    for fine in ("", "plain", "12,345", "a=b", "https://www.linkedin.com/posts/p1"):
        assert spreadsheet_safe(fine) == fine


def test_links_off_linkedin_or_without_http_scheme_are_not_sampled(workspace: dict[str, Path]) -> None:
    _rewrite_posts(
        workspace,
        [
            _post("Ann Rao", 1, "Intro\n10", "https://www.linkedin.com/posts/ok"),
            _post("Bo Lee", 1, "Intro\n10", "http://evil.test/p"),
            _post("Cy Dunn", 1, "Intro\n10", "javascript:alert(1)"),
            _post("Di Fox", 1, "Intro\n10", "https://notlinkedin.com/p"),
            _post("Ed Gray", 1, "Intro\n10", "https://linkedin.com.evil.test/p"),
        ],
    )

    assert _go(workspace, own=5, control=0) == 0

    assert _sample(workspace)["link"].to_list() == ["https://www.linkedin.com/posts/ok"]


def test_sample_has_no_column_holding_the_parsed_number(workspace: dict[str, Path]) -> None:
    _go(workspace)

    columns = set(_sample(workspace).columns)
    assert not columns & {"trailing_number", "number", "value", "reaction_count"}


def test_sample_carries_no_names(workspace: dict[str, Path]) -> None:
    _go(workspace)

    text = workspace["sample"].read_text(encoding="utf-8")
    for name in NAMES:
        assert name not in text


def test_sample_ref_points_back_to_the_harmonised_row(workspace: dict[str, Path]) -> None:
    _go(workspace)

    refs = _sample(workspace)["ref"]
    assert refs.str.fullmatch(r"b/w1\.xlsx#1:r\d+").all()


def test_same_seed_gives_the_same_sample_file(workspace: dict[str, Path]) -> None:
    _go(workspace)
    first = workspace["sample"].read_bytes()

    _go(workspace)

    assert workspace["sample"].read_bytes() == first


def test_harmonised_posts_are_not_modified(workspace: dict[str, Path]) -> None:
    path = workspace["interim"] / "harmonised_posts.csv"
    before = path.read_bytes()

    _go(workspace)

    assert path.read_bytes() == before


def test_run_fails_cleanly_when_the_harmonised_posts_are_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "harmonised_posts.csv").unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()
    assert not workspace["sample"].exists()


def test_run_fails_cleanly_when_a_needed_column_is_missing(workspace: dict[str, Path]) -> None:
    path = workspace["interim"] / "harmonised_posts.csv"
    pd.read_csv(path, dtype=str).drop(columns=["link"]).to_csv(path, index=False)

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_and_names_the_key_when_the_id_key_is_missing(
    workspace: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level("ERROR"):
        code = _go(workspace)

    assert code == 1
    assert "FP15_ID_KEY" in caplog.text
    assert not workspace["sample"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(workspace: dict[str, Path]) -> None:
    _go(workspace)
    (workspace["raw"] / "dummy.bin").write_bytes(b"changed")
    workspace["report"].unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()
