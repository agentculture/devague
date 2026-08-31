"""Tests for the today-spec projection (bvts t9, claim c7 / honesty condition h7).

The today spec is a projection of an explicit **behavior ledger** — the delta
records every delivery contributes — not a merge of frame claims. This module
pins the three acceptance criteria of t9:

1. a pure function projects current behaviors from delta records honoring
   ``superseded`` flags and supersedes links; conflicts with no covering link
   surface as explicit human-decision items, never auto-resolved;
2. the walk enumerates ``store.list_slugs`` plus the plan and delivery stores
   fail-open — a corrupt or newer-schema file is skipped with a visible
   diagnostic — and the same stores in produce the same projection out;
3. the projection computes its own coverage span (earliest/latest ledgered
   delivery, frames absent from the ledger) for the boundary statement.

Covers claim c7 and honesty condition h7.
"""

from __future__ import annotations

import json

import pytest

from devague import delivery_store, plan_store, store, today
from devague.delivery import DELIVERY_SCHEMA_VERSION, Delivery, RunReference
from devague.frame import Frame
from devague.plan import Plan

_FRAME_CREATED = "2026-01-01T00:00:00Z"
_PLAN_CREATED = "2026-01-02T00:00:00Z"


# ── fixtures ─────────────────────────────────────────────────────────────────


def _frame(slug: str, title: str = "A frame", created: str = _FRAME_CREATED) -> Frame:
    frame = Frame(slug=slug, title=title, created=created)
    store.save(frame)
    return frame


def _plan(slug: str, frame_slug: str, created: str = _PLAN_CREATED) -> Plan:
    plan = Plan(slug=slug, title="A plan", frame_slug=frame_slug, created=created)
    plan_store.save(plan)
    return plan


def _delivery(plan_slug: str, created: str = _PLAN_CREATED) -> Delivery:
    """A fresh (unsaved) ledger with an explicit ``created`` stamp.

    Explicit timestamps matter: ``delivery_store.save`` only defaults ``created``
    when it is empty, and the determinism test compares two independently built
    tmp-dir stores — a wall-clock default would make that comparison flaky.
    """
    return Delivery(plan_slug=plan_slug, created=created)


def _seed_one(tmp_path, monkeypatch, *, frame="alpha", plan="alpha") -> Delivery:
    monkeypatch.chdir(tmp_path)
    _frame(frame)
    _plan(plan, frame)
    return _delivery(plan)


def _project() -> today.ProjectionResult:
    return today.project_today()


def _texts(result: today.ProjectionResult) -> list[str]:
    return [b.behavior_text for b in result.behaviors]


# ── criterion 1: the pure projection ─────────────────────────────────────────


def test_empty_state_projects_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _project()
    assert result.behaviors == ()
    assert result.conflicts == ()
    assert result.diagnostics == ()
    assert result.coverage.earliest is None
    assert result.coverage.latest is None


def test_added_delta_projects_as_current_behavior(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "the CLI grows a today verb", caused_by=["c7"])
    delivery_store.save(ledger)

    result = _project()
    assert _texts(result) == ["the CLI grows a today verb"]
    behavior = result.behaviors[0]
    assert behavior.key == "alpha:b1"
    assert behavior.kind == "added"
    assert behavior.plan_slug == "alpha"
    assert behavior.frame_slug == "alpha"
    assert behavior.caused_by == ("c7",)
    assert behavior.lineage == ("alpha:b1",)
    assert result.conflicts == ()


def test_superseded_delta_never_projects(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "old behavior", caused_by=["c7"])
    ledger.add_delta("amended", "new behavior", caused_by=["c7"])
    ledger.supersede("b1", replacement_ref="b2")
    delivery_store.save(ledger)

    result = _project()
    assert _texts(result) == ["new behavior"]
    assert result.behaviors[0].lineage == ("alpha:b1", "alpha:b2")
    assert result.conflicts == ()


def test_retracted_supersession_restores_the_conflict(tmp_path, monkeypatch):
    """Retraction is an event, not a deletion — the flag clears and both
    deltas are live again, which is a human-decision item, not a re-ordering.
    """
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "old behavior", caused_by=["c7"])
    ledger.add_delta("amended", "new behavior", caused_by=["c7", "b1"])
    ledger.supersede("b1", replacement_ref="b2")
    ledger.retract_supersession("b1")
    delivery_store.save(ledger)

    result = _project()
    assert result.behaviors == ()
    assert [c.reason for c in result.conflicts] == [today.CONFLICT_COMPETING]
    assert {p.key for p in result.conflicts[0].parties} == {"alpha:b1", "alpha:b2"}


