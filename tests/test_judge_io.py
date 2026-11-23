"""src/judge_io.py: LLM-judge plumbing, tested with a fake client and invented sentences only.

No network, no real API call, no real post text. The rubric and scale used here are invented test values: they are not
the study's rubric or scale, and nothing in this file decides what any trait means. approved_to_run in the shipped
config is never changed; tests build in-memory copies with dataclasses.replace.
"""
from __future__ import annotations

import ast
import csv
import dataclasses
import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from src.judge_io import (
    PLACEHOLDER,
    BatchResult,
    JudgeConfig,
    JudgeFailure,
    JudgeNotReadyError,
    ParsedScores,
    build_request,
    load_judge_config,
    parse_response,
    run_batch,
)

ROOT = Path(__file__).resolve().parent.parent
SHIPPED_CONFIG_PATH = ROOT / "configs" / "judge.yaml"
JUDGE_SOURCE_PATH = ROOT / "src" / "judge_io.py"
EXPECTED_TRAITS = ("intelligence", "self_confidence", "determination", "integrity", "sociability")
EXPECTED_CONFIG_KEYS = {
    "traits", "rubric_text", "score_scale", "provider_no_training", "approved_to_run", "model_name",
}
TEST_RUBRIC = "INVENTED RUBRIC SENTENCE FOR TESTS ONLY"
TEST_SCALE = (1, 2, 3)  # invented for the tests; the real scale is for the humans to write
TEXT_MARKER = "quillmoor"  # appears only in invented post text, so it must never show up anywhere else
INVENTED_POSTS = (
    ("p1", f"We opened a bakery in {TEXT_MARKER} and the croissants sold out by noon."),
    ("p2", "The harbour festival was lovely and I met so many kind people."),
    ("p3", "A short note about our new lighthouse tours."),
)
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {"anthropic", "openai", "requests", "httpx", "urllib", "urllib3", "socket", "ssl", "http", "aiohttp", "websockets"}
)
REMOVE = object()  # marks a trait to drop from a reply built by reply_with


class FakeClient:
    """Any object with complete(payload) works; this one records every payload it receives."""

    def __init__(self, respond: Callable[[dict], object]) -> None:
        self._respond = respond
        self.payloads: list[dict] = []

    def complete(self, payload: dict) -> object:
        self.payloads.append(dict(payload))
        return self._respond(payload)


@pytest.fixture
def ready_config() -> JudgeConfig:
    return dataclasses.replace(
        load_judge_config(), rubric_text=TEST_RUBRIC, score_scale=TEST_SCALE, approved_to_run=True
    )


def good_reply(config: JudgeConfig, post_id: str, values: tuple[float, ...] | None = None) -> str:
    chosen = values if values is not None else tuple(TEST_SCALE[0] for _ in config.traits)
    return json.dumps({"post_id": post_id, "scores": dict(zip(config.traits, chosen))})


def reply_with(config: JudgeConfig, post_id: str, **changes: object) -> str:
    """A good reply with some scores replaced or added (a value of REMOVE drops that trait)."""
    scores: dict[str, object] = {trait: TEST_SCALE[0] for trait in config.traits}
    for trait, value in changes.items():
        if value is REMOVE:
            scores.pop(trait)
        else:
            scores[trait] = value
    return json.dumps({"post_id": post_id, "scores": scores})


def always_good(config: JudgeConfig) -> Callable[[dict], object]:
    return lambda payload: good_reply(config, payload["post_id"])


