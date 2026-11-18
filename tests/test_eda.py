"""Tests for src.eda: the runner that assembles the six EDA sections into reports/eda_limitations.md."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src import eda
from src.eda import build_report, run
from src.eda_common import EdaSettings
from src.eda_gaps import COMPANY_COLUMNS
from src.name_key import name_key
from src.verify_raw import ManifestMismatch

LOOSE = EdaSettings(min_posts=2, disclosure_min=1, model_min=1, size_bands=2)
NAMES = ("Zed Sentinel", "Yara Sentinel", "Xan Sentinel")
POST_TEXT = "SENTINEL-POST-TEXT-never-in-the-report"
LINK = "https://sentinel.example/in/zed"
EMAIL = "sentinel@example.org"
COMPANY_NAME = "Sentinel Holdings Ltd"
LEADER_IDS = ("LEADERID-SENTINEL-1", "LEADERID-SENTINEL-2", "LEADERID-SENTINEL-3")
SECTIONS = (
    "## 1. Coverage",
    "## 2. Gaps",
    "## 3. Balance",
    "## 4. Distribution of cells per leader",
    "## 5. Quality issues already found",
    "## 6. Possible selection bias",
)


def _posts() -> pd.DataFrame:
    """Zed: 3 raw cells; Yara: 2; Xan: 1. Every cell carries post text, a link and a profile url that must not leak."""
    owners = [NAMES[0]] * 3 + [NAMES[1]] * 2 + [NAMES[2]]
    return pd.DataFrame(
        {
            "leader": owners,
            "company": COMPANY_NAME,
            "title": "Chief Executive Officer",
            "ceo_type": ["Founder-CEO"] * 3 + ["Professional CEO"] * 3,
            "post_text": POST_TEXT,
            "link": LINK,
            "profile_url": LINK,
            "role_start_year": "",
            "post_date": "",
            "post_date_text": "",
            "text_kind": "raw",
        }
    )


def _proposal() -> pd.DataFrame:
    rows = [
        (LEADER_IDS[0], name_key(NAMES[0]), "clear", "w#1", "row:1", "s1", "row:1"),
        (LEADER_IDS[1], name_key(NAMES[1]), "clear", "w#2", "row:2", "", "row:2"),
        (LEADER_IDS[2], name_key(NAMES[2]), "clear", "w#3", "", "", "row:3"),
    ]
    return pd.DataFrame(rows, columns=["leader_id", "key", "status", "sheets", "roster", "summaries", "company"])


def _leaders() -> pd.DataFrame:
    rows = [
        (LEADER_IDS[0], "exact", "1", "1", "3"),
        (LEADER_IDS[1], "exact", "1", "0", "2"),
        (LEADER_IDS[2], "none", "0", "0", "1"),
    ]
    return pd.DataFrame(rows, columns=["leader_id", "company_match", "in_roster", "in_summaries", "n_raw_post_cells"])


def _matches() -> pd.DataFrame:
    rows = [
        ("sheets", "w#1", "company", "row:1", "exact", "1", "true"),
        ("sheets", "w#2", "company", "row:2", "exact", "1", "false"),
    ]
    columns = ["source_a", "ref_a", "source_b", "ref_b", "match_type", "n_candidates", "company_agrees"]
    return pd.DataFrame(rows, columns=columns)


def _clean() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "leader_id": [LEADER_IDS[0]] * 3,
            "post_text_clean": POST_TEXT,
            "language": ["English", "English", "Hinglish"],
        }
    )


def _company() -> pd.DataFrame:
    frame = pd.DataFrame("", index=range(3), columns=[*COMPANY_COLUMNS, "CompanyName", "Person_Name", "Email"])
    frame["CompanyName"] = COMPANY_NAME
    frame["Person_Name"] = list(NAMES)
    frame["Email"] = EMAIL
    frame["SectorPraticeAreaFeed"] = ["Tech > SaaS", "Finance > Banking", "Energy"]
    frame["NumberofEmployees"] = ["100", "300", "500"]
    frame["Gender"] = ["1", "0", "1"]
    return frame


def _report() -> str:
    return build_report(_posts(), _leaders(), _proposal(), _matches(), _clean(), _company(), LOOSE)


def _write_interim(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    tables = {
        "harmonised_posts": _posts(),
        "leader_id_proposal": _proposal(),
        "leader_table": _leaders(),
        "id_matches": _matches(),
        "posts_clean": _clean(),
        "company_data": _company(),
    }
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


def _thresholds(path: Path) -> Path:
    path.write_text(
        "min_posts_per_leader: 2\neda_disclosure_min_leaders: 1\neda_model_min_leaders: 1\neda_size_bands: 2\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    monkeypatch.setattr(eda, "verify_raw", lambda directory: "ok")
    interim = tmp_path / "interim"
    _write_interim(interim)
    return {
        "raw": tmp_path / "raw",
        "interim": interim,
        "report": tmp_path / "reports" / "eda_limitations.md",
        "thresholds": _thresholds(tmp_path / "thresholds.yaml"),
    }


def _run(workspace: dict[str, Path]) -> int:
    return run(workspace["raw"], workspace["interim"], workspace["report"], workspace["thresholds"])


# ---- the report -------------------------------------------------------------------------------


def test_the_report_has_the_six_sections_in_order() -> None:
    text = _report()

    positions = [text.index(section) for section in SECTIONS]

    assert positions == sorted(positions)


def test_the_report_states_its_limits_up_front() -> None:
    text = _report().lower()
    head = text[: text.index("## 1. coverage")]

    assert "counts and aggregates only" in head
    assert "stand in for posts until g1 is signed" in head
    assert "scraping_approved" in head
    assert "nothing is filled in or guessed" in head
    assert "image projected in public posts" in head
    assert "no gate is signed off" in head


def test_the_report_never_carries_names_text_links_ids_emails_or_refs() -> None:
    text = _report()
    forbidden_values = (*NAMES, *LEADER_IDS, POST_TEXT, LINK, EMAIL, COMPANY_NAME, name_key(NAMES[0]))

    for forbidden in (*forbidden_values, "row:", "w#", "http"):
        assert forbidden not in text


def test_the_report_ends_with_one_newline() -> None:
    text = _report()

    assert text.endswith("\n") and not text.endswith("\n\n")


# ---- run --------------------------------------------------------------------------------------


def test_run_writes_the_report_and_returns_zero(workspace: dict[str, Path]) -> None:
    assert _run(workspace) == 0

    text = workspace["report"].read_text(encoding="utf-8")
    assert all(section in text for section in SECTIONS)


def test_run_report_has_no_post_text_link_name_or_email(workspace: dict[str, Path]) -> None:
    _run(workspace)

    text = workspace["report"].read_text(encoding="utf-8")
    for forbidden in (*NAMES, *LEADER_IDS, POST_TEXT, LINK, EMAIL, COMPANY_NAME):
        assert forbidden not in text


def test_run_verifies_the_raw_manifest_first(workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Path] = []
    monkeypatch.setattr(eda, "verify_raw", lambda directory: seen.append(directory) or "ok")

    _run(workspace)

    assert seen == [workspace["raw"]]


def test_run_stops_and_writes_nothing_when_the_manifest_does_not_match(
    workspace: dict[str, Path], monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def refuse(directory: Path) -> str:
        raise ManifestMismatch("raw changed")

    monkeypatch.setattr(eda, "verify_raw", refuse)

    with caplog.at_level(logging.ERROR):
        code = _run(workspace)

    assert code == 1
    assert not workspace["report"].exists()
    assert "eda FAILED" in caplog.text


def test_run_fails_cleanly_when_an_interim_file_is_missing(workspace: dict[str, Path]) -> None:
    (workspace["interim"] / "id_matches.csv").unlink()

    assert _run(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_a_column_is_missing(workspace: dict[str, Path]) -> None:
    path = workspace["interim"] / "leader_table.csv"
    pd.read_csv(path, dtype=str).drop(columns=["company_match"]).to_csv(path, index=False)

    assert _run(workspace) == 1
    assert not workspace["report"].exists()


def test_run_fails_cleanly_when_a_threshold_key_is_missing(workspace: dict[str, Path]) -> None:
    workspace["thresholds"].write_text("min_posts_per_leader: 2\n", encoding="utf-8")

    assert _run(workspace) == 1


def test_run_does_not_change_the_interim_inputs(workspace: dict[str, Path]) -> None:
    before = {path.name: path.read_bytes() for path in workspace["interim"].glob("*.csv")}

    _run(workspace)

    assert {path.name: path.read_bytes() for path in workspace["interim"].glob("*.csv")} == before


def test_main_returns_the_exit_code_of_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(eda, "run", lambda: 7)

    assert eda.main() == 7