def test_removed_delta_retires_the_behavior(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior that later goes away", caused_by=["c7"])
    ledger.add_delta("removed", "a behavior that later goes away", caused_by=["d1"])
    ledger.supersede("b1", replacement_ref="b2")
    delivery_store.save(ledger)

    result = _project()
    assert result.behaviors == ()
    assert result.conflicts == ()
    assert result.retired_lineage_count == 1


def test_two_amendeds_of_one_target_conflict_and_neither_projects(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "original", caused_by=["c7"])
    ledger.add_delta("amended", "first amendment", caused_by=["c7", "b1"])
    ledger.add_delta("amended", "second amendment", caused_by=["c7", "b1"])
    ledger.supersede("b1", replacement_ref="b2")
    delivery_store.save(ledger)

    result = _project()
    assert result.behaviors == ()
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.reason == today.CONFLICT_COMPETING
    assert [p.key for p in conflict.parties] == ["alpha:b2", "alpha:b3"]
    assert [p.behavior_text for p in conflict.parties] == [
        "first amendment",
        "second amendment",
    ]


def test_added_colliding_with_removed_conflicts(tmp_path, monkeypatch):
    """A removal that never superseded its target leaves both live — the
    ledger does not say which one wins, so a human must.
    """
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "the behavior", caused_by=["c7"])
    ledger.add_delta("removed", "the behavior", caused_by=["d1", "b1"])
    delivery_store.save(ledger)

    result = _project()
    assert result.behaviors == ()
    assert [c.reason for c in result.conflicts] == [today.CONFLICT_COMPETING]
    assert {p.kind for p in result.conflicts[0].parties} == {"added", "removed"}


