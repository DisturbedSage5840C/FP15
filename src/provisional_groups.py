"""Per-leader group labels for the provisional comparisons (step 14, part 3).

PROVISIONAL. Exploratory only. One row per leader with at least one raw post cell, keyed by `leader_id`. The labels
reuse the rules of the balance counts in `src.eda_balance` (ceo_type, title family, gender exactly as coded, sector,
firm size band) so the comparison groups are the same groups the EDA report counted. Gender is used as coded in
Company_Data; nothing here says what 1 or 0 mean and nothing is inferred from names.

The name key is turned into a `leader_id` in memory and the key itself is dropped, so the returned frame holds no
name. `leader_id_for` needs the secret id key (`make check-key`).
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
