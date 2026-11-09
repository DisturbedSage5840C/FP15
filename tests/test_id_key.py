"""Tests for the secret id key and the keyed leader_id (src.id_key, src.id_matching). Synthetic values only."""
from pathlib import Path

import pytest

from src.id_key import ENV_VAR, MissingIdKey, load_id_key, main
from src.id_matching import leader_id_for


def test_key_comes_from_the_environment_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_VAR, "from-env")

    assert load_id_key(env_file=tmp_path / ".env") == b"from-env"


def test_key_falls_back_to_the_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"# comment\nOTHER=1\n{ENV_VAR}='from-file'\n", encoding="utf-8")

    assert load_id_key(env_file=env_file) == b"from-file"


def test_environment_variable_wins_over_the_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_VAR, "from-env")
    env_file = tmp_path / ".env"
    env_file.write_text(f"{ENV_VAR}=from-file\n", encoding="utf-8")

    assert load_id_key(env_file=env_file) == b"from-env"


@pytest.mark.parametrize("content", [None, "", "OTHER=1\n", f"{ENV_VAR}=\n", f"{ENV_VAR}=   \n"])
def test_missing_or_blank_key_raises_a_clear_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str | None
) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    env_file = tmp_path / ".env"
    if content is not None:
        env_file.write_text(content, encoding="utf-8")

    with pytest.raises(MissingIdKey, match=ENV_VAR):
        load_id_key(env_file=env_file)


def test_blank_environment_variable_counts_as_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_VAR, "  ")

    with pytest.raises(MissingIdKey):
        load_id_key(env_file=tmp_path / ".env")


def test_main_returns_zero_without_printing_the_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(ENV_VAR, "super-secret-value")

    assert main() == 0
    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out + captured.err


def test_main_fails_with_a_clear_message_when_the_key_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)

    assert main() == 1
    assert ENV_VAR in caplog.text and ".env" in caplog.text


def test_leader_id_is_stable_prefixed_and_carries_no_name() -> None:
    assert leader_id_for("ann lee") == leader_id_for("ann lee")
    assert leader_id_for("ann lee") != leader_id_for("bo rao")
    assert leader_id_for("ann lee").startswith("L")
    assert "ann" not in leader_id_for("ann lee")


def test_leader_id_changes_with_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "key-one")
    first = leader_id_for("ann lee")
    monkeypatch.setenv(ENV_VAR, "key-two")

    assert leader_id_for("ann lee") != first


def test_leader_id_cannot_be_rebuilt_from_a_plain_hash_of_the_name() -> None:
    import hashlib

    plain = "L" + hashlib.sha256(b"ann lee").hexdigest()[:10]

    assert leader_id_for("ann lee") != plain


def test_leader_id_needs_the_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MissingIdKey):
        leader_id_for("ann lee")
