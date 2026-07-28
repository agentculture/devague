"""#64 integration test: real markdownlint-cli2 against a hostile-input export.

Unit tests (``tests/test_md_safety.py``, ``tests/test_render.py``,
``tests/test_render_plan.py``) pin the renderer behavior against a hand-rolled
check and hard-coded expected strings. This test instead drives the actual CLI
end to end (``devague new`` … ``devague export``; ``devague plan new`` …
``devague plan export``) against a frame whose announcement ends in '.' and
whose claims/tasks/risks carry bare URLs, then shells out to the real
``markdownlint-cli2`` binary — the same dev tool this repo's own ``CLAUDE.md``
documents (``markdownlint-cli2 "**/*.md"``) and the one league-of-agents-platform's
CI gates on — and asserts zero errors, with no hand-editing.

``markdownlint-cli2`` is dev tooling here, not installed by this repo's own CI
(``tests.yml`` / ``security-checks.yml`` run neither Node nor markdownlint), so
this test skips cleanly when the binary is not on PATH rather than failing the
suite.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, not shipped code
from pathlib import Path

import pytest

from devague import plan_store, store
from devague.cli import main

_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.yaml"

pytestmark = pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)

_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _run_markdownlint(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_CONFIG), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        check=False,
    )


def _export_hostile_spec(monkeypatch, tmp_path) -> Path:
    monkeypatch.chdir(tmp_path)
    main(["new", "League of Agents is live at https://league-of-agents.ai."])
    main(
        [
            "interrogate",
            "c1",
            "--honesty",
            "announcement is true, verified at http://status.league-of-agents.ai.",
            "--origin",
            "user",
        ]
    )
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(
            [
                "capture",
                "--kind",
                kind,
                f"{kind} text ends in a period, see https://league-of-agents.ai.",
                "--origin",
                "user",
            ]
        )
    frame = store.load(store.current_slug())
    for c in frame.claims:
        if c.id == "c1":
            continue
        main(["interrogate", c.id, "--honesty", "must hold.", "--origin", "user"])
    main(["export"])
    frame = store.load(store.current_slug())
    return Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"


def _export_hostile_plan(monkeypatch, tmp_path) -> Path:
    spec_path = _export_hostile_spec(monkeypatch, tmp_path)
    frame = store.load(store.current_slug())
    main(["plan", "new", "--frame", frame.slug])
    main(
        [
            "plan",
            "task",
            "Ship the beautiful, welcoming home page.",
            "--accept",
            "page is live, verified at https://league-of-agents.ai.",
            *[flag for tid in _ALL_TARGETS for flag in ("--covers", tid)],
        ]
    )
    main(
        [
            "plan",
            "risk",
            "traffic spike risk, see http://status.league-of-agents.ai for load.",
            "--kind",
            "unknown_nonblocking",
            "--task",
            "t1",
        ]
    )
    main(["plan", "export"])
    plan = plan_store.load(plan_store.current_slug())
    plan_path = Path("docs/plans") / f"{plan.created[:10]}-{plan.slug}.md"
    return spec_path, plan_path


def test_hostile_spec_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path = _export_hostile_spec(monkeypatch, tmp_path)
    assert spec_path.exists()
    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_hostile_plan_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path, plan_path = _export_hostile_plan(monkeypatch, tmp_path)
    assert plan_path.exists()
    result = _run_markdownlint(spec_path, plan_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ── issue-backlog-sweep t3 (#93, #49, #83, #87 c6/h6, c22/h18): a frame ──────
# mixing bare and already-backticked underscore identifiers, open parks of
# two kinds, and a rejected claim that also carried a hard question and
# seeded a scope entry — the real counter-evidence corpus shape ─────────────


def _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path) -> Path:
    monkeypatch.chdir(tmp_path)
    main(["new", "Sweep closes the issue backlog"])
    main(
        [
            "capture",
            "--kind",
            "audience",
            "operators driving _think and challenge",
            "--origin",
            "user",
        ]
    )
    main(
        [
            "capture",
            "--kind",
            "after_state",
            "specs escape `_read_file` and __init__.py safely",
            "--origin",
            "user",
        ]
    )
    main(
        [
            "capture",
            "--kind",
            "before_state",
            "exports failed markdownlint on _read_file identifiers",
            "--origin",
            "user",
        ]
    )
    main(["capture", "--kind", "boundary", "escaping never mutates frame JSON", "--origin", "user"])
    main(["capture", "--kind", "success_signal", "0 markdownlint-cli2 errors", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold.", "--origin", "user"])
    main(["park", "residual risk about scale", "--kind", "unknown_nonblocking"])
    main(["park", "later docs follow-up", "--kind", "follow_up"])

    # The #83 repro shape: capture (proposed), interrogate --risk, reject —
    # the hard question and the scope seed below must both vanish on export.
    main(
        [
            "capture",
            "--kind",
            "boundary",
            "the policy gate must receive rewritten args",
            "--origin",
            "llm",
        ]
    )
    frame = store.load(store.current_slug())
    contested = next(c for c in frame.claims if c.text.startswith("the policy gate"))
    main(["interrogate", contested.id, "--risk", "a hook could launder a denied command"])
    main(
        [
            "scope",
            "devague/render/spec_md.py",
            "--finding",
            "`_follow_up` no longer drops parks",
            "--seeds",
            contested.id,
        ]
    )
    main(["reject", contested.id])

    main(["converge"])
    main(["export"])
    frame = store.load(store.current_slug())
    return Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"


def test_mixed_identifier_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    assert spec_path.exists()
    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_mixed_identifier_export_omits_rejected_content(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    out = spec_path.read_text(encoding="utf-8")
    assert "launder a denied command" not in out
    assert "policy gate must receive rewritten args" not in out
    assert "(rejected)" in out  # the dead scope seed is flagged, not silently dropped


def test_mixed_identifier_export_lists_both_open_park_kinds(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    out = spec_path.read_text(encoding="utf-8")
    assert "## Open parks" in out
    assert "[unknown_nonblocking] residual risk about scale" in out
    assert "[follow_up] later docs follow-up" in out


def _content_only(raw_json: str) -> dict:
    """Parse a frame JSON file, dropping the ``updated`` timestamp — the one
    field ``store.save`` always bumps on every write, unrelated to the
    escaping fix under test here.
    """
    d = json.loads(raw_json)
    d.pop("updated", None)
    return d


def test_repeated_export_is_byte_stable_and_frame_json_content_unchanged(
    tmp_path, monkeypatch
) -> None:
    # #87 acceptance (c6/h6, c22/h18): escaping is presentational only — the
    # rendered spec-md is byte-stable across repeated exports of the same
    # frame, and the frame JSON's content (everything `show --json` reads,
    # modulo the `updated` timestamp every save bumps) is untouched.
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    frame_json_path = store.path_for(store.current_slug())
    first_spec = spec_path.read_text(encoding="utf-8")
    first_json = frame_json_path.read_text(encoding="utf-8")

    main(["export"])

    second_spec = spec_path.read_text(encoding="utf-8")
    second_json = frame_json_path.read_text(encoding="utf-8")
    assert first_spec == second_spec
    assert _content_only(first_json) == _content_only(second_json)

    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ── t14 (#92): a re-exported spec with a contested-by-deviation marker ──────


def _build_and_export_contested_frame(monkeypatch, tmp_path) -> Path:
    """A converged, exported frame carrying an approved deviation (#92) whose
    ``--affects`` names a confirmed claim and whose ``reason`` is hostile
    input (an underscore identifier, a bare URL, trailing punctuation) --
    proves the contested marker's own ``_safe()`` composition holds under the
    same hostile-input contract every other verbatim field in this file is
    pinned against.
    """
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the contested marker end to end."])
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind} text.", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold.", "--origin", "user"])
    slug = store.current_slug()

    main(["plan", "new", "--frame", slug])
    plan = plan_store.load(slug)
    args = ["plan", "task", "cover everything.", "--accept", "all good."]
    for tg in plan.targets:
        args += ["--covers", tg.id]
    main(args)

    main(
        [
            "deviate",
            "walk transcripts recursively",
            "--task",
            "t1",
            "--reason",
            "measured 408 of 695 files (59%) below __the_depth__ the walker "
            "searches, see https://example.com/report.",
            "--affects",
            "c1",
            "--classification",
            "risky",
        ]
    )

    main(["converge"])
    main(["export"])
    frame = store.load(slug)
    return Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"


def test_contested_marker_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_contested_frame(monkeypatch, tmp_path)
    assert spec_path.exists()
    out = spec_path.read_text(encoding="utf-8")
    assert "contested by `d1`" in out
    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ── t19: the repo's OWN issue-backlog-sweep frame + plan as lint corpus ───────
#
# Every test above builds a synthetic frame. This one exports the real,
# committed `.devague/frames/issue-backlog-sweep.json` and its plan — the
# largest real corpus this repo has (36 claims, 23 scope entries, 5 parks, 19
# tasks) and the one whose text was written by hand rather than shaped to suit
# the renderer. It is the release's own dogfood: if the escaping/park/scope
# rendering shipped here cannot lint the state that specified it, the fix is
# not done. It also guards against the artifact drifting out of lint-clean as
# the frame grows on future runs.

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SWEEP_SLUG = "issue-backlog-sweep"


def _copy_real_sweep_state(tmp_path) -> bool:
    """Copy the committed sweep frame + plan into ``tmp_path``. Returns False
    when they are absent (a consumer checkout without the state) so the test
    skips rather than failing on someone else's tree.
    """
    frame_src = _REPO_ROOT / ".devague" / "frames" / f"{_SWEEP_SLUG}.json"
    plan_src = _REPO_ROOT / ".devague" / "plans" / f"{_SWEEP_SLUG}.json"
    if not (frame_src.exists() and plan_src.exists()):
        return False
    for sub, src in (("frames", frame_src), ("plans", plan_src)):
        dest_dir = tmp_path / ".devague" / sub
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / f"{_SWEEP_SLUG}.json").write_text(src.read_text(encoding="utf-8"))
    return True


def test_real_issue_backlog_sweep_frame_exports_lint_clean(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    if not _copy_real_sweep_state(tmp_path):
        pytest.skip("committed issue-backlog-sweep state not present in this checkout")

    assert main(["converge", "--frame", _SWEEP_SLUG]) == 0
    assert main(["export", "--frame", _SWEEP_SLUG]) == 0
    frame = store.load(_SWEEP_SLUG)
    spec_path = Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"
    assert spec_path.exists()

    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_real_issue_backlog_sweep_plan_exports_lint_clean(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    if not _copy_real_sweep_state(tmp_path):
        pytest.skip("committed issue-backlog-sweep state not present in this checkout")

    assert main(["plan", "converge", "--plan", _SWEEP_SLUG]) == 0
    assert main(["plan", "export", "--plan", _SWEEP_SLUG]) == 0
    plan = plan_store.load(_SWEEP_SLUG)
    plan_path = Path("docs/plans") / f"{plan.created[:10]}-{plan.slug}.md"
    assert plan_path.exists()

    result = _run_markdownlint(plan_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_real_sweep_export_is_byte_stable_and_never_mutates_frame_json(
    tmp_path, monkeypatch
) -> None:
    # The release's escaping is presentational only (#87 c22/h18) — proven here
    # against real state rather than a synthetic fixture.
    monkeypatch.chdir(tmp_path)
    if not _copy_real_sweep_state(tmp_path):
        pytest.skip("committed issue-backlog-sweep state not present in this checkout")

    main(["converge", "--frame", _SWEEP_SLUG])
    main(["export", "--frame", _SWEEP_SLUG])
    frame = store.load(_SWEEP_SLUG)
    spec_path = Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"
    frame_json_path = store.path_for(_SWEEP_SLUG)
    first_spec = spec_path.read_text(encoding="utf-8")
    first_json = frame_json_path.read_text(encoding="utf-8")

    main(["export", "--frame", _SWEEP_SLUG])

    assert spec_path.read_text(encoding="utf-8") == first_spec
    assert _content_only(frame_json_path.read_text(encoding="utf-8")) == _content_only(first_json)


# ── t19 / #94: an underscore-bearing URL survives the real renderers ──────────


def test_underscore_url_in_claim_text_survives_export_and_lints(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    url = "https://example.com/some_path/file_name"
    main(
        [
            "new",
            f"Ship the walker documented at {url}",
            "--title",
            "underscore-url",
        ]
    )
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind}: see {url} for the corpus", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", f"verified against {url}", "--origin", "user"])
    main(["converge"])
    main(["export"])
    frame = store.load(store.current_slug())
    spec_path = Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"
    out = spec_path.read_text(encoding="utf-8")

    # The link is intact and autolinked — not truncated at the first
    # underscore, and not backticked mid-URL (#94, both composition orders).
    assert f"<{url}>" in out
    assert "some_path`" not in out
    assert "<https://example.com/>" not in out

    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_underscore_url_in_plan_task_survives_export_and_lints(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    url = "https://example.com/org/repo/main/__init__.py"
    main(["new", "Ship the plan renderer", "--title", "underscore-url-plan"])
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind} text.", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold.", "--origin", "user"])
    main(["converge"])
    slug = store.current_slug()
    main(["plan", "new", "--frame", slug])
    plan = plan_store.load(slug)
    args = ["plan", "task", f"Walk the corpus at {url}", "--accept", f"verified at {url}"]
    for tg in plan.targets:
        args += ["--covers", tg.id]
    main(args)
    main(["plan", "converge"])
    main(["plan", "export"])
    plan = plan_store.load(slug)
    plan_path = Path("docs/plans") / f"{plan.created[:10]}-{plan.slug}.md"
    out = plan_path.read_text(encoding="utf-8")

    assert f"<{url}>" in out
    assert "`__init__.py`>" not in out

    result = _run_markdownlint(plan_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
