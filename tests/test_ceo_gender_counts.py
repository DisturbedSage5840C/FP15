"""Tests for src.ceo_gender_counts: the ceo_type split per leader and the Gender counts, exactly as coded."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import ceo_gender_counts
from src.ceo_gender_counts import (
    FOUNDER,
    PROFESSIONAL,
    ceo_type_counts,
    gender_counts,
    render_report,
)
from src.verify_raw import ManifestMismatch

ODD_VALUE = "ZZ-odd-value-that-must-never-be-printed"


def _posts(*rows: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=["leader", "ceo_type"])


def _company(*genders: str) -> pd.DataFrame:
    frame = pd.DataFrame({"Gender": list(genders)})
    frame["Person_Name"] = [f"Person {i}" for i in range(len(genders))]
    return frame


# ---- ceo_type, per leader ---------------------------------------------------------------------


def test_leader_with_a_label_on_some_rows_and_blank_on_others_counts_once_as_labelled() -> None:
    posts = _posts(("Asha Rao", PROFESSIONAL), ("Asha Rao", ""), ("Asha Rao", ""))

    counts = ceo_type_counts(posts)

    assert (counts.leaders, counts.professional, counts.founder, counts.blank) == (1, 1, 0, 0)


def test_two_spellings_of_one_name_pool_into_one_leader() -> None:
    posts = _posts(("Asha Rao", FOUNDER), ("Rao, Asha", ""))

    counts = ceo_type_counts(posts)

    assert (counts.leaders, counts.founder, counts.blank) == (1, 1, 0)


def test_leader_with_no_label_on_any_row_is_blank() -> None:
    posts = _posts(("Ben Cole", ""), ("Ben Cole", "  "))

    counts = ceo_type_counts(posts)

    assert (counts.leaders, counts.blank) == (1, 1)


def test_leader_with_only_an_unrecognised_value_is_counted_apart_and_never_named() -> None:
    posts = _posts(("Cy Dee", ODD_VALUE), ("Cy Dee", ""))

    counts = ceo_type_counts(posts)

    assert (counts.leaders, counts.unrecognised_only, counts.blank) == (1, 1, 0)


def test_leader_with_both_labels_is_counted_as_conflicting_not_assigned() -> None:
    posts = _posts(("Di Eve", PROFESSIONAL), ("Di Eve", FOUNDER))

    counts = ceo_type_counts(posts)

    assert (counts.conflicting, counts.professional, counts.founder) == (1, 0, 0)


def test_leader_counts_add_up_to_all_leaders() -> None:
    posts = _posts(
        ("A One", PROFESSIONAL), ("B Two", FOUNDER), ("C Three", ""), ("D Four", ODD_VALUE),
        ("E Five", PROFESSIONAL), ("E Five", FOUNDER),
    )

    counts = ceo_type_counts(posts)

    assert counts.leaders == 5
    assert counts.professional + counts.founder + counts.blank + counts.unrecognised_only + counts.conflicting == 5


def test_cell_counts_and_rows_without_a_leader_name() -> None:
    posts = _posts(
        ("A One", PROFESSIONAL), ("A One", ""), ("B Two", FOUNDER), ("B Two", ODD_VALUE), ("", PROFESSIONAL),
    )

    counts = ceo_type_counts(posts)

    assert (counts.cells_professional, counts.cells_founder, counts.cells_blank, counts.cells_unrecognised) == (1, 1, 1, 1)
    assert counts.cells_without_leader == 1


def test_missing_column_raises_a_clear_error() -> None:
    with pytest.raises(ValueError, match="ceo_type"):
        ceo_type_counts(pd.DataFrame({"leader": ["A One"]}))


# ---- Gender, exactly as coded -----------------------------------------------------------------


def test_gender_counts_coded_one_coded_zero_and_blank() -> None:
    counts = gender_counts(_company("1", "1", "0", "", ".", "-", " "))

    assert (counts.rows, counts.coded_1, counts.coded_0, counts.blank, counts.other) == (7, 2, 1, 4, 0)


def test_gender_values_other_than_one_or_zero_are_counted_not_coerced() -> None:
    counts = gender_counts(_company("1", "1.0", "2", "0"))

    assert (counts.coded_1, counts.coded_0, counts.other) == (1, 1, 2)


def test_gender_missing_column_raises_a_clear_error() -> None:
    with pytest.raises(ValueError, match="Gender"):
        gender_counts(pd.DataFrame({"Person_Name": ["A One"]}))


# ---- report -----------------------------------------------------------------------------------


def _report() -> str:
    posts = _posts(("Asha Rao", PROFESSIONAL), ("Ben Cole", FOUNDER), ("Cy Dee", ODD_VALUE), ("Di Eve", ""))
    return render_report(ceo_type_counts(posts), gender_counts(_company("1", "1", "0", "")))


def test_report_holds_the_counts() -> None:
    text = _report()

    assert "Professional CEO" in text and "Founder-CEO" in text
    assert "| coded 1 | 2 |" in text
    assert "| coded 0 | 1 |" in text
    assert "| blank | 1 |" in text


def test_report_has_no_names_and_no_cell_values() -> None:
    text = _report()

    for forbidden in ("Asha", "Rao", "Cy Dee", ODD_VALUE, "Person 0"):
        assert forbidden not in text


def test_report_does_not_interpret_what_one_and_zero_mean() -> None:
    lowered = _report().lower()

    for word in ("female", "male", "woman", "man "):
        assert word not in lowered
    assert "not interpreted" in lowered


# ---- entry points -----------------------------------------------------------------------------


@pytest.fixture
def interim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "interim"
    folder.mkdir()
    _posts(("Asha Rao", PROFESSIONAL), ("Ben Cole", FOUNDER)).to_csv(folder / "harmonised_posts.csv", index=False)
    _company("1", "0", "").to_csv(folder / "company_data.csv", index=False)
    monkeypatch.setattr(ceo_gender_counts, "verify_raw", lambda raw_dir: "ok")
    return folder


def test_run_writes_a_counts_only_report(interim: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    report = tmp_path / "reports" / "ceo_type_gender_counts.md"

    with caplog.at_level(logging.INFO):
        code = ceo_gender_counts.run(tmp_path / "raw", interim, report)

    assert code == 0
    text = report.read_text(encoding="utf-8")
    assert "| coded 1 | 1 |" in text
    assert "Asha" not in text and "Person 0" not in text


def test_run_fails_when_the_manifest_does_not_match(
    interim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bad(raw_dir: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(ceo_gender_counts, "verify_raw", _bad)

    assert ceo_gender_counts.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1
    assert not (tmp_path / "r.md").exists()


def test_run_fails_when_an_input_file_is_missing(interim: Path, tmp_path: Path) -> None:
    (interim / "company_data.csv").unlink()

    assert ceo_gender_counts.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_run_fails_when_the_gender_column_is_missing(interim: Path, tmp_path: Path) -> None:
    pd.DataFrame({"Person_Name": ["A One"]}).to_csv(interim / "company_data.csv", index=False)

    assert ceo_gender_counts.run(tmp_path / "raw", interim, tmp_path / "r.md") == 1


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ceo_gender_counts, "run", lambda: 0)

    assert ceo_gender_counts.main() == 0
