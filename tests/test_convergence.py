from __future__ import annotations

import dataclasses
import json

import pytest

from devague.convergence import evaluate, suggest_move
from devague.frame import LAPSE_CODES, Frame

_REQUIRED_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "boundary",
    "success_signal",
)


def _full_frame() -> Frame:
    f = Frame(slug="s", title="t")
    for kind in _REQUIRED_KINDS:
        c = f.add_claim(kind, f"{kind} text", origin="user")  # user -> confirmed
        f.add_honesty(c, "must hold", origin="user")  # user -> confirmed
    return f


def test_full_frame_converges() -> None:
    res = evaluate(_full_frame())
    assert res.ready is True
    assert res.blockers == []


def test_missing_required_kinds_reported() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")
    res = evaluate(f)
    assert res.ready is False
    assert any("audience" in m for m in res.blockers)
    assert any("after_state" in m for m in res.blockers)


def test_proposed_claim_blocks() -> None:
    f = _full_frame()
    f.add_claim("boundary", "maybe not this", origin="llm")  # proposed
    res = evaluate(f)
    assert res.ready is False
    assert any("still proposed" in m for m in res.blockers)


def test_confirmed_claim_without_honesty_blocks() -> None:
    f = _full_frame()
    c = f.add_claim("success_signal", "extra signal", origin="user")  # confirmed, no honesty
    res = evaluate(f)
    assert res.ready is False
    assert any(c.id in m and "honesty" in m for m in res.blockers)


def test_blocking_vagueness_and_hard_question_block() -> None:
    f = _full_frame()
    f.add_vagueness("scale?", "unknown_blocking")
    res = evaluate(f)
    assert any("blocking vagueness" in m for m in res.blockers)
    f2 = _full_frame()
    f2.add_hard_question(f2.claims[0], "what if zero?", blocking=True)
    res2 = evaluate(f2)
    assert any("blocking hard question" in m for m in res2.blockers)


# --- #5 spec contract: gate semantics for the new claim kinds (t4/t5) ---------


def test_unconfirmed_assumption_is_warning_not_blocker() -> None:
    f = _full_frame()
    f.add_claim("assumption", "frames stay small", origin="llm")  # proposed
    res = evaluate(f)
    assert res.ready is True  # an assumption never blocks
    assert any("assumption" in w for w in res.warnings)


def test_rejected_assumption_does_not_warn() -> None:
    # Issue #83: a rejected assumption was explicitly decided against — it is
    # not "unconfirmed" in the actionable sense the warning describes, and
    # the warning has no useful next move for it (confirming would reverse
    # the rejection; re-rejecting is a no-op). Must not warn.
    f = _full_frame()
    c = f.add_claim("assumption", "frames stay small", origin="llm")
    f.reject(c.id)
    res = evaluate(f)
    assert res.ready is True
    assert not any("assumption" in w for w in res.warnings)


def test_requirement_is_spec_affecting() -> None:
    f = _full_frame()
    r = f.add_claim("requirement", "must round-trip", origin="user")  # confirmed, no honesty
    res = evaluate(f)
    assert res.ready is False
    assert any(r.id in b and "honesty" in b for b in res.blockers)


def test_descriptive_kinds_do_not_block() -> None:
    f = _full_frame()
    f.add_claim("non_goal", "not a PRD generator", origin="user")
    f.add_claim("decision", "keep the shipped vocabulary", origin="user")
    assert evaluate(f).ready is True  # neither needs a honesty condition


def test_structured_result_lists_parked_items() -> None:
    f = _full_frame()
    f.add_vagueness("ship a JSON Schema file?", "follow_up")
    res = evaluate(f)
    assert res.ready is True
    assert any("follow_up" in p for p in res.parked_items)
    assert res.required_next_moves == []  # nothing left to do


# --- resolve-parked-vagueness (t3): resolved items stop blocking/parked ------


def test_resolved_blocking_vagueness_no_longer_blocks() -> None:
    f = _full_frame()
    v = f.add_vagueness("scale?", "unknown_blocking")
    f.resolve_vagueness(v.id, "decided: cap at 10k")
    res = evaluate(f)
    assert res.ready is True
    assert not any("blocking vagueness" in m for m in res.blockers)
    assert res.required_next_moves == []


def test_unresolved_blocking_vagueness_still_blocks_alongside_resolved_one() -> None:
    f = _full_frame()
    resolved_v = f.add_vagueness("scale?", "unknown_blocking")
    f.resolve_vagueness(resolved_v.id, "decided: cap at 10k")
    still_open = f.add_vagueness("auth model?", "unknown_blocking")
    res = evaluate(f)
    assert res.ready is False
    assert any(still_open.id in m for m in res.blockers)
    assert not any(resolved_v.id in m for m in res.blockers)


def test_suggest_move_for_blocking_vagueness_names_park_resolve_verbatim() -> None:
    hint = suggest_move("blocking vagueness v3 unresolved")
    assert "devague park --resolve v3" in hint
    assert "--decision" in hint
    # the old dead-end hint must be gone
    assert "re-park it as non-blocking" not in hint


