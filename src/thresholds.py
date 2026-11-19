"""One reader for configs/thresholds.yaml, so no pass mark or setting is ever hard-coded in a module."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_THRESHOLDS_PATH = Path("configs/thresholds.yaml")


def load_threshold(key: str, path: Path = DEFAULT_THRESHOLDS_PATH) -> Any:
    """The value stored under `key`; a missing key (or an empty file) is named in the error."""
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if key not in values:
        raise ValueError(f"{path}: missing key {key}")
    return values[key]
