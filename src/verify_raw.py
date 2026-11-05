"""Hash manifest for data/raw: written on the first run, verified on every later run.

data/raw is read-only (CLAUDE.md). This module only ever reads those files; the sole
file it creates is MANIFEST.sha256, in sha256sum-compatible format.
"""
from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

MANIFEST_NAME = "MANIFEST.sha256"
IGNORED_NAMES = frozenset({".gitkeep", ".DS_Store", MANIFEST_NAME})
DEFAULT_RAW_DIR = Path("data/raw")
HASH_CHUNK_BYTES = 1024 * 1024


class ManifestMismatch(Exception):
    """Raised when data/raw no longer matches its recorded manifest."""


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(raw_dir: Path) -> dict[str, str]:
    """Return {relative posix path: sha256} for every data file under raw_dir."""
    files = (
        p for p in raw_dir.rglob("*") if p.is_file() and p.name not in IGNORED_NAMES
    )
    return {
        p.relative_to(raw_dir).as_posix(): _sha256_of(p)
        for p in sorted(files, key=lambda p: p.relative_to(raw_dir).as_posix())
    }


def write_manifest(raw_dir: Path, manifest: dict[str, str]) -> Path:
    path = raw_dir / MANIFEST_NAME
    lines = [f"{digest}  {name}" for name, digest in sorted(manifest.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def read_manifest(raw_dir: Path) -> dict[str, str]:
    path = raw_dir / MANIFEST_NAME
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        digest, separator, name = line.partition("  ")
        if not separator or len(digest) != 64:
            raise ManifestMismatch(f"{path}:{line_number}: malformed manifest line")
        entries[name] = digest
    return entries


def verify_manifest(raw_dir: Path) -> None:
    """Raise ManifestMismatch naming every changed, missing or unlisted file."""
    recorded = read_manifest(raw_dir)
    current = build_manifest(raw_dir)

    problems = (
        [f"changed: {n}" for n in sorted(recorded.keys() & current.keys()) if recorded[n] != current[n]]
        + [f"missing: {n}" for n in sorted(recorded.keys() - current.keys())]
        + [f"unlisted: {n}" for n in sorted(current.keys() - recorded.keys())]
    )
    if problems:
        raise ManifestMismatch("data/raw does not match MANIFEST.sha256 -> " + "; ".join(problems))


def run(raw_dir: Path = DEFAULT_RAW_DIR) -> str:
    """Write the manifest on first run, otherwise verify it. Returns 'written' or 'verified'."""
    if (raw_dir / MANIFEST_NAME).exists():
        verify_manifest(raw_dir)
        return "verified"

    manifest = build_manifest(raw_dir)
    if not manifest:
        raise FileNotFoundError(f"no data files found in {raw_dir}; refusing to write an empty manifest")
    write_manifest(raw_dir, manifest)
    return "written"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        status = run(DEFAULT_RAW_DIR)
    except (ManifestMismatch, FileNotFoundError) as error:
        logger.error("verify_raw FAILED: %s", error)
        return 1
    logger.info("verify_raw: manifest %s for %s", status, DEFAULT_RAW_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
