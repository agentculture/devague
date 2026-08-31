"""Unmet-obligation warnings in both convergence engines (bvts t7).

An obligation (``Frame.obligations`` / ``Plan.obligations``) is a behavioral
commitment; an approved, non-superseded ``EvidenceRecord`` in the delivery
ledger is the only thing that discharges one. This module pins three
properties:

* the join itself — approved + non-superseded evidence meets an obligation,
  nothing else does;
* the soft-rollout contract — the warnings never move ``ready``/``ready_for_*``,
  exactly like the S1/S2 sharpness warnings they are modelled on;
* the fail-open contract — a missing, truncated, or newer-schema plan/delivery
  file degrades to "nothing known to be met" plus a diagnostic, never a crash
  and never a blocker (the :mod:`devague.contested` pattern, reused verbatim).
"""

from __future__ import annotations

import json

import pytest

from devague import delivery_store, obligation_evidence, plan_store, store
from devague.cli import main
from devague.convergence import evaluate as evaluate_frame
from devague.delivery import Delivery
from devague.frame import Frame
from devague.plan import CoverageTarget, Plan
from devague.plan_convergence import evaluate as evaluate_plan

_REQUIRED_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "boundary",
    "success_signal",
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _full_frame() -> Frame:
    """A frame that converges cleanly (the tests/test_convergence.py shape)."""
    f = Frame(slug="s", title="t")
    for kind in _REQUIRED_KINDS:
        c = f.add_claim(kind, f"{kind} text", origin="user")
        f.add_honesty(c, "must hold", origin="user")
    return f


def _converging_plan() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="s")
    p.targets = [CoverageTarget(id="c1", kind="announcement", text="shipped")]
    t = p.add_task("do the thing")
    t.instruction = "implement the feature"
    p.add_acceptance(t, "it works")
    p.add_cover(t, "c1")
    return p


def _evidence(delivery: Delivery, obligation_ref: str, **kw) -> object:
    return delivery.add_evidence(
        obligation_ref=obligation_ref,
        test_ref="tests/test_x.py::test_y",
        behavior_text="asserts the seam behaves",
        contract_text="the contract snapshot",
        evidence_type="automated",
        strength="coverage",
        strength_basis="the test executes the seam",
        outcome="pass",
        **kw,
    )


# ── the pure join (frame side) ────────────────────────────────────────────────


def test_frame_obligation_without_evidence_warns() -> None:
    f = _full_frame()
    ob = f.add_obligation("c1", "cli", "converge prints the warning")
    res = evaluate_frame(f, met_obligations=set())
    hits = [w for w in res.warnings if ob.id in w]
    assert len(hits) == 1
    assert "untested" in hits[0]
    assert "cli" in hits[0]  # AC3: the seam is named
    assert "c1" in hits[0]


def test_frame_obligation_with_approved_evidence_does_not_warn() -> None:
    f = _full_frame()
    ob = f.add_obligation("c1", "cli", "converge prints the warning")
    res = evaluate_frame(f, met_obligations={ob.id})
    assert not [w for w in res.warnings if ob.id in w]


def test_rejected_frame_obligation_never_warns() -> None:
    f = _full_frame()
    ob = f.add_obligation("c1", "cli", "a withdrawn commitment")
    f.set_obligation_status(ob.id, "rejected")
    res = evaluate_frame(f, met_obligations=set())
    assert not [w for w in res.warnings if ob.id in w]


def test_proposed_frame_obligation_still_warns() -> None:
    """A proposed obligation is not yet adjudicated, but it is also not
    discharged — it warrants the same untested signal; only a *rejected* one
    is silent."""
    f = _full_frame()
    ob = f.add_obligation("c1", "cli", "a proposed commitment", origin="llm")
    assert ob.status == "proposed"
    assert [w for w in evaluate_frame(f, met_obligations=set()).warnings if ob.id in w]


def test_frame_obligation_warning_defaults_to_nothing_met() -> None:
    """Omitting ``met_obligations`` means "no evidence state was loaded", which
    is honestly reported as untested rather than silently assumed discharged."""
    f = _full_frame()
    ob = f.add_obligation("c1", "cli", "converge prints the warning")
    assert [w for w in evaluate_frame(f).warnings if ob.id in w]


def test_frame_obligation_warnings_never_gate() -> None:
    """AC2: ``ready_for_spec`` is untouched by the new warnings."""
    baseline = evaluate_frame(_full_frame())
    f = _full_frame()
    f.add_obligation("c1", "cli", "totally untested")
    res = evaluate_frame(f, met_obligations=set())
    assert res.ready is baseline.ready is True
    assert res.blockers == baseline.blockers == []
    assert res.parked_items == baseline.parked_items
    assert res.required_next_moves == baseline.required_next_moves


# ── the pure join (plan side) ─────────────────────────────────────────────────


