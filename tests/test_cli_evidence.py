"""Tests for ``devague evidence`` — file/list/adjudicate an evidence record
against a plan's delivery ledger (bvts t5).

``devague evidence`` mirrors ``devague oblige``'s file/list/confirm/reject
shape (:mod:`devague.cli._commands.oblige`) and ``devague deviate``'s plan
resolution (:mod:`devague.cli._commands.deviate`): the record files into the
current/named plan's delivery ledger via :mod:`devague.delivery_store`.
Acceptance criteria (verbatim from the confirmed plan):

1. ``devague evidence`` files a record naming obligation ref, test ref,
   behavior text, type, strength, and run reference; outcome pass or fail is
   recorded verbatim and a fail outcome round-trips visibly through list
   output
2. run reference shape is validated at filing (commit SHA format and
   parseable timestamp); a record missing a run reference at execution
   strength or above is refused
3. llm-origin lands proposed; confirm and reject are the only status
   mutations; no CLI code path executes a test (no subprocess to pytest
   anywhere, pinned by test)
"""

from __future__ import annotations

import argparse
import json

import pytest

from devague import delivery_store, plan_store, store
from devague.cli import _build_parser, main
from devague.cli._commands.learn import MOVES

RUN_COMMIT = "a6fdd8e"
RUN_TS = "2026-08-31T10:00:00Z"