def test_unanchored_removal_is_a_human_decision_item(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("removed", "something nobody ever added", caused_by=["d1"])
    delivery_store.save(ledger)

    result = _project()
    assert result.behaviors == ()
    assert [c.reason for c in result.conflicts] == [today.CONFLICT_UNANCHORED_REMOVAL]
    assert result.conflicts[0].parties[0].key == "alpha:b1"


def test_conflicts_are_never_auto_resolved_by_order_or_slug(tmp_path, monkeypatch):
    """Two ledgers amending unlinked behaviors must not be silently ordered."""
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _frame("beta")
    _plan("alpha", "alpha")
    _plan("beta", "beta")

    first = _delivery("alpha")
    first.add_delta("added", "shared behavior", caused_by=["c1"])
    delivery_store.save(first)

    second = _delivery("beta")
    second.add_delta("removed", "shared behavior", caused_by=["c1", "alpha:b1"])
    delivery_store.save(second)

    result = _project()
    # The cross-ledger ref links them into one lineage; nothing superseded the
    # added delta, so the ledger is ambiguous and both stay unprojected.
    assert result.behaviors == ()
    assert [c.reason for c in result.conflicts] == [today.CONFLICT_COMPETING]
    assert [p.key for p in result.conflicts[0].parties] == ["alpha:b1", "beta:b1"]


def test_qualified_cross_ledger_supersession_resolves(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _frame("beta")
    _plan("alpha", "alpha")
    _plan("beta", "beta")

    first = _delivery("alpha")
    first.add_delta("added", "old cross-ledger behavior", caused_by=["c1"])
    first.supersede("b1")  # superseded by work recorded in another ledger
    delivery_store.save(first)

    second = _delivery("beta")
    second.add_delta("amended", "new cross-ledger behavior", caused_by=["c1", "alpha:b1"])
    delivery_store.save(second)

    result = _project()
    assert _texts(result) == ["new cross-ledger behavior"]
    assert result.behaviors[0].lineage == ("alpha:b1", "beta:b1")
    assert result.conflicts == ()


def test_proposed_and_rejected_deltas_stay_out_of_the_projection(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "approved behavior", caused_by=["c7"])
    ledger.add_delta("added", "proposed behavior", caused_by=["c7"], origin="llm")
    ledger.add_delta("added", "rejected behavior", caused_by=["c7"])
    ledger.set_delta_status("b3", "rejected")
    delivery_store.save(ledger)

    result = _project()
    assert _texts(result) == ["approved behavior"]
    assert result.proposed_delta_count == 1
    assert result.rejected_delta_count == 1


def test_reference_to_a_non_approved_delta_is_diagnosed(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "proposed behavior", caused_by=["c7"], origin="llm")
    ledger.add_delta("amended", "amends an unadjudicated delta", caused_by=["c7", "b1"])
    delivery_store.save(ledger)

    result = _project()
    assert _texts(result) == ["amends an unadjudicated delta"]
    assert any("b1" in d and "proposed" in d for d in result.diagnostics)


def test_dangling_delta_reference_is_diagnosed(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("amended", "amends a delta that isn't there", caused_by=["c7", "b99"])
    delivery_store.save(ledger)

    result = _project()
    assert _texts(result) == ["amends a delta that isn't there"]
    assert any("b99" in d for d in result.diagnostics)


# ── provenance and evidence ──────────────────────────────────────────────────


def _evidence(ledger: Delivery, *, strength: str, outcome: str, behavior: str) -> str:
    run = None
    if strength in ("execution", "sensitivity"):
        run = RunReference(timestamp="2026-01-03T00:00:00Z", commit="deadbeef")
    return ledger.add_evidence(
        obligation_ref="o1",
        test_ref=f"tests/test_x.py::{strength}",
        behavior_text=behavior,
        contract_text="the claim text snapshot",
        evidence_type="automated",
        strength=strength,
        strength_basis="read the test",
        outcome=outcome,
        run=run,
    ).id


def test_projection_carries_backward_and_forward_provenance(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    eid = _evidence(ledger, strength="execution", outcome="pass", behavior="asserted")
    ledger.add_delta("added", "a proven behavior", caused_by=["c7", "d2"], evidence_refs=[eid])
    delivery_store.save(ledger)

    behavior = _project().behaviors[0]
    assert behavior.caused_by == ("c7", "d2")
    assert behavior.plan_slug == "alpha"
    assert behavior.frame_slug == "alpha"
    assert behavior.evidence_refs == ("e1",)
    assert [e.key for e in behavior.evidence] == ["alpha:e1"]
    assert behavior.evidence[0].run_commit == "deadbeef"
    assert behavior.best_strength == "execution"
    assert behavior.has_failing_evidence is False
    assert behavior.unresolved_evidence_refs == ()


def test_best_strength_is_the_strongest_passing_approved_evidence(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    weak = _evidence(ledger, strength="coverage", outcome="pass", behavior="weak")
    strong = _evidence(ledger, strength="fidelity", outcome="pass", behavior="strong")
    ledger.add_delta("added", "a behavior", caused_by=["c7"], evidence_refs=[weak, strong])
    delivery_store.save(ledger)

    behavior = _project().behaviors[0]
    assert behavior.best_strength == "fidelity"


def test_failing_evidence_never_raises_strength_and_stays_visible(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    passing = _evidence(ledger, strength="coverage", outcome="pass", behavior="weak")
    failing = _evidence(ledger, strength="execution", outcome="fail", behavior="broken")
    ledger.add_delta("added", "a behavior", caused_by=["c7"], evidence_refs=[passing, failing])
    delivery_store.save(ledger)

    behavior = _project().behaviors[0]
    assert behavior.best_strength == "coverage"
    assert behavior.has_failing_evidence is True
    assert len(behavior.evidence) == 2


def test_unapproved_and_superseded_evidence_do_not_back_a_behavior(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    stale = _evidence(ledger, strength="fidelity", outcome="pass", behavior="stale")
    ledger.supersede(stale)
    proposed = ledger.add_evidence(
        obligation_ref="o1",
        test_ref="tests/test_x.py::proposed",
        behavior_text="proposed",
        contract_text="snapshot",
        evidence_type="automated",
        strength="fidelity",
        strength_basis="read the test",
        outcome="pass",
        origin="llm",
    ).id
    ledger.add_delta("added", "a behavior", caused_by=["c7"], evidence_refs=[stale, proposed])
    delivery_store.save(ledger)

    behavior = _project().behaviors[0]
    assert behavior.best_strength is None
    assert len(behavior.evidence) == 2  # still visible, just not load-bearing
    assert {e.status for e in behavior.evidence} == {"approved", "proposed"}


def test_unresolved_evidence_ref_is_surfaced_not_dropped(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"], evidence_refs=["e42"])
    delivery_store.save(ledger)

    behavior = _project().behaviors[0]
    assert behavior.evidence_refs == ("e42",)
    assert behavior.evidence == ()
    assert behavior.unresolved_evidence_refs == ("e42",)


# ── criterion 2: the fail-open walk ──────────────────────────────────────────


def test_corrupt_delivery_is_skipped_with_a_visible_diagnostic(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"])
    delivery_store.save(ledger)
    delivery_store.path_for("alpha").write_text("{not json", encoding="utf-8")

    result = _project()
    assert result.behaviors == ()
    assert any("alpha" in d and "unreadable" in d for d in result.diagnostics)


def test_newer_schema_delivery_is_skipped_with_a_visible_diagnostic(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"])
    path = delivery_store.save(ledger)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["schema_version"] = DELIVERY_SCHEMA_VERSION + 1
    path.write_text(json.dumps(raw), encoding="utf-8")

    result = _project()
    assert result.behaviors == ()
    assert any("schema" in d for d in result.diagnostics)


def test_corrupt_plan_is_diagnosed_but_its_ledger_still_projects(tmp_path, monkeypatch):
    """A plan file is only the frame link — losing it must not silently drop
    real ledgered behavior (h7: never a silent omission).
    """
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"])
    delivery_store.save(ledger)
    plan_store.path_for("alpha").write_text("{not json", encoding="utf-8")

    result = _project()
    assert _texts(result) == ["a behavior"]
    assert result.behaviors[0].frame_slug == ""
    assert any("plan" in d and "alpha" in d for d in result.diagnostics)


def test_newer_schema_plan_is_diagnosed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    path = plan_store.path_for("alpha")
    _plan("alpha", "alpha")
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["schema_version"] = 99
    path.write_text(json.dumps(raw), encoding="utf-8")

    result = _project()
    assert any("plan" in d and "schema" in d for d in result.diagnostics)


def test_corrupt_frame_is_diagnosed_and_still_counted_as_a_frame(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    store.path_for("alpha").write_text("{not json", encoding="utf-8")

    result = _project()
    assert any("frame" in d and "alpha" in d for d in result.diagnostics)
    assert result.coverage.total_frames == 1
    assert result.coverage.frames_absent_from_ledger == ("alpha",)


def test_missing_delivery_ledger_is_not_a_diagnostic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _plan("alpha", "alpha")

    result = _project()
    assert result.diagnostics == ()
    assert result.behaviors == ()


def test_the_projection_writes_nothing(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"])
    delivery_store.save(ledger)

    before = {str(p): p.read_bytes() for p in sorted(tmp_path.rglob("*")) if p.is_file()}
    _project()
    after = {str(p): p.read_bytes() for p in sorted(tmp_path.rglob("*")) if p.is_file()}
    assert before == after


def _build_store(root, monkeypatch):
    monkeypatch.chdir(root)
    _frame("alpha")
    _frame("gamma")
    _plan("alpha", "alpha")
    ledger = _delivery("alpha")
    ledger.add_delta("added", "one", caused_by=["c7"])
    ledger.add_delta("amended", "two", caused_by=["c7", "b1"])
    ledger.add_delta("added", "three", caused_by=["c7"])
    ledger.supersede("b1", replacement_ref="b2")
    delivery_store.save(ledger)


def test_same_stores_in_same_projection_out(tmp_path, monkeypatch):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()

    _build_store(first_root, monkeypatch)
    first = today.result_to_dict(_project())

    _build_store(second_root, monkeypatch)
    second = today.result_to_dict(_project())

    assert first == second


def test_projection_is_stable_across_repeated_runs(tmp_path, monkeypatch):
    _build_store(tmp_path, monkeypatch)
    first_run = today.result_to_dict(_project())
    second_run = today.result_to_dict(_project())
    assert first_run == second_run


# ── criterion 3: the coverage span ───────────────────────────────────────────


def test_coverage_span_reports_earliest_and_latest_ledgered_delivery(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for slug, created in (("alpha", "2026-03-01T00:00:00Z"), ("beta", "2026-01-05T00:00:00Z")):
        _frame(slug)
        _plan(slug, slug)
        ledger = _delivery(slug, created=created)
        ledger.add_delta("added", f"{slug} behavior", caused_by=["c1"])
        delivery_store.save(ledger)

    coverage = _project().coverage
    assert coverage.earliest.plan_slug == "beta"
    assert coverage.earliest.created == "2026-01-05T00:00:00Z"
    assert coverage.latest.plan_slug == "alpha"
    assert coverage.latest.created == "2026-03-01T00:00:00Z"
    assert coverage.ledgered_plan_slugs == ("alpha", "beta")


def test_coverage_span_lists_frames_absent_from_the_ledger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _frame("beta")
    _frame("gamma")
    _plan("alpha", "alpha")
    _plan("beta", "beta")  # a plan with no ledger at all
    ledger = _delivery("alpha")
    ledger.add_delta("added", "a behavior", caused_by=["c1"])
    delivery_store.save(ledger)

    coverage = _project().coverage
    assert coverage.total_frames == 3
    assert coverage.total_plans == 2
    assert coverage.frames_absent_from_ledger == ("beta", "gamma")


def test_a_ledger_with_only_unadjudicated_deltas_still_counts_as_ledgered(tmp_path, monkeypatch):
    """The boundary statement is about what the ledger *covers*, not about what
    survived adjudication — a frame with filed-but-proposed deltas is not
    'absent from the ledger'.
    """
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "proposed behavior", caused_by=["c7"], origin="llm")
    delivery_store.save(ledger)

    coverage = _project().coverage
    assert coverage.frames_absent_from_ledger == ()
    assert coverage.ledgered_plan_slugs == ("alpha",)


def test_an_undated_ledger_is_excluded_from_the_span_with_a_diagnostic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _plan("alpha", "alpha")
    ledger = _delivery("alpha")
    ledger.add_delta("added", "a behavior", caused_by=["c1"])
    delivery_store.save(ledger)
    # Both stores backfill `created` on save, so blank it on disk instead.
    for path in (delivery_store.path_for("alpha"), plan_store.path_for("alpha")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["created"] = ""
        path.write_text(json.dumps(raw), encoding="utf-8")

    result = _project()
    assert result.coverage.earliest is None
    assert result.coverage.latest is None
    assert any("undated" in d for d in result.diagnostics)


def test_plan_created_backfills_a_ledger_with_no_created_stamp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _frame("alpha")
    _plan("alpha", "alpha", created="2026-02-02T00:00:00Z")
    ledger = _delivery("alpha")
    ledger.add_delta("added", "a behavior", caused_by=["c1"])
    path = delivery_store.save(ledger)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["created"] = ""
    path.write_text(json.dumps(raw), encoding="utf-8")

    coverage = _project().coverage
    assert coverage.earliest.created == "2026-02-02T00:00:00Z"


# ── the JSON shape t10/t11 consume ───────────────────────────────────────────


def test_result_to_dict_is_json_serialisable_and_complete(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    eid = _evidence(ledger, strength="fidelity", outcome="pass", behavior="asserted")
    ledger.add_delta("added", "a behavior", caused_by=["c7"], evidence_refs=[eid])
    ledger.add_delta("removed", "an orphan removal", caused_by=["d1"])
    delivery_store.save(ledger)

    payload = today.result_to_dict(_project())
    json.dumps(payload)  # must not raise
    assert set(payload) == {
        "behaviors",
        "conflicts",
        "coverage",
        "diagnostics",
        "proposed_delta_count",
        "rejected_delta_count",
        "retired_lineage_count",
    }
    assert payload["behaviors"][0]["behavior_text"] == "a behavior"
    assert payload["behaviors"][0]["best_strength"] == "fidelity"
    assert payload["conflicts"][0]["reason"] == today.CONFLICT_UNANCHORED_REMOVAL
    assert payload["coverage"]["total_frames"] == 1


def test_project_is_pure_over_loaded_state(tmp_path, monkeypatch):
    """``project`` takes already-loaded state and touches no store."""
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"])
    delivery_store.save(ledger)

    state = today.load_state()
    monkeypatch.chdir(tmp_path / "..")  # the stores are no longer reachable
    result = today.project(state)
    assert _texts(result) == ["a behavior"]


@pytest.mark.parametrize("reason", [today.CONFLICT_COMPETING, today.CONFLICT_UNANCHORED_REMOVAL])
def test_conflict_reasons_are_a_closed_vocabulary(reason):
    assert reason in today.CONFLICT_REASONS
