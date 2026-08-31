"""Tests for the today-spec renderer (t10, claim c8/h8, c23/h19, h9/h1).

Pins the four acceptance criteria of t10:

1. each current behavior renders its provenance, evidence strength, and
   evidence age from the run reference;
2. the artifact opens with a derived coverage-boundary statement from the
   projection span, not hand-written text;
3. (CLI-level, see ``tests/test_today_cli.py``) the command writes only
   ``docs/current-spec.md``;
4. the artifact is standalone-readable and lints clean.
"""

from __future__ import annotations

from devague import delivery_store, plan_store, store
from devague.delivery import Delivery, RunReference
from devague.frame import Frame
from devague.plan import Plan
from devague.render import today_md
from devague.today import project_today

_FRAME_CREATED = "2026-01-01T00:00:00Z"
_PLAN_CREATED = "2026-01-02T00:00:00Z"


def _frame(slug: str, title: str = "A frame", created: str = _FRAME_CREATED) -> Frame:
    frame = Frame(slug=slug, title=title, created=created)
    store.save(frame)
    return frame


def _plan(slug: str, frame_slug: str, created: str = _PLAN_CREATED) -> Plan:
    plan = Plan(slug=slug, title="A plan", frame_slug=frame_slug, created=created)
    plan_store.save(plan)
    return plan


def _seed_one(tmp_path, monkeypatch, *, frame="alpha", plan="alpha") -> Delivery:
    monkeypatch.chdir(tmp_path)
    _frame(frame)
    _plan(plan, frame)
    return Delivery(plan_slug=plan, created=_PLAN_CREATED)


def test_empty_projection_renders_coverage_boundary_as_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = project_today()
    text = today_md.render_today(result)

    assert text.startswith("# Current spec — what the app does today\n")
    assert "## Coverage boundary" in text
    assert "No plan has a ledgered delivery yet" in text
    assert "0 of 0 plans and 0 of 0 frames are covered" in text
    assert "## Current behavior" in text
    assert "No behavior currently projects from the ledger." in text


def test_coverage_boundary_is_derived_from_span_numbers(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"])
    delivery_store.save(ledger)
    # A second frame with no ledgered delivery at all.
    _frame("beta")

    result = project_today()
    text = today_md.render_today(result)

    assert "1 of 1 plan have a ledgered delivery" in text
    assert "`alpha`" in text
    assert f"`{_PLAN_CREATED}`" in text
    assert "plan `alpha`" in text
    assert "1 of 2" in text  # frames absent from ledger: beta out of 2 total
    assert "`beta`" in text


def test_behavior_renders_provenance_and_evidence_with_run_date(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
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

    result = project_today()
    text = today_md.render_today(result)

    assert "the CLI grows a today verb" in text
    assert "caused by `c7`" in text
    assert "plan `alpha`, frame `alpha`" in text
    # Evidence age renders as the run date beside the strength (never bare "pass").
    assert "execution: pass (run 2026-08-31 @ abc1234)" in text
    assert "proof: best strength `execution`" in text


def test_failing_evidence_never_smoothed_into_proven(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a shaky behavior", caused_by=["c7"], evidence_refs=["e1"])
    ledger.add_evidence(
        obligation_ref="c7",
        test_ref="tests/test_today.py::test_y",
        behavior_text="a shaky behavior",
        contract_text="claim c7 text",
        evidence_type="automated",
        strength="execution",
        strength_basis="ran the suite",
        outcome="fail",
        run=RunReference(timestamp="2026-08-31T00:00:00Z", commit="deadbee"),
    )
    delivery_store.save(ledger)

    result = project_today()
    text = today_md.render_today(result)

    assert "⚠ unproven: failing evidence on record" in text
    assert "execution: fail (run 2026-08-31 @ deadbee)" in text


def test_behavior_with_no_evidence_renders_visibly_unproven(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "an unevidenced behavior", caused_by=["c7"])
    delivery_store.save(ledger)

    result = project_today()
    text = today_md.render_today(result)

    assert "⚠ unproven: no passing evidence on record" in text
    assert "evidence: none on record" in text


def test_conflicts_render_as_human_decision_items(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("removed", "something nobody ever added", caused_by=["d1"])
    delivery_store.save(ledger)

    result = project_today()
    text = today_md.render_today(result)

    assert "## Conflicts" in text
    assert "unanchored-removal" in text
    assert "human decision required" in text


def test_ledger_status_section_shows_pending_and_excluded_counts(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "user behavior", caused_by=["c7"])
    ledger.add_delta("added", "llm-proposed behavior", caused_by=["c8"], origin="llm")
    delivery_store.save(ledger)

    result = project_today()
    text = today_md.render_today(result)

    assert "## Ledger status" in text
    assert "proposed deltas awaiting adjudication: 1" in text
    # Only the user-origin (approved) delta projects as current behavior.
    assert "llm-proposed behavior" not in text.split("## Ledger status")[0]


def test_diagnostics_render_visibly_when_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    frame_dir = tmp_path / ".devague" / "frames"
    frame_dir.mkdir(parents=True)
    (frame_dir / "broken.json").write_text("{not valid json", encoding="utf-8")

    result = project_today()
    text = today_md.render_today(result)

    assert "## Diagnostics" in text
    assert "broken" in text


def test_render_today_is_deterministic(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a deterministic behavior", caused_by=["c7"])
    delivery_store.save(ledger)

    result = project_today()
    first = today_md.render_today(result)
    second = today_md.render_today(project_today())
    assert first == second


def test_render_today_has_no_per_run_timestamp_outside_evidence(tmp_path, monkeypatch):
    ledger = _seed_one(tmp_path, monkeypatch)
    ledger.add_delta("added", "a behavior", caused_by=["c7"], evidence_refs=["e1"])
    ledger.add_evidence(
        obligation_ref="c7",
        test_ref="tests/test_today.py::test_z",
        behavior_text="a behavior",
        contract_text="claim c7 text",
        evidence_type="automated",
        strength="execution",
        strength_basis="ran the suite",
        outcome="pass",
        run=RunReference(timestamp="2026-08-31T00:00:00Z", commit="c0ffee1"),
    )
    delivery_store.save(ledger)

    result = project_today()
    text = today_md.render_today(result)
    # The only occurrence of the run date is inside the evidence line.
    assert text.count("2026-08-31") == 1
