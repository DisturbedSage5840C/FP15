#!/usr/bin/env python3
"""AI-assisted provisional coding for the already-drawn 300-post gold set.

This is deliberately narrower than the general judge: it runs only while the
general judge remains disabled in configs/judge.yaml.  It sends a post's text
and opaque post id to a provider with storage disabled, writes only opaque ids,
scores and fixed reason codes locally, and never signs G2.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from src.gold_set_draw import read_gold_file
from src.id_key import MissingIdKey, _read_env_file, load_id_key
from src.judge_io import DEFAULT_CONFIG_PATH, JudgeConfig, load_judge_config
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_GOLD_PATH = Path("data/derived/gold_set_300.csv")
DEFAULT_AI_PATH = Path("data/interim/goldset_AI1.csv")
DEFAULT_TEMPLATE_PATH = Path("data/interim/goldset_human_template.csv")
DEFAULT_CACHE_PATH = Path("data/interim/goldset_AI1_cache.csv")
CODER_ID = "AI-1"
HUMAN_CODERS = ("H1", "H2", "H3")
MODEL_NAME = "gpt-4.1-mini"
API_ENV = "OPENAI_API_KEY"
TRAITS = ("intelligence", "self_confidence", "determination", "integrity", "sociability")
REASON_CODES = frozenset({
    "explicit_claim", "example_or_evidence", "self_description", "goal_or_persistence",
    "values_or_ethics", "other_people_focus", "no_clear_signal", "insufficient_text", "other",
})
SCORE_COLUMNS = (*TRAITS,)
INPUT_COLUMNS = ("leader_id", "post_id", "post_text")
HUMAN_COLUMNS = ("leader_id", "post_id", "coder_id", *SCORE_COLUMNS, "reason_code")
AI_COLUMNS = (
    "leader_id", "post_id", "coder_id", "model_name", "prompt_hash",
    *(f"run1_{trait}" for trait in TRAITS), *(f"run2_{trait}" for trait in TRAITS),
    *SCORE_COLUMNS, "reason_code", *(f"agree_{trait}" for trait in TRAITS),
)
CACHE_COLUMNS = ("post_id", "prompt_hash", "run", *SCORE_COLUMNS, "reason_code")


class GoldsetClient(Protocol):
    def complete(self, *, post_id: str, text: str, prompt: str, model: str) -> object: ...


@dataclass(frozen=True)
class Code:
    scores: tuple[int | None, ...]
    reason_code: str


def _env_value(name: str, env_file: Path = Path(".env")) -> str:
    return os.environ.get(name, "").strip() or _read_env_file(env_file).get(name, "").strip()


def _require_goldset_mode(config: JudgeConfig) -> None:
    """Allow the narrow gold-set coder only while the broader judge stays off."""
    if config.approved_to_run is not False:
        raise ValueError("gold-set coding mode requires approved_to_run to remain false")
    if config.provider_no_training is not True:
        raise ValueError("gold-set coding mode requires provider_no_training to be true")
    if tuple(config.traits) != TRAITS:
        raise ValueError("gold-set coding mode requires exactly the five Northouse traits")
    if tuple(config.score_scale) != (1, 2, 3, 4, 5):
        raise ValueError("gold-set coding mode requires the 1--5 score scale")
    if not config.rubric_text.strip() or config.rubric_text.strip().upper() == "PLACEHOLDER":
        raise ValueError("gold-set coding mode requires a non-placeholder rubric")


def _prompt(config: JudgeConfig) -> str:
    return (
        config.rubric_text.strip()
        + "\n\nAI-ASSISTED GOLD-SET CODING ADDENDUM: Return exactly one JSON object with post_id, scores and reason_code. "
        + "scores must contain exactly the five rubric traits; each value is 1, 2, 3, 4, 5, or null for not enough "
        + "evidence. Use null only when the post itself is insufficient to apply the rubric. reason_code must be one of: "
        + ", ".join(sorted(REASON_CODES))
        + ". Do not include explanation text."
    )


def prompt_hash(config: JudgeConfig) -> str:
    return hashlib.sha256(_prompt(config).encode("utf-8")).hexdigest()


def _parse(raw: object, post_id: str) -> Code:
    if not isinstance(raw, str):
        raise ValueError("not_a_string")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("not_json") from error
    if not isinstance(value, dict) or value.get("post_id") != post_id:
        raise ValueError("post_id_mismatch")
    scores = value.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(TRAITS):
        raise ValueError("invalid_scores")
    parsed: list[int | None] = []
    for trait in TRAITS:
        score = scores[trait]
        if score is None:
            parsed.append(None)
        elif isinstance(score, int) and not isinstance(score, bool) and score in range(1, 6):
            parsed.append(score)
        else:
            raise ValueError("out_of_scale")
    reason = value.get("reason_code")
    if not isinstance(reason, str) or reason not in REASON_CODES:
        raise ValueError("invalid_reason_code")
    return Code(tuple(parsed), reason)


class OpenAIResponsesClient:
    """Minimal Responses API client. `store: false` requests no provider-side response storage."""

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def complete(self, *, post_id: str, text: str, prompt: str, model: str) -> object:
        body = json.dumps({
            "model": model,
            "store": False,
            "temperature": 0,
            "input": [{"role": "system", "content": prompt}, {"role": "user", "content": f"post_id: {post_id}\npost:\n{text}"}],
        }).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint, data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:  # nosec B310 -- fixed HTTPS endpoint
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            raise RuntimeError("provider_error") from error
        try:
            return payload["output"][0]["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("provider_response_shape") from error


def _read_cache(path: Path) -> dict[tuple[str, str, int], Code]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if tuple(frame.columns) != CACHE_COLUMNS:
        raise ValueError("gold-set AI cache has an unexpected schema")
    out: dict[tuple[str, str, int], Code] = {}
    for row in frame.itertuples(index=False):
        values = list(row)
        key = (values[0], values[1], int(values[2]))
        scores = tuple(None if value == "" else int(value) for value in values[3:8])
        code = Code(scores, values[8])
        if key in out:
            raise ValueError("gold-set AI cache repeats a key")
        out[key] = code
    return out


def _write_cache(cache: Mapping[tuple[str, str, int], Code], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CACHE_COLUMNS)
        for (post_id, hashed, run), code in sorted(cache.items()):
            writer.writerow([post_id, hashed, run, *["" if score is None else score for score in code.scores], code.reason_code])


def _code_one(
    post_id: str, text: str, run: int, hashed: str, prompt: str, cache: dict[tuple[str, str, int], Code], client: GoldsetClient
) -> Code:
    key = (post_id, hashed, run)
    if key not in cache:
        cache[key] = _parse(client.complete(post_id=post_id, text=text, prompt=prompt, model=MODEL_NAME), post_id)
    return cache[key]


def _require_input(frame: pd.DataFrame) -> None:
    if tuple(frame.columns) != INPUT_COLUMNS:
        raise ValueError("gold-set input must have leader_id, post_id and post_text only, in that order")
    if frame["post_id"].duplicated().any() or frame["post_id"].eq("").any() or frame["leader_id"].eq("").any():
        raise ValueError("gold-set input has missing or repeated ids")


def code_goldset(frame: pd.DataFrame, config: JudgeConfig, client: GoldsetClient, cache_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Code every input twice, using cache entries keyed by post id, prompt hash and run number."""
    _require_goldset_mode(config)
    _require_input(frame)
    hashed, prompt = prompt_hash(config), _prompt(config)
    cache = _read_cache(cache_path)
    rows: list[dict[str, object]] = []
    for item in frame.itertuples(index=False):
        leader_id, post_id, text = item
        first = _code_one(post_id, text, 1, hashed, prompt, cache, client)
        second = _code_one(post_id, text, 2, hashed, prompt, cache, client)
        row: dict[str, object] = {"leader_id": leader_id, "post_id": post_id, "coder_id": CODER_ID, "model_name": MODEL_NAME, "prompt_hash": hashed}
        row.update({f"run1_{trait}": score for trait, score in zip(TRAITS, first.scores, strict=True)})
        row.update({f"run2_{trait}": score for trait, score in zip(TRAITS, second.scores, strict=True)})
        row.update({trait: score for trait, score in zip(TRAITS, first.scores, strict=True)})
        row["reason_code"] = first.reason_code
        row.update({f"agree_{trait}": first.scores[index] == second.scores[index] for index, trait in enumerate(TRAITS)})
        rows.append(row)
    _write_cache(cache, cache_path)
    coded = pd.DataFrame(rows, columns=AI_COLUMNS)
    template = pd.DataFrame(
        [{"leader_id": leader, "post_id": post, "coder_id": coder} for leader, post in frame[["leader_id", "post_id"]].itertuples(index=False) for coder in HUMAN_CODERS],
        columns=HUMAN_COLUMNS,
    )
    return coded, template


