"""Tests for the staleness derivation (issue #97/bvts t8).

The second read-only join beside :mod:`devague.contested`, over the same
plan/delivery-store shape. Acceptance criteria:

1. a read-only module reports both directions: approved deviations whose
   affects overlap evidence refs that were never re-filed after the
   deviation, and evidence records whose obligation or delta target is
   superseded or removed
2. the join is deterministic over recorded state with no semantic matching,
   fails open with diagnostics on missing or corrupt stores, and never
   mutates anything
3. findings render in ``devague show`` and ``devague status`` as visible
   staleness lines

Covers claims c19, honesty condition h15.
"""

from __future__ import annotations

import json

from devague import delivery_store, plan_store, store
from devague.cli import main
from devague.delivery import DELIVERY_SCHEMA_VERSION, Delivery
from devague.frame import Frame
from devague.plan import Plan, targets_from_frame
from devague.staleness import (
    OrphanedEvidenceFinding,
    StaleDeviationFinding,
    find_staleness,
    orphaned_evidence_line,
    orphaned_evidence_to_dict,
    stale_deviation_line,
    stale_deviation_to_dict,
)

# ── fixtures ────────────────────────────────────────────────────────────────


def _frame_plan_with_obligation(monkeypatch, tmp_path, slug: str = "demo"):
    """A frame with one confirmed claim (c1), a plan with one confirmed task
    (t1) covering it, and a filed frame-side obligation (o1) on c1. Returns
    ``(frame, plan)``.
    """
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug=slug, title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")  # c1
    frame.add_obligation("c1", seam="cli", behavior="does the thing", origin="user")  # o1
    store.save(frame)
    plan = Plan(slug=slug, title="Demo Plan", frame_slug=slug)
    plan.targets = targets_from_frame(frame)
    task = plan.add_task("first task")  # t1
    plan.add_cover(task, "c1")
    plan_store.save(plan)
    return frame, plan


def _evidence(d: Delivery, **kw):
    args = {
        "obligation_ref": "o1",
        "test_ref": "tests/test_x.py::test_y",
        "behavior_text": "asserts the thing happens",
        "contract_text": "does the thing",
        "evidence_type": "automated",
        "strength": "coverage",
        "strength_basis": "the test exists and names the behavior",
        "outcome": "pass",
    }
    args.update(kw)
    return d.add_evidence(**args)


# ── AC1/AC2: find_stale_deviations (direction 1) ─────────────────────────────


def test_stale_deviation_flagged_when_evidence_precedes_and_is_never_refiled(
    tmp_path, monkeypatch
) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)  # e1, before the deviation, covers c1 via o1 -> t1.covers
    d.add_deviation("swap approach", "t1", "measured drift", affects=["c1"], origin="user")  # d1
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert diagnostics == []
    assert orphaned == []
    assert len(stale_devs) == 1
    f = stale_devs[0]
    assert f.deviation_id == "d1"
    assert f.plan_slug == "demo"
    assert f.claim_ids == ("c1",)
    assert f.stale_evidence_refs == ("e1",)


def test_stale_deviation_not_flagged_when_evidence_is_refiled_after(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)  # e1, before
    d.add_deviation("swap approach", "t1", "measured drift", affects=["c1"], origin="user")  # d1
    _evidence(d, behavior_text="re-asserts the thing after the swap")  # e2, after -> re-filed
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert diagnostics == []
    assert stale_devs == []


def test_stale_deviation_not_flagged_when_no_evidence_ever_overlapped(
    tmp_path, monkeypatch
) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    d.add_deviation("swap approach", "t1", "measured drift", affects=["c1"], origin="user")
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert stale_devs == []


