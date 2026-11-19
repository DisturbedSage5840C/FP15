"""Tests for the local G1 counting page (src/templates/segmentation_counter.html). Synthetic data only.

The page keeps its pure logic in one <script id="logic"> block that defines `Counter`; these tests run that block
under node (skipped when node is missing) and read the page text for the no-network and no-machine-count rules.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from src.segment import CHECK_COLUMNS
from src.segment_score import load_human_counts
from src.segment_viewer import TEMPLATE_PATH

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")
EXPORT_COLUMNS = ["n", "leader_id", "ref", "post_text", "human_post_count", "human_note"]
TRICKY_TEXT = 'Line one, with a comma\nLine "two" has quotes\r\n\nLast line after a blank one'
FAKE_ROWS = [
    ["1", "aaaa0000aaaa0000", "wb.xlsx#0:r2", TRICKY_TEXT, "", ""],
    ["2", "bbbb1111bbbb1111", "wb.xlsx#1:r2", "'=defused text", "", ""],
    ["3", "cccc2222cccc2222", "wb.xlsx#1:r3", "plain text", "", ""],
]


def _csv_text(header: list[str], rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _logic_source() -> str:
    match = re.search(r'<script id="logic">(.*?)</script>', TEMPLATE_PATH.read_text(encoding="utf-8"), re.S)
    assert match, 'the page needs one <script id="logic"> block'
    return match.group(1)


def _js(call: str, tmp_path: Path) -> Any:
    """Run one JS expression that uses `Counter`; its value comes back as parsed JSON."""
    assert NODE is not None
    script = tmp_path / "logic_test.js"
    script.write_text(f"{_logic_source()}\nconsole.log(JSON.stringify({call}));\n", encoding="utf-8")
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(done.stdout)


def _sheet_js(rows: list[list[str]] | None = None) -> str:
    text = _csv_text(CHECK_COLUMNS, rows if rows is not None else FAKE_ROWS)
    return f"Counter.readSheet({json.dumps(text)})"


def _filled(counts: dict[str, str], notes: dict[str, str] | None = None) -> dict[str, dict[str, str]]:
    return {n: {"count": value, "note": (notes or {}).get(n, "")} for n, value in counts.items()}


def _export(tmp_path: Path, progress: dict[str, dict[str, str]]) -> Any:
    return _js(f"Counter.buildExport({_sheet_js()}.rows, {json.dumps(progress)})", tmp_path)


# ---- the page text: no network, no machine count ------------------------------------------------


def test_the_page_makes_no_network_request_and_names_no_external_address() -> None:
    page = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert not re.search(r"https?://|//[a-z0-9.-]+\.[a-z]{2,}", page, re.I), "external address in the page"
    assert not re.search(r"<link\b|@import|<script[^>]*\bsrc=|<img[^>]*\bsrc=\s*[\"'](?!data:)", page, re.I)
    for api in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "EventSource", "import("):
        assert api not in page, api


def test_the_page_forbids_every_connection_in_its_security_policy() -> None:
    page = TEMPLATE_PATH.read_text(encoding="utf-8")

    policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', page)
    assert policy, "the page needs a Content-Security-Policy meta tag"
    assert "default-src 'none'" in policy.group(1)
    assert "connect-src 'none'" in policy.group(1)


def test_the_page_neither_shows_nor_computes_a_segmenter_count() -> None:
    page = TEMPLATE_PATH.read_text(encoding="utf-8").lower()

    assert not any(word in page for word in ("segmenter", "machine", "segment_cell", "segmentation_score"))


def test_post_text_is_put_on_the_page_as_text_never_as_markup() -> None:
    page = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "innerHTML" not in page
    assert "insertAdjacentHTML" not in page
    assert "document.write" not in page


# ---- csv reading and writing --------------------------------------------------------------------


@needs_node
def test_a_quoted_cell_with_commas_quotes_and_line_breaks_is_read_back_exactly(tmp_path: Path) -> None:
    sheet = _js(_sheet_js(), tmp_path)

    assert sheet["ok"] is True
    assert sheet["rows"][0]["post_text"] == TRICKY_TEXT
    assert [row["n"] for row in sheet["rows"]] == ["1", "2", "3"]


@needs_node
def test_a_sheet_with_the_wrong_columns_is_refused_with_the_missing_names(tmp_path: Path) -> None:
    text = _csv_text(["n", "ref"], [["1", "x"]])

    result = _js(f"Counter.readSheet({json.dumps(text)})", tmp_path)

    assert result["ok"] is False
    assert "leader_id" in result["message"]


@needs_node
def test_a_byte_order_mark_and_windows_line_endings_do_not_break_reading(tmp_path: Path) -> None:
    text = "\ufeff" + _csv_text(CHECK_COLUMNS, FAKE_ROWS[1:]).replace("\n", "\r\n")

    result = _js(f"Counter.readSheet({json.dumps(text)})", tmp_path)

    assert result["ok"] is True
    assert len(result["rows"]) == 2


@needs_node
def test_the_names_file_is_joined_by_n_and_an_unmatched_n_is_an_error(tmp_path: Path) -> None:
    header = ["n", "leader_name", "company_name"]
    good = _csv_text(header, [["1", "A One", "F One"], ["2", "B Two", ""], ["3", "C", "D"]])
    short = _csv_text(header, [["1", "A One", "F One"]])

    joined = _js(f"Counter.joinNames({_sheet_js()}.rows, Counter.readNames({json.dumps(good)}).rows)", tmp_path)
    broken = _js(f"Counter.joinNames({_sheet_js()}.rows, Counter.readNames({json.dumps(short)}).rows)", tmp_path)

    assert joined["ok"] is True and joined["byN"]["2"] == {"leader_name": "B Two", "company_name": ""}
    assert broken["ok"] is False
    assert "2" in broken["message"]


# ---- integer validation -------------------------------------------------------------------------


@needs_node
@pytest.mark.parametrize("raw", ["0", "1", "12", " 3 ", "007"])
def test_a_whole_number_is_accepted(tmp_path: Path, raw: str) -> None:
    result = _js(f"Counter.validateCount({json.dumps(raw)})", tmp_path)

    assert result["ok"] is True
    assert result["value"] == str(int(raw))


@needs_node
@pytest.mark.parametrize("raw", ["", "  ", "2.5", "-1", "+2", "1e2", "two", "3 posts", "1,5", "٣", "0x10"])
def test_a_blank_decimal_negative_or_text_count_is_refused(tmp_path: Path, raw: str) -> None:
    result = _js(f"Counter.validateCount({json.dumps(raw)})", tmp_path)

    assert result["ok"] is False


# ---- export -------------------------------------------------------------------------------------


@needs_node
def test_export_has_exactly_the_live_sheet_columns_in_order(tmp_path: Path) -> None:
    result = _export(tmp_path, _filled({"1": "2", "2": "1", "3": "4"}, {"2": "reposted, one post"}))

    assert result["ok"] is True
    header = next(csv.reader(io.StringIO(result["csv"])))
    assert header == EXPORT_COLUMNS == CHECK_COLUMNS


@needs_node
def test_export_keeps_every_other_column_unchanged_and_adds_counts_and_notes(tmp_path: Path) -> None:
    result = _export(tmp_path, _filled({"1": "2", "2": "1", "3": "4"}, {"2": 'a note, with "quotes"'}))

    rows = list(csv.reader(io.StringIO(result["csv"], newline="")))[1:]
    assert [row[:4] for row in rows] == [row[:4] for row in FAKE_ROWS]
    assert [row[4] for row in rows] == ["2", "1", "4"]
    assert [row[5] for row in rows] == ["", 'a note, with "quotes"', ""]


@needs_node
def test_export_refuses_a_blank_count_and_names_the_cell(tmp_path: Path) -> None:
    result = _export(tmp_path, _filled({"1": "2", "3": "4"}))

    assert result["ok"] is False
    assert [problem["n"] for problem in result["problems"]] == ["2"]
    assert "2" in result["message"]
    assert "csv" not in result


@needs_node
def test_export_refuses_a_non_integer_count_and_names_every_bad_cell(tmp_path: Path) -> None:
    result = _export(tmp_path, _filled({"1": "2.5", "2": "1", "3": "three"}))

    assert result["ok"] is False
    assert [problem["n"] for problem in result["problems"]] == ["1", "3"]
    assert "1" in result["message"] and "3" in result["message"]


@needs_node
def test_the_exported_file_is_read_by_the_scorer_loader_and_keeps_the_refs(tmp_path: Path) -> None:
    result = _export(tmp_path, _filled({"1": "2", "2": "0", "3": "10"}))
    counted = tmp_path / "segmentation_check_200_counted.csv"
    counted.write_text(result["csv"], encoding="utf-8", newline="")

    loaded = load_human_counts(counted)

    assert [(row.n, row.ref, row.count) for row in loaded] == [
        (1, "wb.xlsx#0:r2", 2),
        (2, "wb.xlsx#1:r2", 0),
        (3, "wb.xlsx#1:r3", 10),
    ]


@needs_node
def test_progress_counts_only_valid_whole_numbers(tmp_path: Path) -> None:
    progress = _filled({"1": "2", "2": "x", "3": ""})

    done = _js(f"Counter.countDone({_sheet_js()}.rows, {json.dumps(progress)})", tmp_path)

    assert done == 1


@needs_node
def test_the_progress_key_changes_when_the_sheet_changes(tmp_path: Path) -> None:
    first = _js(f"Counter.fingerprint({_sheet_js()}.rows)", tmp_path)
    same = _js(f"Counter.fingerprint({_sheet_js()}.rows)", tmp_path)
    other = _js(f"Counter.fingerprint({_sheet_js(FAKE_ROWS[:2])}.rows)", tmp_path)

    assert first == same
    assert first != other
    assert "wb.xlsx" not in first


@needs_node
def test_saved_progress_keeps_only_known_cells_with_text_fields(tmp_path: Path) -> None:
    saved = {"1": {"count": "2", "note": "ok"}, "99": {"count": "5", "note": ""}, "2": {"count": 7, "note": None}, "3": "x"}

    cleaned = _js(f"Counter.cleanProgress({json.dumps(saved)}, {_sheet_js()}.rows)", tmp_path)
    nothing = _js(f"Counter.cleanProgress('not an object', {_sheet_js()}.rows)", tmp_path)

    assert cleaned == {"1": {"count": "2", "note": "ok"}}
    assert nothing == {}
