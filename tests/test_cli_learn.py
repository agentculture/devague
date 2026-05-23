"""Tests for the `devague learn` command — teaches the working-backwards method."""

from __future__ import annotations

import json

import pytest

from devague.cli import main


def test_learn_documents_assign_to_workforce_invocation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The learn output contains assign-to-workforce guidance for fanning out
    a converged plan's waves to a workforce.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    # Must mention the assign-to-workforce concept.
    assert "assign-to-workforce" in out
    # Must mention when to fan out: converged plans with parallel waves.
    assert "converged plan" in out or "convergence" in out
    assert "wave" in out or "parallel" in out
    # Must mention the three human gates: spec, implementation split plan, final PR.
    assert "gate" in out or "spec" in out
    # Must mention worktree isolation for safety.
    assert "worktree" in out


def test_learn_json_includes_assign_to_workforce_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The --json payload carries assign-to-workforce guidance as a distinct section."""
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # Must include a documented section about assign-to-workforce.
    assert "assign_to_workforce" in payload or "assign-to-workforce" in str(payload).lower()
