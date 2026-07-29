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
4. a broken delivery ledger is translated into an actionable
   :class:`DevagueError` instead of falling through as "unexpected" (Q5); a
   raw ``|`` or newline in a deviation's ``reason`` cannot corrupt the Drift
   From Plan table (Q2); ``cmd_summary`` has a single return path
   (SonarCloud S3516) and the "no tasks" literal is a single shared constant
   (SonarCloud S1192)
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check only, not shipped code
from pathlib import Path

import pytest

from devague import delivery_store, plan_store, store
from devague.cli import main
from devague.cli._commands import summary as summary_cmd
from devague.delivery import DELIVERY_SCHEMA_VERSION, Delivery
from devague.frame import Frame
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


def test_planned_work_lists_only_confirmed_task_id_and_summary_verbatim() -> None:
    # #88: Planned Work is scoped to confirmed tasks only — a rejected task
    # (however it got there) must never appear, even though it still lives on
    # plan.tasks. Flips the old "every task appears" assumption pinned here
    # before the fix (bit #88).
    plan, frame = _bare_plan_and_frame()
    dropped = plan.add_task("dropped task")
    plan.set_status(dropped.id, "rejected")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    planned = out.split("## Planned Work")[1].split("## Actual Delivery")[0]
    assert "`t1` — first task" in planned
    assert "`t2` — second task" in planned
    assert dropped.id not in planned
    assert "dropped task" not in planned


def test_actual_delivery_has_one_row_per_confirmed_task_with_fill_placeholders() -> None:
    # #88: a rejected task is never paired with a `<fill: status>` row — that
    # pairing is exactly the honesty hazard the issue names (it invites
    # recording a planning decision as a delivery failure). Flips the old
    # "one row per task regardless of status" assumption pinned here before
    # the fix (bit #88).
    plan, frame = _bare_plan_and_frame()
    dropped = plan.add_task("dropped task")
    plan.set_status(dropped.id, "rejected")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    actual = out.split("## Actual Delivery")[1].split("## Mid-work Decisions")[0]
    for tid in ("t1", "t2"):
        assert f"| `{tid}` | `<fill: status>` | `<fill: what landed>` |" in actual
    assert f"| `{dropped.id}` |" not in actual


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


def test_no_tasks_placeholder_is_a_single_shared_constant() -> None:
    # SonarCloud python:S1192 — "(no tasks recorded on this plan)" was
    # duplicated 3x (Planned Work / Actual Delivery / --pr wave-task-map);
    # one module-level constant must back every occurrence.
    assert summary_md.NO_TASKS_PLACEHOLDER == "(no tasks recorded on this plan)"
    plan = Plan(slug="empty", title="Empty Plan", frame_slug="empty")
    delivery = Delivery(plan_slug=plan.slug)
    summary_out = summary_md.render_summary(plan, None, delivery)
    pr_out = summary_md.render_pr_summary(plan, None, delivery)
    assert summary_out.count(summary_md.NO_TASKS_PLACEHOLDER) == 2  # Planned Work + Actual Delivery
    assert summary_md.NO_TASKS_PLACEHOLDER in pr_out  # --pr wave/task map


# ── #88: summary scoped to confirmed tasks ───────────────────────────────────
#
# Repro shape from the issue: a plan rebuilt after scope changes can carry far
# more rejected tasks than confirmed ones (19 confirmed / 68 rejected in the
# reporter's real plan). Planned Work / Actual Delivery must reflect only the
# confirmed contract; a single line preserves the rejected count without
# padding either list with 68 undifferentiated rows. A `proposed` task is
# neither the confirmed contract nor an explicit rejection (it is still under
# adjudication), so it is excluded from both lists AND from the rejected
# count — folding an open decision into "rejected" would misrepresent it as
# already decided against, the same honesty conflation the issue is about.


