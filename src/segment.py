"""Split a raw post cell into single posts, and draw the blind sample a human counts by hand (`make segmentation-sample`).

A raw cell is the text copied from the feed. Each post in it opens with a header: the author's name line
followed by a connection marker line such as "• 3rd+". The segmenter starts a new post at each header.
Counting convention (to be settled by the human check): a repost or an embedded post is one post by the
leader, never a second post. Given the leader's name key, a header whose name line is not the leader's is
embedded: it and everything up to the leader's next header belong to the leader's post, flagged
`is_repost`, and its lines go to `embedded_text`, never to the leader-voice `text`. A header whose name is
the leader's opens a new post. A cell with no header by the leader is one post with an empty leader voice.
Without a leader key every header opens a post (nothing is flagged). A cell with no recognised marker is
one post and is flagged `found_header = False`. Text before the first header stays with the first post.

This module only writes the sample. It does not score it (see src.segment_score) and it does not run the
segmenter over all cells; the sample has no machine count in it, so the human count is blind.
"""
from __future__ import annotations

import logging
import random
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from src.harmonise import DEFAULT_INTERIM_DIR
from src.id_key import MissingIdKey
from src.id_matching import leader_id_for
from src.name_key import name_key
from src.post_interface import classify_line
from src.reaction_count_check import RAW_KIND, _read_posts, spreadsheet_safe
from src.verify_raw import DEFAULT_RAW_DIR, ManifestMismatch
from src.verify_raw import run as verify_raw

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
DEFAULT_SAMPLE_PATH = Path("data/derived/segmentation_check_200.csv")
CONNECTION_MARKER_RULE = "connection_marker"
REPOST_NOTICE = re.compile(r"^.+\s+reposted this$", re.IGNORECASE)
CHECK_COLUMNS = ["n", "leader_id", "ref", "post_text", "human_post_count", "human_note"]
FRAME_COLUMNS = ["leader_key", "ref", "text"]


@dataclass(frozen=True)
class Segment:
    """One post by the leader: its first line number, the leader's own lines, and any embedded lines.

    `text` is the leader's voice only. `embedded_text` holds the reposted or embedded post, kept apart.
    """

    start_line: int
    text: str
    embedded_text: str = ""
    is_repost: bool = False


@dataclass(frozen=True)
class Segmentation:
    """The posts found in one cell, and whether any header was recognised."""

    segments: tuple[Segment, ...]
    found_header: bool

    @property
    def is_repost(self) -> bool:
        """True when any post in the cell is a repost or carries an embedded post."""
        return any(segment.is_repost for segment in self.segments)


@dataclass(frozen=True)
class SegmentSettings:
    """Settings read from configs/thresholds.yaml."""

    check_cells: int
    seed: int


