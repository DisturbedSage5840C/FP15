"""Propose leader matches across people lists with the sorted-token name key. Pure logic, no I/O.

Rules (CLAUDE.md: missing stays missing, nothing is guessed, ambiguity is reported, not resolved):
- exact: the sorted-token key is shared 1:1 (one entity on each side holds the key);
- loose: no exact key, and exactly one candidate whose tokens contain, or are contained in, this
  name's tokens (at least MIN_LOOSE_TOKENS tokens in the shorter name), claimed by no other entity;
- ambiguous: a key shared by several entities on either side, or several loose candidates, or one
  candidate claimed by several entities. Every candidate gets its own row; none is chosen;
- none: nothing matches.
Company agreement is reported for a human to read and never changes a match type.
A leader_id is proposed only for keys held by one entity per source; ambiguous keys stay blank.
"""
from __future__ import annotations

import hashlib
import hmac
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from src.id_key import load_id_key
from src.name_key import name_key

MIN_LOOSE_TOKENS = 2
LEADER_ID_PREFIX = "L"
LEADER_ID_HEX_CHARS = 10
EXACT, LOOSE, AMBIGUOUS, NONE = "exact", "loose", "ambiguous", "none"
CLEAR = "clear"


@dataclass(frozen=True)
class Entity:
    """One name occurrence in one source. `ref` is an opaque pointer back to the source row."""

    source: str
    ref: str
    key: str
    company_key: str = ""


@dataclass(frozen=True)
class Match:
    source_a: str
    ref_a: str
    source_b: str
    ref_b: str
    match_type: str
    n_candidates: int
    company_agrees: bool | None
    key_a: str = ""  # with ref_a it identifies the a entity: sheet refs are shared, keys are not


@dataclass(frozen=True)
class PairSummary:
    """Outcomes counted per entity of side a; b_unreferenced counts side-b entities never named."""

    source_a: str
    source_b: str
    n_a: int
    n_b: int
    exact: int
    loose: int
    ambiguous: int
    none: int
    b_unreferenced: int


@dataclass(frozen=True)
class ProposalRow:
    leader_id: str
    key: str
    status: str
    refs: dict[str, tuple[str, ...]]


def make_entity(source: str, ref: str, name: object, company: object = None) -> Entity | None:
    """Build an Entity, or None when the name is blank (missing stays missing)."""
    key = name_key(name)
    if not key:
        return None
    return Entity(source=source, ref=ref, key=key, company_key=name_key(company))


def duplicate_keys(entities: Sequence[Entity]) -> frozenset[str]:
    counts = Counter(entity.key for entity in entities)
    return frozenset(key for key, count in counts.items() if count > 1)


def _group_by_key(entities: Sequence[Entity]) -> dict[str, tuple[Entity, ...]]:
    grouped: dict[str, list[Entity]] = defaultdict(list)
    for entity in entities:
        grouped[entity.key].append(entity)
    return {key: tuple(items) for key, items in grouped.items()}


def _loose_candidates(entity: Entity, pool: Sequence[Entity]) -> tuple[Entity, ...]:
    mine = frozenset(entity.key.split())
    found: list[Entity] = []
    for other in pool:
        theirs = frozenset(other.key.split())
        shorter, longer = sorted((mine, theirs), key=len)
        if len(shorter) >= MIN_LOOSE_TOKENS and mine != theirs and shorter <= longer:
            found.append(other)
    return tuple(found)


def _plan_entity(
    entity: Entity,
    b_by_key: Mapping[str, tuple[Entity, ...]],
    key_counts_a: Mapping[str, int],
    pool: Sequence[Entity],
) -> tuple[str, tuple[Entity, ...]]:
    exact = b_by_key.get(entity.key, ())
    if exact:
        unique = len(exact) == 1 and key_counts_a[entity.key] == 1
        return (EXACT if unique else AMBIGUOUS), exact
    loose = _loose_candidates(entity, pool)
    if not loose:
        return NONE, ()
    return (LOOSE if len(loose) == 1 else AMBIGUOUS), loose