def test_mixed_status_plan_scopes_planned_work_and_actual_delivery_to_confirmed() -> None:
    # #88 acceptance criteria, pinned literally: "a plan with N confirmed and M
    # rejected tasks emits exactly N Actual Delivery rows and N Planned Work
    # entries plus one line counting the M rejected".
    n_confirmed, n_rejected = 2, 3
    plan, frame = _bare_plan_and_frame()  # seeds t1, t2 confirmed (N=2)
    rejected_ids = []
    for i in range(n_rejected):
        t = plan.add_task(f"rejected task {i}")
        plan.set_status(t.id, "rejected")
        rejected_ids.append(t.id)
    proposed = plan.add_task("still deciding", origin="llm")  # proposed: neither list, no count

    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    planned = out.split("## Planned Work")[1].split("## Actual Delivery")[0]
    actual = out.split("## Actual Delivery")[1].split("## Mid-work Decisions")[0]

    planned_entries = [ln for ln in planned.splitlines() if ln.startswith("- `t")]
    actual_rows = [ln for ln in actual.splitlines() if ln.startswith("| `t")]
    assert len(planned_entries) == n_confirmed
    assert len(actual_rows) == n_confirmed

    for excluded_id in rejected_ids + [proposed.id]:
        assert excluded_id not in planned
        assert excluded_id not in actual

    rejected_line = f"{n_rejected} tasks were rejected during planning — see `devague plan show`."
    assert rejected_line in planned
    # exactly one such line in the whole artifact — not per-section noise
    assert out.count("rejected during planning") == 1


def test_rejected_count_line_uses_singular_wording_for_exactly_one() -> None:
    plan, frame = _bare_plan_and_frame()
    t = plan.add_task("dropped")
    plan.set_status(t.id, "rejected")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    assert "1 task was rejected during planning — see `devague plan show`." in out


def test_no_rejected_tasks_means_no_rejected_count_line() -> None:
    plan, frame = _bare_plan_and_frame()
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    assert "rejected during planning" not in out


def test_summary_data_scopes_planned_work_and_actual_delivery_to_confirmed() -> None:
    plan, frame = _bare_plan_and_frame()
    dropped = plan.add_task("dropped")
    plan.set_status(dropped.id, "rejected")
    proposed = plan.add_task("still deciding", origin="llm")
    data = summary_md.summary_data(plan, frame, Delivery(plan_slug=plan.slug))
    planned_ids = [t["id"] for t in data["sections"]["planned_work"]]
    actual_ids = [t["id"] for t in data["sections"]["actual_delivery"]]
    assert planned_ids == ["t1", "t2"]
    assert actual_ids == ["t1", "t2"]
    assert dropped.id not in planned_ids
    assert proposed.id not in planned_ids
    # JSON parity for the markdown's single rejected-count line: the ids, not
    # just a count (mirroring pending_deviations, which carries ids too).
    assert data["sections"]["rejected_tasks"] == [dropped.id]


def test_pr_wave_and_task_map_stay_rejected_free_on_a_mixed_status_plan() -> None:
    # #88 acceptance criteria: "the --pr wave map stays rejected-free". Pinned
    # here (not in tests/test_plan.py, which already pins dependency_waves
    # itself excluding rejected tasks) because this is the render-layer
    # regression: summary_md must not reintroduce a rejected task via some
    # other path (e.g. iterating plan.tasks directly instead of the waves).
    plan, frame = _bare_plan_and_frame()
    dead = plan.add_task("dead task")
    plan.set_status(dead.id, "rejected")
    delivery = Delivery(plan_slug=plan.slug)

    out = summary_md.render_pr_summary(plan, frame, delivery)
    assert dead.id not in out
    assert "dead task" not in out

    data = summary_md.pr_data(plan, frame, delivery)
    assert all(dead.id not in wave for wave in data["waves"])
    assert dead.id not in data["tasks"]


def test_render_summary_with_rejected_tasks_is_markdownlint_clean_hand_rolled() -> None:
    plan, frame = _bare_plan_and_frame()
    t = plan.add_task("dropped")
    plan.set_status(t.id, "rejected")
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "reason", origin="user", classification="acceptable")
    out = summary_md.render_summary(plan, frame, delivery)
    assert_markdownlint_clean(out)


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