def test_parked_items_excludes_resolved_nonblocking_vagueness() -> None:
    f = _full_frame()
    v = f.add_vagueness("ship a JSON Schema file?", "follow_up")
    f.resolve_vagueness(v.id, "decided: yes, ship it")
    res = evaluate(f)
    assert res.ready is True
    assert res.parked_items == []


def test_parked_items_still_lists_unresolved_nonblocking_vagueness() -> None:
    f = _full_frame()
    f.add_vagueness("ship a JSON Schema file?", "follow_up")
    res = evaluate(f)
    assert any("follow_up" in p for p in res.parked_items)


# --- issue-backlog-sweep (t4): hard-question resolve, #48/#52 ----------------


def test_resolved_blocking_hard_question_no_longer_blocks() -> None:
    f = _full_frame()
    f.add_hard_question(f.claims[0], "what if zero?", blocking=True)  # q1
    f.resolve_hard_question(f.claims[0].id, "q1", "decided: reject zero")
    res = evaluate(f)
    assert res.ready is True
    assert not any("blocking hard question" in m for m in res.blockers)
    assert res.required_next_moves == []


def test_unresolved_blocking_hard_question_still_blocks_alongside_resolved_one() -> None:
    f = _full_frame()
    cid = f.claims[0].id
    f.add_hard_question(f.claims[0], "what if zero?", blocking=True)  # q1, resolved below
    f.resolve_hard_question(cid, "q1", "decided: reject zero")
    f.add_hard_question(f.claims[0], "what about negatives?", blocking=True)  # q2, stays open
    res = evaluate(f)
    assert res.ready is False
    assert any("q2" in m for m in res.blockers)
    assert not any("q1" in m for m in res.blockers)


def test_rejected_claim_with_unresolved_blocking_question_no_longer_blocks() -> None:
    # Issue #52's fix (3): the parent claim itself was decided against via
    # reject, so its unresolved blocking question is moot and must not keep
    # convergence permanently deadlocked.
    f = _full_frame()
    extra = f.add_claim("requirement", "an extra requirement", origin="user")
    f.add_hard_question(extra, "is this even needed?", blocking=True)  # q1
    extra.status = "rejected"
    res = evaluate(f)
    assert res.ready is True
    assert not any("blocking hard question" in m for m in res.blockers)


def test_suggest_move_for_blocking_hard_question_names_interrogate_resolve_verbatim() -> None:
    hint = suggest_move("blocking hard question q3 on c2 unresolved")
    assert "devague interrogate c2 --resolve q3" in hint
    assert "--decision" in hint
    assert "USER" in hint
    # the old dead-end hint (capture/confirm never flips q.resolved) must be gone
    assert "capture/confirm the resulting claim" not in hint


# --- Reasoning Degradation Ledger (issue #97, t4): the gate stays lapse-inert -
#
# The ledger (Frame.lapses) records reasoning degradation; it must never GATE.
# convergence.evaluate touches only frame.claims and frame.open_vagueness — a
# new list field on Frame (the scope_entries precedent) is invisible to it by
# default. These tests pin that invisibility as a property, not an accident:
# if a future change wires lapses into the gate, these fail loudly instead of
# silently degrading the "an honest ledger costs you nothing" contract.


def _serialize(res) -> str:
    """Canonical string form so "byte-identical" is checked literally, not just
    via dataclass ``==`` (which these tests also assert separately)."""
    return json.dumps(dataclasses.asdict(res), sort_keys=True)


_LAPSE_SENTINEL_WHAT = "SENTINEL-LAPSE-WHAT-4f8a1c9d"
_LAPSE_SENTINEL_SKIPPED_CHECK = "SENTINEL-LAPSE-SKIPPED-CHECK-9be27a01"


def _file_lapse(f: Frame, origin: str, final_status: str):
    """File one distinctively-worded lapse on ``f``, driving it to
    ``final_status``. ``origin='llm'`` lands ``proposed``; ``origin='user'``
    lands ``approved``; passing ``final_status='rejected'`` additionally moves
    it to ``rejected`` via ``set_lapse_status`` after filing.
    """
    lapse = f.add_lapse(
        LAPSE_CODES[0],
        _LAPSE_SENTINEL_WHAT,
        skipped_check=_LAPSE_SENTINEL_SKIPPED_CHECK,
        refs=["c1"],
        origin=origin,
    )
    if final_status == "rejected":
        f.set_lapse_status(lapse.id, "rejected")
    assert lapse.status == final_status
    return lapse


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_converge_byte_identical_before_and_after_filing_lapse(origin, final_status) -> None:
    """AC1: converge output is byte-identical before/after filing a lapse, on
    an otherwise fully converged frame — tried for every lapse status."""
    f = _full_frame()
    baseline = evaluate(f)
    baseline_str = _serialize(baseline)

    _file_lapse(f, origin, final_status)

    after = evaluate(f)
    assert after == baseline
    assert _serialize(after) == baseline_str


