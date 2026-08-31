from __future__ import annotations

import pytest

from devague.frame import (
    CLAIM_KINDS,
    SCHEMA_VERSION,
    SPEC_AFFECTING_KINDS,
    Claim,
    ClaimRevision,
    Frame,
    HonestyCondition,
    Vagueness,
    from_dict,
    to_dict,
)


def test_add_claim_user_is_confirmed_llm_is_proposed() -> None:
    f = Frame(slug="s", title="t")
    a = f.add_claim("announcement", "we shipped X", origin="user")
    b = f.add_claim("audience", "devs", origin="llm")
    assert a.id == "c1" and a.status == "confirmed"
    assert b.id == "c2" and b.status == "proposed"


def test_add_honesty_and_hard_question_and_vagueness_ids() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x")
    h = f.add_honesty(c, "must be measurable", origin="llm")
    q = f.add_hard_question(c, "what if empty?", blocking=True)
    v = f.add_vagueness("unsure about scale", "unknown_blocking")
    assert h.id == "h1" and h.status == "proposed"
    assert q.id == "q1" and q.blocking is True and q.resolved is False
    assert v.id == "v1" and v.kind == "unknown_blocking"


def test_set_status_finds_claim_or_honesty() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("audience", "devs", origin="llm")
    h = f.add_honesty(c, "cond", origin="llm")
    assert f.set_status("c1", "confirmed") is True and c.status == "confirmed"
    assert f.set_status("h1", "confirmed") is True and h.status == "confirmed"
    assert f.set_status("nope", "confirmed") is False


def test_roundtrip_to_from_dict() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")
    f.add_honesty(c, "cond")
    f.add_hard_question(c, "q?", blocking=True)
    f.add_vagueness("v", "follow_up", claim_id="c1")
    f.resolve_vagueness("v1", "decided: ship v1", claim_id="c1")
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.claims[0].honesty_conditions[0].text == "cond"
    assert f2.open_vagueness[0].resolved is True
    assert f2.open_vagueness[0].resolution_claim_id == "c1"


# --- #5 spec contract: enriched entity model ----------------------------------


def test_new_claim_kinds_present() -> None:
    for kind in ("non_goal", "requirement", "assumption", "decision"):
        assert kind in CLAIM_KINDS


def test_requirement_is_spec_affecting_descriptive_kinds_are_not() -> None:
    assert "requirement" in SPEC_AFFECTING_KINDS
    # Descriptive kinds (and the soft assumption kind) must not demand a honesty
    # condition / block convergence by being proposed.
    for kind in ("non_goal", "decision", "open_question", "assumption"):
        assert kind not in SPEC_AFFECTING_KINDS


def test_can_add_new_kind_claims() -> None:
    f = Frame(slug="s", title="t")
    r = f.add_claim("requirement", "must persist losslessly", origin="user")
    n = f.add_claim("non_goal", "not a PRD generator", origin="user")
    a = f.add_claim("assumption", "frames are small", origin="llm")
    d = f.add_claim("decision", "keep shipped vocabulary", origin="user")
    assert (r.kind, n.kind, a.kind, d.kind) == (
        "requirement",
        "non_goal",
        "assumption",
        "decision",
    )
    assert a.status == "proposed"  # llm origin still lands proposed


def test_frame_carries_schema_version() -> None:
    f = Frame(slug="s", title="t")
    assert f.schema_version == SCHEMA_VERSION
    assert to_dict(f)["schema_version"] == SCHEMA_VERSION
    assert from_dict(to_dict(f)).schema_version == SCHEMA_VERSION


def test_legacy_frame_without_schema_version_loads() -> None:
    # A 0.4.0 frame has no schema_version key — it must still load.
    f = from_dict({"slug": "s", "title": "t", "claims": [], "open_vagueness": []})
    assert f.schema_version == SCHEMA_VERSION


@pytest.mark.parametrize("bad", [1.9, True, "1", None])
def test_from_dict_rejects_non_integer_schema_version(bad) -> None:
    # int() would silently coerce 1.9->1 / True->1; a malformed type must raise.
    with pytest.raises(ValueError, match="schema_version"):
        from_dict({"slug": "s", "title": "t", "schema_version": bad})


def test_dataclasses_validate_enums() -> None:
    with pytest.raises(ValueError):
        Claim(id="c1", kind="bogus", text="x")
    with pytest.raises(ValueError):
        Claim(id="c1", kind="audience", text="x", origin="alien")
    with pytest.raises(ValueError):
        Claim(id="c1", kind="audience", text="x", status="weird")
    with pytest.raises(ValueError):
        Vagueness(id="v1", text="x", kind="nope")
    with pytest.raises(ValueError):
        HonestyCondition(id="h1", text="x", status="weird")


