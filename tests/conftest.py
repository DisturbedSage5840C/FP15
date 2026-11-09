"""Shared test setup: every test runs with a synthetic id key so no real secret is ever needed."""
import socket
from pathlib import Path
from typing import NoReturn

import pytest
import yaml

from src.id_key import ENV_VAR

ROOT = Path(__file__).resolve().parent.parent
TEST_ID_KEY = "synthetic-test-key-not-a-secret"


@pytest.fixture(autouse=True)
def _synthetic_id_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, TEST_ID_KEY)


def _scraping_approved() -> bool:
    values = yaml.safe_load((ROOT / "configs" / "thresholds.yaml").read_text(encoding="utf-8")) or {}
    return values.get("scraping_approved") is True


@pytest.fixture(autouse=True)
def _block_network_until_scraping_is_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    """While scraping_approved is false, any attempt to resolve a host or open a connection fails the test."""
    if _scraping_approved():
        return

    def _blocked(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("network access is blocked: scraping_approved is false in configs/thresholds.yaml")

    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
