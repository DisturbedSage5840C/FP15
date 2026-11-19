"""Tests for src.segment_viewer: the private n -> name lookup and the viewer install. Synthetic data only."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src import segment_viewer
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.segment import CHECK_COLUMNS, check_frame
from src.segment_viewer import NAMES_COLUMNS, names_frame

POST_COLUMNS = ["leader", "company", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind"]
FAKE_PEOPLE = [("Alpha Testperson", "Fakefirm One"), ("Beta Sampleperson", "Fakefirm Two")]


def _posts() -> pd.DataFrame:
    rows = [
        ("Alpha Testperson", "", "wb.xlsx", "0", "2", "text a1", "", "raw"),
        ("Alpha Testperson", "Fakefirm One", "wb.xlsx", "0", "3", "text a2", "", "raw"),
        ("Beta Sampleperson", "Fakefirm Two", "wb.xlsx", "1", "2", "text b1", "", "raw"),
        ("Beta Sampleperson", "Fakefirm Two", "wb.xlsx", "1", "9", "cleaned b", "", "cleaned"),
    ]
    return pd.DataFrame(rows, columns=POST_COLUMNS)


def _sample(refs: list[str] | None = None) -> pd.DataFrame:
    chosen = pd.DataFrame(
        {
            "leader_key": [name_key("Alpha Testperson"), name_key("Beta Sampleperson")],
            "ref": refs or ["wb.xlsx#0:r2", "wb.xlsx#1:r2"],
            "text": ["text a1", "text b1"],
        }
    )
    return check_frame(chosen)


def test_the_lookup_has_exactly_n_name_and_company_columns() -> None:
    names = names_frame(_sample(), _posts())

    assert list(names.columns) == ["n", "leader_name", "company_name"] == list(NAMES_COLUMNS)


def test_the_lookup_gives_each_sample_row_its_leader_and_company_by_n() -> None:
    names = names_frame(_sample(), _posts())

    assert names["n"].tolist() == [1, 2]
    assert names["leader_name"].tolist() == [p[0] for p in FAKE_PEOPLE]
    assert names["company_name"].tolist() == [p[1] for p in FAKE_PEOPLE]


def test_a_blank_company_on_the_cell_falls_back_to_the_leader_s_first_non_blank_company() -> None:
    names = names_frame(_sample(), _posts())

    assert names.loc[0, "company_name"] == "Fakefirm One"


def test_the_lookup_carries_no_segmenter_count_or_leader_id_or_text() -> None:
    names = names_frame(_sample(), _posts())

    assert not (set(names.columns) & set(CHECK_COLUMNS)) - {"n"}
    assert not any(word in column for column in names.columns for word in ("count", "segment", "machine"))


def test_the_name_is_checked_against_the_sample_leader_id() -> None:
    sample = _sample()
    sample.loc[0, "leader_id"] = leader_id_for(name_key("Somebody Else"))

    with pytest.raises(ValueError, match="1 of 2") as error:
        names_frame(sample, _posts())

    assert "Testperson" not in str(error.value)
    assert "Fakefirm" not in str(error.value)


def test_a_sample_ref_missing_from_the_posts_is_an_error_that_names_no_one() -> None:
    sample = _sample(["wb.xlsx#0:r2", "wb.xlsx#7:r77"])

    with pytest.raises(ValueError, match="1 of 2") as error:
        names_frame(sample, _posts())

    assert "Sampleperson" not in str(error.value)


def test_a_ref_that_the_sample_defused_with_a_quote_is_still_found() -> None:
    posts = _posts()
    posts.loc[0, "workbook"] = "=weird.xlsx"
    sample = _sample(["=weird.xlsx#0:r2", "wb.xlsx#1:r2"])

    names = names_frame(sample, posts)

    assert names["leader_name"].tolist() == [p[0] for p in FAKE_PEOPLE]


# ---- run: files on disk -----------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    interim = tmp_path / "interim"
    interim.mkdir()
    _posts().to_csv(interim / "harmonised_posts.csv", index=False)
    derived = tmp_path / "derived"
    derived.mkdir()
    sample_path = derived / "segmentation_check_200.csv"
    _sample().to_csv(sample_path, index=False)
    monkeypatch.setattr(segment_viewer, "verify_raw", lambda directory: "abc123")
    return {
        "raw": tmp_path / "raw",
        "interim": interim,
        "sample": sample_path,
        "names": derived / "segmentation_check_200_names.csv",
        "viewer": derived / "segmentation_counter.html",
    }


def _run(space: dict[str, Path]) -> int:
    return segment_viewer.run(
        raw_dir=space["raw"],
        interim_dir=space["interim"],
        sample_path=space["sample"],
        names_path=space["names"],
        viewer_path=space["viewer"],
    )


def test_run_writes_the_names_file_and_the_viewer_and_leaves_the_sample_untouched(
    workspace: dict[str, Path],
) -> None:
    before = hashlib.sha256(workspace["sample"].read_bytes()).hexdigest()

    code = _run(workspace)

    assert code == 0
    assert pd.read_csv(workspace["names"], dtype=str).columns.tolist() == list(NAMES_COLUMNS)
    assert workspace["viewer"].read_bytes() == segment_viewer.TEMPLATE_PATH.read_bytes()
    assert hashlib.sha256(workspace["sample"].read_bytes()).hexdigest() == before


def test_run_fails_cleanly_when_the_sample_does_not_exist(workspace: dict[str, Path]) -> None:
    workspace["sample"].unlink()

    assert _run(workspace) == 1
    assert not workspace["names"].exists()


def test_run_fails_cleanly_and_writes_nothing_when_a_name_does_not_match_its_id(
    workspace: dict[str, Path],
) -> None:
    sample = pd.read_csv(workspace["sample"], dtype=str, keep_default_na=False)
    sample.loc[0, "leader_id"] = "0" * 16
    sample.to_csv(workspace["sample"], index=False)

    assert _run(workspace) == 1
    assert not workspace["names"].exists()
    assert not workspace["viewer"].exists()


def test_run_fails_cleanly_when_the_raw_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.verify_raw import ManifestMismatch

    def _fail(directory: Path) -> str:
        raise ManifestMismatch("changed")

    monkeypatch.setattr(segment_viewer, "verify_raw", _fail)

    assert _run(workspace) == 1
    assert not workspace["names"].exists()


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(segment_viewer, "run", lambda: 0)

    assert segment_viewer.main() == 0
