"""Tests for ``devague today`` (t10, acceptance criteria 1-4).

Criterion 3 is pinned here: the command writes ONLY ``docs/current-spec.md``
— every store file and everything under ``docs/specs/`` is byte-identical
before and after a run.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, not shipped code
from pathlib import Path

import pytest

from devague import delivery_store, plan_store, store
from devague.cli import main
from devague.delivery import Delivery, RunReference
from devague.frame import Frame
from devague.plan import Plan
from tests.test_render import assert_markdownlint_clean

CURRENT_SPEC = Path("docs/current-spec.md")
_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.yaml"


def _frame(slug: str, title: str = "A frame", created: str = "2026-01-01T00:00:00Z") -> Frame:
    frame = Frame(slug=slug, title=title, created=created)
    store.save(frame)
    return frame


def _plan(slug: str, frame_slug: str, created: str = "2026-01-02T00:00:00Z") -> Plan:
    plan = Plan(slug=slug, title="A plan", frame_slug=frame_slug, created=created)
    plan_store.save(plan)
    return plan


def _seed_ledgered_state(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _plan("alpha", "alpha")
    ledger = Delivery(plan_slug="alpha", created="2026-01-02T00:00:00Z")
    ledger.add_delta("added", "the CLI grows a today verb", caused_by=["c7"], evidence_refs=["e1"])
    ledger.add_evidence(
        obligation_ref="c7",
        test_ref="tests/test_today.py::test_x",
        behavior_text="the CLI grows a today verb",
        contract_text="claim c7 text",
        evidence_type="automated",
        strength="execution",
        strength_basis="ran the suite",
        outcome="pass",
        run=RunReference(timestamp="2026-08-31T00:00:00Z", commit="abc1234"),
    )
    delivery_store.save(ledger)


def _tree_snapshot(root: Path) -> dict[str, str]:
    """A hash of every file under ``root`` except the current-spec artifact."""
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path == root / CURRENT_SPEC:
            continue
        snapshot[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def test_today_writes_current_spec(tmp_path, monkeypatch):
    _seed_ledgered_state(tmp_path, monkeypatch)
    assert main(["today"]) == 0
    assert CURRENT_SPEC.exists()
    text = CURRENT_SPEC.read_text(encoding="utf-8")
    assert text.startswith("# Current spec — what the app does today\n")
    assert "the CLI grows a today verb" in text


def test_today_touches_only_current_spec(tmp_path, monkeypatch):
    _seed_ledgered_state(tmp_path, monkeypatch)
    before = _tree_snapshot(tmp_path)
    assert main(["today"]) == 0
    after = _tree_snapshot(tmp_path)
    assert before == after
    # docs/specs never created by this command.
    assert not (tmp_path / "docs" / "specs").exists()


def test_today_json_still_writes_the_file_and_emits_projection(tmp_path, monkeypatch, capsys):
    _seed_ledgered_state(tmp_path, monkeypatch)
    assert main(["today", "--json"]) == 0
    assert CURRENT_SPEC.exists()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["behaviors"][0]["behavior_text"] == "the CLI grows a today verb"
    assert payload["coverage"]["ledgered_plans"] == ["alpha"]


def test_today_overwrites_in_place_undated(tmp_path, monkeypatch):
    _seed_ledgered_state(tmp_path, monkeypatch)
    assert main(["today"]) == 0
    first = CURRENT_SPEC.read_text(encoding="utf-8")
    assert main(["today"]) == 0
    second = CURRENT_SPEC.read_text(encoding="utf-8")
    assert first == second
    # Still exactly one file — no dated duplicate spawned.
    assert list((tmp_path / "docs").glob("current-spec*.md")) == [tmp_path / CURRENT_SPEC]


def test_today_pins_markdownlint_clean_by_hand_rolled_check(tmp_path, monkeypatch):
    _seed_ledgered_state(tmp_path, monkeypatch)
    assert main(["today"]) == 0
    assert_markdownlint_clean(CURRENT_SPEC.read_text(encoding="utf-8"))


@pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)
def test_today_passes_real_markdownlint_cli2(tmp_path, monkeypatch):
    _seed_ledgered_state(tmp_path, monkeypatch)
    assert main(["today"]) == 0
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_CONFIG), str(CURRENT_SPEC)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
