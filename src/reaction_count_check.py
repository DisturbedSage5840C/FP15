"""Step A: what does a number at the end of a raw post look like? (`make reaction-check`)

Reads the harmonised posts already on disk (no network, no scraping), classifies every raw cell by the
shape of its trailing number, and draws a small sample for a human to compare by hand against the
post on LinkedIn. One sample row is one raw post cell, with one cell per leader.

Claim limit: this stage never says what the number means. It counts patterns and writes the sample.
The number is never parsed into a column; `last_line` is the verbatim last line, as a reading aid.
The report holds counts and rules only; the sample file (git-ignored) holds ids, links and refs.
"""
from __future__ import annotations

import logging
import random
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.harmonise import DEFAULT_INTERIM_DIR
from src.harmonise_report import _fmt, _table
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
DEFAULT_REPORT_PATH = Path("reports/reaction_count_check.md")
DEFAULT_SAMPLE_PATH = Path("data/derived/reaction_sample.csv")
REQUIRED_COLUMNS = ("leader", "workbook", "sheet_idx", "source_row", "post_text", "link", "text_kind")
SAMPLE_COLUMNS = ["n", "group", "leader_id", "link", "ref", "last_line"]
RAW_KIND, CLEANED_KIND = "raw", "cleaned"
OWN_LINE, CONTROL = "number_on_own_line", "control_no_number"
YEAR_MIN, YEAR_MAX = 1900, 2035
YEAR_DIGITS = 4

_NUMBER_AT_END = re.compile(r"(\d[\d,]*(?:\.\d+)?[KkMm]?)$")
_AGE_FRAGMENT = r"\d{1,3}(?:yr|mo|w|d|h)"
_AGE_LINE = re.compile(_AGE_FRAGMENT)
_AGE_AT_END = re.compile(rf"(?<![\w.]){_AGE_FRAGMENT}$")
_PLAIN_YEAR = re.compile(rf"\d{{{YEAR_DIGITS}}}")
_SUFFIXED = re.compile(r"[KkMm]$")


@dataclass(frozen=True)
class CheckSettings:
    """Sampling settings read from configs/thresholds.yaml (none of them is a pass mark)."""

    n_number_on_own_line: int
    n_control: int
    seed: int


@dataclass(frozen=True)
class TrailingNumber:
    """Shape of the number a text ends in. The value itself is deliberately not kept."""

    position: str
    year_like: bool
    age_before_number: bool
    has_suffix: bool


@dataclass(frozen=True)
class TrailingCounts:
    cells: int
    ends_in_number: int
    own_line: int
    in_hashtag: int
    after_space: int
    glued_to_word: int
    after_punct: int
    year_like: int
    year_like_own_line: int
    age_before_number: int
    ends_in_age_token: int
    with_suffix: int