def test_plan_obligation_without_evidence_warns() -> None:
    p = _converging_plan()
    ob = p.add_obligation("t1", 1, "store round-trip", "the ledger reloads")
    res = evaluate_plan(p, met_obligations=set())
    hits = [w for w in res.warnings if ob.id in w]
    assert len(hits) == 1
    assert "untested" in hits[0]
    assert "store round-trip" in hits[0]  # AC3: the seam is named
    assert "t1" in hits[0]


def test_plan_obligation_with_approved_evidence_does_not_warn() -> None:
    p = _converging_plan()
    ob = p.add_obligation("t1", 1, "store round-trip", "the ledger reloads")
    assert not [w for w in evaluate_plan(p, met_obligations={ob.id}).warnings if ob.id in w]


def test_rejected_plan_obligation_never_warns() -> None:
    p = _converging_plan()
    ob = p.add_obligation("t1", 1, "store round-trip", "withdrawn")
    p.set_obligation_status(ob.id, "rejected")
    assert not [w for w in evaluate_plan(p, met_obligations=set()).warnings if ob.id in w]


def test_plan_obligation_warnings_never_gate() -> None:
    """AC2: ``ready_for_plan`` is untouched by the new warnings."""
    baseline = evaluate_plan(_converging_plan())
    p = _converging_plan()
    p.add_obligation("t1", 1, "store round-trip", "totally untested")
    res = evaluate_plan(p, met_obligations=set())
    assert res.ready is baseline.ready is True
    assert res.blockers == baseline.blockers == []
    assert res.parked_items == baseline.parked_items
    assert res.required_next_moves == baseline.required_next_moves


# ── the evidence predicate ────────────────────────────────────────────────────


def test_only_approved_non_superseded_evidence_counts() -> None:
    d = Delivery(plan_slug="demo")
    approved = _evidence(d, "o1")  # user origin -> approved
    proposed = _evidence(d, "o2", origin="llm")  # -> proposed
    rejected = _evidence(d, "o3")
    d.set_evidence_status(rejected.id, "rejected")
    stale = _evidence(d, "o4")
    replacement = _evidence(d, "o4")
    d.supersede(stale.id, replacement.id)

    assert approved.status == "approved" and proposed.status == "proposed"
    refs = obligation_evidence.approved_evidence_refs(d)
    # o4 is still met — by the *replacement*, not by the superseded record.
    assert refs == {"o1", "o4"}
    assert stale.superseded is True


def test_superseded_sole_evidence_leaves_the_obligation_unmet() -> None:
    d = Delivery(plan_slug="demo")
    stale = _evidence(d, "o1")
    other = _evidence(d, "o9")
    d.supersede(stale.id, other.id)
    assert obligation_evidence.approved_evidence_refs(d) == {"o9"}


# ── fail-open loading (the contested.py contract, reused) ─────────────────────


def _seed_plan_and_delivery(tmp_path, *, frame_slug: str = "s", plan_slug: str = "demo"):
    p = Plan(slug=plan_slug, title="Demo", frame_slug=frame_slug)
    plan_store.save(p)
    d = Delivery(plan_slug=plan_slug)
    return p, d


