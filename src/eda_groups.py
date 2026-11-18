"""Grouping rules shared by the EDA balance and selection sections.

Every grouping here is a proposal for the mentors, not a decision: sector is the first segment of the coded sector
path, size bands are quantile bands of the employee count, and title family is a keyword rule over the title text.
Missing stays missing: a value that cannot be read has no group (it is counted as missing by the caller).
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

from src.company_columns import CLEAR_STATUS, _company_position
from src.company_data import clean_cell, parse_quantity

SECTOR_SEPARATOR = ">"
BLANK_TITLE = "no title"
MIXED_TITLES = "mixed title families"
OTHER_TITLE = "Other title"
NO_COMPANY_ROW, AMBIGUOUS, NOT_IN_PROPOSAL = "no_company_row", "ambiguous", "not_in_proposal"

# (family, pattern) in priority order: the first rule that matches a title names its family.
TITLE_RULES = (
    ("CEO", re.compile(r"\bceo\b|chief executive")),
    ("Managing director", re.compile(r"managing director|\bmd\b")),
    ("Chair", re.compile(r"\bchair")),
    ("Founder", re.compile(r"founder")),
    ("President", re.compile(r"\bpresident\b")),
    ("Other chief officer", re.compile(r"\bc[a-z]o\b|\bchief\b.*\bofficer\b")),
)


# ---- sector -----------------------------------------------------------------------------------


def sector_of(value: object) -> str | None:
    """The first segment of the coded sector path, as coded; None when the cell or that segment is blank."""
    text = clean_cell(value)
    if text is None:
        return None
    first = text.split(SECTOR_SEPARATOR)[0].strip()
    return first or None


# ---- firm size bands --------------------------------------------------------------------------


def _readable(values: Iterable[object]) -> list[float]:
    numbers = (parse_quantity(value) for value in values)
    return [number for number in numbers if number is not None]


def size_band_edges(values: Iterable[object], bands: int) -> tuple[float, ...]:
    """Quantile cut points (bands - 1 of them) over the values `parse_quantity` can read."""
    readable = _readable(values)
    if len(readable) < bands:
        raise ValueError(f"size bands: {len(readable)} readable values are too few for {bands} bands")
    cuts = [step / bands for step in range(1, bands)]
    return tuple(float(edge) for edge in np.quantile(readable, cuts))


def size_band(value: object, edges: tuple[float, ...]) -> int | None:
    """Band number from 1 (smallest); a value on an edge falls in the lower band. None when unreadable."""
    number = parse_quantity(value)
    if number is None:
        return None
    return 1 + sum(1 for edge in edges if number > edge)


def size_band_label(band: int, bands: int) -> str:
    if band == 1:
        return f"size band {band} (smallest)"
    if band == bands:
        return f"size band {band} (largest)"
    return f"size band {band}"


# ---- title family -----------------------------------------------------------------------------


def _title_family(title: str) -> str:
    lowered = title.lower()
    for family, pattern in TITLE_RULES:
        if pattern.search(lowered):
            return family
    return OTHER_TITLE


def leader_title_family(titles: Iterable[object]) -> str:
    """One family for a leader: the family of their non-blank titles, or "mixed" when the titles disagree."""
    texts = (clean_cell(title) for title in titles)
    families = {_title_family(text) for text in texts if text is not None}
    if not families:
        return BLANK_TITLE
    return next(iter(families)) if len(families) == 1 else MIXED_TITLES


# ---- Company_Data match lookup ----------------------------------------------------------------


def proposal_lookup(proposal: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """Name key -> (status, company reference) from leader_id_proposal."""
    return {
        key: (status, ref)
        for key, status, ref in zip(proposal["key"], proposal["status"], proposal["company"], strict=True)
    }


def classify_matches(
    members: Iterable[str], lookup: Mapping[str, tuple[str, str]], company_rows: int
) -> tuple[dict[str, int], dict[str, int]]:
    """Company row position per leader with a clear match, and the count of every other outcome."""
    positions: dict[str, int] = {}
    others = {AMBIGUOUS: 0, NO_COMPANY_ROW: 0, NOT_IN_PROPOSAL: 0}
    for key in members:
        if key not in lookup:
            others[NOT_IN_PROPOSAL] += 1
            continue
        status, ref = lookup[key]
        if status != CLEAR_STATUS:
            others[AMBIGUOUS] += 1
            continue
        position = _company_position(ref)
        if position is None:
            others[NO_COMPANY_ROW] += 1
        elif position >= company_rows:
            raise ValueError(f"leader_id_proposal: company reference {ref} is beyond the {company_rows} company rows")
        else:
            positions[key] = position
    return positions, others
