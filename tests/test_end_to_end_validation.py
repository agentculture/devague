"""End-to-end success-signal measurement, driving the installed CLI via
``subprocess`` (bvts t15, covers c16 h12 c1 c15).

This module makes the success-signal claim of the whole obligations +
evidence + convergence-warnings + ``today`` feature set falsifiable: every
count asserted below comes from *parsing actual stdout of a real ``devague``
process*, never from reaching into a store to shortcut the assertion.

Acceptance criteria (verbatim from the confirmed plan):

1. an integration test plants an obligation, files evidence against it, and
   asserts the converge warning count drops to zero for that obligation —
   measured from real command output
2. ``devague summary`` renders one evidence-backed Delivery Claims row per met
   obligation in the test scenario, counted from output
3. ``devague today`` runs clean over all existing frames, plans, and
   deliveries in this repo with every store file byte-identical afterwards,
   and the committed artifact passes markdownlint
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, driving the real CLI
import sys
from pathlib import Path

import pytest

_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = _REPO_ROOT / ".markdownlint-cli2.yaml"
_REAL_DEVAGUE_DIR = _REPO_ROOT / ".devague"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Invoke the real CLI as a subprocess — the honest "real command output"
    form named in this task's instruction, not an in-process ``main()`` call.
    """
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [sys.executable, "-m", "devague", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"devague {' '.join(args)} failed (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


# ── AC1 + AC2: plant an obligation, file evidence, watch the warning drop ────


_REQUIRED_KINDS = (
    "audience",
    "after_state",
    "before_state",
    "boundary",
    "success_signal",
)


def _build_converged_frame(cwd: Path) -> str:
    out = _run(["new", "Ship the obligation-to-evidence loop", "--title", "bvts-t15"], cwd).stdout
    match = re.search(r"created frame '([^']+)'", out)
    assert match, f"could not parse frame slug from: {out!r}"
    slug = match.group(1)
    for kind in _REQUIRED_KINDS:
        _run(["capture", "--kind", kind, f"{kind} text", "--origin", "user"], cwd)
    show_out = _run(["show", "--json"], cwd).stdout
    import json as _json

    claim_ids = [c["id"] for c in _json.loads(show_out)["claims"]]
    for cid in claim_ids:
        _run(["interrogate", cid, "--honesty", "must hold", "--origin", "user"], cwd)
    converge = _run(["converge"], cwd).stdout
    assert "converged" in converge
    return slug


def _seed_minimal_converged_plan(cwd: Path, frame_slug: str) -> str:
    _run(["plan", "new", "--frame", frame_slug], cwd)
    import json as _json

    show = _json.loads(_run(["plan", "show", "--json"], cwd).stdout)
    target_ids = [t["id"] for t in show["targets"]]
    args = ["plan", "task", "cover every target", "--accept", "every target is covered"]
    for tid in target_ids:
        args += ["--covers", tid]
    _run(args, cwd)
    task_show = _json.loads(_run(["plan", "show", "--json"], cwd).stdout)
    task_id = task_show["tasks"][0]["id"]
    _run(["plan", "confirm", task_id], cwd)
    converge = _run(["plan", "converge"], cwd).stdout
    assert "converged" in converge
    return frame_slug


def _count_untested_lines(converge_stdout: str, obligation_id: str) -> int:
    """Count converge-output lines that name ``obligation_id`` as untested —
    the honest way to measure the warning, straight from real stdout."""
    return sum(
        1 for line in converge_stdout.splitlines() if obligation_id in line and "untested" in line
    )


def test_planted_obligation_warns_then_clears_once_evidence_is_approved(tmp_path) -> None:
    """AC1: plant an obligation, file evidence against it, and watch the
    converge warning count for that obligation drop from 1 to 0 — both counts
    measured from real ``devague converge`` stdout, never from the store."""
    frame_slug = _build_converged_frame(tmp_path)

    oblige_out = _run(
        [
            "oblige",
            "c1",
            "--seam",
            "cli",
            "--behavior",
            "the loop actually discharges the obligation",
        ],
        tmp_path,
    ).stdout
    match = re.search(r"filed (o\d+)", oblige_out)
    assert match, f"could not parse obligation id from: {oblige_out!r}"
    obligation_id = match.group(1)

    before = _run(["converge"], tmp_path).stdout
    assert _count_untested_lines(before, obligation_id) == 1

    _seed_minimal_converged_plan(tmp_path, frame_slug)

    evidence_out = _run(
        [
            "evidence",
            "--obligation",
            obligation_id,
            "--test",
            "tests/test_end_to_end_validation.py::"
            "test_planted_obligation_warns_then_clears_once_evidence_is_approved",
            "--behavior",
            "the loop actually discharges the obligation",
            "--contract",
            "the loop actually discharges the obligation",
            "--type",
            "automated",
            "--strength",
            "execution",
            "--basis",
            "this very test executed the loop end to end",
            "--outcome",
            "pass",
            "--run-commit",
            "a6fdd8e",
            "--run-timestamp",
            "2026-08-31T10:00:00Z",
        ],
        tmp_path,
    ).stdout
    assert "(approved)" in evidence_out

    after = _run(["converge"], tmp_path).stdout
    assert _count_untested_lines(after, obligation_id) == 0

    # AC2: devague summary renders exactly one evidence-backed Delivery Claims
    # row for this one met obligation — counted from real stdout.
    summary_out = _run(["summary"], tmp_path).stdout
    assert "## Delivery Claims" in summary_out
    section = summary_out.split("## Delivery Claims", 1)[1]
    section = section.split("\n## ", 1)[0]
    data_rows = [line for line in section.splitlines() if line.startswith("| `c1`")]
    assert len(data_rows) == 1, f"expected exactly one c1 row, got: {data_rows!r}"
    assert "`execution`" in data_rows[0]
    assert "untested" not in data_rows[0]
    assert "<fill:" not in data_rows[0]


# ── AC3: devague today over this repo's real state, read-only ───────────────


def _tree_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        snapshot[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


@pytest.mark.skipif(not _REAL_DEVAGUE_DIR.exists(), reason="no .devague directory in this checkout")
def test_today_runs_clean_over_this_repos_real_state(tmp_path) -> None:
    """AC3: copy this repo's real ``.devague`` (frames, plans, deliveries)
    into a tmp workdir — so a failure here can never mutate real state — run
    ``devague today`` for real, and assert every copied store file is
    byte-identical before and after; only ``docs/current-spec.md`` may appear."""
    work = tmp_path / "repo-copy"
    work.mkdir()
    shutil.copytree(_REAL_DEVAGUE_DIR, work / ".devague")

    before = _tree_snapshot(work)
    assert before, "expected at least one real store file to have been copied"

    out = _run(["today"], work).stdout
    assert "wrote docs/current-spec.md" in out

    current_spec = work / "docs" / "current-spec.md"
    assert current_spec.exists()

    after = _tree_snapshot(work)
    new_files = set(after) - set(before)
    assert new_files == {"docs/current-spec.md"}, f"unexpected new/changed files: {new_files}"
    for rel, digest in before.items():
        assert after[rel] == digest, f"{rel} changed by 'devague today'"


@pytest.mark.skipif(not _REAL_DEVAGUE_DIR.exists(), reason="no .devague directory in this checkout")
@pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)
def test_today_artifact_over_real_state_passes_markdownlint(tmp_path) -> None:
    work = tmp_path / "repo-copy"
    work.mkdir()
    shutil.copytree(_REAL_DEVAGUE_DIR, work / ".devague")
    _run(["today"], work)
    current_spec = work / "docs" / "current-spec.md"
    assert current_spec.exists()
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_CONFIG), str(current_spec)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
