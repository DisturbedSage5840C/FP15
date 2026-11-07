"""Step B: which text features can be computed reliably from data already in data/raw? (`make extra-features`)

Applies the per-text rules in src.text_features to every raw post cell already on disk (no network, no
scraping), reports how common each feature is, and lists cells where a rule is known to handle the
text badly. Examples are cell refs plus leader ids; post text, names and links never reach the report.

Claim limit: the counts describe the text in the cells, not the person. They are cell-level because a
cell can still hold page chrome and several author blocks until segmentation exists.
"""
from __future__ import annotations

import logging
import math
import random
import statistics
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _pct, _table
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.text_features import TextFeatures, compute_features
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
DEFAULT_REPORT_PATH = Path("reports/extra_features.md")
REQUIRED_COLUMNS = ("leader", "workbook", "sheet_idx", "source_row", "post_text", "text_kind")
RAW_KIND = "raw"
NO_LEADER = "(no leader)"
LENGTH_PERCENTILE = 0.9
PAIR_SEPARATOR = "\t"

COUNT_FEATURES = (
    "hashtags", "numeric_hashtags", "mentions", "stray_at", "urls", "bare_domains", "question_marks",
    "question_runs", "emoji", "symbols", "devanagari_tokens", "roman_markers", "follow_lines",
)
FLAG_FEATURES = ("repost_line", "repost_phrase", "repost_word_in_text")


@dataclass(frozen=True)
class FeatureSettings:
    """Sampling settings read from configs/thresholds.yaml (none of them is a pass mark)."""

    examples_per_class: int
    seed: int


@dataclass(frozen=True)
class PrevalenceRow:
    """How many cells have a feature, and the typical amount among those that do."""

    feature: str
    cells: int
    share: float
    median: float | None


@dataclass(frozen=True)
class FailureClass:
    """A kind of text a rule is known to handle badly, with a threshold-free test for it."""

    name: str
    problem: str
    matches: Callable[[TextFeatures], bool]


FAILURE_CLASSES: tuple[FailureClass, ...] = (
    FailureClass(
        "length_several_blocks",
        "Two or more Follow lines mean the cell holds several author blocks, so its length is not one post's length.",
        lambda f: f.follow_lines >= 2,
    ),
    FailureClass(
        "hashtag_numeric_only",
        "A hashtag made only of digits (for example a ranking) is not a topic tag and is counted apart.",
        lambda f: f.numeric_hashtags > 0,
    ),
    FailureClass(
        "mention_stray_at",
        "An at-sign not followed by a name (a time, a place) is not a mention; mentions are also undercounted "
        "because copied text often drops the at-sign.",
        lambda f: f.stray_at > 0,
    ),
    FailureClass(
        "url_bare_domain",
        "A web address written without a scheme or www is only caught by the rough bare-domain rule, "
        "and the rule can also match a file name or an abbreviation.",
        lambda f: f.bare_domains > 0,
    ),
    FailureClass(
        "question_runs",
        "Runs such as ?? or ?! are counted as one run each, so the plain question-mark count mixes questions and emphasis.",
        lambda f: f.question_runs > 0,
    ),
    FailureClass(
        "emoji_symbol_only",
        "Arrows, ticks and similar text-style symbols are counted apart from emoji; whether they count as emoji is a choice.",
        lambda f: f.symbols > 0 and f.emoji == 0,
    ),
    FailureClass(
        "hinglish_borderline",
        "One or two romanised Hindi marker words and no Devanagari: some are English words too, so the share is unreliable.",
        lambda f: 1 <= f.roman_markers <= 2 and f.devanagari_tokens == 0,
    ),
    FailureClass(
        "repost_word_in_running_text",
        "The word reposted appears inside a sentence without a repost line, so it may be the writer's own wording.",
        lambda f: f.repost_word_in_text and not f.repost_line and not f.repost_phrase,
    ),
)