# ── lapse ledger evidence in Delivery Claims (issue #97 t3) ──────────────────
#
# devague summary cites approved reasoning-degradation lapses (Frame.lapses,
# issue #97 t1) as evidence grounding the Delivery Claims confidence column,
# following the exact approved/pending/rejected discipline _mid_work_lines and
# _drift_lines already apply to deviation records: approved lapses render
# fully, a proposed (not-yet-adjudicated) lapse renders as visibly pending, a
# rejected lapse is omitted entirely, and a frame with no lapses at all (or no
# frame — a degraded load, criterion 4) leaves the existing hardcoded
# placeholder row as the section's only content.


def test_delivery_claims_keeps_placeholder_row_when_frame_is_none() -> None:
    plan, frame = _bare_plan_and_frame()  # frame is None
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    assert "`<fill: what was delivered>`" in claims
    assert "`<fill: confidence>`" in claims
    assert "Lapse ledger evidence" not in claims


def test_delivery_claims_keeps_placeholder_row_when_lapses_list_is_empty() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    assert "`<fill: what was delivered>`" in claims
    assert "Lapse ledger evidence" not in claims


def test_delivery_claims_cites_approved_lapse_as_evidence() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_lapse("grader-unverified", "graded without a rubric", origin="user")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    assert "Lapse ledger evidence" in claims
    assert "`l1`" in claims
    assert "`grader-unverified`" in claims
    assert "graded without a rubric" in claims


def test_delivery_claims_proposed_lapse_renders_visibly_pending_not_approved() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_lapse("control-absent", "no control group used", origin="llm")  # -> proposed
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    assert "`l1`" in claims
    assert "pending approval" in claims
    # never rendered as a row of the approved-evidence table
    assert "| `l1` |" not in claims
    assert "no control group used" not in claims


def test_delivery_claims_omits_rejected_lapse_entirely() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    rec = frame.add_lapse("n-below-claim", "claimed generality from n=1", origin="user")
    frame.set_lapse_status(rec.id, "rejected")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    assert "l1" not in out
    assert "claimed generality from n=1" not in out


def test_delivery_claims_lapse_evidence_table_escapes_pipe_and_flattens_newline() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_lapse("provenance-missing", "cited | without\na source", origin="user")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    row = next(ln for ln in claims.splitlines() if ln.startswith("| `l1`"))
    assert "\n" not in row
    assert "\\|" in row
    # splitting on an *unescaped* pipe still yields exactly 5 fields: leading
    # '', 3 columns, trailing '' — the raw pipe in `what` never adds a column.
    cells = re.split(r"(?<!\\)\|", row)
    assert len(cells) == 5


def test_render_summary_with_lapses_is_markdownlint_clean_hand_rolled() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_lapse("grader-unverified", "graded without a rubric", origin="user")
    frame.add_lapse("control-absent", "no control group used", origin="llm")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    assert_markdownlint_clean(out)


@pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)
def test_render_summary_with_lapses_passes_real_markdownlint_cli2(tmp_path) -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_lapse("grader-unverified", "graded without a rubric", origin="user")
    frame.add_lapse("control-absent", "no control group used", origin="llm")
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    summary_path = tmp_path / "summary_lapses.md"
    summary_path.write_text(out, encoding="utf-8")
    result = _run_markdownlint(summary_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_summary_data_lapse_evidence_shape() -> None:
    plan, _ = _bare_plan_and_frame()
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_lapse("grader-unverified", "graded without a rubric", origin="user")
    frame.add_lapse("control-absent", "no control group used", origin="llm")
    data = summary_md.summary_data(plan, frame, Delivery(plan_slug=plan.slug))
    evidence = data["sections"]["lapse_evidence"]
    assert evidence["approved"] == [
        {"id": "l1", "code": "grader-unverified", "what": "graded without a rubric"}
    ]
    assert evidence["pending"] == ["l2"]


def test_summary_data_lapse_evidence_empty_when_no_frame() -> None:
    plan, frame = _bare_plan_and_frame()  # frame is None
    data = summary_md.summary_data(plan, frame, Delivery(plan_slug=plan.slug))
    assert data["sections"]["lapse_evidence"] == {"approved": [], "pending": []}


def test_cli_summary_cites_lapse_filed_directly_on_frame(tmp_path, monkeypatch, capsys) -> None:
    # #97 t3: no `devague lapse` CLI verb exists yet in this worktree (t2 is a
    # sibling task) — files the lapse straight onto the stored Frame the way
    # t1's own tests do, then drives `devague summary` end to end through the
    # real CLI + store round-trip.
    _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    slug = store.current_slug()
    f = store.load(slug)
    f.add_lapse("grader-unverified", "graded without a rubric", origin="user")
    f.add_lapse("control-absent", "no control group used", origin="llm")
    store.save(f)
    capsys.readouterr()
    rc = main(["summary"])
    assert rc == 0
    out = capsys.readouterr().out
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    assert "`l1`" in claims
    assert "graded without a rubric" in claims
    assert "`l2`" in claims
    assert "pending approval" in claims


def test_cli_summary_degrades_with_lapses_exactly_as_today_when_frame_missing(
    tmp_path, monkeypatch, capsys
) -> None:
    # Acceptance criterion 4: a frame that fails to load degrades in summary
    # exactly as today — no new failure mode introduced by the lapse ledger.
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    store.path_for(slug).unlink()
    capsys.readouterr()
    rc = main(["summary"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No source frame available" in out
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    assert "Lapse ledger evidence" not in claims


# ── drift table safety: a raw '|'/newline in `reason` cannot break the table (Q2) ──


def test_drift_lines_escapes_pipe_in_reason_to_protect_table_structure() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "blocked | upstream | vendor", origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    row = next(ln for ln in drift.splitlines() if ln.startswith("| `t1`"))
    # the raw pipes from the reason were escaped, not left as live separators
    assert "\\|" in row
    # splitting on an *unescaped* pipe must still yield exactly 5 fields:
    # leading '', 3 columns, trailing ''
    cells = re.split(r"(?<!\\)\|", row)
    assert len(cells) == 5


def test_drift_lines_flattens_newline_in_reason() -> None:
    plan, frame = _bare_plan_and_frame()
    delivery = Delivery(plan_slug=plan.slug)
    delivery.add_deviation("swap", "t1", "line one\nline two", origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    drift = out.split("## Drift From Plan")[1].split("## Evidence")[0]
    row = next(ln for ln in drift.splitlines() if ln.startswith("| `t1`"))
    assert "\n" not in row
    assert "line one line two" in row


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
def test_cmd_summary_has_a_single_return_statement() -> None:
    # SonarCloud python:S3516 ("Refactor this method to not always return the
    # same value"): cmd_summary had two separate `return 0` branches (--pr and
    # non---pr), each always returning the literal 0. `_dispatch` treats a
    # `None` return as success too, so the fix folds the branches down to one
    # return path instead of duplicating the literal.
    src = inspect.getsource(summary_cmd.cmd_summary)
    tree = ast.parse(src)
    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) <= 1


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


# ── broken delivery ledger errors are translated, not "unexpected" (Q5) ──────


def test_cli_summary_delivery_schema_too_new_errors_with_hint(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    delivery_store.save(Delivery(plan_slug=slug))
    p = delivery_store.path_for(slug)
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = DELIVERY_SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")
    capsys.readouterr()
    rc = main(["summary"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "upgrade devague" in err
    assert "hint:" in err
    assert "unexpected" not in err


def test_cli_summary_delivery_malformed_json_errors_with_hint(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _plan_with_two_tasks(monkeypatch, tmp_path, capsys)
    p = delivery_store.path_for(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not valid json", encoding="utf-8")
    capsys.readouterr()
    rc = main(["summary"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "malformed" in err
    assert "repair or remove" in err
    assert "unexpected" not in err


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
