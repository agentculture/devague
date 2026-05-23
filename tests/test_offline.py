"""t8: every contract operation runs fully offline — zero network access (c7, h7).

Two guarantees: devague's own source imports no networking library, and a full
frame -> spec -> plan session runs to completion with ``socket`` access stubbed
to raise. If any operation reached the network, the session would fail.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

from devague import store
from devague.cli import main

_NET_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(socket|ssl|urllib|http|ftplib|requests|httpx|aiohttp)\b",
    re.MULTILINE,
)


def test_source_imports_no_networking_library() -> None:
    offenders = [
        str(py)
        for py in Path("devague").rglob("*.py")
        if _NET_IMPORT.search(py.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"networking import found in: {offenders}"


@pytest.fixture
def block_network(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("network access attempted during an offline operation")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def test_full_session_runs_offline(block_network, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["new", "Specs in minutes"]) == 0
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        assert main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"]) == 0
    # confirm a honesty condition on every confirmed spec-affecting claim
    for c in store.load(store.current_slug()).claims:
        assert main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"]) == 0
    assert main(["converge"]) == 0
    assert main(["export"]) == 0

    slug = store.current_slug()
    assert main(["plan", "new", "--frame", slug]) == 0
    assert main(["plan", "task", "do it", "--accept", "done", "--origin", "user"]) == 0
    assert main(["show"]) == 0
    assert main(["list"]) == 0