def test_converge_byte_identical_with_all_three_lapse_statuses_at_once() -> None:
    """AC1, comprehensive: proposed + approved + rejected lapses filed together
    on one frame must not move the needle versus the lapse-free baseline."""
    f = _full_frame()
    baseline = evaluate(f)
    baseline_str = _serialize(baseline)

    f.add_lapse(LAPSE_CODES[0], "a proposed lapse", origin="llm")
    approved = f.add_lapse(LAPSE_CODES[1], "an approved lapse", origin="user")
    rejected = f.add_lapse(LAPSE_CODES[2], "a rejected lapse", origin="user")
    f.set_lapse_status(rejected.id, "rejected")
    assert approved.status == "approved"
    assert rejected.status == "rejected"

    after = evaluate(f)
    assert after == baseline
    assert _serialize(after) == baseline_str


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_converge_output_stays_lapse_free_on_converged_frame(origin, final_status) -> None:
    """AC2: no lapse id, code, or filed text ever appears in blockers/warnings/
    parked_items/required_next_moves — checked on a frame that DOES converge."""
    f = _full_frame()
    lapse = _file_lapse(f, origin, final_status)
    res = evaluate(f)
    haystack = " ".join(res.blockers + res.warnings + res.parked_items + res.required_next_moves)
    assert lapse.id not in haystack
    assert lapse.code not in haystack
    assert _LAPSE_SENTINEL_WHAT not in haystack
    assert _LAPSE_SENTINEL_SKIPPED_CHECK not in haystack


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_converge_output_stays_lapse_free_on_unconverged_frame(origin, final_status) -> None:
    """AC2, the other half: an INCOMPLETE frame (real blockers present) must
    still keep every blocker/warning/parked_item/required_next_move lapse-free
    — a lapse filed alongside a real gap must not bleed lapse text into the
    gate's own reporting of that gap."""
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")  # confirmed, but far from converged
    lapse = _file_lapse(f, origin, final_status)
    res = evaluate(f)
    assert res.ready is False  # sanity: this frame genuinely does not converge
    haystack = " ".join(res.blockers + res.warnings + res.parked_items + res.required_next_moves)
    assert lapse.id not in haystack
    assert lapse.code not in haystack
    assert _LAPSE_SENTINEL_WHAT not in haystack
    assert _LAPSE_SENTINEL_SKIPPED_CHECK not in haystack


# --- Unmet-obligation warnings (bvts t7): warning-only, and lapse-free --------
#
# The obligation warnings are the first new signal added beside the lapse pins
# above, and they are the one most likely to be confused with the ledger: both
# are append-only records about honesty. These pins keep the two separated —
# an obligation warning never gates, and no warning text ever derives from a
# lapse, even when a frame carries both at once.


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_unmet_obligation_warning_never_gates(origin, final_status) -> None:
    """The gate half of AC2: filing an obligation with no evidence adds a
    warning and changes nothing else — ready, blockers, parked_items and
    required_next_moves are identical to the obligation-free baseline."""
    baseline = evaluate(_full_frame())
    f = _full_frame()
    ob = f.add_obligation("c1", "cli", "the seam behaves", origin=origin)
    if final_status == "rejected":
        f.set_obligation_status(ob.id, "rejected")
    res = evaluate(f, met_obligations=set())

    assert res.ready is baseline.ready is True
    assert res.blockers == baseline.blockers
    assert res.parked_items == baseline.parked_items
    assert res.required_next_moves == baseline.required_next_moves
    # A rejected obligation is withdrawn — no warning at all; the other two warn.
    expected = 0 if final_status == "rejected" else 1
    assert len([w for w in res.warnings if ob.id in w]) == expected


def test_obligation_warnings_never_derive_from_lapses() -> None:
    """The lapse half of AC2: with a lapse AND an unmet obligation filed on the
    same frame, the obligation warning appears and NOTHING in the result names
    the lapse."""
    f = _full_frame()
    lapse = _file_lapse(f, "user", "approved")
    ob = f.add_obligation("c1", "cli", "the seam behaves")
    res = evaluate(f, met_obligations=set())
    haystack = " ".join(res.blockers + res.warnings + res.parked_items + res.required_next_moves)

    assert any(ob.id in w and "untested" in w for w in res.warnings)
    assert lapse.id not in haystack
    assert lapse.code not in haystack
    assert _LAPSE_SENTINEL_WHAT not in haystack
    assert _LAPSE_SENTINEL_SKIPPED_CHECK not in haystack


def test_lapse_only_frame_gains_no_obligation_warning() -> None:
    """A lapse is not an obligation: filing one must not conjure an unmet
    obligation warning out of the ledger."""
    f = _full_frame()
    baseline = evaluate(f, met_obligations=set())
    _file_lapse(f, "user", "approved")
    assert evaluate(f, met_obligations=set()) == baseline