def write_outputs(coded: pd.DataFrame, template: pd.DataFrame, ai_path: Path, template_path: Path) -> None:
    if tuple(coded.columns) != AI_COLUMNS or tuple(template.columns) != HUMAN_COLUMNS:
        raise ValueError("gold-set AI output schema changed unexpectedly")
    ai_path.parent.mkdir(parents=True, exist_ok=True)
    coded.to_csv(ai_path, index=False)
    template.to_csv(template_path, index=False)


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    gold_path: Path = DEFAULT_GOLD_PATH,
    ai_path: Path = DEFAULT_AI_PATH,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    client_factory: Callable[[str], GoldsetClient] = OpenAIResponsesClient,
) -> int:
    """Fail closed before opening/sending data unless every narrow coding precondition holds."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        load_id_key()  # Same secret-presence check as make check-key; the value is never used or logged here.
        config = load_judge_config(config_path)
        _require_goldset_mode(config)
        api_key = _env_value(API_ENV)
        if not api_key:
            raise MissingIdKey(f"{API_ENV} is not set; gold-set AI coding will not send post text")
        coded, template = code_goldset(read_gold_file(gold_path), config, client_factory(api_key), cache_path)
        write_outputs(coded, template, ai_path, template_path)
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("code-goldset-ai FAILED: %s", error)
        return 1
    logger.info("wrote AI-1 coding and human template (git-ignored; ids, scores and fixed codes only)")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