# --- resolve-parked-vagueness t1: Vagueness resolution state (schema v3) ------


def test_schema_version_is_6() -> None:
    # v3 (resolve-parked-vagueness t1) added Vagueness.resolved/resolution; v4
    # (issue-backlog-sweep t2) reserved the next bump for t4's HardQuestion
    # resolution field — t2 itself only hardened load order/tolerance; v5
    # (issue #97 t1) adds Frame.lapses / LapseRecord, the Reasoning
    # Degradation Ledger; v6 (bvts t1) adds Frame.obligations / Obligation.
    assert SCHEMA_VERSION == 6


def test_vagueness_gains_resolved_and_resolution_defaults() -> None:
    v = Vagueness(id="v1", text="x", kind="follow_up", claim_id="c1")
    assert v.resolved is False
    assert v.resolution == ""
    assert (v.id, v.text, v.kind, v.claim_id) == ("v1", "x", "follow_up", "c1")


def test_resolve_vagueness_marks_resolved_and_records_resolution() -> None:
    f = Frame(slug="s", title="t")
    f.add_vagueness("unsure about scale", "unknown_blocking")
    resolved = f.resolve_vagueness("v1", "decided: cap at 10k")
    assert resolved.resolved is True
    assert resolved.resolution == "decided: cap at 10k"
    assert f.open_vagueness[0].resolved is True
    assert f.open_vagueness[0].resolution == "decided: cap at 10k"


def test_resolve_vagueness_unknown_id_raises() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown"):
        f.resolve_vagueness("v99", "decision")


def test_resolve_vagueness_already_resolved_raises() -> None:
    f = Frame(slug="s", title="t")
    f.add_vagueness("unsure about scale", "unknown_blocking")
    f.resolve_vagueness("v1", "decision one")
    with pytest.raises(ValueError, match="already"):
        f.resolve_vagueness("v1", "decision two")


def test_set_status_does_not_touch_vagueness() -> None:
    # v-ids stay out of confirm/reject (decision c11) — set_status must not
    # find or mutate a Vagueness by id.
    f = Frame(slug="s", title="t")
    f.add_vagueness("unsure about scale", "unknown_blocking")
    assert f.set_status("v1", "confirmed") is False
    assert f.open_vagueness[0].resolved is False


def test_legacy_v2_vagueness_without_resolved_keys_defaults() -> None:
    # A v2 frame's open_vagueness entries predate resolved/resolution.
    d = {
        "slug": "s",
        "title": "t",
        "schema_version": 2,
        "claims": [],
        "open_vagueness": [{"id": "v1", "text": "x", "kind": "follow_up", "claim_id": None}],
    }
    f = from_dict(d)
    assert f.open_vagueness[0].resolved is False
    assert f.open_vagueness[0].resolution == ""


# --- resolve-parked-vagueness t5: deciding-claim link on resolve --------------


def test_vagueness_gains_resolution_claim_id_default() -> None:
    v = Vagueness(id="v1", text="x", kind="follow_up", claim_id="c1")
    assert v.resolution_claim_id is None


def test_resolve_vagueness_records_deciding_claim() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")  # c1
    f.add_vagueness("unsure about scale", "unknown_blocking")
    resolved = f.resolve_vagueness("v1", "decided: cap at 10k", claim_id="c1")
    assert resolved.resolution_claim_id == "c1"
    assert f.open_vagueness[0].resolution_claim_id == "c1"


def test_resolve_vagueness_without_claim_id_leaves_it_none() -> None:
    f = Frame(slug="s", title="t")
    f.add_vagueness("unsure about scale", "unknown_blocking")
    resolved = f.resolve_vagueness("v1", "decided: cap at 10k")
    assert resolved.resolution_claim_id is None


def test_resolve_vagueness_claim_id_does_not_overwrite_owning_claim_id() -> None:
    # claim_id is the *owning* claim set at park time; resolution_claim_id is
    # the *deciding* claim recorded at resolve time — resolve must not clobber
    # the former with the latter.
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")  # c1
    f.add_claim("audience", "devs", origin="user")  # c2
    f.add_vagueness("unsure about scale", "unknown_blocking", claim_id="c1")
    resolved = f.resolve_vagueness("v1", "decided: cap at 10k", claim_id="c2")
    assert resolved.claim_id == "c1"
    assert resolved.resolution_claim_id == "c2"


