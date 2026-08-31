"""Tests for the delivery store's evidence + behavioral-delta record families (bvts t3).

The peer of :mod:`tests.test_deviate` (which pins ``DeviationRecord``): this
file pins the two record families the behavior-validation seam adds to
:mod:`devague.delivery` — :class:`EvidenceRecord` and :class:`DeltaRecord` —
plus the append-only supersession event that flips the ``superseded`` flag on a
target record. Acceptance criteria:

1. an evidence record carries obligation ref, test ref, asserted behavior text,
   the claim-or-criterion text snapshot, evidence type, strength level with a
   recorded (never inferred) basis, a run reference at execution strength and
   above, origin and status
2. a delta record carries kind, behavior text, provenance back to a claim or
   deviation and forward to evidence, plus a ``superseded`` flag that
   supersession flips *on the target* so a reader needs no ledger scan
3. both families are append-only: adjudication and the superseded flag are the
   only mutations; llm origin lands proposed
4. ``DELIVERY_SCHEMA_VERSION`` is 2, checked fail-closed against the RAW dict,
   and a v1 delivery file loads with no error and re-saves under 2
"""

from __future__ import annotations

import json

import pytest

from devague import delivery_store
from devague.delivery import (
    DELIVERY_SCHEMA_VERSION,
    DELTA_KINDS,
    EVIDENCE_OUTCOMES,
    EVIDENCE_STATUSES,
    EVIDENCE_TYPES,
    RUN_REQUIRED_STRENGTHS,
    STRENGTH_LEVELS,
    Delivery,
    DeltaRecord,
    EvidenceRecord,
    RunReference,
    SupersessionEvent,
    from_dict,
    to_dict,
)

RUN = {"timestamp": "2026-08-31T10:00:00Z", "commit": "a6fdd8e"}


def _evidence(d: Delivery, **kw) -> EvidenceRecord:
    args = {
        "obligation_ref": "o1",
        "test_ref": "tests/test_x.py::test_y",
        "behavior_text": "asserts the ledger refuses an unknown code",
        "contract_text": "the ledger refuses an unknown code",
        "evidence_type": "automated",
        "strength": "coverage",
        "strength_basis": "the test exists and names the behavior",
        "outcome": "pass",
    }
    args.update(kw)
    return d.add_evidence(**args)


def _delta(d: Delivery, **kw) -> DeltaRecord:
    args = {
        "kind": "added",
        "behavior_text": "devague lapse files an append-only ledger entry",
        "caused_by": ["c4"],
    }
    args.update(kw)
    return d.add_delta(**args)


def _delivery() -> Delivery:
    d = Delivery(plan_slug="demo")
    _evidence(d)
    _delta(d, evidence_refs=["e1"])
    return d


# ── vocabularies ─────────────────────────────────────────────────────────────


def test_evidence_types_are_the_four_specced_types() -> None:
    assert set(EVIDENCE_TYPES) == {"automated", "integration", "manual", "observation"}


def test_strength_levels_are_the_progressive_ladder_in_order() -> None:
    assert STRENGTH_LEVELS == ("coverage", "fidelity", "execution", "sensitivity")


def test_run_reference_required_from_execution_upwards() -> None:
    assert set(RUN_REQUIRED_STRENGTHS) == {"execution", "sensitivity"}


def test_delta_kinds_are_added_amended_removed() -> None:
    assert set(DELTA_KINDS) == {"added", "amended", "removed"}


def test_evidence_statuses_mirror_the_deviation_vocabulary() -> None:
    assert set(EVIDENCE_STATUSES) == {"proposed", "approved", "rejected"}


def test_evidence_outcomes_include_fail() -> None:
    # A failing outcome is filable and rendered, never suppressed (h2).
    assert set(EVIDENCE_OUTCOMES) == {"pass", "fail"}


# ── AC1: EvidenceRecord shape ────────────────────────────────────────────────


