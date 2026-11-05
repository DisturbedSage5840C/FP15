"""Tests for the raw-data hash manifest (write on first run, verify afterwards)."""
from pathlib import Path

import pytest

from src.verify_raw import (
    MANIFEST_NAME,
    ManifestMismatch,
    build_manifest,
    main,
    run,
    verify_manifest,
)


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "a.xlsx").write_bytes(b"alpha")
    (raw / "b.zip").write_bytes(b"bravo")
    (raw / ".gitkeep").write_bytes(b"")
    return raw


def test_build_manifest_hashes_data_files_and_skips_housekeeping(raw_dir: Path) -> None:
    manifest = build_manifest(raw_dir)

    assert sorted(manifest) == ["a.xlsx", "b.zip"]
    assert len(manifest["a.xlsx"]) == 64  # sha256 hex digest


def test_first_run_writes_manifest_and_second_run_passes(raw_dir: Path) -> None:
    first = run(raw_dir)
    second = run(raw_dir)

    assert first == "written"
    assert second == "verified"
    assert (raw_dir / MANIFEST_NAME).exists()


def test_manifest_is_sha256sum_compatible(raw_dir: Path) -> None:
    run(raw_dir)

    lines = (raw_dir / MANIFEST_NAME).read_text().splitlines()

    assert all(len(line.split("  ", 1)[0]) == 64 for line in lines)
    assert [line.split("  ", 1)[1] for line in lines] == ["a.xlsx", "b.zip"]


def test_verification_fails_when_a_file_changes(raw_dir: Path) -> None:
    run(raw_dir)
    (raw_dir / "a.xlsx").write_bytes(b"tampered")

    with pytest.raises(ManifestMismatch, match="a.xlsx"):
        run(raw_dir)


def test_verification_fails_when_a_file_is_missing(raw_dir: Path) -> None:
    run(raw_dir)
    (raw_dir / "b.zip").unlink()

    with pytest.raises(ManifestMismatch, match="b.zip"):
        verify_manifest(raw_dir)


def test_verification_fails_when_an_unlisted_file_appears(raw_dir: Path) -> None:
    run(raw_dir)
    (raw_dir / "c.csv").write_bytes(b"new")

    with pytest.raises(ManifestMismatch, match="c.csv"):
        verify_manifest(raw_dir)


def test_run_never_modifies_existing_data_files(raw_dir: Path) -> None:
    before = {p.name: p.read_bytes() for p in raw_dir.iterdir()}

    run(raw_dir)
    run(raw_dir)

    after = {p.name: p.read_bytes() for p in raw_dir.iterdir() if p.name != MANIFEST_NAME}
    assert after == before


def test_malformed_manifest_line_is_rejected(raw_dir: Path) -> None:
    (raw_dir / MANIFEST_NAME).write_text("not-a-hash  a.xlsx\n")

    with pytest.raises(ManifestMismatch, match="malformed"):
        verify_manifest(raw_dir)


def test_main_returns_zero_when_manifest_is_written_then_verified(
    raw_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.verify_raw.DEFAULT_RAW_DIR", raw_dir)

    assert main() == 0
    assert main() == 0


def test_main_returns_one_when_a_file_changed(raw_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.verify_raw.DEFAULT_RAW_DIR", raw_dir)
    assert main() == 0
    (raw_dir / "a.xlsx").write_bytes(b"tampered")

    assert main() == 1


def test_empty_raw_dir_refuses_to_write_a_manifest(tmp_path: Path) -> None:
    empty = tmp_path / "raw"
    empty.mkdir()

    with pytest.raises(FileNotFoundError):
        run(empty)