def load_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> SegmentSettings:
    """Read the sample size and seed; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("segmentation_check_cells", "segmentation_check_seed"):
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return SegmentSettings(int(values["segmentation_check_cells"]), int(values["segmentation_check_seed"]))


def ref_for(workbook: str, sheet_idx: str, source_row: str) -> str:
    """The id of one raw cell: workbook, sheet index and source row. Holds no name."""
    return f"{workbook}#{sheet_idx}:r{source_row}"


def _is_marker(line: str) -> bool:
    rule = classify_line(line)
    return rule is not None and rule.name == CONNECTION_MARKER_RULE


def _header_starts(lines: Sequence[str]) -> list[int]:
    """First line of each header: the non-blank line above a marker, or the marker itself at the top."""
    starts: list[int] = []
    for index, line in enumerate(lines):
        if not _is_marker(line):
            continue
        above = next((i for i in range(index - 1, -1, -1) if lines[i].strip()), None)
        if above is not None and _is_marker(lines[above]):
            continue
        starts.append(index if above is None else above)
    return starts


def _is_leader_header(lines: Sequence[str], start: int, leader_key: str) -> bool:
    """Whether the header opening at `start` names the leader.

    The name line may carry extra tokens ("Dr.", "CFA") or lack some, so one token set must contain the
    other. A header with no readable name line (the marker is the first line) is taken as the leader's own.
    """
    if _is_marker(lines[start]):
        return True
    header, leader = set(name_key(lines[start]).split()), set(leader_key.split())
    return not header or header <= leader or leader <= header


def _build_segment(lines: Sequence[str], first: int, last: int, embedded_from: int | None) -> Segment:
    """One post from lines[first:last]; lines from `embedded_from` on are the embedded post."""
    split = last if embedded_from is None else embedded_from
    own = lines[first:split]
    notice = any(REPOST_NOTICE.match(line.strip()) for line in own)
    voice = [line for line in own if not REPOST_NOTICE.match(line.strip())]
    return Segment(first, "\n".join(voice), "\n".join(lines[split:last]), embedded_from is not None or notice)


def segment_cell(text: str, leader_key: str | None = None) -> Segmentation:
    """Split a cell into posts by the leader. A blank cell has no posts.

    With a `leader_key` (the sorted-token name key), a header by someone else is embedded in the current
    post, not a new post (see the module docstring). Without one, every header opens a post.
    """
    if not text.strip():
        return Segmentation((), False)
    lines = text.split("\n")
    starts = _header_starts(lines)
    if not starts:
        return Segmentation((Segment(0, text),), False)
    own = [s for s in starts if leader_key is None or _is_leader_header(lines, s, leader_key)]
    foreign = [s for s in starts if s not in own]
    bounds = [0, *[s for s in own if s != starts[0]], len(lines)]
    segments = tuple(
        _build_segment(lines, first, last, next((f for f in foreign if first <= f < last), None))
        for first, last in zip(bounds, bounds[1:])
    )
    return Segmentation(segments, True)


def raw_cell_frame(posts: pd.DataFrame) -> pd.DataFrame:
    """Raw cells that have a leader key and some text, as (leader_key, ref, text)."""
    rows = []
    for row in posts[posts["text_kind"] == RAW_KIND].itertuples(index=False):
        key = name_key(row.leader)
        if key and row.post_text.strip():
            rows.append((key, ref_for(row.workbook, row.sheet_idx, row.source_row), row.post_text))
    return pd.DataFrame(rows, columns=FRAME_COLUMNS)


def select_check_cells(frame: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """`n` cells, one per leader where possible; extra cells fill the sample only when leaders run out.

    Pools are sorted before drawing, so the result depends on the seed and the data, never on row order.
    """
    ordered = frame.sort_values(["leader_key", "ref"], kind="stable").reset_index(drop=True)
    rng = random.Random(seed)
    leaders = sorted(set(ordered["leader_key"]))
    first = [
        int(rng.choice(ordered.index[ordered["leader_key"] == leader].to_list()))
        for leader in sorted(rng.sample(leaders, min(n, len(leaders))))
    ]
    taken = set(first)
    rest = [i for i in ordered.index if i not in taken]
    extra = sorted(rng.sample(rest, min(n - len(first), len(rest))))
    chosen = ordered.loc[sorted([*first, *extra])]
    return chosen.sort_values("ref", kind="stable").reset_index(drop=True)


def check_frame(chosen: pd.DataFrame) -> pd.DataFrame:
    """The blind sample: ids and text, with empty columns for the human's count. No machine count."""
    out = pd.DataFrame(
        {
            "n": range(1, len(chosen) + 1),
            "leader_id": [leader_id_for(key) for key in chosen["leader_key"]],
            "ref": [spreadsheet_safe(value) for value in chosen["ref"]],
            "post_text": [spreadsheet_safe(value) for value in chosen["text"]],
            "human_post_count": "",
            "human_note": "",
        }
    )
    return out[CHECK_COLUMNS]


def run(
    raw_dir: Path = DEFAULT_RAW_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    sample_path: Path = DEFAULT_SAMPLE_PATH,
    settings: SegmentSettings | None = None,
) -> int:
    """Verify the raw manifest and write the blind sample; an existing sample is kept. 0 on success."""
    try:
        logger.info("manifest %s for %s", verify_raw(raw_dir), raw_dir)
        active = settings or load_settings()
        if sample_path.exists():
            logger.info("%s already exists; kept as is so human counts are never overwritten", sample_path)
            return 0
        frame = raw_cell_frame(_read_posts(interim_dir))
        sample = check_frame(select_check_cells(frame, active.check_cells, active.seed))
    except (ManifestMismatch, FileNotFoundError, ValueError, MissingIdKey) as error:
        logger.error("segmentation-sample FAILED: %s", error)
        return 1
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(sample_path, index=False)
    logger.info("wrote %s (%d rows)", sample_path, len(sample))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