def test_evidence_carries_every_specced_field() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(
        d,
        strength="execution",
        strength_basis="ran the suite at a6fdd8e",
        run=RunReference(**RUN),
    )
    assert rec.id == "e1"
    assert rec.obligation_ref == "o1"
    assert rec.test_ref == "tests/test_x.py::test_y"
    assert rec.behavior_text == "asserts the ledger refuses an unknown code"
    assert rec.contract_text == "the ledger refuses an unknown code"
    assert rec.evidence_type == "automated"
    assert rec.strength == "execution"
    assert rec.strength_basis == "ran the suite at a6fdd8e"
    assert rec.outcome == "pass"
    assert rec.run == RunReference(timestamp=RUN["timestamp"], commit=RUN["commit"])
    assert rec.origin == "user"
    assert rec.status == "approved"
    assert rec.superseded is False


def test_evidence_ids_are_sequential() -> None:
    d = Delivery(plan_slug="demo")
    assert (_evidence(d).id, _evidence(d).id) == ("e1", "e2")


def test_evidence_text_on_both_ends_is_required() -> None:
    # Ids are resolvable pointers, not the payload (c17/h13): a record without
    # BOTH the asserted-behavior text and the contract text snapshot is refused.
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="behavior"):
        _evidence(d, behavior_text="")
    with pytest.raises(ValueError, match="text"):
        _evidence(d, contract_text="")
    assert d.evidence == []


def test_evidence_requires_obligation_and_test_refs() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="obligation"):
        _evidence(d, obligation_ref="")
    with pytest.raises(ValueError, match="test"):
        _evidence(d, test_ref="")


def test_evidence_rejects_unknown_type_strength_outcome_origin() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="evidence type"):
        _evidence(d, evidence_type="vibes")
    with pytest.raises(ValueError, match="strength"):
        _evidence(d, strength="overwhelming")
    with pytest.raises(ValueError, match="outcome"):
        _evidence(d, outcome="mostly")
    with pytest.raises(ValueError, match="origin"):
        _evidence(d, origin="robot")


def test_strength_basis_is_required_free_text_never_inferred() -> None:
    # The basis is recorded beside the level, never derived from it (c18/h14).
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="basis"):
        _evidence(d, strength_basis="")


def test_execution_strength_requires_a_run_reference() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="run reference"):
        _evidence(d, strength="execution", strength_basis="it passes")
    with pytest.raises(ValueError, match="run reference"):
        _evidence(d, strength="sensitivity", strength_basis="mutation demo")


def test_coverage_and_fidelity_do_not_require_a_run_reference() -> None:
    d = Delivery(plan_slug="demo")
    assert _evidence(d, strength="coverage").run is None
    assert _evidence(d, strength="fidelity", strength_basis="read the test").run is None


def test_run_reference_requires_both_timestamp_and_commit() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        RunReference(timestamp="", commit="a6fdd8e")
    with pytest.raises(ValueError, match="commit"):
        RunReference(timestamp=RUN["timestamp"], commit="")


def test_failing_outcome_is_filable() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d, outcome="fail")
    assert rec.outcome == "fail"


# ── AC1/AC3: origin drives status ────────────────────────────────────────────


def test_evidence_llm_origin_lands_proposed_user_auto_approves() -> None:
    d = Delivery(plan_slug="demo")
    assert _evidence(d, origin="llm").status == "proposed"
    assert _evidence(d, origin="user").status == "approved"


def test_delta_llm_origin_lands_proposed_user_auto_approves() -> None:
    d = Delivery(plan_slug="demo")
    assert _delta(d, origin="llm").status == "proposed"
    assert _delta(d, origin="user").status == "approved"


# ── AC2: DeltaRecord shape ───────────────────────────────────────────────────


