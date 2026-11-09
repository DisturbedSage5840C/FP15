"""Shared test setup: every test runs with a synthetic id key so no real secret is ever needed."""
import pytest

from src.id_key import ENV_VAR

TEST_ID_KEY = "synthetic-test-key-not-a-secret"


@pytest.fixture(autouse=True)
def _synthetic_id_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, TEST_ID_KEY)
