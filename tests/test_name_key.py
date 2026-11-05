"""Tests for the sorted-token name key (src.name_key). Synthetic names only."""
import pytest

from src.name_key import name_key


def test_token_order_does_not_matter() -> None:
    assert name_key("Ann Lee") == name_key("Lee Ann")


def test_case_punctuation_and_spacing_are_ignored() -> None:
    assert name_key("  ann   LEE. ") == "ann lee"


def test_accents_are_folded() -> None:
    assert name_key("José Muñoz") == name_key("Jose Munoz")


def test_hyphen_splits_into_tokens() -> None:
    assert name_key("Jean-Luc Pic") == "jean luc pic"


@pytest.mark.parametrize("blank", [None, "", "   ", float("nan"), "...", "-"])
def test_blank_or_symbol_only_values_give_an_empty_key(blank: object) -> None:
    assert name_key(blank) == ""


def test_different_people_get_different_keys() -> None:
    assert name_key("Ann Lee") != name_key("Ann Leeds")


def test_non_string_cells_are_converted() -> None:
    assert name_key(12345) == "12345"