def test_delta_carries_kind_text_and_two_way_provenance() -> None:
    d = Delivery(plan_slug="demo")
    rec = _delta(d, kind="amended", caused_by=["c4", "d1"], evidence_refs=["e1", "e2"])
    assert rec.id == "b1"
    assert rec.kind == "amended"
    assert rec.behavior_text == "devague lapse files an append-only ledger entry"
    assert rec.caused_by == ["c4", "d1"]
    assert rec.evidence_refs == ["e1", "e2"]
    assert rec.origin == "user"
    assert rec.status == "approved"
    assert rec.superseded is False


def test_delta_ids_are_sequential_and_independent_of_evidence_ids() -> None:
    d = Delivery(plan_slug="demo")
    _evidence(d)
    assert (_delta(d).id, _delta(d).id) == ("b1", "b2")


def test_delta_requires_behavior_text_and_backward_provenance() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="behavior"):
        _delta(d, behavior_text="")
    with pytest.raises(ValueError, match="provenance"):
        _delta(d, caused_by=[])
    assert d.deltas == []


def test_delta_forward_evidence_refs_may_be_empty() -> None:
    # Evidence can legitimately be filed after the delta; backward provenance
    # is what can never be missing.
    d = Delivery(plan_slug="demo")
    assert _delta(d).evidence_refs == []


def test_delta_rejects_unknown_kind_and_origin() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="delta kind"):
        _delta(d, kind="rewritten")
    with pytest.raises(ValueError, match="origin"):
        _delta(d, origin="robot")


# ── AC2: supersession flips the flag ON THE TARGET, append-only ──────────────


def test_supersede_flips_the_flag_on_the_target_evidence_record() -> None:
    d = Delivery(plan_slug="demo")
    old = _evidence(d)
    new = _evidence(d, behavior_text="asserts it correctly this time")
    event = d.supersede(old.id, new.id)
    assert old.superseded is True
    assert new.superseded is False
    assert isinstance(event, SupersessionEvent)
    assert (event.id, event.action, event.target_ref, event.replacement_ref) == (
        "s1",
        "supersede",
        old.id,
        new.id,
    )
    assert d.supersessions == [event]


def test_supersede_works_on_a_delta_record_too() -> None:
    d = Delivery(plan_slug="demo")
    old = _delta(d)
    d.supersede(old.id)
    assert old.superseded is True
    assert d.supersessions[0].replacement_ref is None


def test_superseded_flag_is_readable_without_scanning_the_ledger() -> None:
    # The whole point of the flag (v1 park resolution): a reader holding the
    # record needs no inbound-link scan.
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    d.supersede(rec.id)
    reloaded = from_dict(to_dict(d))
    assert reloaded.find_evidence(rec.id).superseded is True


def test_retract_supersession_clears_the_flag_and_appends_an_event() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    d.supersede(rec.id)
    event = d.retract_supersession(rec.id)
    assert rec.superseded is False
    assert event.action == "retract"
    assert [e.action for e in d.supersessions] == ["supersede", "retract"]


def test_supersede_never_edits_record_content() -> None:
    d = Delivery(plan_slug="demo")
    old = _evidence(d)
    before = {k: v for k, v in to_dict(d)["evidence"][0].items() if k != "superseded"}
    d.supersede(old.id, _evidence(d).id)
    after = {k: v for k, v in to_dict(d)["evidence"][0].items() if k != "superseded"}
    assert before == after


def test_supersede_unknown_target_raises() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="no such record"):
        d.supersede("e99")


def test_supersede_unknown_replacement_raises() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    with pytest.raises(ValueError, match="no such record"):
        d.supersede(rec.id, "e99")
    assert rec.superseded is False


def test_supersede_self_is_refused() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    with pytest.raises(ValueError, match="itself"):
        d.supersede(rec.id, rec.id)
    assert rec.superseded is False


def test_double_supersede_is_refused_and_retract_requires_a_flag() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    d.supersede(rec.id)
    with pytest.raises(ValueError, match="already superseded"):
        d.supersede(rec.id)
    d.retract_supersession(rec.id)
    with pytest.raises(ValueError, match="not superseded"):
        d.retract_supersession(rec.id)
    assert len(d.supersessions) == 2