def read_rows(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


# --- the shipped config -------------------------------------------------------------------------------------------


def test_shipped_config_has_exactly_the_agreed_keys() -> None:
    values = yaml.safe_load(SHIPPED_CONFIG_PATH.read_text(encoding="utf-8"))

    assert set(values) == EXPECTED_CONFIG_KEYS


def test_shipped_config_lists_the_five_trait_names_and_leaves_the_rest_for_the_humans() -> None:
    config = load_judge_config()

    assert config.traits == EXPECTED_TRAITS
    assert config.rubric_text == PLACEHOLDER
    assert config.score_scale == PLACEHOLDER
    assert config.provider_no_training is True
    assert config.approved_to_run is False
    assert config.model_name == ""


def test_the_shipped_config_cannot_build_a_request_yet() -> None:
    with pytest.raises(JudgeNotReadyError):
        build_request("p1", "An invented sentence.", load_judge_config())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"approved_to_run": "false"}, "approved_to_run"),
        ({"provider_no_training": "yes"}, "provider_no_training"),
        ({"traits": []}, "traits"),
        ({"traits": ["intelligence", "intelligence"]}, "traits"),
        ({"traits": ["intelligence", ""]}, "traits"),
        ({"rubric_text": 7}, "rubric_text"),
        ({"model_name": None}, "model_name"),
    ],
)
def test_loading_rejects_values_of_the_wrong_kind(tmp_path: Path, change: dict, message: str) -> None:
    values = yaml.safe_load(SHIPPED_CONFIG_PATH.read_text(encoding="utf-8")) | change
    path = tmp_path / "judge.yaml"
    path.write_text(yaml.safe_dump(values), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_judge_config(path)


def test_loading_rejects_a_missing_key(tmp_path: Path) -> None:
    values = yaml.safe_load(SHIPPED_CONFIG_PATH.read_text(encoding="utf-8"))
    del values["approved_to_run"]
    path = tmp_path / "judge.yaml"
    path.write_text(yaml.safe_dump(values), encoding="utf-8")

    with pytest.raises(ValueError, match="approved_to_run"):
        load_judge_config(path)


def test_loading_a_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_judge_config(tmp_path / "nope.yaml")


# --- build_request ------------------------------------------------------------------------------------------------


def test_payload_holds_only_the_post_id_the_text_and_the_rubric(ready_config: JudgeConfig) -> None:
    payload = build_request("p1", "An invented sentence about harbours.", ready_config)

    assert payload == {"post_id": "p1", "text": "An invented sentence about harbours.", "rubric": TEST_RUBRIC}


def test_each_payload_is_a_fresh_object(ready_config: JudgeConfig) -> None:
    first = build_request("p1", "An invented sentence.", ready_config)
    first["text"] = "changed by the caller"

    second = build_request("p1", "An invented sentence.", ready_config)

    assert second["text"] == "An invented sentence."


@pytest.mark.parametrize("rubric", [PLACEHOLDER, "  PLACEHOLDER  ", "placeholder", "", "   "])
def test_a_placeholder_or_blank_rubric_refuses(ready_config: JudgeConfig, rubric: str) -> None:
    config = dataclasses.replace(ready_config, rubric_text=rubric)

    with pytest.raises(JudgeNotReadyError, match="rubric_text"):
        build_request("p1", "An invented sentence.", config)


def test_approved_to_run_false_refuses(ready_config: JudgeConfig) -> None:
    config = dataclasses.replace(ready_config, approved_to_run=False)

    with pytest.raises(JudgeNotReadyError, match="approved_to_run"):
        build_request("p1", "An invented sentence.", config)


def test_a_provider_that_may_train_on_the_text_refuses(ready_config: JudgeConfig) -> None:
    config = dataclasses.replace(ready_config, provider_no_training=False)

    with pytest.raises(JudgeNotReadyError, match="provider_no_training"):
        build_request("p1", "An invented sentence.", config)


@pytest.mark.parametrize(
    "scale",
    [PLACEHOLDER, "1 to 5", [], (2,), (1, 1, 2), (1, True, 3), (1, "2", 3), (1, float("nan"), 3), (1, float("inf"), 3)],
)
def test_a_scale_that_is_a_placeholder_or_not_a_list_of_distinct_numbers_refuses(
    ready_config: JudgeConfig, scale: object
) -> None:
    config = dataclasses.replace(ready_config, score_scale=scale)

    with pytest.raises(JudgeNotReadyError, match="score_scale"):
        build_request("p1", "An invented sentence.", config)


def test_a_refusal_message_never_contains_the_post_text(ready_config: JudgeConfig) -> None:
    config = dataclasses.replace(ready_config, approved_to_run=False)

    with pytest.raises(JudgeNotReadyError) as caught:
        build_request("p1", f"A sentence about {TEXT_MARKER}.", config)

    assert TEXT_MARKER not in str(caught.value)


@pytest.mark.parametrize("post_id", ["", "   "])
def test_an_empty_post_id_is_rejected(ready_config: JudgeConfig, post_id: str) -> None:
    with pytest.raises(ValueError, match="post_id"):
        build_request(post_id, "An invented sentence.", ready_config)


@pytest.mark.parametrize("text", ["", "   \n"])
def test_empty_post_text_is_rejected_not_sent(ready_config: JudgeConfig, text: str) -> None:
    with pytest.raises(ValueError, match="text"):
        build_request("p1", text, ready_config)


def test_non_string_inputs_raise_type_error_naming_only_the_type(ready_config: JudgeConfig) -> None:
    with pytest.raises(TypeError, match="got int"):
        build_request("p1", 5, ready_config)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="got NoneType"):
        build_request(None, "An invented sentence.", ready_config)  # type: ignore[arg-type]