def test_resolve_vagueness_unknown_claim_id_raises() -> None:
    f = Frame(slug="s", title="t")
    f.add_vagueness("unsure about scale", "unknown_blocking")
    with pytest.raises(ValueError, match="unknown claim"):
        f.resolve_vagueness("v1", "decided", claim_id="c99")
    # Fails closed before mutating: the vagueness stays unresolved.
    assert f.open_vagueness[0].resolved is False


def test_legacy_v3_vagueness_without_resolution_claim_id_defaults() -> None:
    # An early-v3 frame's open_vagueness entries (t1) predate resolution_claim_id.
    d = {
        "slug": "s",
        "title": "t",
        "schema_version": 3,
        "claims": [],
        "open_vagueness": [
            {
                "id": "v1",
                "text": "x",
                "kind": "follow_up",
                "claim_id": None,
                "resolved": True,
                "resolution": "done",
            }
        ],
    }
    f = from_dict(d)
    assert f.open_vagueness[0].resolved is True
    assert f.open_vagueness[0].resolution == "done"
    assert f.open_vagueness[0].resolution_claim_id is None


# --- issue-backlog-sweep t4: HardQuestion resolution (schema v4, #48/#52) -----


def test_hard_question_gains_resolution_default() -> None:
    from devague.frame import HardQuestion

    q = HardQuestion(id="q1", text="what if empty?", blocking=True)
    assert q.resolved is False
    assert q.resolution == ""


def test_resolve_hard_question_marks_resolved_and_records_resolution() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_hard_question(c, "is this real?", blocking=True)  # q1
    resolved = f.resolve_hard_question("c1", "q1", "decided: yes, it is real")
    assert resolved.resolved is True
    assert resolved.resolution == "decided: yes, it is real"
    assert c.hard_questions[0].resolved is True
    assert c.hard_questions[0].resolution == "decided: yes, it is real"


def test_resolve_hard_question_decision_is_optional() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_hard_question(c, "is this real?", blocking=True)  # q1
    resolved = f.resolve_hard_question("c1", "q1")
    assert resolved.resolved is True
    assert resolved.resolution == ""


def test_resolve_hard_question_unknown_claim_raises() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown claim"):
        f.resolve_hard_question("c99", "q1", "decision")


def test_resolve_hard_question_unknown_qid_raises() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")  # c1
    with pytest.raises(ValueError, match="no such hard question"):
        f.resolve_hard_question("c1", "q99", "decision")


def test_resolve_hard_question_wrong_claim_raises() -> None:
    # q1 belongs to c1, not c2 — the claim id disambiguates (decision c36), so
    # naming the right qid on the wrong claim must fail closed, not silently
    # resolve across claims.
    f = Frame(slug="s", title="t")
    c1 = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_claim("audience", "devs", origin="user")  # c2
    f.add_hard_question(c1, "is this real?", blocking=True)  # q1, owned by c1
    with pytest.raises(ValueError, match="no such hard question"):
        f.resolve_hard_question("c2", "q1", "decision")
    assert c1.hard_questions[0].resolved is False


def test_resolve_hard_question_already_resolved_raises() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_hard_question(c, "is this real?", blocking=True)  # q1
    f.resolve_hard_question("c1", "q1", "decision one")
    with pytest.raises(ValueError, match="already"):
        f.resolve_hard_question("c1", "q1", "decision two")
    assert c.hard_questions[0].resolution == "decision one"  # untouched


def test_roundtrip_preserves_hard_question_resolution() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")
    f.add_hard_question(c, "is this real?", blocking=True)
    f.resolve_hard_question("c1", "q1", "decided: yes")
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.claims[0].hard_questions[0].resolved is True
    assert f2.claims[0].hard_questions[0].resolution == "decided: yes"


def test_legacy_v3_hard_question_without_resolution_defaults() -> None:
    # A v3-or-older frame's hard_questions predate the resolution field.
    d = {
        "slug": "s",
        "title": "t",
        "schema_version": 3,
        "claims": [
            {
                "id": "c1",
                "kind": "announcement",
                "text": "x",
                "hard_questions": [
                    {"id": "q1", "text": "is this real?", "resolved": False, "blocking": True}
                ],
            }
        ],
    }
    f = from_dict(d)
    assert f.claims[0].hard_questions[0].resolved is False
    assert f.claims[0].hard_questions[0].resolution == ""


# --- reject cascade (issue #83): rejecting a claim sweeps its attachments ----