def test_retract_unknown_target_raises() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError, match="no such record"):
        d.retract_supersession("e99")


def test_constructing_a_record_revalidates_at_load_time() -> None:
    # Unlike frame.LapseRecord.code (a churning vocabulary validated only at
    # the filing path), these vocabularies are structural and never retire, so
    # a tampered stored status/action is refused when from_dict rebuilds it.
    with pytest.raises(ValueError, match="evidence status"):
        from_dict(
            {
                "plan_slug": "demo",
                "evidence": [
                    {
                        "id": "e1",
                        "obligation_ref": "o1",
                        "test_ref": "t",
                        "behavior_text": "b",
                        "contract_text": "c",
                        "evidence_type": "automated",
                        "strength": "coverage",
                        "strength_basis": "basis",
                        "outcome": "pass",
                        "status": "bogus",
                    }
                ],
            }
        )
    with pytest.raises(ValueError, match="delta status"):
        from_dict(
            {
                "plan_slug": "demo",
                "deltas": [
                    {"id": "b1", "kind": "added", "behavior_text": "b", "status": "bogus"},
                ],
            }
        )
    with pytest.raises(ValueError, match="supersession action"):
        from_dict(
            {
                "plan_slug": "demo",
                "supersessions": [{"id": "s1", "action": "vanish", "target_ref": "e1"}],
            }
        )


def test_supersede_rejects_unknown_origin() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    with pytest.raises(ValueError, match="origin"):
        d.supersede(rec.id, origin="robot")


# ── AC3: append-only — adjudication + flag are the only mutations ────────────


def test_no_amend_or_delete_api_exists_for_either_family() -> None:
    for name in (
        "amend_evidence",
        "delete_evidence",
        "remove_evidence",
        "amend_delta",
        "delete_delta",
        "remove_delta",
    ):
        assert not hasattr(Delivery, name), f"Delivery must not expose {name}"


def test_set_evidence_status_adjudicates() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d, origin="llm")
    assert d.set_evidence_status(rec.id, "approved") is True
    assert rec.status == "approved"
    assert d.set_evidence_status("e99", "approved") is False


def test_set_delta_status_adjudicates() -> None:
    d = Delivery(plan_slug="demo")
    rec = _delta(d, origin="llm")
    assert d.set_delta_status(rec.id, "rejected") is True
    assert rec.status == "rejected"
    assert d.set_delta_status("b99", "approved") is False


def test_set_evidence_status_rejects_unknown_status_without_mutating() -> None:
    d = Delivery(plan_slug="demo")
    rec = _evidence(d)
    with pytest.raises(ValueError, match="evidence status"):
        d.set_evidence_status(rec.id, "bogus")
    assert rec.status == "approved"


def test_set_delta_status_rejects_unknown_status_without_mutating() -> None:
    d = Delivery(plan_slug="demo")
    rec = _delta(d)
    with pytest.raises(ValueError, match="delta status"):
        d.set_delta_status(rec.id, "bogus")
    assert rec.status == "approved"


def test_find_evidence_and_find_delta() -> None:
    d = _delivery()
    assert d.find_evidence("e1") is not None
    assert d.find_evidence("b1") is None
    assert d.find_delta("b1") is not None
    assert d.find_delta("e1") is None


def test_filing_is_pure_append_earlier_records_untouched() -> None:
    d = Delivery(plan_slug="demo")
    first = _evidence(d)
    snapshot = to_dict(d)["evidence"][0]
    _evidence(d, behavior_text="something else")
    _delta(d)
    assert to_dict(d)["evidence"][0] == snapshot
    assert d.evidence[0] is first


# ── AC4: schema version 2, fail-closed on the RAW dict ───────────────────────


def test_delivery_schema_version_is_two() -> None:
    assert DELIVERY_SCHEMA_VERSION == 2


