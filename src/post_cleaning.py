"""Clean the raw post cells into a new table and report counts only (`make post-cleaning`).

For every raw cell (after dropping exact duplicate cells within a leader) this writes one row to the git-ignored
data/interim/posts_clean.csv: the leader_id (never the name), the cell reference, the text with applied interface
lines removed (a NEW column; the raw text is never changed), the post age in months, the reaction count when the
Step A check is confirmed (otherwise "unverified") and a script-based language flag.

It does NOT run the segmenter over all cells. That waits for the human to confirm the 200-cell sample.
The committed report holds counts and rule names only. Frequent unclassified lines (candidates for new rules)
go to a git-ignored file because they may quote post text.
"""
from __future__ import annotations

import logging
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.post_fields import LANGUAGE_FLAGS, LANGUAGE_KEYS, LanguageSettings, age_months, language_flag, load_language_settings
from src.post_interface import (
    ALL_RULES,
    LinePattern,
    classify_line,
    clean_text,
    line_frequencies,
    rule_counts,
)
from src.reaction_count_check import RAW_KIND, _read_posts, find_trailing_number, spreadsheet_safe
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
DEFAULT_REPORT_PATH = Path("reports/post_cleaning.md")
DEFAULT_CLEAN_PATH = Path("data/interim/posts_clean.csv")
DEFAULT_CANDIDATES_PATH = Path("data/derived/interface_candidates.csv")
CLEAN_COLUMNS = [
    "leader_id", "workbook", "sheet_idx", "source_row",
    "post_text_clean", "age_months", "reaction_status", "reaction_count", "language",
]
PARSED = "parsed"
UNVERIFIED = "unverified"
_COUNT_LINE = re.compile(r"^\d{1,3}(,\d{3})+$|^\d+$")
_SETTING_KEYS = (*LANGUAGE_KEYS, "interface_min_leaders", "reaction_check_confirmed")


@dataclass(frozen=True)
class CleaningSettings:
    """Settings read from configs/thresholds.yaml."""

    language: LanguageSettings
    interface_min_leaders: int
    reaction_check_confirmed: bool


def load_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> CleaningSettings:
    """Read the cleaning settings; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in _SETTING_KEYS:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return CleaningSettings(
        language=load_language_settings(path),
        interface_min_leaders=int(values["interface_min_leaders"]),
        reaction_check_confirmed=bool(values["reaction_check_confirmed"]),
    )


def drop_exact_duplicates(posts: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep the first of each identical (leader, text) pair; return the kept rows and how many were dropped."""
    keys = posts["leader"].map(name_key)
    duplicated = pd.Series(list(zip(keys, posts["post_text"])), index=posts.index).duplicated()
    return posts[~duplicated].reset_index(drop=True), int(duplicated.sum())


def _eligible_shape(text: str) -> bool:
    """True when the text ends in a plain number alone on its own line (no year, suffix or age line)."""
    shape = find_trailing_number(text)
    return (
        shape is not None
        and shape.position == "own_line"
        and not shape.year_like
        and not shape.has_suffix
        and not shape.age_before_number
    )


def parse_reaction(text: str, settings: CleaningSettings) -> tuple[str, str]:
    """(status, count). A count is read only when the human check is confirmed and the shape is eligible."""
    if not settings.reaction_check_confirmed or not _eligible_shape(text):
        return UNVERIFIED, ""
    last_line = text.strip().rsplit("\n", 1)[-1].strip()
    if not _COUNT_LINE.match(last_line):
        return UNVERIFIED, ""
    return PARSED, last_line.replace(",", "")


def unclassified_patterns(cells: Iterable[tuple[str, str]], min_leaders: int) -> list[LinePattern]:
    """Frequent lines that no interface rule covers: candidates for new rules."""
    unmatched = [
        (leader, "\n".join(line for line in text.split("\n") if classify_line(line) is None))
        for leader, text in cells
    ]
    return line_frequencies(unmatched, min_leaders)


def build_clean_frame(cells: pd.DataFrame, settings: CleaningSettings) -> pd.DataFrame:
    """One row per raw cell with the new columns. The raw text is not carried over."""
    rows = []
    for row in cells.itertuples(index=False):
        cleaned = clean_text(row.post_text)
        age = age_months(row.post_text)
        status, count = parse_reaction(row.post_text, settings)
        rows.append(
            (
                leader_id_for(name_key(row.leader)),
                row.workbook,
                row.sheet_idx,
                row.source_row,
                cleaned,
                "" if age is None else str(age),
                status,
                count,
                language_flag(cleaned, settings.language),
            )
        )
    return pd.DataFrame(rows, columns=CLEAN_COLUMNS)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("wrote %s", path)


