"""LLM-judge plumbing: build a request, parse a reply, run a batch. Functions only, no network, no provider SDK.

Nothing here decides what a trait means. The trait names, the rubric and the score scale all come from
configs/judge.yaml, where the rubric and the scale are written by the humans. This module refuses to build a request
while the rubric or the scale is still PLACEHOLDER, while approved_to_run is not true, or while provider_no_training is
not true. approved_to_run is a human switch: no code here or in the tests flips it.

The client is always passed in, as any object with a complete(payload) method. This module never creates one, so the
network call, the model choice and the provider's no-training settings live outside the repo's tested code.

What leaves this module
- A request payload holds exactly three fields: post_id, text and rubric.
- A reply is never repaired or guessed. Anything that is not exactly one valid score per configured trait on the
  configured scale becomes a JudgeFailure: a post_id and a fixed code, never any text from the reply or the exception.
- run_batch writes only post_id and numbers, and logs only counts and ids. No post text reaches disk or a log line.

Known limitations (stated, not fixed)
- Reply parsing is strict on purpose. A reply wrapped in a markdown fence, or a number sent as a string, is a failure.
  If real replies turn out to need a looser format, that is a human decision recorded in docs/decisions.md.
- A failed post is not retried. It stays missing and is listed by post_id.
- Nothing here has met a real model. It is tested with a fake client on invented sentences only.
"""
from __future__ import annotations

import csv
import json
import logging
import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

PLACEHOLDER = "PLACEHOLDER"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "judge.yaml"
POST_ID_COLUMN = "post_id"

_CONFIG_KEYS = ("traits", "rubric_text", "score_scale", "provider_no_training", "approved_to_run", "model_name")

logger = logging.getLogger(__name__)


class JudgeNotReadyError(RuntimeError):
    """The judge config is not cleared to run. The message names the setting, never any post text."""


class _DuplicateKeyError(ValueError):
    """Raised while reading a reply that repeats a key. Internal: it becomes the duplicate_key failure code."""


class JudgeClient(Protocol):
    """Anything with complete(payload). This module only calls it; it never builds one."""

    def complete(self, payload: dict[str, str]) -> object: ...


@dataclass(frozen=True)
class JudgeConfig:
    """The settings from configs/judge.yaml. score_scale is PLACEHOLDER (a string) until the humans write it."""

    traits: tuple[str, ...]
    rubric_text: str
    score_scale: str | tuple[float, ...]
    provider_no_training: bool
    approved_to_run: bool
    model_name: str


@dataclass(frozen=True)
class ParsedScores:
    """One valid reply: the post id and one number per trait, in the config's trait order."""

    post_id: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class JudgeFailure:
    """A post that stays missing. Only the post id and a fixed code: no reply text, no exception text."""

    post_id: str
    code: str


@dataclass(frozen=True)
class BatchResult:
    """What a batch returned, in input order. Failed posts are listed by id and have no numbers."""

    scored: tuple[ParsedScores, ...]
    failed: tuple[JudgeFailure, ...]


# --- config ---------------------------------------------------------------------------------------------------------