def test_frame_side_loader_collects_refs_from_matching_plans(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _p, d = _seed_plan_and_delivery(tmp_path)
    _evidence(d, "o1")
    delivery_store.save(d)
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == {"o1"}
    assert diags == []


def test_frame_side_loader_ignores_other_frames_plans(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _p, d = _seed_plan_and_delivery(tmp_path, frame_slug="somewhere-else")
    _evidence(d, "o1")
    delivery_store.save(d)
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == set()
    assert diags == []


def test_frame_side_loader_is_silent_when_no_ledger_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_plan_and_delivery(tmp_path)  # plan saved, ledger never written
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == set()
    assert diags == []


def test_frame_side_loader_fails_open_on_corrupt_ledger(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _p, d = _seed_plan_and_delivery(tmp_path)
    delivery_store.save(d)
    delivery_store.path_for("demo").write_text("{not json", encoding="utf-8")
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == set()
    assert len(diags) == 1 and diags[0].startswith("obligations:")


def test_frame_side_loader_fails_open_on_newer_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _p, d = _seed_plan_and_delivery(tmp_path)
    delivery_store.save(d)
    path = delivery_store.path_for("demo")
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["schema_version"] = 9999
    path.write_text(json.dumps(raw), encoding="utf-8")
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == set()
    assert len(diags) == 1 and "schema" in diags[0]


def test_frame_side_loader_fails_open_on_corrupt_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _seed_plan_and_delivery(tmp_path)
    plan_store.path_for("demo").write_text("{not json", encoding="utf-8")
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == set()
    assert len(diags) == 1 and "plan" in diags[0]


def test_frame_side_loader_fails_open_when_plans_cannot_be_listed(monkeypatch) -> None:
    """The outermost fail-open branch: even an unreadable plans directory is a
    diagnostic, not an exception."""

    def _boom():
        raise OSError("permission denied")

    monkeypatch.setattr(plan_store, "list_slugs", _boom)
    refs, diags = obligation_evidence.met_obligation_refs_for_frame("s")
    assert refs == set()
    assert len(diags) == 1 and diags[0].startswith("obligations:")


def test_plan_side_loader_reads_only_its_own_ledger(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _p, mine = _seed_plan_and_delivery(tmp_path, plan_slug="mine")
    _evidence(mine, "o1")
    delivery_store.save(mine)
    _q, theirs = _seed_plan_and_delivery(tmp_path, plan_slug="theirs")
    _evidence(theirs, "o2")
    delivery_store.save(theirs)
    refs, diags = obligation_evidence.met_obligation_refs_for_plan("mine")
    assert refs == {"o1"} and diags == []


def test_plan_side_loader_is_silent_without_a_ledger(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    refs, diags = obligation_evidence.met_obligation_refs_for_plan("nothing-here")
    assert refs == set() and diags == []


def test_plan_side_loader_fails_open_on_corrupt_ledger(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _p, d = _seed_plan_and_delivery(tmp_path)
    delivery_store.save(d)
    delivery_store.path_for("demo").write_text("]]not json", encoding="utf-8")
    refs, diags = obligation_evidence.met_obligation_refs_for_plan("demo")
    assert refs == set()
    assert len(diags) == 1 and diags[0].startswith("obligations:")


# ── CLI wiring ────────────────────────────────────────────────────────────────


def _cli_converged_frame(monkeypatch, tmp_path) -> str:
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the obligation warnings"])
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def test_frame_converge_json_carries_the_warning(tmp_path, monkeypatch, capsys) -> None:
    slug = _cli_converged_frame(monkeypatch, tmp_path)
    f = store.load(slug)
    ob = f.add_obligation("c1", "cli", "converge surfaces unmet obligations")
    store.save(f)
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_for_spec"] is True  # AC2: still not gating
    assert any(ob.id in w and "untested" in w for w in payload["warnings"])


def test_frame_converge_drops_the_warning_once_evidence_is_approved(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _cli_converged_frame(monkeypatch, tmp_path)
    f = store.load(slug)
    ob = f.add_obligation("c1", "cli", "converge surfaces unmet obligations")
    store.save(f)
    p = Plan(slug="demo", title="Demo", frame_slug=slug)
    plan_store.save(p)
    d = Delivery(plan_slug="demo")
    _evidence(d, ob.id)
    delivery_store.save(d)
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert not [w for w in payload["warnings"] if ob.id in w]


def test_frame_status_json_carries_the_warning(tmp_path, monkeypatch, capsys) -> None:
    slug = _cli_converged_frame(monkeypatch, tmp_path)
    f = store.load(slug)
    ob = f.add_obligation("c1", "cli", "status surfaces unmet obligations")
    store.save(f)
    capsys.readouterr()
    assert main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(ob.id in w for w in payload["warnings"])


def test_frame_converge_survives_a_corrupt_ledger(tmp_path, monkeypatch, capsys) -> None:
    """Fail-open at the CLI edge: a broken ledger is a stderr diagnostic, and
    converge still exits 0 with its verdict on stdout."""
    slug = _cli_converged_frame(monkeypatch, tmp_path)
    f = store.load(slug)
    f.add_obligation("c1", "cli", "converge surfaces unmet obligations")
    store.save(f)
    p = Plan(slug="demo", title="Demo", frame_slug=slug)
    plan_store.save(p)
    delivery_store.save(Delivery(plan_slug="demo"))
    delivery_store.path_for("demo").write_text("{nope", encoding="utf-8")
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ready_for_spec"] is True
    assert "obligations:" in captured.err


def _cli_converged_plan(monkeypatch, tmp_path, capsys) -> str:
    slug = _cli_converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    args = ["plan", "task", "Build everything", "--accept", "all targets satisfied"]
    for tid in [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]:
        args += ["--covers", tid]
    main(args)
    capsys.readouterr()
    return slug


@pytest.mark.parametrize("verb", ["converge", "status"])
def test_plan_converge_and_status_carry_the_warning(verb, tmp_path, monkeypatch, capsys) -> None:
    slug = _cli_converged_plan(monkeypatch, tmp_path, capsys)
    p = plan_store.load(slug)
    ob = p.add_obligation("t1", 1, "cli", "plan converge surfaces unmet obligations")
    plan_store.save(p)
    capsys.readouterr()
    assert main(["plan", verb, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_for_plan"] is True  # AC2: still not gating
    assert any(ob.id in w and "untested" in w for w in payload["warnings"])


def test_plan_converge_drops_the_warning_once_evidence_is_approved(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _cli_converged_plan(monkeypatch, tmp_path, capsys)
    p = plan_store.load(slug)
    ob = p.add_obligation("t1", 1, "cli", "plan converge surfaces unmet obligations")
    plan_store.save(p)
    d = Delivery(plan_slug=p.slug)
    _evidence(d, ob.id)
    delivery_store.save(d)
    capsys.readouterr()
    assert main(["plan", "converge", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert not [w for w in payload["warnings"] if ob.id in w]