def test_reject_claim_cascades_over_honesty_and_hard_question() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("boundary", "policy gate must receive rewritten args", origin="llm")
    h = f.add_honesty(c, "the ordering holds", origin="llm")  # h1, proposed
    q = f.add_hard_question(c, "risk: a hook could launder a command", blocking=False)  # q1
    cascaded = f.reject(c.id)
    assert c.status == "rejected"
    assert h.status == "rejected"
    assert cascaded == [h.id, q.id]  # honesty ids first, then hard-question ids


def test_reject_claim_cascade_skips_already_rejected_honesty() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("boundary", "x", origin="llm")
    h1 = f.add_honesty(c, "cond one", origin="llm")
    h2 = f.add_honesty(c, "cond two", origin="llm")
    f.set_status(h1.id, "rejected")  # already decided independently
    cascaded = f.reject(c.id)
    assert h1.status == "rejected" and h2.status == "rejected"
    assert cascaded == [h2.id]  # h1 wasn't newly cascaded — it was already rejected


def test_reject_claim_cascade_skips_resolved_hard_question() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("boundary", "x", origin="llm")
    q1 = f.add_hard_question(c, "still open", blocking=True)
    q2 = f.add_hard_question(c, "already answered", blocking=True)
    f.resolve_hard_question(c.id, q2.id, "decided: yes")
    cascaded = f.reject(c.id)
    assert cascaded == [q1.id]  # the already-resolved question is not "swept"


def test_reject_already_rejected_claim_reports_no_cascade_again() -> None:
    # Idempotence / no double-reporting: a second reject of the same claim
    # must not re-claim credit for the cascade the first call performed.
    f = Frame(slug="s", title="t")
    c = f.add_claim("boundary", "x", origin="llm")
    f.add_honesty(c, "cond", origin="llm")
    f.add_hard_question(c, "risk", blocking=False)
    first = f.reject(c.id)
    assert first != []
    second = f.reject(c.id)
    assert second == []
    assert c.status == "rejected"


def test_reject_bare_honesty_id_is_a_plain_flip_no_cascade() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("boundary", "x", origin="llm")
    h = f.add_honesty(c, "cond", origin="llm")
    cascaded = f.reject(h.id)
    assert h.status == "rejected"
    assert c.status == "proposed"  # the parent claim is untouched
    assert cascaded == []


def test_reject_unknown_id_raises() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown"):
        f.reject("zzz")


# --- amend (issue #84): claim + scope-entry correction without id churn -------


def test_amend_claim_confirmed_flips_to_proposed_and_reports_flip() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("before_state", "count is 16", origin="user")  # user -> confirmed
    h = f.add_honesty(c, "count is independently verified", origin="user")
    c.instruction = "verify via `grep -c literal file.py`"
    assert c.status == "confirmed"

    claim, flipped = f.amend_claim("c1", text="count is 21")

    assert flipped is True
    assert claim is c
    assert claim.id == "c1"  # no id churn
    assert claim.text == "count is 21"
    assert claim.status == "proposed"  # flipped, mirroring interrogate --instruction
    assert claim.origin == "user"  # never changes silently
    # Every attachment survives, untouched:
    assert claim.honesty_conditions == [h]
    assert claim.instruction == "verify via `grep -c literal file.py`"


def test_amend_claim_not_confirmed_does_not_flip() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "x", origin="llm")  # llm -> proposed
    claim, flipped = f.amend_claim("c1", text="x, corrected")
    assert flipped is False
    assert claim.status == "proposed"
    assert claim.origin == "llm"


def test_amend_claim_rejected_stays_rejected_no_flip() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "x", origin="llm")
    f.reject("c1")
    claim, flipped = f.amend_claim("c1", text="x, corrected")
    assert flipped is False
    assert claim.status == "rejected"


def test_amend_claim_kind_only() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "x", origin="user")
    claim, _ = f.amend_claim("c1", kind="requirement")
    assert claim.kind == "requirement"
    assert claim.text == "x"  # untouched


def test_amend_claim_records_revision_with_reason() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("before_state", "count is 16", origin="user")
    f.amend_claim("c1", text="count is 21", reason="reviewer caught a miscount")
    claim = f.find_claim("c1")
    assert claim.revisions == [
        ClaimRevision(text="count is 16", kind="before_state", reason="reviewer caught a miscount")
    ]
    assert claim.text == "count is 21"  # current value is the corrected one


def test_amend_claim_revision_defaults_reason_empty() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "x", origin="user")
    f.amend_claim("c1", text="y")
    assert f.find_claim("c1").revisions[0].reason == ""


