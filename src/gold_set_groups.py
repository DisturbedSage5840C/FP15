"""Leader labels as the gold-set draw made them (step 16): company-data columns, gender exactly as coded.

FROZEN. This is the labelling the already-drawn gold set was stratified with: gender, sector and size come from
Company_Data through the leader-id proposal, and gender is kept as coded ("coded 1", "coded 0"). The provisional
comparisons (src/provisional_groups.py) now take their firm and group variables from the leader master with the
confirmed gender words; changing the strata of the draw would change a gate input, so that is a human decision and
this module is kept apart on purpose. It still calls the live label helpers of `src.eda_balance` and
`src.eda_groups`; tests/test_gold_set_groups.py pins the literal labels ("coded 1 (man)" and the rest) so a
change in those helpers that moves the strata fails a test instead of passing silently.

One row per leader with at least one raw post cell, keyed by `leader_id`. The name key is turned into a `leader_id`
in memory and the key itself is dropped, so the returned frame holds no name. `leader_id_for` needs the secret id key
(`make check-key`).
"""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.company_columns import leader_post_counts
from src.eda_balance import (
    CEO_TYPE_FACTOR,
    COMPANY_COLUMNS,
    GENDER_COLUMN,
    GENDER_FACTOR,
    POST_COLUMNS,
    SECTOR_COLUMN,
    SECTOR_FACTOR,
    SIZE_COLUMN,
    SIZE_FACTOR,
    TITLE_FACTOR,
    _ceo_type_label,
    _cell_facts,
    _company_labels,
    _gender_label,
    _sector_label,
    _size_labeller,
)
from src.eda_gaps import PROPOSAL_COLUMNS, _require
from src.eda_groups import classify_matches, leader_title_family, proposal_lookup, size_band_edges

FACTORS = (CEO_TYPE_FACTOR, TITLE_FACTOR, GENDER_FACTOR, SECTOR_FACTOR, SIZE_FACTOR)
GROUP_COLUMNS = ("leader_id", *FACTORS)


def _check_inputs(posts: pd.DataFrame, proposal: pd.DataFrame, company: pd.DataFrame) -> None:
    _require(posts, POST_COLUMNS, "harmonised_posts")
    _require(proposal, PROPOSAL_COLUMNS, "leader_id_proposal")
    _require(company, COMPANY_COLUMNS, "company_data")


def leader_groups(
    posts: pd.DataFrame,
    proposal: pd.DataFrame,
    company: pd.DataFrame,
    bands: int,
    id_of: Callable[[str], str],
) -> pd.DataFrame:
    """One row per leader with a raw cell: leader_id and the label of each comparison factor."""
    _check_inputs(posts, proposal, company)
    members = {key for key, count in leader_post_counts(posts).items() if count >= 1}
    positions, _ = classify_matches(members, proposal_lookup(proposal), len(company))
    ceo_values, titles = _cell_facts(posts, members)
    edges = size_band_edges(company[SIZE_COLUMN], bands)
    by_factor = {
        CEO_TYPE_FACTOR: {key: _ceo_type_label(ceo_values.get(key, set())) for key in members},
        TITLE_FACTOR: {key: leader_title_family(titles.get(key, [])) for key in members},
        GENDER_FACTOR: _company_labels(members, positions, company[GENDER_COLUMN].tolist(), _gender_label),
        SECTOR_FACTOR: _company_labels(members, positions, company[SECTOR_COLUMN].tolist(), _sector_label),
        SIZE_FACTOR: _company_labels(
            members, positions, company[SIZE_COLUMN].tolist(), _size_labeller(edges, bands)
        ),
    }
    rows = [{"leader_id": id_of(key), **{factor: by_factor[factor][key] for factor in FACTORS}} for key in sorted(members)]
    return pd.DataFrame(rows, columns=list(GROUP_COLUMNS))
