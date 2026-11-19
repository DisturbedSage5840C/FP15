"""Tests for src.thresholds: one reader for configs/thresholds.yaml. Synthetic config files only."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.thresholds import DEFAULT_THRESHOLDS_PATH, load_threshold


def _config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "thresholds.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_present_key_is_returned_with_its_yaml_type(tmp_path: Path) -> None:
    path = _config(tmp_path, "alpha_min: 0.5\ncells: 12\n")

    assert load_threshold("alpha_min", path) == 0.5
    assert load_threshold("cells", path) == 12


def test_a_missing_key_is_named_in_the_error(tmp_path: Path) -> None:
    path = _config(tmp_path, "cells: 12\n")

    with pytest.raises(ValueError, match="missing key alpha_min"):
        load_threshold("alpha_min", path)


def test_an_empty_file_is_a_missing_key_not_a_crash(tmp_path: Path) -> None:
    path = _config(tmp_path, "")

    with pytest.raises(ValueError, match="missing key anything"):
        load_threshold("anything", path)


def test_the_default_path_is_the_project_config() -> None:
    assert DEFAULT_THRESHOLDS_PATH == Path("configs/thresholds.yaml")
