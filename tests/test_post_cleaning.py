"""Tests for src.post_cleaning: duplicates, interface lines, age, reaction count and language (synthetic text)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import post_cleaning
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.post_cleaning import (
    CLEAN_COLUMNS,
    CleaningSettings,
    drop_exact_duplicates,
    load_settings,
    parse_reaction,
    render_report,
    unclassified_patterns,
)
from src.post_fields import LanguageSettings
from src.verify_raw import ManifestMismatch

LANGUAGE = LanguageSettings(min_letters=5, minor_share=0.2)
SETTINGS = CleaningSettings(language=LANGUAGE, interface_min_leaders=2, reaction_check_confirmed=False)
CONFIRMED = CleaningSettings(language=LANGUAGE, interface_min_leaders=2, reaction_check_confirmed=True)

CELL = "Person A\n• 3rd+\nHeadline\n5yr •\nA real sentence in English about work.\n…more\nFollow\nLike\nComment\n42"
POST_COLUMNS = ["leader", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]


def _posts(*rows: tuple[str, str, str, str, str, str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=POST_COLUMNS)


def test_exact_duplicates_within_a_leader_are_dropped_and_counted() -> None:
    posts = _posts(
        ("Ann Rao", "w.xlsx", "1", "2", "Same text", "", "raw"),
        ("Ann Rao", "w.xlsx", "1", "3", "Same text", "", "raw"),
        ("Bo Lee", "w.xlsx", "2", "2", "Same text", "", "raw"),
    )

    kept, removed = drop_exact_duplicates(posts)

    assert removed == 1
    assert kept["source_row"].to_list() == ["2", "2"]


def test_the_same_text_for_two_leaders_is_not_a_duplicate() -> None:
    posts = _posts(
        ("Ann Rao", "w.xlsx", "1", "2", "Same text", "", "raw"),
        ("Bo Lee", "w.xlsx", "2", "2", "Same text", "", "raw"),
    )

    assert drop_exact_duplicates(posts)[1] == 0


def test_dropping_duplicates_does_not_change_the_input() -> None:
    posts = _posts(("A B", "w", "1", "2", "x", "", "raw"), ("A B", "w", "1", "3", "x", "", "raw"))

    drop_exact_duplicates(posts)

    assert len(posts) == 2


def test_reaction_is_unverified_until_the_human_check_is_confirmed() -> None:
    assert parse_reaction(CELL, SETTINGS) == ("unverified", "")


def test_a_number_alone_on_the_last_line_is_parsed_once_confirmed() -> None:
    assert parse_reaction(CELL, CONFIRMED) == ("parsed", "42")


def test_a_thousands_separator_is_read_as_one_number() -> None:
    assert parse_reaction("Body\n1,204", CONFIRMED) == ("parsed", "1204")


@pytest.mark.parametrize("text", ["Body\n2019", "Body\n3K", "Body text 42", "5yr\n12", "No number", ""])
def test_other_shapes_stay_unverified_even_when_confirmed(text: str) -> None:
    assert parse_reaction(text, CONFIRMED) == ("unverified", "")


def test_unclassified_patterns_exclude_lines_a_rule_already_covers() -> None:
    cells = [("a", "Follow\nOdd repeated line"), ("b", "Follow\nOdd repeated line")]

    result = unclassified_patterns(cells, min_leaders=2)

    assert [p.pattern for p in result] == ["Odd repeated line"]


def test_settings_load_from_the_thresholds_file(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text(
        "language_min_letters: 7\nlanguage_minor_share: 0.3\ninterface_min_leaders: 25\n"
        "reaction_check_confirmed: false\n",
        encoding="utf-8",
    )

    assert load_settings(path) == CleaningSettings(LanguageSettings(7, 0.3), 25, False)


def test_a_missing_settings_key_is_named(tmp_path: Path) -> None:
    path = tmp_path / "t.yaml"
    path.write_text("language_min_letters: 7\n", encoding="utf-8")

    with pytest.raises(ValueError, match="language_minor_share"):
        load_settings(path)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    interim = tmp_path / "interim"
    interim.mkdir()
    rows = [(f"Leader {i}", "w.xlsx", "1", str(i), CELL, "", "raw") for i in range(3)]
    rows.append(("Leader 0", "w.xlsx", "1", "9", CELL, "", "raw"))
    rows.append(("Leader 0", "w.xlsx", "1", "10", "Cleaned copy", "", "cleaned"))
    _posts(*rows).to_csv(interim / "harmonised_posts.csv", index=False)
    monkeypatch.setattr(post_cleaning, "verify_raw", lambda directory: "abc123")
    return {
        "raw": tmp_path / "raw",
        "interim": interim,
        "report": tmp_path / "reports" / "post_cleaning.md",
        "clean": interim / "posts_clean.csv",
        "candidates": tmp_path / "derived" / "interface_candidates.csv",
    }


def _go(workspace: dict[str, Path], settings: CleaningSettings = SETTINGS) -> int:
    return post_cleaning.run(
        workspace["raw"], workspace["interim"], workspace["report"], workspace["clean"], workspace["candidates"], settings
    )


def test_run_writes_the_clean_table_without_names_or_changes_to_the_raw_text(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    clean = pd.read_csv(workspace["clean"], dtype=str, keep_default_na=False)
    assert list(clean.columns) == CLEAN_COLUMNS
    assert len(clean) == 3
    assert clean["leader_id"].iloc[0] == leader_id_for(name_key("Leader 0"))
    assert "post_text" not in clean.columns
    assert "Follow" not in clean["post_text_clean"].iloc[0]
    assert clean["age_months"].iloc[0] == "60.0"
    assert set(clean["reaction_status"]) == {"unverified"}
    assert clean["language"].iloc[0] == "English"


def test_run_writes_a_counts_only_report(workspace: dict[str, Path]) -> None:
    assert _go(workspace) == 0

    report = workspace["report"].read_text(encoding="utf-8")
    assert "| Exact duplicate cells removed within a leader | 1 |" in report
    assert "connection_marker" in report
    assert "Leader" not in report and "real sentence" not in report


def test_run_writes_the_frequent_unclassified_lines_to_a_git_ignored_candidates_file(
    workspace: dict[str, Path],
) -> None:
    assert _go(workspace) == 0

    candidates = pd.read_csv(workspace["candidates"], dtype=str, keep_default_na=False)
    assert list(candidates.columns) == ["pattern", "lines", "leaders"]
    assert "Headline" in candidates["pattern"].to_list()


def test_render_report_states_that_the_segmenter_was_not_run_on_all_cells() -> None:
    text = render_report(
        cells=10, removed=0, rule_table={"follow": (4, 3)}, applied={"follow"}, unclassified=2,
        age_parsed=8, languages={"English": 9, "other": 1}, reaction_shape={"own_line": 6, "total": 7},
        reaction_confirmed=False, language_settings=LANGUAGE,
    )

    assert "not run on all cells" in text
    assert "unverified" in text
    assert "| follow | applied | 4 | 3 |" in text


def test_run_fails_cleanly_when_the_harmonised_posts_are_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "harmonised_posts.csv").unlink()

    assert _go(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_the_id_key_is_missing(
    workspace: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level("ERROR"):
        code = _go(workspace)

    assert code == 1
    assert "FP15_ID_KEY" in caplog.text
    assert not workspace["clean"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(post_cleaning, "verify_raw", _fail)

    assert _go(workspace) == 1
    assert not workspace["clean"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(post_cleaning, "run", lambda: 0)

    assert post_cleaning.main([]) == 0


def test_candidate_lines_that_a_spreadsheet_would_run_as_a_formula_are_defused() -> None:
    cells = pd.DataFrame(
        {"leader": ["Ann Rao", "Bo Lee"], "post_text": ["=1+1\nPlain", "=1+1\nPlain"]}
    )

    candidates = post_cleaning._candidates_frame(cells, min_leaders=2)

    assert "'=<n>+<n>" in candidates["pattern"].to_list()
    assert not any(pattern.startswith("=") for pattern in candidates["pattern"])
