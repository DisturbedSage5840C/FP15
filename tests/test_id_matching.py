"""Tests for sorted-token ID matching (src.id_matching). Synthetic names only."""
import pytest

from src.id_matching import (
    Entity,
    duplicate_keys,
    leader_id_for,
    make_entity,
    match_entities,
    propose_leader_ids,
    summarise_pair,
)


def _e(source: str, ref: str, name: str, company: str | None = None) -> Entity:
    entity = make_entity(source, ref, name, company)
    assert entity is not None
    return entity


def test_make_entity_returns_none_for_a_blank_name() -> None:
    assert make_entity("roster", "1", None, "Acme") is None
    assert make_entity("roster", "1", "  ", "Acme") is None
    assert make_entity("roster", "1", float("nan"), None) is None


def test_make_entity_keys_names_and_companies_with_the_sorted_token_key() -> None:
    entity = _e("roster", "7", "Lee, Ann", "ACME  Ltd.")

    assert entity.key == "ann lee"
    assert entity.company_key == "acme ltd"
    assert (entity.source, entity.ref) == ("roster", "7")


def test_make_entity_company_key_is_blank_when_company_missing() -> None:
    assert _e("roster", "1", "Ann Lee", None).company_key == ""


def test_duplicate_keys_lists_keys_shared_by_more_than_one_entity() -> None:
    entities = [_e("s", "1", "Ann Lee"), _e("s", "2", "lee ann"), _e("s", "3", "Bo Rao")]

    assert duplicate_keys(entities) == frozenset({"ann lee"})


def test_exact_match_is_one_to_one_and_ignores_token_order_and_case() -> None:
    a = [_e("sheets", "a1", "Ann Lee")]
    b = [_e("company", "b1", "LEE, ann"), _e("company", "b2", "Bo Rao")]

    (match,) = match_entities(a, b)

    assert (match.match_type, match.ref_b, match.n_candidates) == ("exact", "b1", 1)
    assert (match.source_a, match.source_b) == ("sheets", "company")


def test_a_key_shared_by_two_entities_in_b_is_ambiguous_with_one_row_per_candidate() -> None:
    a = [_e("sheets", "a1", "Ann Lee")]
    b = [_e("company", "b1", "Ann Lee"), _e("company", "b2", "Lee Ann")]

    matches = match_entities(a, b)

    assert {m.match_type for m in matches} == {"ambiguous"}
    assert sorted(m.ref_b for m in matches) == ["b1", "b2"]
    assert all(m.n_candidates == 2 for m in matches)


def test_a_key_shared_by_two_entities_in_a_is_ambiguous_even_with_one_candidate() -> None:
    a = [_e("roster", "a1", "Ann Lee"), _e("roster", "a2", "Lee Ann")]
    b = [_e("company", "b1", "Ann Lee")]

    matches = match_entities(a, b)

    assert {m.match_type for m in matches} == {"ambiguous"}
    assert sorted(m.ref_a for m in matches) == ["a1", "a2"]


def test_no_shared_key_gives_a_none_row_with_blank_ref() -> None:
    (match,) = match_entities([_e("sheets", "a1", "Ann Lee")], [_e("company", "b1", "Bo Rao")])

    assert (match.match_type, match.ref_b, match.n_candidates) == ("none", "", 0)


def test_loose_match_when_all_tokens_of_one_name_are_inside_the_other() -> None:
    a = [_e("sheets", "a1", "Ann Marie Lee")]
    b = [_e("company", "b1", "Ann Lee"), _e("company", "b2", "Bo Rao")]

    (match,) = match_entities(a, b)

    assert (match.match_type, match.ref_b, match.n_candidates) == ("loose", "b1", 1)


def test_loose_match_works_in_the_other_direction_too() -> None:
    (match,) = match_entities([_e("s", "a1", "Ann Lee")], [_e("c", "b1", "Ann Marie Lee")])

    assert (match.match_type, match.ref_b) == ("loose", "b1")


def test_a_single_token_name_is_never_loosely_matched() -> None:
    (match,) = match_entities([_e("s", "a1", "Ann")], [_e("c", "b1", "Ann Lee")])

    assert match.match_type == "none"


def test_loose_match_with_two_candidates_is_ambiguous_and_never_resolved() -> None:
    a = [_e("s", "a1", "Ann Marie Lee")]
    b = [_e("c", "b1", "Ann Lee"), _e("c", "b2", "Marie Lee")]

    matches = match_entities(a, b)

    assert {m.match_type for m in matches} == {"ambiguous"}
    assert sorted(m.ref_b for m in matches) == ["b1", "b2"]


def test_loose_match_claimed_by_two_entities_in_a_is_ambiguous() -> None:
    a = [_e("s", "a1", "Ann Marie Lee"), _e("s", "a2", "Ann Rose Lee")]
    b = [_e("c", "b1", "Ann Lee")]

    matches = match_entities(a, b)

    assert {m.match_type for m in matches} == {"ambiguous"}
    assert sorted(m.ref_a for m in matches) == ["a1", "a2"]


def test_an_exact_match_blocks_loose_matching_for_that_entity() -> None:
    a = [_e("s", "a1", "Ann Lee")]
    b = [_e("c", "b1", "Ann Lee"), _e("c", "b2", "Ann Marie Lee")]

    (match,) = match_entities(a, b)

    assert (match.match_type, match.ref_b) == ("exact", "b1")


