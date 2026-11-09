"""The secret key behind every leader_id (`make check-key`).

leader_id is an HMAC of the normalised name, so nobody without this key can rebuild an id from a guessed
name. The key lives in the FP15_ID_KEY environment variable or in a git-ignored .env file, never in the repo.
The key itself is never logged or printed.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_VAR = "FP15_ID_KEY"
DEFAULT_ENV_FILE = Path(".env")
QUOTE_CHARS = "'\""


class MissingIdKey(RuntimeError):
    """Raised when no usable id key is set. The message says how to set one; it never shows a key."""


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in QUOTE_CHARS:
        return value[1:-1]
    return value


def _read_env_file(path: Path) -> Mapping[str, str]:
    """NAME=value lines from a .env file; comments and blank lines are skipped, a missing file is empty."""
    if not path.is_file():
        return {}
    pairs: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        name, _, value = text.partition("=")
        pairs[name.strip()] = _unquote(value)
    return pairs


def load_id_key(env_file: Path = DEFAULT_ENV_FILE) -> bytes:
    """The id key as bytes: the environment variable first, then the .env file. Blank counts as missing."""
    value = os.environ.get(ENV_VAR, "").strip() or _read_env_file(env_file).get(ENV_VAR, "").strip()
    if not value:
        raise MissingIdKey(
            f"{ENV_VAR} is not set. Put a long random value in a git-ignored .env file "
            f"as {ENV_VAR}=<value> or export it in the shell. It must never be committed."
        )
    return value.encode("utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        load_id_key()
    except MissingIdKey as error:
        logger.error("id key check FAILED: %s", error)
        return 1
    logger.info("id key found (value not shown)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