def test_amend_claim_multiple_amends_append_to_revisions_in_order() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "v1", origin="user")
    f.amend_claim("c1", text="v2")
    f.amend_claim("c1", text="v3")
    claim = f.find_claim("c1")
    assert [r.text for r in claim.revisions] == ["v1", "v2"]
    assert claim.text == "v3"


def test_amend_claim_preserves_inbound_scope_seed() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("before_state", "count is 16", origin="user")
    f.add_scope_entry("colleague/tools.py:669-722", "spawn literal count", seeds=["c1"])
    f.amend_claim("c1", text="count is 21")
    # The seed reference still resolves to a live (non-rejected) claim — no
    # id churn means no dangling provenance (the damage issue #84 documents).
    assert f.scope_entries[0].seeds == ["c1"]
    assert f.find_claim("c1").status != "rejected"


def test_amend_claim_unknown_id_raises() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown claim id"):
        f.amend_claim("c99", text="x")


def test_amend_claim_requires_text_or_kind() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "x", origin="user")
    with pytest.raises(ValueError, match="requires a new text"):
        f.amend_claim("c1")


def test_amend_claim_unknown_kind_raises() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("boundary", "x", origin="user")
    with pytest.raises(ValueError, match="unknown claim kind"):
        f.amend_claim("c1", kind="bogus")


def test_amend_claim_roundtrips_revisions_via_dict() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("before_state", "count is 16", origin="user")
    f.amend_claim("c1", text="count is 21", reason="miscount")
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.claims[0].revisions[0].text == "count is 16"
    assert f2.claims[0].revisions[0].reason == "miscount"


def test_legacy_claim_dict_without_revisions_loads_with_empty_list() -> None:
    legacy = {
        "slug": "s",
        "title": "t",
        "claims": [
            {
                "id": "c1",
                "kind": "boundary",
                "text": "x",
                "origin": "user",
                "status": "confirmed",
            }
        ],
        "open_vagueness": [],
    }
    f = from_dict(legacy)
    assert f.claims[0].revisions == []


def test_amend_scope_entry_replaces_finding_in_place() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("before_state", "count is 16", origin="user")
    entry = f.add_scope_entry("colleague subprocess inventory", "16 spawn literals", seeds=["c1"])
    amended = f.amend_scope_entry("s1", "21 spawn literals across 15 modules")
    assert amended is entry
    assert entry.id == "s1"  # no id churn
    assert entry.surface == "colleague subprocess inventory"  # untouched
    assert entry.finding == "21 spawn literals across 15 modules"
    assert entry.seeds == ["c1"]  # untouched


def test_amend_scope_entry_unknown_id_raises() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown scope entry id"):
        f.amend_scope_entry("s99", "x")


def test_amend_scope_entry_empty_finding_raises() -> None:
    f = Frame(slug="s", title="t")
    f.add_scope_entry("a.py", "first")
    with pytest.raises(ValueError, match="requires a new finding"):
        f.amend_scope_entry("s1", "")


# --- scope --seeds accepts question ids (issue #84's "smaller, related gap") -


def test_find_hard_question_looks_up_across_all_claims() -> None:
    f = Frame(slug="s", title="t")
    c1 = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_claim("audience", "devs", origin="user")  # c2
    q = f.add_hard_question(c1, "is this real?", blocking=True)  # q1
    assert f.find_hard_question("q1") is q


def test_find_hard_question_unknown_id_returns_none() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")  # c1
    assert f.find_hard_question("q99") is None


def test_add_scope_entry_accepts_hard_question_seed_id() -> None:
    # The /scope routing table sends a "needs a user decision" finding to the
    # `question` move rather than `capture` — a scope entry recording that
    # finding must be able to cite the hard question it seeded, not just a
    # claim (#84).
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_hard_question(c, "is this real?", blocking=True)  # q1
    entry = f.add_scope_entry("some/surface.py", "a finding", seeds=["q1"])
    assert entry.seeds == ["q1"]


def test_add_scope_entry_accepts_mixed_claim_and_question_seeds() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")  # c1
    f.add_hard_question(c, "is this real?", blocking=True)  # q1
    entry = f.add_scope_entry("some/surface.py", "a finding", seeds=["c1", "q1"])
    assert entry.seeds == ["c1", "q1"]


def test_add_scope_entry_unknown_question_seed_id_raises() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")  # c1 — no hard question exists
    with pytest.raises(ValueError, match="unknown seed claim id"):
        f.add_scope_entry("some/surface.py", "a finding", seeds=["q1"])
    assert f.scope_entries == []  # transactional: nothing recorded on the refusal