def load_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> CheckSettings:
    """Read the three sampling keys; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keys = ("reaction_check_number_on_own_line", "reaction_check_control", "reaction_check_seed")
    for key in keys:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return CheckSettings(*(int(values[key]) for key in keys))


def _position(stripped: str, token: str) -> str:
    before = stripped[: len(stripped) - len(token)]
    last_line = stripped.rsplit("\n", 1)[-1]
    if stripped.split()[-1].startswith("#"):
        return "in_hashtag"
    if not before or last_line.strip() == token:
        return "own_line"
    previous = before[-1]
    if previous.isspace():
        return "after_space"
    return "glued_to_word" if previous.isalnum() or previous == "_" else "after_punct"


def _year_like(token: str) -> bool:
    return bool(_PLAIN_YEAR.fullmatch(token)) and YEAR_MIN <= int(token) <= YEAR_MAX


def _age_line_before(stripped: str) -> bool:
    """True when the nearest non-blank line above the final line is a relative age such as 5yr."""
    lines = [line.strip() for line in stripped.split("\n")]
    above = [line for line in lines[:-1] if line]
    return bool(above) and _AGE_LINE.fullmatch(above[-1]) is not None


def find_trailing_number(text: str) -> TrailingNumber | None:
    """Describe the number the text ends in, or None when it does not end in a digit-led token."""
    stripped = text.strip()
    found = _NUMBER_AT_END.search(stripped)
    if found is None:
        return None
    token = found.group(1)
    position = _position(stripped, token)
    return TrailingNumber(
        position=position,
        year_like=_year_like(token),
        age_before_number=position == "own_line" and _age_line_before(stripped),
        has_suffix=_SUFFIXED.search(token) is not None,
    )


def ends_in_age_token(text: str) -> bool:
    """True when the text ends in a relative-age token such as 5yr, 3mo, 2w, 1d or 4h."""
    return _AGE_AT_END.search(text.strip()) is not None


def count_trailing(texts: Iterable[str]) -> TrailingCounts:
    """Tally trailing-number shapes over a collection of texts."""
    all_texts = list(texts)
    hits = [shape for shape in map(find_trailing_number, all_texts) if shape is not None]

    def at(name: str) -> int:
        return sum(1 for shape in hits if shape.position == name)

    return TrailingCounts(
        cells=len(all_texts),
        ends_in_number=len(hits),
        own_line=at("own_line"),
        in_hashtag=at("in_hashtag"),
        after_space=at("after_space"),
        glued_to_word=at("glued_to_word"),
        after_punct=at("after_punct"),
        year_like=sum(1 for shape in hits if shape.year_like),
        year_like_own_line=sum(1 for shape in hits if shape.year_like and shape.position == "own_line"),
        age_before_number=sum(1 for shape in hits if shape.age_before_number),
        ends_in_age_token=sum(1 for text in all_texts if ends_in_age_token(text)),
        with_suffix=sum(1 for shape in hits if shape.has_suffix),
    )


def _draw_leaders(frame: pd.DataFrame, group: str, count: int, taken: set[str], rng: random.Random) -> list[str]:
    pool = sorted(set(frame.loc[frame["group"] == group, "leader_key"]) - taken)
    return sorted(rng.sample(pool, min(count, len(pool))))


def select_sample(frame: pd.DataFrame, n_own_line: int, n_control: int, seed: int) -> pd.DataFrame:
    """One cell per leader: `n_own_line` from the own-line group, then `n_control` from the control group.

    Leaders and cells are drawn from sorted pools, so the result depends on the seed and the data only,
    never on row order. A group with fewer leaders than asked returns what it has.
    """
    ordered = frame.sort_values(["leader_key", "ref"], kind="stable").reset_index(drop=True)
    rng = random.Random(seed)
    chosen: list[tuple[str, str]] = []
    taken: set[str] = set()
    for group, count in ((OWN_LINE, n_own_line), (CONTROL, n_control)):
        leaders = _draw_leaders(ordered, group, count, taken, rng)
        taken.update(leaders)
        chosen.extend((group, leader) for leader in leaders)
    rows = []
    for group, leader in chosen:
        cells = ordered[(ordered["group"] == group) & (ordered["leader_key"] == leader)]
        rows.append(cells.iloc[rng.randrange(len(cells))])
    return pd.DataFrame(rows, columns=ordered.columns).reset_index(drop=True)


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.strip().split("\n")]
    return lines[-1] if lines else ""


def _group_of(text: str) -> str:
    shape = find_trailing_number(text)
    if shape is None:
        return CONTROL
    return OWN_LINE if shape.position == "own_line" else ""


def _eligible_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Raw cells with a link and a leader key, tagged own-line or control (other endings are left out)."""
    rows = []
    for row in raw.itertuples(index=False):
        key, group = name_key(row.leader), _group_of(row.post_text)
        if key and row.link and group:
            ref = f"{row.workbook}#{row.sheet_idx}:r{row.source_row}"
            rows.append((key, group, ref, row.link, _last_line(row.post_text)))
    return pd.DataFrame(rows, columns=["leader_key", "group", "ref", "link", "last_line"])


def _sample_frame(chosen: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "n": range(1, len(chosen) + 1),
            "group": chosen["group"].to_list(),
            "leader_id": [leader_id_for(key) for key in chosen["leader_key"]],
            "link": chosen["link"].to_list(),
            "ref": chosen["ref"].to_list(),
            "last_line": chosen["last_line"].to_list(),
        }
    )
    return out[SAMPLE_COLUMNS]