def load_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> FeatureSettings:
    """Read the two sampling keys; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keys = ("extra_features_examples_per_class", "extra_features_seed")
    for key in keys:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return FeatureSettings(*(int(values[key]) for key in keys))


def _row(feature: str, amounts: list[int], total: int, is_flag: bool) -> PrevalenceRow:
    have = [amount for amount in amounts if amount >= 1]
    median = None if is_flag or not have else float(statistics.median(have))
    return PrevalenceRow(feature, len(have), len(have) / total if total else 0.0, median)


def prevalence_rows(features: Sequence[TextFeatures]) -> list[PrevalenceRow]:
    """One row per count or flag feature: cells with at least one, their share, and the median among them."""
    total = len(features)
    rows = [_row(name, [int(getattr(item, name)) for item in features], total, False) for name in COUNT_FEATURES]
    rows += [_row(name, [int(getattr(item, name)) for item in features], total, True) for name in FLAG_FEATURES]
    return rows


def _percentile(sorted_values: list[int], fraction: float) -> int:
    return sorted_values[max(math.ceil(fraction * len(sorted_values)) - 1, 0)] if sorted_values else 0


def length_rows(features: Sequence[TextFeatures]) -> list[tuple[object, ...]]:
    """Median, 90th percentile and maximum of characters and words over all cells."""
    rows: list[tuple[object, ...]] = []
    for name in ("chars", "words"):
        values = sorted(int(getattr(item, name)) for item in features)
        median = _fmt(int(statistics.median(values))) if values else "n/a"
        rows.append((name, median, _fmt(_percentile(values, LENGTH_PERCENTILE)), _fmt(values[-1] if values else 0)))
    return rows


def pick_examples(items: Sequence[str], n: int, seed: int, label: str) -> list[str]:
    """At most n items, drawn from the sorted pool with a seed and a label, so the draw is repeatable."""
    pool = sorted(items)
    if len(pool) <= n:
        return pool
    return sorted(random.Random(f"{seed}:{label}").sample(pool, n))


def _read_posts(interim_dir: Path) -> pd.DataFrame:
    path = interim_dir / "harmonised_posts.csv"
    posts = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [name for name in REQUIRED_COLUMNS if name not in posts.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {', '.join(missing)}")
    return posts


def _cells(posts: pd.DataFrame) -> list[tuple[str, str, TextFeatures]]:
    """(cell ref, leader id, features) for every raw cell."""
    cells = []
    for row in posts[posts["text_kind"] == RAW_KIND].itertuples(index=False):
        key = name_key(row.leader)
        leader_id = leader_id_for(key) if key else NO_LEADER
        ref = f"{row.workbook}#{row.sheet_idx}:r{row.source_row}"
        cells.append((ref, leader_id, compute_features(row.post_text)))
    return cells


def _rule_rows() -> list[tuple[object, ...]]:
    return [
        ("Length (characters, words)", "Count of characters and whitespace-separated words after trimming.",
         "Computable now, but cell-level", "Reliable per post only after segmentation."),
        ("Hashtags", "A # followed by letters or digits, not glued to a word or inside a web address.",
         "Reliable now", "Digit-only tags are counted apart."),
        ("Mentions", "An at-sign followed directly by a name, outside web addresses and email addresses.",
         "Undercount", "Copied text often drops the at-sign; stray at-signs are counted apart."),
        ("Links", "A scheme address, a www address, or a known short-link host; bare domains are a rough extra count.",
         "Reliable for the first group", "Bare domains can match file names."),
        ("Question marks", "Count of the question mark outside web addresses; runs such as ?? are counted apart.",
         "Reliable now", "Does not separate questions from emphasis."),
        ("Emoji", "Pictographic characters, with flags, keycaps and joined sequences counted once each.",
         "Reliable for the pictographic core", "Arrows, ticks and similar symbols are reported apart."),
        ("Hinglish share", "Devanagari word tokens, plus romanised Hindi markers from a fixed word list.",
         "Devanagari reliable; romanised list unvalidated", "The word list needs mentor approval."),
        ("Repost vs own text", "Flags only: a line that is exactly Repost, an engagement phrase line, the word reposted.",
         "Not computable before segmentation", "Which part of a cell is the leader's own needs segmentation."),
    ]


def _prevalence_lines(rows: list[PrevalenceRow], total: int) -> list[str]:
    body = [
        (row.feature, _fmt(row.cells), _pct(row.cells, total), "" if row.median is None else f"{row.median:g}")
        for row in rows
    ]
    return _table(("Feature", "Cells with at least one", "Share of raw cells", "Median among those"), body)


def _class_lines(item: FailureClass, cells: list[tuple[str, str, TextFeatures]], settings: FeatureSettings) -> list[str]:
    pairs = [f"{ref}{PAIR_SEPARATOR}{leader_id}" for ref, leader_id, found in cells if item.matches(found)]
    picked = pick_examples(pairs, settings.examples_per_class, settings.seed, item.name)
    lines = [f"### {item.name}", "", item.problem, ""]
    lines += _table(("Measure", "Count"), [("Cells matching", _fmt(len(pairs))), ("Examples listed", _fmt(len(picked)))])
    lines += ["", *_table(("Cell", "Leader ID"), [tuple(pair.split(PAIR_SEPARATOR)) for pair in picked]), ""]
    return lines


def _decision_lines() -> list[str]:
    return [
        "## Needs a human decision",
        "",
        "- Approve, change or drop the romanised Hindi word list. It is an unvalidated proposal.",
        "- Decide whether text-style symbols (arrows, ticks) count as emoji.",
        "- Decide whether bare domains count as links.",
        "- Decide whether to wait for segmentation before using length or repost features in any analysis.",
    ]


def render_report(cells: list[tuple[str, str, TextFeatures]], settings: FeatureSettings) -> str:
    """Markdown with rules, counts, cell refs and leader ids only: no names, post text or links."""
    found = [item for _, _, item in cells]
    lines = [
        "# Extra text features",
        "",
        "Computed from raw post cells already in data/interim. Nothing was downloaded or scraped.",
        "The counts describe the text in a cell, not the person; any claim built on them is about the "
        "image projected in public posts.",
        "They are cell-level: a cell can still hold page chrome and several author blocks until segmentation exists.",
        "",
        "## Rules",
        "",
        *_table(("Feature", "Rule", "Verdict", "Caveat"), _rule_rows()),
        "",
        "## How common each feature is",
        "",
        *_table(("Measure", "Count"), [("Raw cells analysed", _fmt(len(cells)))]),
        "",
        *_prevalence_lines(prevalence_rows(found), len(cells)),
        "",
        *_table(("Length", "Median", "90th percentile", "Maximum"), length_rows(found)),
        "",
        "## Where the rules handle text badly",
        "",
        f"Up to {settings.examples_per_class} example cells per kind, drawn with seed {settings.seed}. "
        "Each is a cell ref and a leader id; open the cell in data/interim to read it.",
        "",
    ]
    for item in FAILURE_CLASSES:
        lines += _class_lines(item, cells, settings)
    return "\n".join(lines + _decision_lines()) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("wrote %s", path)


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    settings: FeatureSettings | None = None,
) -> int:
    """Verify the raw manifest, compute the features, write the report; 0 on success, 1 on a clean failure."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        active = settings or load_settings()
        posts = _read_posts(interim_dir)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("extra-features FAILED: %s", error)
        return 1
    _write(report_path, render_report(_cells(posts), active))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