def _require_bool(values: dict, key: str) -> bool:
    value = values[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be true or false in the judge config")
    return value


def _require_traits(values: dict) -> tuple[str, ...]:
    traits = values["traits"]
    if not isinstance(traits, list) or not traits:
        raise ValueError("traits must be a non-empty list in the judge config")
    if not all(isinstance(trait, str) and trait.strip() for trait in traits):
        raise ValueError("traits must all be non-empty strings in the judge config")
    if len(set(traits)) != len(traits):
        raise ValueError("traits must not repeat in the judge config")
    return tuple(traits)


def _require_string(values: dict, key: str) -> str:
    value = values[key]
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string in the judge config")
    return value


def _require_scale(values: dict) -> str | tuple[float, ...]:
    scale = values["score_scale"]
    if isinstance(scale, list):
        return tuple(scale)
    if isinstance(scale, str):
        return scale
    raise ValueError("score_scale must be PLACEHOLDER or a list of numbers in the judge config")


def load_judge_config(path: Path | str = DEFAULT_CONFIG_PATH) -> JudgeConfig:
    """Read configs/judge.yaml. A missing file raises FileNotFoundError; a missing or wrong-kind key raises ValueError.

    Loading never checks readiness: the shipped file loads fine while it is still a placeholder. The gate is in
    build_request, parse_response and run_batch. Errors name the key, never the value.
    """
    values = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        raise ValueError("the judge config must be a mapping of settings")
    for key in _CONFIG_KEYS:
        if key not in values:
            raise ValueError(f"the judge config has no '{key}' setting")
    return JudgeConfig(
        traits=_require_traits(values),
        rubric_text=_require_string(values, "rubric_text"),
        score_scale=_require_scale(values),
        provider_no_training=_require_bool(values, "provider_no_training"),
        approved_to_run=_require_bool(values, "approved_to_run"),
        model_name=_require_string(values, "model_name"),
    )


# --- the readiness gate ---------------------------------------------------------------------------------------------


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _checked_scale(scale: object) -> tuple[float, ...]:
    """Return the scale as a tuple, or refuse: it must be at least two distinct finite numbers (no bools, no text)."""
    if not isinstance(scale, (list, tuple)):
        raise JudgeNotReadyError("score_scale is still a placeholder: the humans must write the list of allowed values")
    if len(scale) < 2 or not all(_is_number(value) and math.isfinite(value) for value in scale):
        raise JudgeNotReadyError("score_scale must be a list of at least two finite numbers")
    if len(set(scale)) != len(scale):
        raise JudgeNotReadyError("score_scale must not repeat a value")
    return tuple(scale)


def _check_ready(config: JudgeConfig) -> tuple[float, ...]:
    """Refuse unless the config is cleared to run. Returns the validated scale."""
    rubric = config.rubric_text
    if not isinstance(rubric, str) or not rubric.strip() or rubric.strip().upper() == PLACEHOLDER:
        raise JudgeNotReadyError("rubric_text is still a placeholder or blank: the humans must write it")
    scale = _checked_scale(config.score_scale)
    if config.approved_to_run is not True:
        raise JudgeNotReadyError("approved_to_run is not true: a human must clear the judge to run")
    if config.provider_no_training is not True:
        raise JudgeNotReadyError("provider_no_training is not true: no text may be sent to a provider that may train")
    return scale


# --- request --------------------------------------------------------------------------------------------------------


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, got {type(value).__name__}")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def build_request(post_id: str, text: str, config: JudgeConfig) -> dict[str, str]:
    """Return the payload for one post: exactly post_id, text and rubric, as a fresh dict.

    Raises JudgeNotReadyError while the rubric or scale is a placeholder, approved_to_run is false, or
    provider_no_training is not true. Raises ValueError for an empty post_id or text, and TypeError (naming only the
    type) for a non-string. No error message contains the post text.
    """
    _check_ready(config)
    return {
        "post_id": _require_text(post_id, "post_id"),
        "text": _require_text(text, "text"),
        "rubric": config.rubric_text,
    }


# --- reply ----------------------------------------------------------------------------------------------------------


def _object_without_repeats(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise _DuplicateKeyError
    return dict(pairs)


def _read_reply(raw: str) -> object:
    """Parse strict JSON, refusing repeated keys. Raises ValueError, _DuplicateKeyError or RecursionError."""
    return json.loads(raw, object_pairs_hook=_object_without_repeats)


def _score_for(value: object, allowed: dict[float, float]) -> float | str:
    """The scale's own value for one reported number, or a failure code."""
    if not _is_number(value):
        return "not_a_number"
    return allowed[value] if value in allowed else "out_of_scale"  # type: ignore[index]


def _scores_in_order(
    scores: dict[str, object], traits: tuple[str, ...], scale: tuple[float, ...]
) -> tuple[float, ...] | str:
    """One value per trait in config order, or a failure code. Nothing is filled in or coerced."""
    if any(trait not in scores for trait in traits):
        return "missing_trait"
    if set(scores) - set(traits):
        return "unexpected_trait"
    allowed = {value: value for value in scale}
    chosen = [_score_for(scores[trait], allowed) for trait in traits]
    failure = next((item for item in chosen if isinstance(item, str)), None)
    return failure if failure is not None else tuple(chosen)  # type: ignore[arg-type]


def parse_response(raw: object, expected_post_id: str, config: JudgeConfig) -> ParsedScores | JudgeFailure:
    """Check one reply. It must be one JSON object with the same post_id and one value per trait on the scale.

    A bad reply returns JudgeFailure(expected_post_id, code) and is never repaired or guessed. The codes are:
    not_a_string, not_json, duplicate_key, not_an_object, post_id_mismatch, missing_scores, missing_trait,
    unexpected_trait, not_a_number, out_of_scale. The record carries no text from the reply, and the wrong id a reply
    names is not echoed. Raises JudgeNotReadyError if the config's scale is not filled in.
    """
    scale = _checked_scale(config.score_scale)
    post_id = _require_text(expected_post_id, "expected_post_id")
    if not isinstance(raw, str):
        return JudgeFailure(post_id, "not_a_string")
    try:
        reply = _read_reply(raw)
    except _DuplicateKeyError:
        return JudgeFailure(post_id, "duplicate_key")
    except (ValueError, RecursionError):
        return JudgeFailure(post_id, "not_json")
    if not isinstance(reply, dict):
        return JudgeFailure(post_id, "not_an_object")
    returned_id = reply.get("post_id")
    if not isinstance(returned_id, str) or returned_id != post_id:
        return JudgeFailure(post_id, "post_id_mismatch")
    scores = reply.get("scores")
    if not isinstance(scores, dict):
        return JudgeFailure(post_id, "missing_scores")
    values = _scores_in_order(scores, config.traits, scale)
    if isinstance(values, str):
        return JudgeFailure(post_id, values)
    return ParsedScores(post_id=post_id, values=values)


# --- batch ----------------------------------------------------------------------------------------------------------


def _checked_posts(posts: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    """Refuse a batch with a malformed pair, an empty post id or a repeated post id, before anything is sent."""
    pairs = tuple(posts)
    seen: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise TypeError("each post must be a (post_id, text) pair")
        post_id = _require_text(pair[0], "post_id")
        if post_id in seen:
            raise ValueError("duplicate post_id in the batch")
        seen.add(post_id)
    return tuple((pair[0], pair[1]) for pair in pairs)


def _judge_one(post_id: str, text: object, client: JudgeClient, config: JudgeConfig) -> ParsedScores | JudgeFailure:
    if not isinstance(text, str) or not text.strip():
        return JudgeFailure(post_id, "invalid_post")
    payload = build_request(post_id, text, config)
    try:
        raw = client.complete(payload)
    except Exception:  # noqa: BLE001 - any client failure leaves this post missing; its message may echo the text
        return JudgeFailure(post_id, "client_error")
    return parse_response(raw, post_id, config)


def _write_scores(path: Path, traits: tuple[str, ...], outcomes: tuple[ParsedScores | JudgeFailure, ...]) -> None:
    """Write post_id and numbers only. A failed post gets blank cells, so it stays missing."""
    blank = [""] * len(traits)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([POST_ID_COLUMN, *traits])
        for outcome in outcomes:
            cells = [str(value) for value in outcome.values] if isinstance(outcome, ParsedScores) else blank
            writer.writerow([outcome.post_id, *cells])


def _log_summary(result: BatchResult) -> None:
    codes = Counter(failure.code for failure in result.failed)
    logger.info("judge batch finished: %d scored, %d failed %s", len(result.scored), len(result.failed), dict(codes))
    for failure in result.failed:
        logger.warning("judge post left missing: post_id=%s code=%s", failure.post_id, failure.code)


def run_batch(
    posts: Iterable[tuple[str, str]], client: JudgeClient, config: JudgeConfig, output_path: Path | str
) -> BatchResult:
    """Send each post to the client one at a time, in order, and write post_id and numbers to output_path.

    The gate (rubric, scale, approval, no-training) and the post ids are checked first: if either refuses, nothing is
    sent and no file is written. A post that fails stays missing: it is listed in the result by post_id and code, with
    blank cells in the file. No post text is written to disk or logged. Raises ValueError for a repeated post_id.
    """
    _check_ready(config)
    checked = _checked_posts(posts)
    outcomes = tuple(_judge_one(post_id, text, client, config) for post_id, text in checked)
    _write_scores(Path(output_path), config.traits, outcomes)
    result = BatchResult(
        scored=tuple(item for item in outcomes if isinstance(item, ParsedScores)),
        failed=tuple(item for item in outcomes if isinstance(item, JudgeFailure)),
    )
    _log_summary(result)
    return result
