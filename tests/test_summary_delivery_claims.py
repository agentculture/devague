"""Tests for the Delivery Claims table's evidence-backed rows (bvts t11, covers c20).

Extends the ``## Delivery Claims`` section (:mod:`devague.render.summary_md`)
beyond the hardcoded placeholder row: one row per obligation-bearing claim,
populated from real :class:`~devague.delivery.EvidenceRecord` state, with the
confidence column being the strength ladder itself (one scale, not two — the
v2 park resolution) and an APPROVED reasoning-degradation lapse capping the
rendered strength of any claim it names, directly or via a resolvable
obligation/evidence ref. Acceptance criteria:

1. one row per obligation-bearing claim: claim text, ladder strength as the
   confidence column, evidence pointer with age — replacing the hardcoded
   placeholder row
2. an approved lapse caps the rendered strength regardless of the filed
   strength (e.g. ``grader-unverified`` caps below ``execution``); proposed
   evidence renders visibly pending; rejected evidence is omitted
3. unmet obligations render as visibly untested rows; staleness findings
   (bvts t8) render beside affected rows
"""

from __future__ import annotations

from devague.delivery import Delivery, RunReference
from devague.frame import Frame
from devague.plan import Plan
from devague.render import summary_md
from devague.staleness import OrphanedEvidenceFinding, StaleDeviationFinding
from tests.test_render import assert_markdownlint_clean

RUN = RunReference(timestamp="2026-08-01T10:00:00Z", commit="abc1234")


# ── fixtures ──────────────────────────────────────────────────────────────────
def _frame_with_obligation(claim_text: str = "ship the feature"):
    """A frame with one confirmed claim (c1) and one approved frame-side
    obligation (o1) attached to it. Returns ``(frame, claim, obligation)``.
    """
    frame = Frame(slug="demo", title="Demo Frame")
    claim = frame.add_claim("announcement", claim_text, origin="user")
    obligation = frame.add_obligation(
        claim.id, seam="cli", behavior="does the thing", origin="user"
    )
    return frame, claim, obligation


def _plan_for(frame: Frame) -> Plan:
    return Plan(slug=frame.slug, title="Demo Plan", frame_slug=frame.slug)


def _evidence(delivery: Delivery, obligation_ref: str, **kw):
    args = {
        "obligation_ref": obligation_ref,
        "test_ref": "tests/test_x.py::test_y",
        "behavior_text": "asserts the thing happens",
        "contract_text": "does the thing",
        "evidence_type": "automated",
        "strength": "execution",
        "strength_basis": "the test runs in CI and currently passes",
        "outcome": "pass",
        "run": RUN,
    }
    args.update(kw)
    return delivery.add_evidence(**args)


def _claims_section(out: str) -> str:
    return out.split("## Delivery Claims")[1].split("## Remaining Work")[0]


# ── AC1: real rows replace the placeholder ────────────────────────────────────
def test_no_obligations_keeps_the_placeholder_row() -> None:
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_claim("announcement", "ship the feature", origin="user")  # no obligation
    plan = _plan_for(frame)
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = _claims_section(out)
    assert "`<fill: what was delivered>`" in claims


def test_obligation_bearing_claim_with_passing_evidence_renders_a_real_row() -> None:
    frame, claim, obligation = _frame_with_obligation("ship the feature")
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    out = summary_md.render_summary(plan, frame, delivery)
    claims = _claims_section(out)
    assert "`<fill: what was delivered>`" not in claims
    row = next(ln for ln in claims.splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "ship the feature" in row
    assert "`execution`" in row
    assert "tests/test_x.py::test_y" in row
    assert "2026-08-01" in row  # evidence pointer carries the run's age


def test_proposed_obligation_does_not_seat_a_row() -> None:
    # An obligation filed by an LLM lands `proposed` and is not yet a real
    # commitment (mirrors the rest of the module's approved-only discipline).
    frame = Frame(slug="demo", title="Demo Frame")
    claim = frame.add_claim("announcement", "ship the feature", origin="user")
    frame.add_obligation(claim.id, seam="cli", behavior="does the thing", origin="llm")
    plan = _plan_for(frame)
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    claims = _claims_section(out)
    assert "`<fill: what was delivered>`" in claims
    assert claim.id not in claims.split("Lapse ledger evidence")[0]


# ── AC3: untested / failing / pending evidence rows ───────────────────────────
def test_obligation_with_no_evidence_renders_untested() -> None:
    frame, claim, _obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    out = summary_md.render_summary(plan, frame, Delivery(plan_slug=plan.slug))
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "untested" in row
    assert "(none filed)" in row


def test_failing_approved_evidence_renders_visibly_not_hidden() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, outcome="fail")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "FAILING" in row