def _agrees(entity: Entity, candidate: Entity) -> bool | None:
    if not entity.company_key or not candidate.company_key:
        return None
    return entity.company_key == candidate.company_key


def _rows_for(entity: Entity, kind: str, candidates: tuple[Entity, ...], source_b: str) -> list[Match]:
    if not candidates:
        return [Match(entity.source, entity.ref, source_b, "", kind, 0, None, entity.key)]
    return [
        Match(entity.source, entity.ref, c.source, c.ref, kind, len(candidates), _agrees(entity, c), entity.key)
        for c in candidates
    ]


def match_entities(a: Sequence[Entity], b: Sequence[Entity]) -> tuple[Match, ...]:
    """Match every entity of `a` against `b`; one row per entity, or one per candidate if ambiguous."""
    b_by_key = _group_by_key(b)
    key_counts_a = Counter(entity.key for entity in a)
    plans = [(entity, *_plan_entity(entity, b_by_key, key_counts_a, b)) for entity in a]
    claims = Counter(c for _, kind, cands in plans if kind != NONE for c in cands)
    source_b = b[0].source if b else ""
    rows: list[Match] = []
    for entity, kind, candidates in plans:
        final_kind = AMBIGUOUS if kind == LOOSE and claims[candidates[0]] > 1 else kind
        rows.extend(_rows_for(entity, final_kind, candidates, source_b))
    return tuple(rows)


def summarise_pair(a: Sequence[Entity], b: Sequence[Entity], matches: Sequence[Match]) -> PairSummary:
    outcome = {(match.ref_a, match.key_a): match.match_type for match in matches}
    counts = Counter(outcome.get((entity.ref, entity.key), NONE) for entity in a)
    referenced = {match.ref_b for match in matches if match.match_type != NONE}
    return PairSummary(
        source_a=a[0].source if a else "",
        source_b=b[0].source if b else "",
        n_a=len(a),
        n_b=len(b),
        exact=counts[EXACT],
        loose=counts[LOOSE],
        ambiguous=counts[AMBIGUOUS],
        none=counts[NONE],
        b_unreferenced=sum(1 for entity in b if entity.ref not in referenced),
    )


def leader_id_for(key: str) -> str:
    """A stable pseudonymous id: an HMAC-SHA256 of the name key under the secret id key.

    Without the key (src.id_key) an id cannot be rebuilt from a guessed name, so ids are safe to publish
    as counts-only references. Raises MissingIdKey when no key is set.
    """
    digest = hmac.new(load_id_key(), key.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{LEADER_ID_PREFIX}{digest[:LEADER_ID_HEX_CHARS]}"


def _collect_refs(sources: Mapping[str, Sequence[Entity]]) -> dict[str, dict[str, list[str]]]:
    by_key: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for source, entities in sources.items():
        for entity in entities:
            by_key[entity.key].setdefault(source, []).append(entity.ref)
    return by_key


def propose_leader_ids(
    sources: Mapping[str, Sequence[Entity]],
    id_for: Callable[[str], str] = leader_id_for,
) -> tuple[ProposalRow, ...]:
    """One row per key across all sources. Ambiguous keys (shared inside one source) get no id."""
    rows: list[ProposalRow] = []
    seen_ids: dict[str, str] = {}
    for key, refs in sorted(_collect_refs(sources).items()):
        ambiguous = any(len(items) > 1 for items in refs.values())
        leader_id = "" if ambiguous else id_for(key)
        if leader_id and seen_ids.setdefault(leader_id, key) != key:
            raise ValueError(f"leader_id collision for id {leader_id}")
        rows.append(
            ProposalRow(
                leader_id=leader_id,
                key=key,
                status=AMBIGUOUS if ambiguous else CLEAR,
                refs={source: tuple(items) for source, items in refs.items()},
            )
        )
    return tuple(rows)
