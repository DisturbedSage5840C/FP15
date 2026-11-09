"""Tests for src.dedup_rules: link types, trailing-line stripping and the conservative collapse rule (synthetic)."""
from __future__ import annotations

import pytest

from src.dedup_rules import collapse_group, collapses_into, link_type, relation, strip_trailing


@pytest.mark.parametrize(
    ("link", "expected"),
    [
        ("https://www.linkedin.com/posts/someone_abc-activity-123", "linkedin_post"),
        ("linkedin.com/feed/update/urn:li:activity:123", "linkedin_post"),
        ("https://in.linkedin.com/in/someone", "linkedin_profile_or_company"),
        ("https://www.linkedin.com/company/acme/", "linkedin_profile_or_company"),
        ("https://www.linkedin.com/groups/12", "linkedin_other_path"),
        ("https://example.org/a", "other_domain"),
        ("https://notlinkedin.com/posts/x", "other_domain"),
        ("", "no_link"),
        ("   ", "no_link"),
    ],
)
def test_link_type_uses_only_domain_and_path(link: str, expected: str) -> None:
    assert link_type(link) == expected


def test_strip_trailing_removes_bare_numbers_and_age_lines_only_at_the_end() -> None:
    assert strip_trailing("Body line\n12\n") == "Body line"
    assert strip_trailing("Body line\n1,204\n3K") == "Body line"
    assert strip_trailing("Body\n5mo •") == "Body"
    assert strip_trailing("5mo • stays at the top\nBody") == "5mo • stays at the top Body"
    assert strip_trailing("Body 42") == "Body 42"


@pytest.mark.parametrize(
    ("texts", "label"),
    [
        (["Body\n12", "Body\n15"], "trailing_only"),
        (["Start of post", "Start of post and more"], "prefix"),
        (["Name A\nHeadline\nBody", "Name B\nOther line\nBody"], "first_lines"),
        (["One thing", "Another thing"], "other"),
    ],
)
def test_relation_labels_how_texts_differ(texts: list[str], label: str) -> None:
    assert relation(texts) == label


def test_identical_text_collapses() -> None:
    assert collapses_into("Same", "Same", is_post_url=False)


def test_a_text_that_is_the_start_of_the_kept_text_collapses() -> None:
    assert collapses_into("Start of post and more", "Start of post", is_post_url=False)


def test_an_empty_text_never_collapses_by_prefix() -> None:
    assert not collapses_into("Anything", "", is_post_url=False)


def test_trailing_number_difference_collapses_only_for_a_post_url() -> None:
    assert collapses_into("Body\n15", "Body\n12", is_post_url=True)
    assert not collapses_into("Body\n15", "Body\n12", is_post_url=False)


def test_different_content_does_not_collapse() -> None:
    assert not collapses_into("One thing", "Another thing", is_post_url=True)


def test_collapse_group_keeps_the_longer_text_and_counts_versions() -> None:
    kept = collapse_group(["Start", "Start and more", "Start and more"], is_post_url=False)

    assert kept == [(1, 3)]


def test_collapse_group_keeps_every_row_that_matches_no_rule() -> None:
    kept = collapse_group(["One thing", "Another thing", "One thing"], is_post_url=True)

    assert kept == [(0, 2), (1, 1)]


def test_collapse_group_merges_trailing_number_variants_for_a_post_url() -> None:
    assert collapse_group(["Body\n12", "Body\n15"], is_post_url=True) == [(0, 2)]
    assert collapse_group(["Body\n12", "Body\n15"], is_post_url=False) == [(0, 1), (1, 1)]