# --- parse_response -----------------------------------------------------------------------------------------------


def test_a_valid_reply_gives_one_value_per_trait_in_config_order(ready_config: JudgeConfig) -> None:
    raw = json.dumps({"post_id": "p1", "scores": dict(zip(reversed(ready_config.traits), (1, 2, 3, 1, 2)))})

    result = parse_response(raw, "p1", ready_config)

    assert result == ParsedScores(post_id="p1", values=(2, 1, 3, 2, 1))


def test_a_float_that_equals_a_scale_value_is_accepted(ready_config: JudgeConfig) -> None:
    result = parse_response(reply_with(ready_config, "p1", intelligence=2.0), "p1", ready_config)

    assert isinstance(result, ParsedScores)
    assert result.values[0] == 2


@pytest.mark.parametrize("raw", [None, 5, {"post_id": "p1"}, b"{}", ["p1"]])
def test_a_reply_that_is_not_text_is_an_error_record(ready_config: JudgeConfig, raw: object) -> None:
    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "not_a_string")  # type: ignore[arg-type]


@pytest.mark.parametrize("raw", ["", "not json at all", "{", "{'post_id': 'p1'}"])
def test_a_reply_that_is_not_json_is_an_error_record(ready_config: JudgeConfig, raw: str) -> None:
    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "not_json")


def test_a_reply_wrapped_in_a_markdown_fence_is_not_repaired(ready_config: JudgeConfig) -> None:
    fenced = "```json\n" + good_reply(ready_config, "p1") + "\n```"

    assert parse_response(fenced, "p1", ready_config) == JudgeFailure("p1", "not_json")


@pytest.mark.parametrize("raw", ["[1, 2, 3]", '"p1"', "7", "null"])
def test_a_reply_that_is_not_an_object_is_an_error_record(ready_config: JudgeConfig, raw: str) -> None:
    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "not_an_object")


def test_a_duplicate_key_is_an_error_record_not_a_silent_pick_of_the_last(ready_config: JudgeConfig) -> None:
    raw = '{"post_id": "p1", "scores": {}, "post_id": "p1"}'

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "duplicate_key")


def test_a_duplicate_trait_key_is_an_error_record(ready_config: JudgeConfig) -> None:
    pairs = ", ".join(f'"{trait}": 1' for trait in ready_config.traits) + ', "intelligence": 2'
    raw = '{"post_id": "p1", "scores": {' + pairs + "}}"

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "duplicate_key")


def test_a_mismatched_post_id_is_rejected_and_the_wrong_id_is_not_echoed(ready_config: JudgeConfig) -> None:
    result = parse_response(good_reply(ready_config, "p2-other"), "p1", ready_config)

    assert result == JudgeFailure("p1", "post_id_mismatch")
    assert "p2-other" not in repr(result)