def test_proposed_evidence_renders_pending_adjudication() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, origin="llm")  # -> proposed
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "pending adjudication" in row


def test_rejected_evidence_is_not_counted_claim_renders_untested() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    ev = _evidence(delivery, obligation.id, origin="llm")
    delivery.set_evidence_status(ev.id, "rejected")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "untested" in row


def test_superseded_evidence_is_not_counted_claim_renders_untested() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    ev = _evidence(delivery, obligation.id)
    delivery.supersede(ev.id, origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "untested" in row


# ── AC2: an approved lapse caps the rendered strength ─────────────────────────
def test_approved_grader_unverified_lapse_caps_strength_below_execution() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    frame.add_lapse("grader-unverified", "graded without a rubric", refs=[claim.id], origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`fidelity`" in row
    assert "`execution`" not in row


def test_lapse_cap_applies_regardless_of_filed_strength() -> None:
    # Even a `sensitivity`-level filing gets pulled down by the cap.
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="sensitivity")
    frame.add_lapse(
        "provenance-missing",
        "no chain of custody on the fixture data",
        refs=[claim.id],
        origin="user",
    )
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`coverage`" in row


def test_lapse_cap_resolves_via_obligation_ref() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    frame.add_lapse(
        "grader-unverified", "graded without a rubric", refs=[obligation.id], origin="user"
    )
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`fidelity`" in row


def test_lapse_cap_resolves_via_evidence_ref() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    ev = _evidence(delivery, obligation.id, strength="execution")
    frame.add_lapse("grader-unverified", "graded without a rubric", refs=[ev.id], origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`fidelity`" in row


def test_freetext_lapse_ref_matching_no_id_does_not_cap() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    frame.add_lapse(
        "grader-unverified",
        "graded without a rubric",
        refs=["see the incident writeup, not an id"],
        origin="user",
    )
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`execution`" in row


def test_proposed_lapse_does_not_cap_only_approved_lapses_do() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    frame.add_lapse(
        "grader-unverified", "graded without a rubric", refs=[claim.id], origin="llm"
    )  # -> proposed, never adjudicated
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`execution`" in row


def test_rejected_lapse_does_not_cap() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    rec = frame.add_lapse(
        "grader-unverified", "graded without a rubric", refs=[claim.id], origin="user"
    )
    frame.set_lapse_status(rec.id, "rejected")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`execution`" in row


def test_multiple_matching_lapses_apply_the_most_restrictive_cap() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    # control-absent caps at `execution` (weaker restriction); provenance-missing
    # caps at `coverage` (stronger restriction) -- the stronger one must win.
    frame.add_lapse("control-absent", "no baseline", refs=[claim.id], origin="user")
    frame.add_lapse("provenance-missing", "unclear origin", refs=[claim.id], origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "`coverage`" in row


def test_lapse_cap_mapping_is_a_documented_per_code_table() -> None:
    assert summary_md.LAPSE_STRENGTH_CAPS["grader-unverified"] == "fidelity"
    assert summary_md.LAPSE_STRENGTH_CAPS["assumption-for-measurement"] == "fidelity"
    assert summary_md.LAPSE_STRENGTH_CAPS["control-absent"] == "execution"
    assert summary_md.LAPSE_STRENGTH_CAPS["n-below-claim"] == "fidelity"
    assert summary_md.LAPSE_STRENGTH_CAPS["instrument-changed-mid-series"] == "fidelity"
    assert summary_md.LAPSE_STRENGTH_CAPS["provenance-missing"] == "coverage"


# ── AC3: staleness findings render beside affected rows ───────────────────────
def test_stale_deviation_finding_renders_beside_its_claim_row() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    finding = StaleDeviationFinding(
        deviation_id="d1",
        what="swapped the approach",
        reason="blocked upstream",
        classification="risky",
        plan_slug=plan.slug,
        claim_ids=(claim.id,),
        stale_evidence_refs=("e1",),
    )
    out = summary_md.render_summary(plan, frame, delivery, stale_deviations=[finding])
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "stale" in row
    assert "d1" in row


def test_orphaned_evidence_finding_renders_beside_its_claim_row() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    ev = _evidence(delivery, obligation.id, strength="execution")
    finding = OrphanedEvidenceFinding(
        evidence_id=ev.id,
        obligation_ref=obligation.id,
        test_ref=ev.test_ref,
        plan_slug=plan.slug,
        reason="obligation rejected",
    )
    out = summary_md.render_summary(plan, frame, delivery, orphaned_evidence=[finding])
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "stale" in row
    assert "obligation rejected" in row


def test_staleness_params_are_none_safe_for_existing_callers() -> None:
    # Every caller that predates t11 (including every test above t11) never
    # passes stale_deviations/orphaned_evidence -- must keep working unchanged.
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    out = summary_md.render_summary(plan, frame, delivery)  # no staleness args at all
    assert f"`{claim.id}`" in out


# ── table safety + markdownlint ────────────────────────────────────────────────
def test_claim_text_with_pipe_and_newline_does_not_corrupt_the_table() -> None:
    frame, claim, obligation = _frame_with_obligation("ships | breaks\na table")
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id)
    out = summary_md.render_summary(plan, frame, delivery)
    row = next(ln for ln in _claims_section(out).splitlines() if ln.startswith(f"| `{claim.id}`"))
    assert "\n" not in row


def test_render_summary_with_real_rows_is_markdownlint_clean() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    _evidence(delivery, obligation.id, strength="execution")
    frame.add_lapse("grader-unverified", "graded without a rubric", refs=[claim.id], origin="user")
    out = summary_md.render_summary(plan, frame, delivery)
    assert_markdownlint_clean(out)


# ── summary_data (--json) parity ───────────────────────────────────────────────
def test_summary_data_delivery_claims_shape() -> None:
    frame, claim, obligation = _frame_with_obligation()
    plan = _plan_for(frame)
    delivery = Delivery(plan_slug=plan.slug)
    ev = _evidence(delivery, obligation.id, strength="execution")
    data = summary_md.summary_data(plan, frame, delivery)
    rows = data["sections"]["delivery_claims"]
    assert isinstance(rows, list)
    assert rows[0]["claim"] == claim.id
    assert rows[0]["status"] == "passing"
    assert rows[0]["confidence"] == "execution"
    assert rows[0]["evidence"] == ev.id
    assert rows[0]["test_ref"] == ev.test_ref
    assert rows[0]["run"] == {"timestamp": RUN.timestamp, "commit": RUN.commit}


def test_summary_data_delivery_claims_is_fill_placeholder_when_no_rows() -> None:
    frame = Frame(slug="demo", title="Demo Frame")
    frame.add_claim("announcement", "ship the feature", origin="user")  # no obligation
    plan = _plan_for(frame)
    data = summary_md.summary_data(plan, frame, Delivery(plan_slug=plan.slug))
    assert data["sections"]["delivery_claims"] == "<fill: delivery claims>"


# ── CLI wiring: summary.py loads staleness fail-open at the edge (bvts t11) ───
def test_cli_summary_passes_staleness_findings_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    from devague import delivery_store, plan_store, store
    from devague.cli import main
    from devague.plan import targets_from_frame

    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo Frame")
    claim = frame.add_claim("announcement", "ship the feature", origin="user")
    obligation = frame.add_obligation(
        claim.id, seam="cli", behavior="does the thing", origin="user"
    )
    store.save(frame)

    plan = Plan(slug="demo", title="Demo Plan", frame_slug="demo")
    plan.targets = targets_from_frame(frame)
    task = plan.add_task("first task")
    plan.add_cover(task, claim.id)
    plan_store.save(plan)

    delivery = Delivery(plan_slug="demo")
    _evidence(delivery, obligation.id, strength="execution")
    dev = delivery.add_deviation("swap", "t1", "reason", origin="user", affects=[claim.id])
    assert dev.status == "approved"
    delivery_store.save(delivery)

    capsys.readouterr()
    rc = main(["summary", "--plan", "demo"])
    assert rc == 0
    out = capsys.readouterr().out
    claims = out.split("## Delivery Claims")[1].split("## Remaining Work")[0]
    row = next(ln for ln in claims.splitlines() if ln.startswith(f"| `{claim.id}`"))
    # The deviation's evidence is at-or-before it in the shared-timeline
    # convention (e1 vs d1) and is never re-filed after -- a stale finding.
    assert "stale" in row