def test_roundtrip_preserves_both_families_and_events() -> None:
    d = _delivery()
    d.add_deviation("swapped approach", "t1", "faster path")
    d.supersede("e1")
    restored = from_dict(to_dict(d))
    assert restored.evidence == d.evidence
    assert restored.deltas == d.deltas
    assert restored.supersessions == d.supersessions
    assert restored.deviations == d.deviations


def test_from_dict_rebuilds_run_reference_as_a_dataclass() -> None:
    d = Delivery(plan_slug="demo")
    _evidence(d, strength="execution", strength_basis="ran it", run=RunReference(**RUN))
    restored = from_dict(to_dict(d))
    assert isinstance(restored.evidence[0].run, RunReference)
    assert restored.evidence[0].run.commit == "a6fdd8e"


def test_from_dict_tolerates_a_v1_delivery_with_no_new_families() -> None:
    raw = {
        "plan_slug": "demo",
        "schema_version": 1,
        "deviations": [
            {"id": "d1", "what": "x", "task_ref": "t1", "reason": "why"},
        ],
    }
    restored = from_dict(raw)
    assert restored.schema_version == 1
    assert (restored.evidence, restored.deltas, restored.supersessions) == ([], [], [])


def test_v1_file_loads_with_no_error_and_resaves_under_v2(tmp_path, monkeypatch) -> None:
    # AC4's data-loss guard, read the other way round: a v1 ledger written by
    # an older binary must still load, and re-saving stamps the current version.
    monkeypatch.chdir(tmp_path)
    delivery_store.DELIVERIES_DIR.mkdir(parents=True, exist_ok=True)
    v1 = {
        "plan_slug": "demo",
        "schema_version": 1,
        "created": "2026-07-14T00:00:00Z",
        "updated": "2026-07-14T00:00:00Z",
        "deviations": [
            {
                "id": "d1",
                "what": "used a different library",
                "task_ref": "t1",
                "reason": "faster",
                "affects": [],
                "origin": "user",
                "status": "approved",
                "classification": None,
            }
        ],
    }
    delivery_store.path_for("demo").write_text(json.dumps(v1), encoding="utf-8")
    loaded = delivery_store.load("demo")
    assert loaded.deviations[0].what == "used a different library"
    assert loaded.evidence == []
    delivery_store.save(loaded)
    raw = json.loads(delivery_store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 2
    assert raw["evidence"] == [] and raw["deltas"] == [] and raw["supersessions"] == []


def test_load_fails_closed_on_the_raw_dict_before_parsing(tmp_path, monkeypatch) -> None:
    # The raw-dict check must fire BEFORE from_dict: a genuinely newer file may
    # carry record shapes this binary cannot build, and the operator must see
    # IncompatibleDeliverySchemaError rather than an opaque TypeError/KeyError.
    monkeypatch.chdir(tmp_path)
    delivery_store.DELIVERIES_DIR.mkdir(parents=True, exist_ok=True)
    future = {
        "plan_slug": "demo",
        "schema_version": DELIVERY_SCHEMA_VERSION + 1,
        "deviations": [{"totally": "unknown shape"}],
        "evidence": [{"totally": "unknown shape"}],
    }
    delivery_store.path_for("demo").write_text(json.dumps(future), encoding="utf-8")
    with pytest.raises(delivery_store.IncompatibleDeliverySchemaError, match="upgrade devague"):
        delivery_store.load("demo")


def test_save_stamps_v2_and_persists_evidence_and_deltas(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    loaded = delivery_store.load("demo")
    assert loaded.schema_version == 2
    assert loaded.evidence[0].test_ref == "tests/test_x.py::test_y"
    assert loaded.deltas[0].evidence_refs == ["e1"]


def test_records_are_dataclasses_after_a_store_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    loaded = delivery_store.load("demo")
    assert isinstance(loaded.evidence[0], EvidenceRecord)
    assert isinstance(loaded.deltas[0], DeltaRecord)
