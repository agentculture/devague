"""Tests for ``devague summary`` and :mod:`devague.render.summary_md` (#53-esd t4).

Covers the render module directly (``render_summary`` / ``render_pr_summary`` /
``summary_data`` / ``pr_data``) and the CLI move end to end. Acceptance criteria:

1. renders all eight sections in the SKILL.md order; Intent and Planned Work
   pre-filled verbatim from frame and plan; Actual Delivery has one row per task
   with explicit fill placeholders; Mid-work Decisions and Drift From Plan quote
   approved deviation ids, never a proposed one as if it were approved
2. no placeholder ever renders as a completed claim; run status stays a
   placeholder; two renders are byte-identical; state is untouched
3. ``--pr`` emits the condensed PR-body skeleton (stdout-only tested);
   markdownlint-safe output
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check only, not shipped code
from pathlib import Path

import pytest

from devague import delivery_store, plan_store, store
from devague.cli import main
from devague.delivery import Delivery
from devague.plan import Plan
from devague.render import summary_md
from tests.test_render import assert_markdownlint_clean

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")
_SECTIONS_IN_ORDER = [
    "## Intent",
    "## Planned Work",
    "## Actual Delivery",
    "## Mid-work Decisions",
    "## Drift From Plan",
    "## Evidence",
    "## Delivery Claims",
    "## Remaining Work / Follow-up",
]

_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.yaml"


# ── fixtures ──────────────────────────────────────────────────────────────────
def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame that passes the frame gate; return its slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the execution seam"])  # c1 announcement
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def _plan_with_two_tasks(monkeypatch, tmp_path, capsys) -> str:
    """Seed a converged frame + plan with two tasks (t1, t2); return the plan slug."""
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "first task", "--accept", "criterion one", "--covers", "c1"])
    main(
        [
            "plan",
            "task",
            "second task",
            "--dep",
            "t1",
            "--accept",
            "criterion two",
            "--covers",
            "c2",
        ]
    )
    capsys.readouterr()
    return slug


def _bare_plan_and_frame() -> tuple[Plan, None]:
    p = Plan(slug="demo", title="Demo Plan", frame_slug="demo")
    p.add_task("first task")
    p.add_task("second task")
    return p, None


def _run_markdownlint(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_CONFIG), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        check=False,
    )


# ── render module: section shape ─────────────────────────────────────────────
def test_render_summary_has_all_eight_sections_in_order() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    positions = [out.index(h) for h in _SECTIONS_IN_ORDER]
    assert positions == sorted(positions)
    assert out.startswith("# Delivery Summary — Demo Plan")


def test_render_summary_run_status_is_placeholder() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    assert "run: `<complete | partial | failed>`" in out
    # never any of the real values standing in for the placeholder
    assert "run: `complete`" not in out
    assert "run: `partial`" not in out
    assert "run: `failed`" not in out


def test_planned_work_lists_every_task_id_and_summary_verbatim() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    planned = out.split("## Planned Work")[1].split("## Actual Delivery")[0]
    assert "`t1` — first task" in planned
    assert "`t2` — second task" in planned


def test_actual_delivery_has_one_row_per_task_with_fill_placeholders() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    actual = out.split("## Actual Delivery")[1].split("## Mid-work Decisions")[0]
    for tid in ("t1", "t2"):
        assert f"| `{tid}` | `<fill: status>` | `<fill: what landed>` |" in actual


def test_no_placeholder_ever_looks_like_a_completed_claim() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    # every `<fill: ...>` marker lives inside a backtick code span (never bare
    # '<' that could be mistaken for real inline HTML / an actual completed
    # value) — strip every code span and confirm no "<fill:" text survives
    # outside one.
    outside_code_spans = re.sub(r"`[^`]*`", "", out)
    assert "<fill:" not in outside_code_spans
    # "delivered"/"complete" only ever appear as fill-me prompt text inside a
    # backticked placeholder (e.g. "`<fill: what was delivered>`") — never as a
    # bare claim asserting something actually happened.
    assert "delivered" not in outside_code_spans.lower()
    assert "complete" not in outside_code_spans.lower()


def test_double_render_is_byte_identical() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    first = summary_md.render_summary(plan, frame, delivery)
    second = summary_md.render_summary(plan, frame, delivery)
    assert first == second


def test_render_summary_degrades_gracefully_with_no_frame() -> None:
    plan, _frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, None, Delivery(plan_slug=plan.slug))
    assert "No source frame available" in out
    assert "## Intent" in out


def test_empty_plan_shows_no_tasks_placeholder_text() -> None:
    plan = Plan(slug="empty", title="Empty Plan", frame_slug="empty")
    out = summary_md.render_summary(plan, None, Delivery(plan_slug=plan.slug))
    assert "(no tasks recorded on this plan)" in out


# ── deviation records: drift + mid-work ──────────────────────────────────────
def test_approved_deviation_appears_in_drift_and_mid_work() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation(
        "used a workaround", "t1", "blocked upstream", origin="user", classification="risky"
    )
    out = summary_md.render_summary(plan, frame, delivery)
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    mid_work = out.split("## Mid-work Decisions")[1].split("## Drift From Plan")[0]
    assert "`d1`" in drift
    assert "`t1`" in drift
    assert "`risky`" in drift
    assert "`d1`" in mid_work
    assert "used a workaround" in mid_work


def test_proposed_deviation_never_rendered_as_approved() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("llm proposed swap", "t1", "reason", origin="llm")  # -> proposed
    out = summary_md.render_summary(plan, frame, delivery)
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    mid_work = out.split("## Mid-work Decisions")[1].split("## Drift From Plan")[0]
    # never quoted as approved drift
    assert "`d1`" not in drift
    assert "no approved deviation records yet" in drift
    # surfaces in mid-work only under an explicit pending marker
    assert "`d1`" in mid_work
    assert "pending approval" in mid_work
    assert "llm proposed swap" not in drift


def test_rejected_deviation_omitted_everywhere() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("bad idea", "t1", "reason", origin="llm")
    delivery.set_status("d1", "rejected")
    out = summary_md.render_summary(plan, frame, delivery)
    assert "d1" not in out
    assert "bad idea" not in out


def test_missing_classification_on_approved_deviation_is_a_fill_placeholder() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user")  # approved, no classification
    out = summary_md.render_summary(plan, frame, delivery)
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    assert "`<fill: classification>`" in drift


def test_no_deviations_recorded_yet_empty_state() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    assert "(no deviations recorded yet)" in out


# ── markdown safety ───────────────────────────────────────────────────────────
def test_render_summary_is_markdownlint_clean_hand_rolled() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user", classification="acceptable")
    out = summary_md.render_summary(plan, frame, delivery)
    assert_markdownlint_clean(out)


def test_render_pr_summary_is_markdownlint_clean_hand_rolled() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user", classification="acceptable")
    out = summary_md.render_pr_summary(plan, frame, delivery)
    assert_markdownlint_clean(out)


@pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)
def test_render_summary_passes_real_markdownlint_cli2(tmp_path) -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user", classification="acceptable")
    out = summary_md.render_summary(plan, frame, delivery)
    pr_out = summary_md.render_pr_summary(plan, frame, delivery)
    summary_path = tmp_path / "summary.md"
    pr_path = tmp_path / "pr.md"
    summary_path.write_text(out, encoding="utf-8")
    pr_path.write_text(pr_out, encoding="utf-8")
    result = _run_markdownlint(summary_path, pr_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ── --pr mode ─────────────────────────────────────────────────────────────────
def test_pr_data_shape() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user", classification="acceptable")
    data = summary_md.pr_data(plan, frame, delivery)
    assert data["plan"] == plan.slug
    assert data["title"] == plan.title
    # _bare_plan_and_frame's two tasks carry no dependency, so both land in wave 0.
    assert data["waves"] == [["t1", "t2"]]
    assert data["tasks"] == {"t1": "first task", "t2": "second task"}
    assert data["approved_deviations"] == [
        {"id": "d1", "task": "t1", "what": "swap", "reason": "reason"}
    ]
    assert data["deliveries_pointer"].startswith("docs/deliveries/")
    assert data["deliveries_pointer"].endswith(f"-{plan.slug}.md")


def test_render_pr_summary_renders_title_announcement_waves_and_pointer() -> None:
    plan, _frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user")
    out = summary_md.render_pr_summary(plan, None, delivery)
    assert out.startswith("# Demo Plan")
    assert "## Wave / Task Map" in out
    assert "`t1` — first task" in out
    assert "## Approved Deviations" in out
    assert "`d1`" in out
    assert "Delivery summary: `docs/deliveries/" in out


# ── CLI: text / json / --pr / degrade / no plan ──────────────────────────────
def test_cli_summary_text_mode_prints_all_sections(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    rc = main(["summary"])
    assert rc == 0
    out = capsys.readouterr().out
    for h in _SECTIONS_IN_ORDER:
        assert h in out
    assert "`t1` — first task" in out
    assert "`t2` — second task" in out


def test_cli_summary_json_mode_shape(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    rc = main(["summary", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_status"] == "<complete | partial | failed>"
    ids = [t["id"] for t in payload["sections"]["planned_work"]]
    assert ids == ["t1", "t2"]
    assert payload["sections"]["intent"]["announcement"] == "Ship the execution seam"


def test_cli_summary_pr_mode_stdout_only(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    rc = main(["summary", "--pr"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("#")
    assert "## Wave / Task Map" in captured.out
    assert "Delivery summary: `docs/deliveries/" in captured.out


def test_cli_summary_pr_json_mode(tmp_path, monkeypatch, capsys) -> None:
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    rc = main(["summary", "--pr", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == slug
    assert payload["waves"] == [["t1"], ["t2"]]


def test_cli_summary_degrades_when_frame_deleted(tmp_path, monkeypatch, capsys) -> None:
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    store.path_for(slug).unlink()
    rc = main(["summary"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No source frame available" in out


def test_cli_summary_no_plan_selected_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["summary"])
    assert rc == 1
    assert "no plan selected" in capsys.readouterr().err


def test_cli_summary_plan_flag_selects_named_plan(tmp_path, monkeypatch, capsys) -> None:
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    rc = main(["summary", "--plan", slug])
    assert rc == 0
    assert "first task" in capsys.readouterr().out


# ── deviation records quoted end-to-end via the real CLI + delivery store ────
def test_cli_summary_quotes_approved_deviation_recorded_via_deviate(
    tmp_path, monkeypatch, capsys
) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    main(["deviate", "used a workaround", "--task", "t1", "--reason", "blocked upstream"])
    capsys.readouterr()
    rc = main(["summary"])
    assert rc == 0
    out = capsys.readouterr().out
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    assert "`d1`" in drift
    assert "blocked upstream" in drift


def test_cli_summary_proposed_deviation_not_quoted_as_drift(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    main(
        [
            "deviate",
            "llm swap",
            "--task",
            "t1",
            "--reason",
            "reason",
            "--origin",
            "llm",
        ]
    )
    capsys.readouterr()
    rc = main(["summary"])
    assert rc == 0
    out = capsys.readouterr().out
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    assert "d1" not in drift


# ── no mutation / determinism / no subprocess ────────────────────────────────
def test_summary_never_mutates_plan_frame_or_delivery_state(tmp_path, monkeypatch, capsys) -> None:
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    main(["deviate", "swap", "--task", "t1", "--reason", "why"])
    capsys.readouterr()

    plan_before = plan_store.path_for(slug).read_bytes()
    frame_before = store.path_for(slug).read_bytes()
    delivery_before = delivery_store.path_for(slug).read_bytes()

    main(["summary"])
    main(["summary", "--json"])
    main(["summary", "--pr"])
    main(["summary", "--pr", "--json"])

    assert plan_store.path_for(slug).read_bytes() == plan_before
    assert store.path_for(slug).read_bytes() == frame_before
    assert delivery_store.path_for(slug).read_bytes() == delivery_before


def test_cli_summary_double_render_byte_identical(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    main(["deviate", "swap", "--task", "t1", "--reason", "why"])
    capsys.readouterr()
    main(["summary"])
    first = capsys.readouterr().out
    main(["summary"])
    second = capsys.readouterr().out
    assert first == second


def test_summary_deterministic_no_subprocess_or_llm(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    called = {"n": 0}
    real_run = subprocess.run

    def _guard(*args, **kwargs):
        called["n"] += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _guard)
    main(["summary"])
    main(["summary", "--pr"])
    assert called["n"] == 0