def render_report(
    cells: int,
    removed: int,
    rule_table: Mapping[str, tuple[int, int]],
    applied: set[str],
    unclassified: int,
    age_parsed: int,
    languages: Mapping[str, int],
    reaction_shape: Mapping[str, int],
    reaction_confirmed: bool,
    language_settings: LanguageSettings,
) -> str:
    """The counts-only report. Names rules, never lines of post text."""
    status = "confirmed" if reaction_confirmed else "not confirmed"
    lines = [
        "# Post cleaning (counts only)",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Raw cells after removing exact duplicates | {cells} |",
        f"| Exact duplicate cells removed within a leader | {removed} |",
        f"| Cells with a relative age parsed to months | {age_parsed} |",
        f"| Frequent lines no rule covers (see the git-ignored candidates file) | {unclassified} |",
        "",
        "Exact means the same text for the same leader. The harmonise step already collapsed certain duplicates",
        "(identical, prefix, same post URL with a trailing number) and kept every other row flagged, so the count",
        "here is a lower bound on repeated content.",
        "",
        "## Interface-line rules",
        "",
        "Applied rules write the new column `post_text_clean` only. Proposed rules are counted, not applied.",
        "",
        "| Rule | Status | Lines | Cells |",
        "|---|---|---|---|",
        *[
            f"| {name} | {'applied' if name in applied else 'proposed'} | {n_lines} | {n_cells} |"
            for name, (n_lines, n_cells) in rule_table.items()
        ],
        "",
        "## Age",
        "",
        "Relative age (for example 5yr, 3mo) is turned into months as a number. It is not turned into a date: the",
        "scrape date is unknown.",
        "",
        "## Language flag",
        "",
        f"Method: script-based. Devanagari and Latin letters are counted; fewer than {language_settings.min_letters}",
        f"letters gives `other`; a minor script above {language_settings.minor_share:.0%} of letters gives `mixed`.",
        "",
        "Possible Hinglish (Hindi written in Latin letters): a cell that is mostly Latin letters is flagged",
        f"`Hinglish` when at least {language_settings.hinglish_min_hits} of its Latin-letter words, and at least "
        f"{language_settings.hinglish_min_share:.0%} of them, are on a list of common romanised Hindi function words",
        "(src/hinglish.py). The list holds pronouns, particles, postpositions, auxiliaries, conjunctions and question",
        "words only, no names and no post text. Words that are also common English words are left off, so some",
        "Hinglish is missed. The flag is a counting rule, not a reading of the text.",
        "",
        "| Flag | Cells |",
        "|---|---|",
        *[f"| {flag} | {languages.get(flag, 0)} |" for flag in LANGUAGE_FLAGS],
        "",
        "## Reaction count",
        "",
        "| Measure | Cells |",
        "|---|---|",
        f"| Cells ending in a number | {reaction_shape['total']} |",
        "| Of those, shape eligible (number alone on its own line, not year-like, no suffix, no age line) | "
        f"{reaction_shape['own_line']} |",
        "",
        f"The Step A human comparison is {status} (`reaction_check_confirmed` in configs/thresholds.yaml). "
        "Until it is confirmed every row is marked `unverified` and no count is read.",
        "",
        "## Segmentation",
        "",
        "The segmenter is written and tested but was not run on all cells. It waits for the human to confirm the "
        "200-cell sample.",
        "",
    ]
    return "\n".join(lines)


def _report_inputs(cells: pd.DataFrame, clean: pd.DataFrame, settings: CleaningSettings) -> dict[str, object]:
    texts = cells["post_text"].to_list()
    keyed = list(zip(cells["leader"].map(name_key), texts))
    counts = rule_counts(texts)
    return {
        "rule_table": {rule.name: counts[rule.name] for rule in ALL_RULES},
        "applied": {rule.name for rule in ALL_RULES if rule.applied},
        "unclassified": len(unclassified_patterns(keyed, settings.interface_min_leaders)),
        "age_parsed": int((clean["age_months"] != "").sum()),
        "languages": dict(Counter(clean["language"])),
        "reaction_shape": {
            "total": sum(find_trailing_number(text) is not None for text in texts),
            "own_line": sum(_eligible_shape(text) for text in texts),
        },
        "reaction_confirmed": settings.reaction_check_confirmed,
        "language_settings": settings.language,
    }


def _candidates_frame(cells: pd.DataFrame, min_leaders: int) -> pd.DataFrame:
    """Frequent unclassified lines for a human to read in a spreadsheet, so formula-like text is defused.

    posts_clean.csv is not defused: it feeds the analysis, and a leading quote would change the text measured.
    """
    keyed = list(zip(cells["leader"].map(name_key), cells["post_text"]))
    found = unclassified_patterns(keyed, min_leaders)
    rows = [(spreadsheet_safe(p.pattern), p.lines, p.leaders) for p in found]
    return pd.DataFrame(rows, columns=["pattern", "lines", "leaders"])


def _raw_cells(posts: pd.DataFrame) -> pd.DataFrame:
    raw = posts[posts["text_kind"] == RAW_KIND]
    usable = raw[raw["leader"].map(name_key).astype(bool) & raw["post_text"].str.strip().astype(bool)]
    return usable.reset_index(drop=True)


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    clean_path: Path = DEFAULT_CLEAN_PATH,
    candidates_path: Path = DEFAULT_CANDIDATES_PATH,
    settings: CleaningSettings | None = None,
) -> int:
    """Verify the raw manifest, clean the raw cells, write the table, candidates and report; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        active = settings or load_settings()
        cells, removed = drop_exact_duplicates(_raw_cells(_read_posts(interim_dir)))
        clean = build_clean_frame(cells, active)
        report = render_report(len(cells), removed, **_report_inputs(cells, clean, active))  # type: ignore[arg-type]
        candidates = _candidates_frame(cells, active.interface_min_leaders)
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("post-cleaning FAILED: %s", error)
        return 1
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(clean_path, index=False)
    logger.info("wrote %s (%d rows)", clean_path, len(clean))
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(candidates_path, index=False)
    _write(report_path, report)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
