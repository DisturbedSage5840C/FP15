"""No pipeline code may reach the network while scraping_approved is false (Step 5).

Two layers: a static scan of src/ for network libraries, and a runtime guard (tests/conftest.py) that makes any
attempt to resolve a host or open a socket fail the test that made it.
"""
from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
THRESHOLDS_PATH = ROOT / "configs" / "thresholds.yaml"
SRC_DIR = ROOT / "src"
NETWORK_MODULES = frozenset(
    {
        "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp", "ftplib", "smtplib",
        "poplib", "imaplib", "telnetlib", "xmlrpc", "websocket", "websockets", "paramiko", "pycurl",
        "selenium", "playwright", "scrapy", "mechanize",
    }
)
NETWORK_CALLS = frozenset({"urlopen", "create_connection", "getaddrinfo", "gethostbyname"})


def _scraping_approved() -> bool:
    values = yaml.safe_load(THRESHOLDS_PATH.read_text(encoding="utf-8")) or {}
    if "scraping_approved" not in values:
        raise AssertionError(f"{THRESHOLDS_PATH}: missing key scraping_approved")
    flag = values["scraping_approved"]
    assert isinstance(flag, bool), "scraping_approved must be true or false, not text"
    return flag


def _network_findings(source: str) -> list[str]:
    """Network imports and calls found in one module's source, as short descriptions without any text values."""
    findings: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            findings += [f"import {a.name}" for a in node.names if a.name.split(".")[0] in NETWORK_MODULES]
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in NETWORK_MODULES:
            findings.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in NETWORK_CALLS:
                findings.append(f"call {name}()")
    return findings


def test_the_scraping_flag_is_present_and_false_until_the_supervisor_approves_in_writing() -> None:
    assert _scraping_approved() is False


def test_no_pipeline_module_imports_or_calls_a_network_library_while_scraping_is_not_approved() -> None:
    if _scraping_approved():
        pytest.skip("scraping_approved is true: network use is allowed")

    found = {
        path.name: findings
        for path in sorted(SRC_DIR.glob("*.py"))
        if (findings := _network_findings(path.read_text(encoding="utf-8")))
    }

    assert found == {}


def test_the_scan_detects_network_imports_and_calls() -> None:
    source = "import requests\nfrom urllib.request import urlopen\nimport os\nsocket.create_connection(a)\nurlopen(u)\n"

    assert _network_findings(source) == [
        "import requests", "from urllib.request import ...", "call create_connection()", "call urlopen()"
    ]


def test_the_scan_ignores_modules_that_only_look_similar() -> None:
    assert _network_findings("import httpx_not_really\nimport sockets_game\nfrom pathlib import Path\n") == []


def test_the_runtime_guard_blocks_name_resolution_and_connections() -> None:
    with pytest.raises(RuntimeError, match="scraping_approved"):
        socket.getaddrinfo("example.invalid", 80)
    with pytest.raises(RuntimeError, match="scraping_approved"):
        socket.create_connection(("example.invalid", 80))
