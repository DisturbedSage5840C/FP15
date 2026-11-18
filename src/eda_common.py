"""Shared helpers for the exploratory data analysis (`make eda`): settings and the "<5" rule.

Every count in the EDA report is a count of leaders or cells in a group. A group with fewer leaders than the
disclosure minimum is shown as "<5" instead of its number, and so is any share built on it. When only one cell of a
table is hidden and a total is shown, the next smallest cell is hidden as well, because a total minus the visible cells
would give the hidden one back.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")
SMALL = "<5"
TOO_SMALL_TO_MODEL = "too small to model"
TOTAL_LABEL = "all"


@dataclass(frozen=True)
class EdaSettings:
    """min_posts is the pass mark in thresholds.yaml; the others are descriptive settings, not pass marks."""

    min_posts: int
    disclosure_min: int
    model_min: int
    size_bands: int


def load_eda_settings(path: Path = DEFAULT_THRESHOLDS_PATH) -> EdaSettings:
    """Read the four settings; a missing key is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keys = ("min_posts_per_leader", "eda_disclosure_min_leaders", "eda_model_min_leaders", "eda_size_bands")
    for key in keys:
        if key not in values:
            raise ValueError(f"{path}: missing key {key}")
    return EdaSettings(*(int(values[key]) for key in keys))


def show_count(count: int, minimum: int) -> str:
    """The count with thousands separators, or "<5" when it is below the disclosure minimum."""
    return SMALL if count < minimum else f"{count:,}"


def show_share(part: int, whole: int, minimum: int) -> str:
    """A percentage with one decimal; hidden when the part or the whole is below the disclosure minimum."""
    if part < minimum or whole < minimum:
        return SMALL
    return f"{100 * part / whole:.1f}%"


def protect_cells(counts: Mapping[str, int], minimum: int, total_shown: bool = True) -> dict[str, str]:
    """Show each count, hiding the small ones; with a total shown, a lone hidden cell takes its next smallest with it."""
    shown = {label: show_count(count, minimum) for label, count in counts.items()}
    hidden = [label for label, text in shown.items() if text == SMALL]
    if total_shown and len(hidden) == 1 and len(counts) > 1:
        visible = [label for label in counts if label not in hidden]
        next_smallest = min(visible, key=lambda label: counts[label])
        shown[next_smallest] = SMALL
    return shown


def count_rows(
    counts: Mapping[str, int], settings: EdaSettings
) -> list[tuple[str, str, str, str]]:
    """Table rows (group, leaders, share of all, modelling flag) plus a final total row that is always shown.

    A group below the modelling minimum is flagged whether or not its number is hidden.
    """
    total = sum(counts.values())
    shown = protect_cells(counts, settings.disclosure_min)
    rows = [
        (
            label,
            shown[label],
            SMALL if shown[label] == SMALL else show_share(count, total, settings.disclosure_min),
            TOO_SMALL_TO_MODEL if count < settings.model_min else "",
        )
        for label, count in counts.items()
    ]
    rows.append((TOTAL_LABEL, show_count(total, settings.disclosure_min),
                 show_share(total, total, settings.disclosure_min), ""))
    return rows
