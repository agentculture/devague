"""Tests for ``devague delta`` — file/list/supersede/retract/adjudicate a
behavioral delta against a plan's delivery ledger (bvts t6).

``devague delta`` mirrors ``devague evidence``'s file/list/confirm/reject
shape (:mod:`devague.cli._commands.evidence`) and reuses
``devague.cli._refs`` (extracted from :mod:`devague.cli._commands.deviate`)
for id-shaped ref validation. Acceptance criteria (verbatim from the
confirmed plan):

1. ``devague delta`` files added, amended, or removed deltas with provenance
   refs validated against live frame claim ids and approved deviation ids;
   free-form refs allowed like deviate affects
2. a supersede event flips the superseded flag on the target record and
   appends the event; retraction appends a retraction event and clears the
   flag — no record content is ever edited, pinned by test
3. llm-origin lands proposed; list output distinguishes live, superseded, and
   retracted-supersession states without scanning
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json

import pytest

from devague import delivery_store, plan_store, store
from devague.cli import _build_parser, main
from devague.cli._commands.learn import MOVES


def _seed_plan(monkeypatch, tmp_path) -> str:
    """Seed a converged frame + plan and return the plan slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the delta ledger", "--title", "delta-plan"])
    main(["capture", "--kind", "audience", "developers", "--origin", "user"])
    main(["capture", "--kind", "after_state", "ships cleanly", "--origin", "user"])
    main(["capture", "--kind", "before_state", "was messy", "--origin", "user"])
    main(["capture", "--kind", "boundary", "scope is X only", "--origin", "user"])
    main(["capture", "--kind", "success_signal", "tests pass", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    main(["converge"])
    main(["export"])
    main(["plan", "new", "--frame", store.current_slug()])
    plan = plan_store.load(plan_store.current_slug())
    for tg in plan.targets:
        main(
            [
                "plan",
                "task",
                f"cover {tg.id}",
                "--accept",
                "criterion met",
                "--covers",
                tg.id,
            ]
        )
    plan = plan_store.load(plan_store.current_slug())
    for t in plan.tasks:
        main(["plan", "confirm", t.id])
    return plan_store.current_slug()


def _base_flags(**overrides) -> list[str]:
    flags = {
        "--kind": "added",
        "--behavior": "the ledger records a delta with backward provenance",
        "--caused-by": "c1",
    }
    flags.update(overrides)
    args = ["delta"]
    for k, v in flags.items():
        if v is None:
            continue
        if isinstance(v, list):
            for ref in v:
                args.extend([k, ref])
            continue
        args.extend([k, v])
    return args


# ── CLI: recording + ref validation (acceptance criterion 1) ────────────────


def test_delta_records_entry_round_trip(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags())
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert len(delivery.deltas) == 1
    rec = delivery.deltas[0]
    assert rec.id == "b1"
    assert rec.kind == "added"
    assert rec.behavior_text == "the ledger records a delta with backward provenance"
    assert rec.caused_by == ["c1"]
    assert rec.evidence_refs == []
    assert rec.origin == "user"
    assert rec.status == "approved"
    assert rec.superseded is False


def test_delta_caused_by_unknown_claim_id_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--caused-by": "c99"}))
    assert rc == 1
    err = capsys.readouterr().err
    assert "--caused-by" in err
    assert "c99" in err
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).deltas == []


def test_delta_caused_by_approved_deviation_is_accepted(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    plan = plan_store.load(slug)
    task_id = plan.tasks[0].id
    main(["deviate", "changed course", "--task", task_id, "--reason", "reality diverged"])
    delivery = delivery_store.load(slug)
    assert delivery.deviations[0].id == "d1"
    assert delivery.deviations[0].status == "approved"
    rc = main(_base_flags(**{"--caused-by": "d1"}))
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].caused_by == ["d1"]


def test_delta_caused_by_unapproved_deviation_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    plan = plan_store.load(slug)
    task_id = plan.tasks[0].id
    main(
        [
            "deviate",
            "proposed course change",
            "--task",
            task_id,
            "--reason",
            "reality diverged",
            "--origin",
            "llm",
        ]
    )
    delivery = delivery_store.load(slug)
    assert delivery.deviations[0].status == "proposed"
    rc = main(_base_flags(**{"--caused-by": "d1"}))
    assert rc == 1
    err = capsys.readouterr().err
    assert "--caused-by" in err
    assert "approved deviation" in err
    assert delivery_store.load_or_new(slug).deltas == []


def test_delta_caused_by_existing_delta_id_is_accepted(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    rc = main(_base_flags(**{"--kind": "amended", "--caused-by": "b1"}))
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert delivery.deltas[1].caused_by == ["b1"]


def test_delta_caused_by_unknown_delta_id_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--caused-by": "b99"}))
    assert rc == 1
    err = capsys.readouterr().err
    assert "--caused-by" in err
    assert "b99" in err
    assert delivery_store.load_or_new(slug).deltas == []


def test_delta_caused_by_free_form_text_is_always_allowed(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--caused-by": "operator observed drift in staging"}))
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].caused_by == ["operator observed drift in staging"]


def test_delta_caused_by_qualified_cross_ledger_ref_is_allowed(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--caused-by": "some-other-plan:b7"}))
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].caused_by == ["some-other-plan:b7"]


def test_delta_caused_by_other_id_shaped_ref_is_not_checked(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--caused-by": "t99"}))
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].caused_by == ["t99"]


def test_delta_missing_caused_by_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--kind", "added", "--behavior", "text"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--caused-by" in err
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).deltas == []


def test_delta_missing_behavior_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--kind", "added", "--caused-by", "c1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--behavior" in err
    assert delivery_store.load_or_new(slug).deltas == []


def test_delta_evidence_refs_stored_verbatim_and_unvalidated(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--evidence": ["e1", "e99", "nonsense"]}))
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].evidence_refs == ["e1", "e99", "nonsense"]


def test_delta_llm_origin_lands_proposed_end_to_end(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--origin": "llm"}))
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].status == "proposed"


def test_delta_user_origin_auto_approves(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags())
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].status == "approved"