def _seed_plan(monkeypatch, tmp_path) -> str:
    """Seed a converged frame + plan and return the plan slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the evidence ledger", "--title", "evidence-plan"])
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
        "--obligation": "o1",
        "--test": "tests/test_x.py::test_y",
        "--behavior": "asserts the ledger refuses an unknown code",
        "--contract": "the ledger refuses an unknown code",
        "--type": "automated",
        "--strength": "coverage",
        "--basis": "the test exists and names the behavior",
        "--outcome": "pass",
    }
    flags.update(overrides)
    args = ["evidence"]
    for k, v in flags.items():
        if v is None:
            continue
        args.extend([k, v])
    return args


# ── CLI: recording (acceptance criterion 1) ──────────────────────────────────


def test_evidence_records_entry_round_trip(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags())
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert len(delivery.evidence) == 1
    rec = delivery.evidence[0]
    assert rec.id == "e1"
    assert rec.obligation_ref == "o1"
    assert rec.test_ref == "tests/test_x.py::test_y"
    assert rec.behavior_text == "asserts the ledger refuses an unknown code"
    assert rec.contract_text == "the ledger refuses an unknown code"
    assert rec.evidence_type == "automated"
    assert rec.strength == "coverage"
    assert rec.strength_basis == "the test exists and names the behavior"
    assert rec.outcome == "pass"


def test_evidence_fail_outcome_recorded_verbatim_and_round_trips_in_list(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--outcome": "fail"}))
    assert rc == 0
    delivery = delivery_store.load(slug)
    assert delivery.evidence[0].outcome == "fail"
    capsys.readouterr()
    rc = main(["evidence", "--list", "--plan", slug])
    assert rc == 0
    out = capsys.readouterr().out
    assert "fail" in out


def test_evidence_user_origin_auto_approves_end_to_end(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags())
    assert rc == 0
    assert delivery_store.load(slug).evidence[0].status == "approved"


def test_evidence_llm_origin_lands_proposed_end_to_end(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--origin": "llm"}))
    assert rc == 0
    assert delivery_store.load(slug).evidence[0].status == "proposed"


def test_evidence_json_shape_on_record(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(_base_flags() + ["--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "e1"
    assert payload["obligation_ref"] == "o1"
    assert payload["outcome"] == "pass"
    assert payload["origin"] == "user"
    assert payload["status"] == "approved"
    assert payload["run"] is None
    assert delivery_store.load(slug)  # sanity: ledger exists


def test_evidence_missing_required_flags_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["evidence", "--obligation", "o1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--test" in err
    assert "--behavior" in err
    assert "--contract" in err
    assert "hint:" in err


def test_evidence_plan_flag_targets_named_plan(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--plan": slug}))
    assert rc == 0
    assert len(delivery_store.load(slug).evidence) == 1


def test_evidence_no_plan_selected_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(_base_flags())
    assert rc == 1
    err = capsys.readouterr().err
    assert "hint:" in err


# ── CLI: acceptance criterion 2 — run reference shape + requirement ─────────


def test_evidence_run_reference_records_when_provided(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(
        _base_flags(
            **{
                "--strength": "execution",
                "--run-commit": RUN_COMMIT,
                "--run-timestamp": RUN_TS,
            }
        )
    )
    assert rc == 0
    rec = delivery_store.load(slug).evidence[0]
    assert rec.run is not None
    assert rec.run.commit == RUN_COMMIT
    assert rec.run.timestamp == RUN_TS


def test_evidence_execution_strength_without_run_reference_is_refused(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--strength": "execution"}))
    assert rc == 1
    err = capsys.readouterr().err
    assert "run reference" in err
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).evidence == []


def test_evidence_sensitivity_strength_without_run_reference_is_refused(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--strength": "sensitivity"}))
    assert rc == 1
    err = capsys.readouterr().err
    assert "run reference" in err


def test_evidence_malformed_commit_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(
        _base_flags(
            **{
                "--strength": "execution",
                "--run-commit": "zzz",
                "--run-timestamp": RUN_TS,
            }
        )
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "commit" in err.lower()
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).evidence == []


def test_evidence_malformed_timestamp_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(
        _base_flags(
            **{
                "--strength": "execution",
                "--run-commit": RUN_COMMIT,
                "--run-timestamp": "not-a-timestamp",
            }
        )
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "timestamp" in err.lower()
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).evidence == []


def test_evidence_run_commit_without_timestamp_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--run-commit": RUN_COMMIT}))
    assert rc == 1
    err = capsys.readouterr().err
    assert "hint:" in err


def test_evidence_coverage_strength_needs_no_run_reference(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(_base_flags(**{"--strength": "coverage"}))
    assert rc == 0
    assert delivery_store.load(slug).evidence[0].run is None


# ── CLI: acceptance criterion 3 — adjudication and mode conflicts ───────────


def test_evidence_confirm_marks_approved(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    assert delivery_store.load(slug).evidence[0].status == "proposed"
    rc = main(["evidence", "--confirm", "e1", "--plan", slug])
    assert rc == 0
    assert delivery_store.load(slug).evidence[0].status == "approved"


def test_evidence_reject_marks_rejected(tmp_path, monkeypatch) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    rc = main(["evidence", "--reject", "e1", "--plan", slug])
    assert rc == 0
    assert delivery_store.load(slug).evidence[0].status == "rejected"


def test_evidence_confirm_json_shape(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    capsys.readouterr()
    rc = main(["evidence", "--confirm", "e1", "--plan", slug, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"id": "e1", "status": "approved"}


def test_evidence_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["evidence", "--confirm", "e99", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such evidence" in err
    assert "hint:" in err


def test_evidence_confirm_already_approved_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())  # user origin -> approved
    capsys.readouterr()
    rc = main(["evidence", "--confirm", "e1", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already approved" in err
    assert "hint:" in err


def test_evidence_reject_already_rejected_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags(**{"--origin": "llm"}))
    main(["evidence", "--reject", "e1", "--plan", slug])
    capsys.readouterr()
    rc = main(["evidence", "--reject", "e1", "--plan", slug])
    assert rc == 1
    assert "already rejected" in capsys.readouterr().err


def test_evidence_confirm_and_reject_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["evidence", "--confirm", "e1", "--reject", "e1"])
    assert exc.value.code == 1


def test_evidence_confirm_and_list_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["evidence", "--confirm", "e1", "--list"])
    assert exc.value.code == 1


def test_evidence_confirm_with_record_flags_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["evidence", "--confirm", "e1", "--obligation", "o1", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --confirm/--reject" in err
    assert "hint:" in err


def test_evidence_list_with_record_flags_is_refused(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["evidence", "--list", "--obligation", "o1", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --list" in err
    assert "hint:" in err


def test_evidence_record_flags_without_obligation_are_refused(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    rc = main(["evidence", "--test", "tests/test_x.py::test_y", "--plan", slug])
    assert rc != 0
    err = capsys.readouterr().err
    assert "without" in err
    assert "hint:" in err
    assert delivery_store.load_or_new(slug).evidence == []


# ── CLI: list ─────────────────────────────────────────────────────────────


def test_evidence_list_text_output_empty(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["evidence", "--list", "--plan", slug])
    assert rc == 0
    assert "no evidence" in capsys.readouterr().out


def test_evidence_bare_invocation_lists(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    capsys.readouterr()
    rc = main(["evidence", "--plan", slug])
    assert rc == 0
    out = capsys.readouterr().out
    assert "e1" in out
    assert "pass" in out
    assert "approved" in out


def test_evidence_list_json_shape(tmp_path, monkeypatch, capsys) -> None:
    slug = _seed_plan(monkeypatch, tmp_path)
    main(_base_flags())
    capsys.readouterr()
    rc = main(["evidence", "--list", "--plan", slug, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == slug
    assert len(payload["evidence"]) == 1
    rec = payload["evidence"][0]
    assert rec["id"] == "e1"
    assert rec["obligation_ref"] == "o1"


# ── acceptance criterion: no amend or delete flag on the parser ─────────────


def _evidence_subparser() -> argparse.ArgumentParser:
    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices["evidence"]
    raise AssertionError("evidence subparser not registered")


def test_evidence_parser_has_no_amend_or_delete_flag() -> None:
    p = _evidence_subparser()
    flags = {opt for a in p._actions for opt in (a.option_strings or [])}
    assert "--amend" not in flags
    assert "--delete" not in flags


# ── explain + learn ───────────────────────────────────────────────────────────


def test_explain_evidence_succeeds(capsys) -> None:
    rc = main(["explain", "evidence"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("evidence:")


def test_moves_dict_has_evidence_entry() -> None:
    assert "evidence" in MOVES
    assert isinstance(MOVES["evidence"], str) and MOVES["evidence"]


def test_bare_learn_lists_evidence_move(capsys) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "evidence" in out


# ── deterministic recording: no subprocess anywhere ──────────────────────────


def test_evidence_deterministic_no_subprocess_or_llm(tmp_path, monkeypatch) -> None:
    import subprocess

    slug = _seed_plan(monkeypatch, tmp_path)
    called = {"n": 0}
    real_run = subprocess.run

    def _guard(*args, **kwargs):
        called["n"] += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _guard)
    main(_base_flags(**{"--plan": slug}))
    assert called["n"] == 0


def test_evidence_module_has_no_subprocess_or_os_system_usage() -> None:
    """Pins the acceptance criterion literally: grep the module source for a
    subprocess/os.system invocation. Mirrors how the codebase pins other
    negatives (hasattr guards) — an honest source-level guard, not a mock
    that could pass while a real call sneaks in elsewhere."""
    import inspect

    from devague.cli._commands import evidence as evidence_mod

    source = inspect.getsource(evidence_mod)
    assert "subprocess" not in source
    assert "os.system" not in source


def test_delivery_module_has_no_subprocess_or_os_system_usage() -> None:
    import inspect

    from devague import delivery as delivery_mod

    source = inspect.getsource(delivery_mod)
    assert "subprocess" not in source
    assert "os.system" not in source