def _read_posts(interim_dir: Path) -> pd.DataFrame:
    path = interim_dir / "harmonised_posts.csv"
    posts = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [name for name in REQUIRED_COLUMNS if name not in posts.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {', '.join(missing)}")
    return posts


def _rule_lines(settings: CheckSettings) -> list[str]:
    return [
        "## Pairing rules",
        "",
        "- A cell is one raw post cell (text_kind = raw). Cleaned cells are only counted for comparison.",
        "- Ends in a number: the text, after trimming blanks, ends in a digit-led token "
        "(digits, thousand commas, one decimal part, optional K or M).",
        "- Alone on its own line: the last line holds only that token.",
        "- In a hashtag: the last word starts with #.",
        "- After a space, glued to a word, after punctuation: what sits right before the token.",
        f"- Year-like: exactly {YEAR_DIGITS} plain digits between {YEAR_MIN} and {YEAR_MAX}.",
        "- Relative-age line: the nearest non-blank line above the number is a token like 5yr, 3mo, 2w, 1d or 4h.",
        "- Relative-age token at the end: the text itself ends in such a token.",
        "",
        "## Sample",
        "",
        "- Eligible: has a post link and a leader name (sample only; the counts above use all raw cells).",
        f"- Groups: {settings.n_number_on_own_line} with the number alone on its own line, "
        f"{settings.n_control} that do not end in a number (control).",
        "- Sample: one cell per leader; each leader appears once.",
        f"- Seed: {settings.seed}",
        "- The sample file is git-ignored. It holds leader ids, links and refs, and no parsed number.",
        "- This report does not decide what the number means. A human compares the sample with LinkedIn.",
    ]


def _count_rows(counts: TrailingCounts, cleaned: TrailingCounts) -> list[tuple[object, ...]]:
    return [
        ("Raw cells", _fmt(counts.cells)),
        ("End in a number", _fmt(counts.ends_in_number)),
        ("Number alone on its own line", _fmt(counts.own_line)),
        ("Number inside a hashtag", _fmt(counts.in_hashtag)),
        ("Number after a space on the same line", _fmt(counts.after_space)),
        ("Number glued to a word", _fmt(counts.glued_to_word)),
        ("Number after punctuation", _fmt(counts.after_punct)),
        (f"Year-like ({YEAR_DIGITS} digits, {YEAR_MIN} to {YEAR_MAX})", _fmt(counts.year_like)),
        ("Year-like and alone on its own line", _fmt(counts.year_like_own_line)),
        ("Relative-age line right before the number (like 5yr)", _fmt(counts.age_before_number)),
        ("Text ends in a relative-age token (like 5yr)", _fmt(counts.ends_in_age_token)),
        ("Number with a K or M suffix", _fmt(counts.with_suffix)),
        ("Cleaned cells that end in a number", f"{_fmt(cleaned.ends_in_number)} of {_fmt(cleaned.cells)}"),
    ]


def render_report(
    counts: TrailingCounts,
    cleaned: TrailingCounts,
    frame: pd.DataFrame,
    drawn: pd.DataFrame,
    settings: CheckSettings,
) -> str:
    """Markdown with counts and rules only: no names, post text or links."""
    own = frame[frame["group"] == OWN_LINE]
    control = frame[frame["group"] == CONTROL]
    frame_rows = [
        ("Own-line cells with a link", _fmt(len(own))),
        ("Leaders with such a cell", _fmt(own["leader_key"].nunique())),
        ("Cells with a link that do not end in a number", _fmt(len(control))),
        ("Leaders with such a cell (control)", _fmt(control["leader_key"].nunique())),
        ("Drawn: number alone on its own line", _fmt(int((drawn["group"] == OWN_LINE).sum()))),
        ("Drawn: control", _fmt(int((drawn["group"] == CONTROL).sum()))),
    ]
    lines = ["# Reaction-count check", "", "Counts from raw post cells already in data/interim. Nothing was downloaded.", ""]
    lines += _table(("Measure", "Count"), _count_rows(counts, cleaned))
    lines += ["", "## Sampling frame", ""]
    lines += _table(("Measure", "Count"), frame_rows)
    lines += [""] + _rule_lines(settings)
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("wrote %s", path)


def _counts_for(posts: pd.DataFrame, kind: str) -> TrailingCounts:
    return count_trailing(posts.loc[posts["text_kind"] == kind, "post_text"])


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    sample_path: Path = DEFAULT_SAMPLE_PATH,
    settings: CheckSettings | None = None,
) -> int:
    """Verify the raw manifest, classify trailing numbers, write the report and the sample; 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        active = settings or load_settings()
        posts = _read_posts(interim_dir)
    except (ManifestMismatch, FileNotFoundError, ValueError) as error:
        logger.error("reaction-check FAILED: %s", error)
        return 1
    frame = _eligible_frame(posts[posts["text_kind"] == RAW_KIND])
    chosen = select_sample(frame, active.n_number_on_own_line, active.n_control, active.seed)
    report = render_report(_counts_for(posts, RAW_KIND), _counts_for(posts, CLEANED_KIND), frame, chosen, active)
    _write(report_path, report)
    sample = _sample_frame(chosen)
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(sample_path, index=False)
    logger.info("wrote %s (%d rows)", sample_path, len(sample))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