@pytest.mark.parametrize(
    ("company_a", "company_b", "expected"),
    [("Acme", "ACME", True), ("Acme", "Beta", False), (None, "Beta", None), ("Acme", None, None)],
)
def test_company_agreement_is_informational_and_none_when_a_company_is_blank(
    company_a: str | None, company_b: str | None, expected: bool | None
) -> None:
    a = [_e("s", "a1", "Ann Lee", company_a)]
    b = [_e("c", "b1", "Ann Lee", company_b)]

    (match,) = match_entities(a, b)

    assert match.match_type == "exact"
    assert match.company_agrees is expected


def test_company_disagreement_does_not_change_an_exact_match() -> None:
    (match,) = match_entities([_e("s", "a1", "Ann Lee", "Acme")], [_e("c", "b1", "Ann Lee", "Beta")])

    assert match.match_type == "exact" and match.company_agrees is False


def test_summarise_pair_counts_a_side_outcomes_and_unreferenced_b() -> None:
    a = [
        _e("s", "a1", "Ann Lee"),
        _e("s", "a2", "Bo Rao"),
        _e("s", "a3", "Cy Dunn Park"),
        _e("s", "a4", "Di Fox"),
    ]
    b = [
        _e("c", "b1", "Ann Lee"),
        _e("c", "b2", "Bo Rao"),
        _e("c", "b3", "Rao Bo"),
        _e("c", "b4", "Cy Dunn"),
        _e("c", "b5", "Ed Gray"),
    ]

    summary = summarise_pair(a, b, match_entities(a, b))

    assert (summary.source_a, summary.source_b) == ("s", "c")
    assert (summary.n_a, summary.n_b) == (4, 5)
    assert (summary.exact, summary.loose, summary.ambiguous, summary.none) == (1, 1, 1, 1)
    assert summary.b_unreferenced == 1  # only b5 is never named by a non-"none" match


def test_summarise_pair_counts_each_ambiguous_a_entity_once() -> None:
    a = [_e("s", "a1", "Ann Lee")]
    b = [_e("c", "b1", "Ann Lee"), _e("c", "b2", "Lee Ann")]

    summary = summarise_pair(a, b, match_entities(a, b))

    assert summary.ambiguous == 1 and summary.n_a == 1


def _shared_ref_sheets() -> list[Entity]:
    """Sheet-like entities: unique keys, but several leaders sit on one workbook#index reference."""
    return [_e("sheets", "w1#1", "Ann Lee"), _e("sheets", "w1#1", "Bo Rao"), _e("sheets", "w1#1", "Di Fox")]


def test_each_match_row_carries_the_key_of_its_a_entity() -> None:
    a = _shared_ref_sheets()
    b = [_e("c", "b1", "Ann Lee"), _e("c", "b2", "Di Fox"), _e("c", "b3", "Fox Di")]

    matches = match_entities(a, b)

    kinds = {(m.key_a, m.match_type) for m in matches}
    assert kinds == {("ann lee", "exact"), ("bo rao", "none"), ("di fox", "ambiguous")}


def test_summarise_pair_counts_leaders_that_share_one_source_reference() -> None:
    a = _shared_ref_sheets()
    b = [_e("c", "b1", "Ann Lee"), _e("c", "b2", "Di Fox"), _e("c", "b3", "Fox Di")]

    summary = summarise_pair(a, b, match_entities(a, b))

    assert (summary.exact, summary.loose, summary.ambiguous, summary.none) == (1, 0, 1, 1)


def test_leader_id_is_stable_prefixed_and_depends_only_on_the_key() -> None:
    assert leader_id_for("ann lee") == leader_id_for("ann lee")
    assert leader_id_for("ann lee") != leader_id_for("bo rao")
    assert leader_id_for("ann lee").startswith("L")
    assert "ann" not in leader_id_for("ann lee")


def test_proposal_has_one_row_per_key_across_all_sources() -> None:
    sources = {
        "sheets": [_e("sheets", "s1", "Ann Lee")],
        "roster": [_e("roster", "349", "Lee Ann"), _e("roster", "350", "Bo Rao")],
        "company": [_e("company", "row:1", "Ann Lee")],
    }

    rows = propose_leader_ids(sources)

    by_key = {r.key: r for r in rows}
    assert set(by_key) == {"ann lee", "bo rao"}
    ann = by_key["ann lee"]
    assert ann.status == "clear" and ann.leader_id == leader_id_for("ann lee")
    assert ann.refs == {"sheets": ("s1",), "roster": ("349",), "company": ("row:1",)}
    assert by_key["bo rao"].refs == {"roster": ("350",)}


def test_proposal_leaves_leader_id_blank_for_keys_shared_by_two_entities() -> None:
    sources = {
        "roster": [_e("roster", "1", "Ann Lee"), _e("roster", "2", "Lee Ann")],
        "company": [_e("company", "row:1", "Ann Lee")],
    }

    (row,) = propose_leader_ids(sources)

    assert row.status == "ambiguous" and row.leader_id == ""
    assert row.refs["roster"] == ("1", "2")


def test_proposal_rows_are_sorted_by_key_for_a_stable_output() -> None:
    sources = {"s": [_e("s", "1", "Zed Zee"), _e("s", "2", "Abe Ng")]}

    assert [r.key for r in propose_leader_ids(sources)] == ["abe ng", "zed zee"]


def test_proposal_raises_when_two_different_keys_would_get_the_same_id() -> None:
    sources = {"s": [_e("s", "1", "Ann Lee"), _e("s", "2", "Bo Rao")]}

    with pytest.raises(ValueError, match="collision"):
        propose_leader_ids(sources, id_for=lambda key: "L0")
