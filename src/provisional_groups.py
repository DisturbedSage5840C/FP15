"""Per-leader group labels for the provisional comparisons (step 14, part 3).

PROVISIONAL. Exploratory only. One row per leader with at least one raw post cell, keyed by `leader_id`.
Firm and group variables (gender, sector, firm size) come from the leader master, joined on `leader_id`. ceo_type and
title family still come from the post sheets, because the master carries neither. Labels reuse the rules of the
balance counts in `src.eda_balance` so the comparison groups are the same groups the EDA report counted.

Gender words come from configs/gender_coding.yaml (confirmed 1 = man, 0 = woman). A blank stays missing, any other
code is labelled as such, and nothing is inferred from names. Gender is a person column, so it is read only for master
rows matched on the person ("person_and_firm"). Sector and size are firm columns, so they are read for rows matched on
the person or on the firm alone ("firm_only"). Anything else gets the explicit "no usable company match" label.

Size-band edges are quantiles over every readable firm size in the master (all leaders, not only those with posts), the
same population the master reports; the EDA report cuts over the posting leaders only, so edges can differ.

The master gives a leader whose name key is shared within the post sheets an entry-specific id, so `id_of(key)` is not
in the master for them. That is an error here, not a silent drop, and the message names the likely cause.

The name key is turned into a `leader_id` in memory and the key itself is dropped, so the returned frame holds no
name. `leader_id_for` needs the secret id key (`make check-key`).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping

import pandas as pd

from src.company_columns import leader_post_counts
from src.company_data import clean_cell
from src.eda_balance import (
    BLANK_VALUE,
    CEO_TYPE_FACTOR,
    GENDER_COLUMN,
    GENDER_FACTOR,
    NOT_MATCHED,
    OTHER_GENDER_CODE,
    POST_COLUMNS,
    SECTOR_COLUMN,
    SECTOR_FACTOR,
    SIZE_COLUMN,
    SIZE_FACTOR,
    TITLE_FACTOR,
    _ceo_type_label,
    _cell_facts,
    _sector_label,
    _size_labeller,
)
from src.eda_gaps import _require
from src.eda_groups import leader_title_family, size_band_edges
from src.leader_master import SCOPE_FIRM_ONLY, SCOPE_PERSON_AND_FIRM

FACTORS = (CEO_TYPE_FACTOR, TITLE_FACTOR, GENDER_FACTOR, SECTOR_FACTOR, SIZE_FACTOR)
GROUP_COLUMNS = ("leader_id", *FACTORS)
SCOPE_COLUMN = "columns_scope"
PERSON_SCOPES = frozenset({SCOPE_PERSON_AND_FIRM})
FIRM_SCOPES = frozenset({SCOPE_PERSON_AND_FIRM, SCOPE_FIRM_ONLY})
MASTER_COLUMNS = ("leader_id", SCOPE_COLUMN, GENDER_COLUMN, SECTOR_COLUMN, SIZE_COLUMN)
CODED_VALUES = ("0", "1")


def gender_labeller(coding: Mapping[str, str]) -> Callable[[object], str]:
    """Label a gender cell with the confirmed words; blank stays missing and nothing is guessed."""

    def label(value: object) -> str:
        text = clean_cell(value)
        if text is None:
            return BLANK_VALUE
        if text in CODED_VALUES:
            return coding.get(text, f"coded {text}")
        return OTHER_GENDER_CODE

    return label


def _check_inputs(posts: pd.DataFrame, master: pd.DataFrame) -> None:
    _require(posts, POST_COLUMNS, "harmonised_posts")
    _require(master, MASTER_COLUMNS, "leader_master")


def _master_labels(
    ids: Mapping[str, str],
    firm: pd.DataFrame,
    column: str,
    scopes: frozenset[str],
    label_of: Callable[[object], str],
) -> dict[str, str]:
    """One label per name key from the leader's master row; rows whose scope lacks the column are not matched."""
    return {
        key: label_of(firm.at[leader_id, column]) if firm.at[leader_id, SCOPE_COLUMN] in scopes else NOT_MATCHED
        for key, leader_id in ids.items()
    }


def _check_master_ids(master: pd.DataFrame, ids: Mapping[str, str]) -> None:
    """Every leader id in the master is unique, and every posting leader has one (counts only in the messages)."""
    duplicated = int(master["leader_id"].duplicated().sum())
    if duplicated:
        raise ValueError(f"{duplicated} duplicate leader_id rows in the leader master")
    known = set(master["leader_id"])
    absent = sum(1 for leader_id in ids.values() if leader_id not in known)
    if absent:
        raise ValueError(
            f"{absent} leaders with raw post cells are not in the leader master; a name key shared within the post "
            "sheets gets an entry-specific master id, so check for shared keys or a different FP15_ID_KEY"
        )


def leader_groups(
    posts: pd.DataFrame,
    master: pd.DataFrame,
    bands: int,
    id_of: Callable[[str], str],
    coding: Mapping[str, str],
) -> pd.DataFrame:
    """One row per leader with a raw cell: leader_id and the label of each comparison factor."""
    _check_inputs(posts, master)
    members = {key for key, count in leader_post_counts(posts).items() if count >= 1}
    ids = {key: id_of(key) for key in members}
    _check_master_ids(master, ids)
    firm = master.set_index("leader_id")
    ceo_values, titles = _cell_facts(posts, members)
    edges = size_band_edges(firm[SIZE_COLUMN], bands)
    by_factor = {
        CEO_TYPE_FACTOR: {key: _ceo_type_label(ceo_values.get(key, set())) for key in members},
        TITLE_FACTOR: {key: leader_title_family(titles.get(key, [])) for key in members},
        GENDER_FACTOR: _master_labels(ids, firm, GENDER_COLUMN, PERSON_SCOPES, gender_labeller(coding)),
        SECTOR_FACTOR: _master_labels(ids, firm, SECTOR_COLUMN, FIRM_SCOPES, _sector_label),
        SIZE_FACTOR: _master_labels(ids, firm, SIZE_COLUMN, FIRM_SCOPES, _size_labeller(edges, bands)),
    }
    rows = [{"leader_id": ids[key], **{factor: by_factor[factor][key] for factor in FACTORS}} for key in sorted(members)]
    return pd.DataFrame(rows, columns=list(GROUP_COLUMNS))
