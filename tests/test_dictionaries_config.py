"""configs/dictionaries.yaml: slots for external word lists. No list is downloaded or stored in the repo."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "dictionaries.yaml"
EXPECTED_FIELDS = {"name", "citation", "doi", "path", "licence_checked"}
EXPECTED_DOIS = {"10.1002/ejsp.2561", "10.1037/a0022530"}


@pytest.fixture(scope="module")
def entries() -> list[dict]:
    values = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return values["dictionaries"]


def test_lists_exactly_the_big_two_and_gaucher_slots(entries: list[dict]) -> None:
    assert {entry["doi"] for entry in entries} == EXPECTED_DOIS
    assert len(entries) == 2


def test_every_entry_has_the_agreed_fields_and_no_others(entries: list[dict]) -> None:
    assert all(set(entry) == EXPECTED_FIELDS for entry in entries)


def test_no_licence_is_marked_checked_until_a_human_checks_it(entries: list[dict]) -> None:
    assert all(entry["licence_checked"] is False for entry in entries)


def test_every_local_path_sits_under_data_external(entries: list[dict]) -> None:
    assert all(entry["path"].startswith("data/external/") and ".." not in entry["path"] for entry in entries)


def test_citations_carry_the_journal_volume_and_year(entries: list[dict]) -> None:
    by_doi = {entry["doi"]: entry["citation"] for entry in entries}

    big_two = by_doi["10.1002/ejsp.2561"]
    gaucher = by_doi["10.1037/a0022530"]

    assert all(part in big_two for part in ("2019", "European Journal of Social Psychology", "49(5)", "871"))
    assert all(part in gaucher for part in ("2011", "Journal of Personality and Social Psychology", "101(1)", "109"))


def test_the_external_folder_is_git_ignored_so_no_word_list_can_be_committed() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "data/external/any_list.txt"], cwd=ROOT, check=False
    )

    assert result.returncode == 0