def test_delta_json_shape_on_record(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(_base_flags() + ["--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "b1"
    assert payload["kind"] == "added"
    assert payload["caused_by"] == ["c1"]
    assert payload["origin"] == "user"
    assert payload["status"] == "approved"
    assert payload["superseded"] is False
    assert delivery_store.load(slug)


def test_delta_plan_flag_targets_named_plan(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--plan": slug}))
    assert rc == 0
    assert len(delivery_store.load(slug).deltas) == 1


def test_delta_no_plan_selected_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(_base_flags())
    assert rc == 1
    err = capsys.readouterr().err
    assert "hint:" in err


def test_delta_record_flags_without_kind_are_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--behavior", "text", "--plan", slug])
    assert rc != 0
    err = capsys.readouterr().err
    assert "without" in err
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).deltas == []


# ── CLI: supersede / retract (acceptance criterion 2) ────────────────────────


def test_supersede_flips_flag_and_appends_event(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    rc = main(["delta", "--supersede", "b1", "--plan", slug])
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert delivery.deltas[0].superseded is True
    assert len(delivery.supersessions) == 1
    event = delivery.supersessions[0]
    assert event.action == "supersede"
    assert event.target_ref == "b1"
    assert event.replacement_ref is None


def test_supersede_with_replacement_records_it(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    main(_base_flags(**{"--kind": "amended", "--caused-by": "b1"}))
    rc = main(["delta", "--supersede", "b1", "--replacement", "b2", "--plan", slug])
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert delivery.supersessions[0].replacement_ref == "b2"


def test_retract_clears_flag_and_appends_retraction_event(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    main(["delta", "--supersede", "b1", "--plan", slug])
    rc = main(["delta", "--retract", "b1", "--plan", slug])
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert delivery.deltas[0].superseded is False
    assert len(delivery.supersessions) == 2
    assert delivery.supersessions[1].action == "retract"
    assert delivery.supersessions[1].target_ref == "b1"


def test_supersede_and_retract_never_edit_record_content(tmp_path, monkeypatch) -> None:
    """Pins acceptance criterion 2's "no record content is ever edited": every
    field on the target record besides ``superseded`` is byte-identical before
    and after a supersede/retract round trip."""
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    before = copy.deepcopy(delivery_store.load(slug).deltas[0])
    main(["delta", "--supersede", "b1", "--plan", slug])
    main(["delta", "--retract", "b1", "--plan", slug])
    after = delivery_store.load(slug).deltas[0]
    before_dict = dataclasses.asdict(before)
    after_dict = dataclasses.asdict(after)
    before_dict.pop("superseded")
    after_dict.pop("superseded")
    assert before_dict == after_dict
    assert after.superseded is False


def test_supersede_unknown_target_errors(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--supersede", "b99", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such record" in err
    assert "hint:" in err


def test_supersede_already_superseded_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    main(["delta", "--supersede", "b1", "--plan", slug])
    capsys.readouterr()
    rc = main(["delta", "--supersede", "b1", "--plan", slug])
    assert rc == 1
    assert "already superseded" in capsys.readouterr().err


def test_retract_not_superseded_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    rc = main(["delta", "--retract", "b1", "--plan", slug])
    assert rc == 1
    assert "not superseded" in capsys.readouterr().err


def test_supersede_can_target_an_evidence_record(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(
        [
            "evidence",
            "--obligation",
            "o1",
            "--test",
            "tests/test_x.py::test_y",
            "--behavior",
            "asserts x",
            "--contract",
            "x holds",
            "--type",
            "automated",
            "--strength",
            "coverage",
            "--basis",
            "exists",
            "--outcome",
            "pass",
            "--plan",
            slug,
        ]
    )
    rc = main(["delta", "--supersede", "e1", "--plan", slug])
    assert rc == 0
    assert delivery_store.load(slug).evidence[0].superseded is True


def test_supersede_and_confirm_are_mutually_exclusive(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--supersede", "b1", "--confirm", "b1", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --confirm and --supersede" in err


def test_supersede_with_record_flags_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    rc = main(["delta", "--supersede", "b1", "--kind", "added", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --supersede" in err


# ── CLI: adjudication + list distinguishing live/superseded (criterion 3) ───


def test_delta_confirm_marks_approved(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    assert delivery_store.load(slug).deltas[0].status == "proposed"
    rc = main(["delta", "--confirm", "b1", "--plan", slug])
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].status == "approved"


def test_delta_reject_marks_rejected(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    rc = main(["delta", "--reject", "b1", "--plan", slug])
    assert rc == 0
    assert delivery_store.load(slug).deltas[0].status == "rejected"


def test_delta_confirm_json_shape(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    capsys.readouterr()
    rc = main(["delta", "--confirm", "b1", "--plan", slug, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"id": "b1", "status": "approved"}


def test_delta_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--confirm", "b99", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such delta" in err
    assert "hint:" in err


def test_delta_confirm_already_approved_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    capsys.readouterr()
    rc = main(["delta", "--confirm", "b1", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already approved" in err


def test_delta_confirm_and_reject_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["delta", "--confirm", "b1", "--reject", "b1"])
    assert exc.value.code == 1


def test_delta_confirm_and_list_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["delta", "--confirm", "b1", "--list"])
    assert exc.value.code == 1


def test_delta_list_with_record_flags_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["delta", "--list", "--kind", "added", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --list" in err
    assert "hint:" in err


def test_delta_list_text_output_empty(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["delta", "--list", "--plan", slug])
    assert rc == 0
    assert "no deltas" in capsys.readouterr().out


def test_delta_bare_invocation_lists(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    capsys.readouterr()
    rc = main(["delta", "--plan", slug])
    assert rc == 0
    out = capsys.readouterr().out
    assert "b1" in out
    assert "added" in out
    assert "approved" in out
    assert "[live]" in out


def test_delta_list_shows_superseded_state_without_scanning(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    main(["delta", "--supersede", "b1", "--plan", slug])
    capsys.readouterr()
    rc = main(["delta", "--plan", slug])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[superseded]" in out
    assert "b1" in out
    assert "supersede" in out


def test_delta_list_shows_retracted_supersession_as_live_again(
    tmp_path, monkeypatch, capsys
) -> None:
    """A supersede later retracted renders the record as live again (no
    special state beyond live); the event log carries both events."""
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    main(["delta", "--supersede", "b1", "--plan", slug])
    main(["delta", "--retract", "b1", "--plan", slug])
    capsys.readouterr()
    rc = main(["delta", "--plan", slug])
    assert rc == 0
    out = capsys.readouterr().out
    assert "b1: added" in out
    assert "[live]" in out
    assert "[superseded]" not in out
    assert "retract" in out


def test_delta_list_json_shape(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    main(["delta", "--supersede", "b1", "--plan", slug])
    capsys.readouterr()
    rc = main(["delta", "--list", "--plan", slug, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == slug
    assert len(payload["deltas"]) == 1
    assert payload["deltas"][0]["id"] == "b1"
    assert payload["deltas"][0]["superseded"] is True
    assert len(payload["supersessions"]) == 1
    assert payload["supersessions"][0]["action"] == "supersede"


# ── acceptance criterion: no amend or delete flag on the parser ─────────────


def _delta_subparser() -> argparse.ArgumentParser:
    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices["delta"]
    raise AssertionError("delta subparser not registered")


def test_delta_parser_has_no_amend_or_delete_flag() -> None:
    p = _delta_subparser()
    flags = {opt for a in p._actions for opt in (a.option_strings or [])}
    assert "--amend" not in flags
    assert "--delete" not in flags


# ── explain + learn ───────────────────────────────────────────────────────────


def test_explain_delta_succeeds(capsys) -> None:
    rc = main(["explain", "delta"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("delta:")


def test_moves_dict_has_delta_entry() -> None:
    assert "delta" in MOVES
    assert isinstance(MOVES["delta"], str)
    assert MOVES["delta"]


# ── deviate's own --affects ref checks still pass after the _refs extraction ─


def test_deviate_affects_unknown_ref_still_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    plan = plan_store.load(slug)
    task_id = plan.tasks[0].id
    rc = main(
        [
            "deviate",
            "changed course",
            "--task",
            task_id,
            "--reason",
            "reality diverged",
            "--affects",
            "c99",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "--affects" in err
    assert "does not resolve" in err


def test_deviate_affects_known_claim_still_accepted(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    plan = plan_store.load(slug)
    task_id = plan.tasks[0].id
    rc = main(
        [
            "deviate",
            "changed course",
            "--task",
            task_id,
            "--reason",
            "reality diverged",
            "--affects",
            "c1",
        ]
    )
    assert rc == 0
    assert delivery_store.load(slug).deviations[0].affects == ["c1"]