@pytest.mark.parametrize("returned_id", [None, 1, ["p1"], ""])
def test_a_missing_or_differently_typed_post_id_is_a_mismatch(ready_config: JudgeConfig, returned_id: object) -> None:
    raw = json.dumps({"post_id": returned_id, "scores": {trait: 1 for trait in ready_config.traits}})

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "post_id_mismatch")


def test_a_reply_with_no_post_id_key_is_a_mismatch(ready_config: JudgeConfig) -> None:
    raw = json.dumps({"scores": {trait: 1 for trait in ready_config.traits}})

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "post_id_mismatch")


@pytest.mark.parametrize("scores", [None, [1, 2, 3], "high", 4])
def test_scores_that_are_not_an_object_are_an_error_record(ready_config: JudgeConfig, scores: object) -> None:
    raw = json.dumps({"post_id": "p1", "scores": scores})

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "missing_scores")


def test_a_reply_with_no_scores_key_is_an_error_record(ready_config: JudgeConfig) -> None:
    assert parse_response('{"post_id": "p1"}', "p1", ready_config) == JudgeFailure("p1", "missing_scores")


def test_a_missing_trait_is_rejected_and_never_filled_in(ready_config: JudgeConfig) -> None:
    raw = reply_with(ready_config, "p1", integrity=REMOVE)

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "missing_trait")


def test_an_unexpected_extra_trait_is_rejected(ready_config: JudgeConfig) -> None:
    raw = reply_with(ready_config, "p1", charisma=2)

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "unexpected_trait")


@pytest.mark.parametrize("value", [0, 4, -1, 2.5, 1000])
def test_an_out_of_scale_value_is_rejected(ready_config: JudgeConfig, value: object) -> None:
    raw = reply_with(ready_config, "p1", sociability=value)

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "out_of_scale")


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_the_non_finite_literals_python_json_tolerates_are_out_of_scale(
    ready_config: JudgeConfig, literal: str
) -> None:
    pairs = ", ".join(f'"{trait}": 1' for trait in ready_config.traits[1:])
    raw = '{"post_id": "p1", "scores": {"' + ready_config.traits[0] + '": ' + literal + ", " + pairs + "}}"

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "out_of_scale")


@pytest.mark.parametrize("value", ["2", None, True, False, [2], {"v": 2}])
def test_a_value_that_is_not_a_number_is_rejected_not_coerced(ready_config: JudgeConfig, value: object) -> None:
    raw = reply_with(ready_config, "p1", determination=value)

    assert parse_response(raw, "p1", ready_config) == JudgeFailure("p1", "not_a_number")


def test_an_error_record_never_contains_text_from_the_reply(ready_config: JudgeConfig) -> None:
    raw = json.dumps(
        {"post_id": "p1", "scores": {"intelligence": f"high, because of {TEXT_MARKER}"}, "note": TEXT_MARKER}
    )

    result = parse_response(raw, "p1", ready_config)

    assert isinstance(result, JudgeFailure)
    assert TEXT_MARKER not in repr(result)
    assert set(dataclasses.asdict(result)) == {"post_id", "code"}


def test_parsing_with_a_config_that_is_not_ready_raises(ready_config: JudgeConfig) -> None:
    config = dataclasses.replace(ready_config, score_scale=PLACEHOLDER)

    with pytest.raises(JudgeNotReadyError, match="score_scale"):
        parse_response(good_reply(ready_config, "p1"), "p1", config)


# --- run_batch ----------------------------------------------------------------------------------------------------


def test_run_batch_sends_one_post_at_a_time_in_order_with_only_the_three_fields(
    ready_config: JudgeConfig, tmp_path: Path
) -> None:
    client = FakeClient(always_good(ready_config))

    run_batch(INVENTED_POSTS, client, ready_config, tmp_path / "scores.csv")

    assert [payload["post_id"] for payload in client.payloads] == ["p1", "p2", "p3"]
    assert all(set(payload) == {"post_id", "text", "rubric"} for payload in client.payloads)
    assert [payload["text"] for payload in client.payloads] == [text for _, text in INVENTED_POSTS]


