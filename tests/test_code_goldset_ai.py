"""AI-1 gold-set coder tests with invented ids and invented text only; no network."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from scripts.code_goldset_ai import (
    AI_COLUMNS,
    CACHE_COLUMNS,
    HUMAN_COLUMNS,
    REASON_CODES,
    TRAITS,
    code_goldset,
    prompt_hash,
    write_outputs,
    _require_goldset_mode,
)
from src.judge_io import JudgeConfig


CONFIG = JudgeConfig(TRAITS, "Invented rubric.", (1, 2, 3, 4, 5), True, False, "")


def _posts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"leader_id": "L001", "post_id": "P001", "post_text": "An invented sentence."},
            {"leader_id": "L002", "post_id": "P002", "post_text": "Another invented sentence."},
        ]
    )


class FakeClient:
    def __init__(self, first_null: bool = False) -> None:
        self.calls = 0
        self.first_null = first_null

    def complete(self, *, post_id: str, text: str, prompt: str, model: str) -> str:
        self.calls += 1
        assert text.startswith(("An invented", "Another invented"))
        scores = dict.fromkeys(TRAITS, 3)
        if self.first_null and post_id == "P001":
            scores[TRAITS[0]] = None
        return json.dumps({"post_id": post_id, "scores": scores, "reason_code": "example_or_evidence"})


def test_schema_has_only_opaque_ids_scores_metadata_and_fixed_codes(tmp_path: Path) -> None:
    coded, template = code_goldset(_posts(), CONFIG, FakeClient(), tmp_path / "cache.csv")

    assert tuple(coded.columns) == AI_COLUMNS
    assert tuple(template.columns) == HUMAN_COLUMNS
    assert set(template["coder_id"]) == {"H1", "H2", "H3"}
    assert set(coded["coder_id"]) == {"AI-1"}
    assert set(coded["reason_code"]) <= REASON_CODES
    text = coded.to_csv(index=False).lower()
    for forbidden in ("invented sentence", "leader_name", "company", "http"):
        assert forbidden not in text


def test_null_is_kept_blank_and_scores_are_only_one_to_five(tmp_path: Path) -> None:
    coded, _ = code_goldset(_posts(), CONFIG, FakeClient(first_null=True), tmp_path / "cache.csv")

    assert pd.isna(coded.loc[0, TRAITS[0]])
    values = pd.concat([coded[trait] for trait in TRAITS]).dropna().astype(int)
    assert set(values).issubset({1, 2, 3, 4, 5})


def test_cache_reuses_both_runs_without_calling_the_client_again(tmp_path: Path) -> None:
    cache = tmp_path / "cache.csv"
    first = FakeClient()
    first_coded, _ = code_goldset(_posts(), CONFIG, first, cache)
    second = FakeClient()
    second_coded, _ = code_goldset(_posts(), CONFIG, second, cache)

    assert first.calls == 4
    assert second.calls == 0
    assert first_coded.equals(second_coded)
    assert tuple(pd.read_csv(cache, dtype=str, keep_default_na=False).columns) == CACHE_COLUMNS


@pytest.mark.parametrize(
    "config",
    [
        replace(CONFIG, approved_to_run=True),
        replace(CONFIG, provider_no_training=False),
        replace(CONFIG, score_scale=(1, 2, 3, 4)),
        replace(CONFIG, traits=TRAITS[:-1]),
    ],
)
def test_it_refuses_anything_but_the_narrow_goldset_coding_mode(config: JudgeConfig) -> None:
    with pytest.raises(ValueError):
        _require_goldset_mode(config)


def test_output_writer_refuses_schema_drift_and_writes_no_text(tmp_path: Path) -> None:
    coded, template = code_goldset(_posts(), CONFIG, FakeClient(), tmp_path / "cache.csv")
    ai_path, template_path = tmp_path / "AI1.csv", tmp_path / "template.csv"
    write_outputs(coded, template, ai_path, template_path)

    assert "invented sentence" not in ai_path.read_text(encoding="utf-8").lower()
    with pytest.raises(ValueError):
        write_outputs(coded.drop(columns=["reason_code"]), template, ai_path, template_path)


def test_prompt_hash_changes_when_the_rubric_changes_without_showing_the_rubric() -> None:
    assert prompt_hash(CONFIG) != prompt_hash(replace(CONFIG, rubric_text="A different invented rubric."))