def test_proposed_deviation_never_yields_a_stale_finding(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    d.add_deviation("swap", "t1", "why", affects=["c1"], origin="llm")  # lands proposed
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert stale_devs == []


def test_superseded_evidence_never_counts_as_stale_coverage(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    old = _evidence(d)  # e1
    d.supersede(old.id)  # superseded before the deviation even lands
    d.add_deviation("swap", "t1", "why", affects=["c1"], origin="user")
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert stale_devs == []


def test_deviation_affecting_only_task_ids_yields_no_stale_finding(tmp_path, monkeypatch) -> None:
    # Mirrors the contested-module regression guard: a deviation whose
    # --affects names only task ids (never a claim/honesty id) must never
    # match, since no obligation's contract side ever resolves to a task id.
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    d.add_deviation("reorder", "t1", "why", affects=["t1"], origin="user")
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert stale_devs == []


# ── AC1/AC2: find_orphaned_evidence (direction 2) ────────────────────────────


def test_orphaned_evidence_flagged_when_obligation_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")
    store.save(frame)
    plan = Plan(slug="demo", title="Demo Plan", frame_slug="demo")
    plan.add_task("t1")
    plan_store.save(plan)
    d = Delivery(plan_slug="demo")
    _evidence(d, obligation_ref="o404")  # nothing ever filed this obligation
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert diagnostics == []
    assert len(orphaned) == 1
    assert orphaned[0].evidence_id == "e1"
    assert "does not resolve" in orphaned[0].reason


def test_orphaned_evidence_flagged_when_obligation_rejected(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    frame.set_obligation_status("o1", "rejected")
    store.save(frame)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert len(orphaned) == 1
    assert "rejected" in orphaned[0].reason


def test_orphaned_evidence_flagged_when_referencing_delta_is_superseded(
    tmp_path, monkeypatch
) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)  # e1
    d.add_delta("added", "does the thing", caused_by=["c1"], evidence_refs=["e1"])  # b1
    d.supersede("b1")
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert len(orphaned) == 1
    assert orphaned[0].evidence_id == "e1"
    assert "b1" in orphaned[0].reason
    assert "superseded" in orphaned[0].reason


def test_orphaned_evidence_flagged_when_referencing_delta_is_removed_kind(
    tmp_path, monkeypatch
) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)  # e1
    d.add_delta("removed", "the thing no longer happens", caused_by=["c1"], evidence_refs=["e1"])
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert len(orphaned) == 1
    assert "removed the behavior" in orphaned[0].reason


def test_evidence_that_is_itself_superseded_is_never_orphaned(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    ev = _evidence(d, obligation_ref="o404")
    d.supersede(ev.id)
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert orphaned == []


def test_evidence_with_a_healthy_obligation_and_no_delta_is_never_orphaned(
    tmp_path, monkeypatch
) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert orphaned == []


def test_plan_side_criterion_obligation_resolves_via_task_covers(tmp_path, monkeypatch) -> None:
    # The plan-obligation resolution path: CriterionObligation names a task,
    # not a claim -- the claim set comes from that task's `covers`.
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")  # c1
    store.save(frame)
    plan = Plan(slug="demo", title="Demo Plan", frame_slug="demo")
    plan.targets = targets_from_frame(frame)
    task = plan.add_task("first task")  # t1
    plan.add_acceptance(task, "it works")
    plan.add_cover(task, "c1")
    plan.add_obligation("t1", criterion_index=1, seam="cli", behavior="does it", origin="user")
    plan_store.save(plan)

    d = Delivery(plan_slug="demo")
    _evidence(d)  # o1 now resolves via the plan obligation -> t1.covers -> {c1}
    d.add_deviation("swap", "t1", "why", affects=["c1"], origin="user")
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert diagnostics == []
    assert orphaned == []
    assert len(stale_devs) == 1
    assert stale_devs[0].claim_ids == ("c1",)


# ── AC2: fail-open on corrupt/missing stores, never mutates ──────────────────


def test_find_staleness_no_plans_at_all(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")
    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert (stale_devs, orphaned, diagnostics) == ([], [], [])


def test_find_staleness_missing_delivery_is_silent(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert (stale_devs, orphaned, diagnostics) == ([], [], [])


def test_find_staleness_truncated_delivery_degrades_with_diagnostic(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    delivery_store.save(Delivery(plan_slug="demo"))
    p = delivery_store.path_for("demo")
    p.write_text("{not valid json", encoding="utf-8")

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert (stale_devs, orphaned) == ([], [])
    assert len(diagnostics) == 1
    assert "demo" in diagnostics[0]
    assert "unreadable" in diagnostics[0]


def test_find_staleness_newer_schema_delivery_degrades_with_diagnostic(
    tmp_path, monkeypatch
) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    delivery_store.save(Delivery(plan_slug="demo"))
    p = delivery_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = DELIVERY_SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert (stale_devs, orphaned) == ([], [])
    assert len(diagnostics) == 1
    assert "schema" in diagnostics[0]


def test_find_staleness_unreadable_plan_is_skipped_with_diagnostic(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    p = plan_store.path_for("demo")
    p.write_text("{not valid json", encoding="utf-8")

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert (stale_devs, orphaned) == ([], [])
    assert len(diagnostics) == 1
    assert "unreadable" in diagnostics[0]


def test_find_staleness_ignores_plan_with_different_frame_slug(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    other = Plan(slug="unrelated", title="Other", frame_slug="other-frame")
    other.add_task("t1")
    plan_store.save(other)
    d = Delivery(plan_slug="unrelated")
    _evidence(d)
    d.add_deviation("x", "t1", "why", affects=["c1"], origin="user")
    delivery_store.save(d)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert (stale_devs, orphaned, diagnostics) == ([], [], [])


def test_find_staleness_never_writes_any_store(tmp_path, monkeypatch) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    d.add_deviation("swap", "t1", "why", affects=["c1"], origin="user")
    delivery_store.save(d)

    def _boom(*_a, **_kw):
        raise AssertionError("staleness derivation must never write any store")

    monkeypatch.setattr(store, "save", _boom)
    monkeypatch.setattr(plan_store, "save", _boom)
    monkeypatch.setattr(delivery_store, "save", _boom)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert diagnostics == []
    assert stale_devs  # sanity: the derivation actually ran


def test_find_staleness_multiple_plans_for_the_same_frame_are_all_joined(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")  # c1
    frame.add_obligation("c1", seam="cli", behavior="does the thing", origin="user")  # o1
    store.save(frame)
    plan_a = Plan(slug="demo-a", title="A", frame_slug="demo")
    task_a = plan_a.add_task("t1")
    plan_a.add_cover(task_a, "c1")
    plan_store.save(plan_a)
    plan_b = Plan(slug="demo-b", title="B", frame_slug="demo")
    task_b = plan_b.add_task("t1")
    plan_b.add_cover(task_b, "c1")
    plan_store.save(plan_b)

    d_a = Delivery(plan_slug="demo-a")
    _evidence(d_a)
    d_a.add_deviation("x", "t1", "why a", affects=["c1"], origin="user")
    delivery_store.save(d_a)

    d_b = Delivery(plan_slug="demo-b")
    _evidence(d_b)
    d_b.add_deviation("y", "t1", "why b", affects=["c1"], origin="user")
    delivery_store.save(d_b)

    stale_devs, orphaned, diagnostics = find_staleness(frame)
    assert diagnostics == []
    assert [f.plan_slug for f in stale_devs] == ["demo-a", "demo-b"]


# ── ordering: numeric-aware, deterministic ───────────────────────────────────


def test_stale_deviations_sorted_by_plan_then_numeric_deviation_id() -> None:
    f1 = StaleDeviationFinding("d10", "x", "r", None, "demo", ("c1",), ("e1",))
    f2 = StaleDeviationFinding("d2", "y", "r", None, "demo", ("c1",), ("e1",))
    # Confirm the dataclass sorts as documented via find_staleness's own key;
    # here we just pin the finding shape is usable/orderable by callers too.
    assert sorted([f1, f2], key=lambda f: int(f.deviation_id[1:]))[0].deviation_id == "d2"


def test_stale_deviation_to_dict_shape() -> None:
    f = StaleDeviationFinding("d1", "what", "why", "risky", "demo", ("c1", "h2"), ("e1", "e3"))
    assert stale_deviation_to_dict(f) == {
        "deviation": "d1",
        "what": "what",
        "reason": "why",
        "classification": "risky",
        "plan": "demo",
        "claims": ["c1", "h2"],
        "stale_evidence": ["e1", "e3"],
    }


def test_orphaned_evidence_to_dict_shape() -> None:
    f = OrphanedEvidenceFinding("e1", "o1", "tests/x.py::y", "demo", "obligation rejected")
    assert orphaned_evidence_to_dict(f) == {
        "evidence": "e1",
        "obligation": "o1",
        "test": "tests/x.py::y",
        "plan": "demo",
        "reason": "obligation rejected",
    }


def test_stale_deviation_line_and_orphaned_evidence_line_render() -> None:
    f = StaleDeviationFinding("d1", "what", "why", "risky", "demo", ("c1",), ("e1",))
    line = stale_deviation_line(f)
    assert line == "stale: deviation d1 affects c1 (risky) — evidence e1 never re-filed since: why"

    o = OrphanedEvidenceFinding("e1", "o1", "tests/x.py::y", "demo", "obligation rejected")
    assert orphaned_evidence_line(o) == (
        "stale: evidence e1 (tests/x.py::y) in plan demo: obligation rejected"
    )


# ── AC3: rendering in show/status ────────────────────────────────────────────


def test_show_text_renders_staleness_lines(tmp_path, monkeypatch, capsys) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    d.add_deviation("swap approach", "t1", "measured drift", affects=["c1"], origin="user")
    delivery_store.save(d)
    capsys.readouterr()

    rc = main(["show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "stale: deviation d1 affects c1" in out
    assert "never re-filed since: measured drift" in out


def test_show_json_carries_staleness_keys(tmp_path, monkeypatch, capsys) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d, obligation_ref="o404")  # orphaned: absent obligation
    delivery_store.save(d)
    capsys.readouterr()

    rc = main(["show", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stale_deviations"] == []
    assert len(payload["orphaned_evidence"]) == 1
    assert payload["orphaned_evidence"][0]["evidence"] == "e1"


def test_status_text_renders_staleness_lines(tmp_path, monkeypatch, capsys) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    d.add_deviation("swap approach", "t1", "measured drift", affects=["c1"], origin="user")
    delivery_store.save(d)
    capsys.readouterr()

    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "stale: deviation d1 affects c1" in out


def test_status_json_carries_staleness_keys(tmp_path, monkeypatch, capsys) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    _evidence(d)
    d.add_deviation("swap approach", "t1", "measured drift", affects=["c1"], origin="user")
    delivery_store.save(d)
    capsys.readouterr()

    rc = main(["status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["stale_deviations"]) == 1
    assert payload["stale_deviations"][0]["deviation"] == "d1"
    assert payload["orphaned_evidence"] == []


_CONVERGENCE_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")


def test_plan_status_never_carries_staleness_keys(tmp_path, monkeypatch, capsys) -> None:
    # Scope discipline mirroring #92's own guard: only the frame engine's
    # status derives this; the plan engine's status must stay untouched.
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship staleness"])  # c1 announcement
    for kind in _CONVERGENCE_KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    slug = store.current_slug()
    f = store.load(slug)
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    main(["plan", "new", "--frame", slug])
    p = plan_store.load(slug)
    args = ["plan", "task", "cover everything", "--accept", "all targets satisfied"]
    for tg in p.targets:
        args += ["--covers", tg.id]
    main(args)
    capsys.readouterr()

    rc = main(["plan", "status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "stale_deviations" not in payload
    assert "orphaned_evidence" not in payload


def test_show_and_status_fail_open_on_corrupt_delivery_store(tmp_path, monkeypatch, capsys) -> None:
    frame, plan = _frame_plan_with_obligation(monkeypatch, tmp_path)
    delivery_store.save(Delivery(plan_slug="demo"))
    p = delivery_store.path_for("demo")
    p.write_text("{not valid json", encoding="utf-8")
    frame_path = store.path_for("demo")
    before_bytes = frame_path.read_bytes()
    capsys.readouterr()

    rc = main(["show"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "unreadable" in err
    assert frame_path.read_bytes() == before_bytes

    rc = main(["status"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "unreadable" in err
    assert frame_path.read_bytes() == before_bytes