def test_run_batch_returns_scored_posts_and_writes_ids_and_numbers(ready_config: JudgeConfig, tmp_path: Path) -> None:
    client = FakeClient(always_good(ready_config))
    output = tmp_path / "scores.csv"

    result = run_batch(INVENTED_POSTS, client, ready_config, output)

    assert isinstance(result, BatchResult)
    assert [scored.post_id for scored in result.scored] == ["p1", "p2", "p3"]
    assert result.failed == ()
    assert read_rows(output) == [["post_id", *ready_config.traits]] + [[pid, *["1"] * 5] for pid, _ in INVENTED_POSTS]


def test_a_failed_post_stays_missing_and_is_listed_by_id(ready_config: JudgeConfig, tmp_path: Path) -> None:
    def respond(payload: dict) -> str:
        if payload["post_id"] == "p2":
            return reply_with(ready_config, "p2", sociability=99)
        return good_reply(ready_config, payload["post_id"], (3, 3, 3, 3, 3))

    output = tmp_path / "scores.csv"

    result = run_batch(INVENTED_POSTS, FakeClient(respond), ready_config, output)

    assert [scored.post_id for scored in result.scored] == ["p1", "p3"]
    assert result.failed == (JudgeFailure("p2", "out_of_scale"),)
    rows = read_rows(output)
    assert rows[2] == ["p2", "", "", "", "", ""]
    assert rows[1][1:] == ["3"] * 5


def test_a_reply_for_the_wrong_post_is_a_failure_and_never_a_score(ready_config: JudgeConfig, tmp_path: Path) -> None:
    client = FakeClient(lambda payload: good_reply(ready_config, "p1"))

    result = run_batch(INVENTED_POSTS, client, ready_config, tmp_path / "scores.csv")

    assert [scored.post_id for scored in result.scored] == ["p1"]
    assert result.failed == (JudgeFailure("p2", "post_id_mismatch"), JudgeFailure("p3", "post_id_mismatch"))


def test_a_client_that_raises_leaves_that_post_missing_and_the_batch_goes_on(
    ready_config: JudgeConfig, tmp_path: Path
) -> None:
    def respond(payload: dict) -> str:
        if payload["post_id"] == "p1":
            raise TimeoutError(f"upstream said: {payload['text']}")
        return good_reply(ready_config, payload["post_id"])

    result = run_batch(INVENTED_POSTS, FakeClient(respond), ready_config, tmp_path / "scores.csv")

    assert result.failed == (JudgeFailure("p1", "client_error"),)
    assert [scored.post_id for scored in result.scored] == ["p2", "p3"]
    assert TEXT_MARKER not in repr(result)


def test_an_invalid_post_is_listed_and_never_sent(ready_config: JudgeConfig, tmp_path: Path) -> None:
    posts = (("p1", "An invented sentence."), ("p2", "   "), ("p3", "Another invented sentence."))
    client = FakeClient(always_good(ready_config))

    result = run_batch(posts, client, ready_config, tmp_path / "scores.csv")

    assert [payload["post_id"] for payload in client.payloads] == ["p1", "p3"]
    assert result.failed == (JudgeFailure("p2", "invalid_post"),)


def test_nothing_but_ids_and_numbers_reaches_the_output_file(ready_config: JudgeConfig, tmp_path: Path) -> None:
    def respond(payload: dict) -> str:
        if payload["post_id"] == "p3":
            return f"free text that repeats {TEXT_MARKER} and {TEST_RUBRIC}"
        return good_reply(ready_config, payload["post_id"], (1, 2, 3, 2, 1))

    output = tmp_path / "scores.csv"

    run_batch(INVENTED_POSTS, FakeClient(respond), ready_config, output)

    content = output.read_text(encoding="utf-8")
    rows = read_rows(output)
    assert TEXT_MARKER not in content
    assert TEST_RUBRIC not in content
    assert rows[0] == ["post_id", *ready_config.traits]
    for row in rows[1:]:
        assert row[0] in {"p1", "p2", "p3"}
        assert all(cell == "" or float(cell) in TEST_SCALE for cell in row[1:])


