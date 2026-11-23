"""Step 3 of the leader matching ladder (step 14A): company name, then domain, onto Company_Data firm rows.

Steps 1 and 2 (exact and loose name) live in src/id_matching.py and are unchanged. This module only adds the third
step for leaders that no name step matched. A match counts only when it points to exactly one firm row; several rows
make it ambiguous. A blank company or domain never matches anything (missing stays missing; "." and "-" are blank).
Nothing here is written to disk.
"""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from src.company_data import clean_cell
from src.name_key import name_key

NAME_EXACT = "name_exact"
NAME_LOOSE = "name_loose"
COMPANY_NAME = "company_name"
DOMAIN = "domain"
AMBIGUOUS = "ambiguous"
NONE = "none"

FIRM_NAME_COLUMN = "CompanyName"
DOMAIN_COLUMN = "DomainName"
SECOND_LEVEL_SUFFIXES = frozenset({"co", "com", "org", "net", "ac", "gov", "edu", "nic"})
WWW_LABEL = "www"
MIN_LABELS_FOR_SUFFIX = 2
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")
_NOT_ALNUM = re.compile(r"[^a-z0-9]")


@dataclass(frozen=True)
class FirmIndex:
    """Firm row positions by company-name key and by domain label."""

    by_company: Mapping[str, tuple[int, ...]]
    by_domain: Mapping[str, tuple[int, ...]]


@dataclass(frozen=True)
class FirmStep:
    """Outcome of step 3: a method and the firm rows it points to."""

    method: str
    rows: tuple[int, ...]


def domain_label(value: object) -> str:
    """The registrable name of a web address, squashed to letters and digits; "" for blank, "." and "-"."""
    text = clean_cell(value)
    if text is None:
        return ""
    host = _SCHEME.sub("", text.lower()).split("/")[0].split("?")[0].split(":")[0]
    labels = [part for part in host.split(".") if part]
    if labels and labels[0] == WWW_LABEL:
        labels = labels[1:]
    if len(labels) >= MIN_LABELS_FOR_SUFFIX:
        labels = labels[:-1]
        if len(labels) >= MIN_LABELS_FOR_SUFFIX and labels[-1] in SECOND_LEVEL_SUFFIXES:
            labels = labels[:-1]
    return _NOT_ALNUM.sub("", labels[-1]) if labels else ""


def squash(company_key: str) -> str:
    """A company-name key with its spaces removed, comparable with a domain label."""
    return company_key.replace(" ", "")


def _positions(keys: list[str]) -> dict[str, tuple[int, ...]]:
    found: dict[str, list[int]] = defaultdict(list)
    for position, key in enumerate(keys):
        if key:
            found[key].append(position)
    return {key: tuple(rows) for key, rows in found.items()}


def build_firm_index(company: pd.DataFrame) -> FirmIndex:
    """Index the firm rows of Company_Data; rows with a blank name or domain are simply not indexed."""
    names = [name_key(value) for value in company[FIRM_NAME_COLUMN]]
    domains = [domain_label(value) for value in company[DOMAIN_COLUMN]]
    return FirmIndex(by_company=_positions(names), by_domain=_positions(domains))


def _verdict(method: str, rows: tuple[int, ...]) -> FirmStep:
    return FirmStep(method if len(rows) == 1 else AMBIGUOUS, rows)


def resolve_by_firm(company_key: str, index: FirmIndex) -> FirmStep:
    """Company-name key first, then the domain; accepted only on exactly one firm row."""
    if not company_key:
        return FirmStep(NONE, ())
    by_name = index.by_company.get(company_key, ())
    if by_name:
        return _verdict(COMPANY_NAME, by_name)
    by_domain = index.by_domain.get(squash(company_key), ())
    if by_domain:
        return _verdict(DOMAIN, by_domain)
    return FirmStep(NONE, ())