def test_only_the_output_file_is_written(ready_config: JudgeConfig, tmp_path: Path) -> None:
    run_batch(INVENTED_POSTS, FakeClient(always_good(ready_config)), ready_config, tmp_path / "scores.csv")

    assert [path.name for path in tmp_path.iterdir()] == ["scores.csv"]


def test_no_text_appears_in_any_log_line(
    ready_config: JudgeConfig, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def respond(payload: dict) -> str:
        if payload["post_id"] == "p1":
            raise TimeoutError(f"upstream echoed {payload['text']}")
        if payload["post_id"] == "p2":
            return f"not json, but it repeats {TEXT_MARKER}"
        return good_reply(ready_config, payload["post_id"])

    with caplog.at_level(logging.DEBUG):
        run_batch(INVENTED_POSTS, FakeClient(respond), ready_config, tmp_path / "scores.csv")

    assert caplog.records, "the batch should log a summary, so this test is not vacuous"
    assert TEXT_MARKER not in caplog.text
    assert TEST_RUBRIC not in caplog.text
    assert "croissants" not in caplog.text


@pytest.mark.parametrize(
    "change",
    [
        {"rubric_text": PLACEHOLDER},
        {"approved_to_run": False},
        {"provider_no_training": False},
        {"score_scale": PLACEHOLDER},
    ],
)
def test_a_config_that_is_not_ready_refuses_before_anything_is_sent_or_written(
    ready_config: JudgeConfig, tmp_path: Path, change: dict
) -> None:
    client = FakeClient(always_good(ready_config))
    output = tmp_path / "scores.csv"

    with pytest.raises(JudgeNotReadyError):
        run_batch(INVENTED_POSTS, client, dataclasses.replace(ready_config, **change), output)

    assert client.payloads == []
    assert not output.exists()


def test_the_shipped_config_refuses_a_whole_batch(tmp_path: Path) -> None:
    client = FakeClient(lambda payload: "never used")

    with pytest.raises(JudgeNotReadyError):
        run_batch(INVENTED_POSTS, client, load_judge_config(), tmp_path / "scores.csv")

    assert client.payloads == []


def test_duplicate_post_ids_are_refused_before_anything_is_sent(ready_config: JudgeConfig, tmp_path: Path) -> None:
    posts = (("p1", "An invented sentence."), ("p1", "Another invented sentence."))
    client = FakeClient(always_good(ready_config))

    with pytest.raises(ValueError, match="duplicate"):
        run_batch(posts, client, ready_config, tmp_path / "scores.csv")

    assert client.payloads == []


def test_an_empty_batch_writes_only_the_header(ready_config: JudgeConfig, tmp_path: Path) -> None:
    output = tmp_path / "scores.csv"

    result = run_batch((), FakeClient(always_good(ready_config)), ready_config, output)

    assert result == BatchResult(scored=(), failed=())
    assert read_rows(output) == [["post_id", *ready_config.traits]]


def test_a_batch_result_is_immutable(ready_config: JudgeConfig, tmp_path: Path) -> None:
    result = run_batch(INVENTED_POSTS, FakeClient(always_good(ready_config)), ready_config, tmp_path / "scores.csv")

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.failed = ()  # type: ignore[misc]
    assert isinstance(result.scored, tuple)


# --- the module itself --------------------------------------------------------------------------------------------


def test_the_module_imports_no_network_library_and_no_provider_sdk() -> None:
    tree = ast.parse(JUDGE_SOURCE_PATH.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])

    assert roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS)


def test_the_module_never_calls_print() -> None:
    tree = ast.parse(JUDGE_SOURCE_PATH.read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"]

    assert calls == []
