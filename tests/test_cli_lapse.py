"""Tests for ``devague lapse`` — file/list/adjudicate a reasoning-degradation
lapse on the current frame (issue #97 t2).

``devague lapse`` is the CLI twin of ``devague deviate`` (:mod:`devague.cli.
_commands.deviate`), minus the plan link (``--task``) and minus id-ref
validation — a lapse's ``refs`` stay free text, never checked against known
ids (see :class:`devague.frame.LapseRecord`'s docstring). Acceptance
criteria (verbatim from the confirmed plan):

1. ``devague lapse "<what>" --code <code>`` files against the current frame
   and echoes the minted id; ``--origin llm`` lands proposed; ``--skipped
   "<check>"`` and repeatable ``--ref`` are stored verbatim
2. ``--list [--json]`` renders every record with id, code, and status;
   ``--confirm <lN>`` / ``--reject <lN>`` transition only proposed records,
   refuse otherwise, and are mutually exclusive with recording
3. the argument surface has no amend or delete flag — pinned by a test over
   the parser
4. ``devague explain lapse`` succeeds and bare ``devague learn`` lists the
   move — the MOVES entry is test-pinned
5. recording is deterministic: no subprocess and no LLM call, mirroring the
   deviate determinism test
"""

from __future__ import annotations

import argparse
import json

import pytest

from devague import store
from devague.cli import _build_parser, main
from devague.cli._commands.learn import MOVES
from devague.frame import LAPSE_CODES


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship sharper method", "--title", "sharper-method"])


# ── CLI: recording (acceptance criterion 1) ──────────────────────────────────


def test_lapse_records_entry_round_trip(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    rc = main(
        [
            "lapse",
            "assumed the mean was already normalized",
            "--code",
            "assumption-for-measurement",
        ]
    )
    assert rc == 0
    frame = store.load(slug)
    assert len(frame.lapses) == 1
    rec = frame.lapses[0]
    assert rec.id == "l1"
    assert rec.code == "assumption-for-measurement"
    assert rec.what == "assumed the mean was already normalized"
    assert rec.skipped_check == ""
    assert rec.refs == []


def test_lapse_user_origin_auto_approves_end_to_end(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["lapse", "skipped grading", "--code", "grader-unverified"])
    assert rc == 0
    assert store.load(store.current_slug()).lapses[0].status == "approved"


def test_lapse_llm_origin_lands_proposed_end_to_end(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(
        [
            "lapse",
            "skipped grading",
            "--code",
            "grader-unverified",
            "--origin",
            "llm",
        ]
    )
    assert rc == 0
    assert store.load(store.current_slug()).lapses[0].status == "proposed"


def test_lapse_skipped_and_refs_stored_verbatim(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(
        [
            "lapse",
            "no control group used",
            "--code",
            "control-absent",
            "--skipped",
            "control-group review",
            "--ref",
            "c1",
            "--ref",
            "the auth benchmark",
        ]
    )
    assert rc == 0
    rec = store.load(store.current_slug()).lapses[0]
    assert rec.skipped_check == "control-group review"
    assert rec.refs == ["c1", "the auth benchmark"]


def test_lapse_refs_are_never_validated_against_known_ids(tmp_path, monkeypatch) -> None:
    # Unlike scope --seeds, a lapse's --ref is free text: a nonexistent id
    # (c99) must NOT be refused.
    _seed(monkeypatch, tmp_path)
    rc = main(
        [
            "lapse",
            "provenance unclear",
            "--code",
            "provenance-missing",
            "--ref",
            "c99",
        ]
    )
    assert rc == 0
    assert store.load(store.current_slug()).lapses[0].refs == ["c99"]


def test_lapse_json_shape_on_record(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(
        [
            "lapse",
            "n below claimed sample size",
            "--code",
            "n-below-claim",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "id": "l1",
        "code": "n-below-claim",
        "what": "n below claimed sample size",
        "skipped_check": "",
        "refs": [],
        "origin": "user",
        "status": "approved",
    }


def test_lapse_missing_code_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["lapse", "something went wrong"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--code" in err
    assert "hint:" in err
    assert store.load(store.current_slug()).lapses == []


def test_lapse_unknown_code_rejected_by_parser(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    with pytest.raises(SystemExit):
        main(["lapse", "something went wrong", "--code", "not-a-real-code"])
    assert store.load(store.current_slug()).lapses == []


def test_lapse_all_documented_codes_are_accepted(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    for code in LAPSE_CODES:
        rc = main(["lapse", f"instance of {code}", "--code", code])
        assert rc == 0
    frame = store.load(store.current_slug())
    assert [r.code for r in frame.lapses] == list(LAPSE_CODES)


def test_lapse_frame_flag_targets_named_frame(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "First idea", "--title", "first-idea"])
    capsys.readouterr()
    main(["new", "Second idea", "--title", "second-idea"])
    capsys.readouterr()
    rc = main(
        [
            "lapse",
            "filed against the first frame",
            "--code",
            "grader-unverified",
            "--frame",
            "first-idea",
        ]
    )
    assert rc == 0
    assert len(store.load("first-idea").lapses) == 1
    assert store.load("second-idea").lapses == []


def test_lapse_no_frame_selected_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["lapse", "something", "--code", "grader-unverified"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no frame selected" in err
    assert "hint:" in err


# ── CLI: list (acceptance criterion 2) ───────────────────────────────────────


def test_lapse_list_text_output_empty(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["lapse", "--list"])
    assert rc == 0
    assert "no lapses filed yet" in capsys.readouterr().out


def test_lapse_bare_invocation_lists(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "grading was manual", "--code", "grader-unverified"])
    capsys.readouterr()
    rc = main(["lapse"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "l1" in out
    assert "grading was manual" in out
    assert "grader-unverified" in out
    assert "approved" in out


def test_lapse_list_json_shape(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "first", "--code", "grader-unverified"])
    main(["lapse", "second", "--code", "control-absent"])
    capsys.readouterr()
    rc = main(["lapse", "--list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frame"] == store.current_slug()
    assert [r["id"] for r in payload["lapses"]] == ["l1", "l2"]
    assert [r["code"] for r in payload["lapses"]] == [
        "grader-unverified",
        "control-absent",
    ]
    assert [r["status"] for r in payload["lapses"]] == ["approved", "approved"]


# ── CLI: confirm / reject (user-only) ────────────────────────────────────────


def test_lapse_confirm_marks_approved(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "swap", "--code", "grader-unverified", "--origin", "llm"])
    assert store.load(store.current_slug()).lapses[0].status == "proposed"
    rc = main(["lapse", "--confirm", "l1"])
    assert rc == 0
    assert store.load(store.current_slug()).lapses[0].status == "approved"


def test_lapse_reject_marks_rejected(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "swap", "--code", "grader-unverified", "--origin", "llm"])
    rc = main(["lapse", "--reject", "l1"])
    assert rc == 0
    assert store.load(store.current_slug()).lapses[0].status == "rejected"


def test_lapse_confirm_json_shape(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "swap", "--code", "grader-unverified", "--origin", "llm"])
    capsys.readouterr()
    rc = main(["lapse", "--confirm", "l1", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"id": "l1", "status": "approved"}


def test_lapse_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["lapse", "--confirm", "l99"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such lapse" in err
    assert "hint:" in err


def test_lapse_confirm_already_approved_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "swap", "--code", "grader-unverified"])  # user origin -> approved
    capsys.readouterr()
    rc = main(["lapse", "--confirm", "l1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already approved" in err
    assert "hint:" in err
    assert store.load(store.current_slug()).lapses[0].status == "approved"


def test_lapse_reject_already_rejected_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "swap", "--code", "grader-unverified", "--origin", "llm"])
    main(["lapse", "--reject", "l1"])
    capsys.readouterr()
    rc = main(["lapse", "--reject", "l1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already rejected" in err
    assert store.load(store.current_slug()).lapses[0].status == "rejected"


def test_lapse_reject_after_approve_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["lapse", "swap", "--code", "grader-unverified"])  # auto-approved
    capsys.readouterr()
    rc = main(["lapse", "--reject", "l1"])
    assert rc == 1
    assert "already approved" in capsys.readouterr().err


# ── CLI: conflicting flags refused, never silently resolved ─────────────────


def test_lapse_confirm_and_reject_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["lapse", "--confirm", "l1", "--reject", "l1"])
    assert exc.value.code == 1


def test_lapse_confirm_and_list_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["lapse", "--confirm", "l1", "--list"])
    assert exc.value.code == 1


def test_lapse_reject_and_list_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["lapse", "--reject", "l1", "--list"])
    assert exc.value.code == 1


def test_lapse_confirm_with_positional_what_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["lapse", "swap", "--confirm", "l1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --confirm/--reject" in err
    assert "hint:" in err


def test_lapse_reject_with_positional_what_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["lapse", "swap", "--reject", "l1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --confirm/--reject" in err


def test_lapse_list_with_positional_what_is_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["lapse", "swap", "--list"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --list" in err
    assert "hint:" in err


# ── acceptance criterion 3: no amend or delete flag on the parser ───────────


def _lapse_subparser() -> argparse.ArgumentParser:
    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices["lapse"]
    raise AssertionError("lapse subparser not registered")


def test_lapse_parser_has_no_amend_or_delete_flag() -> None:
    p = _lapse_subparser()
    flags = {opt for a in p._actions for opt in (a.option_strings or [])}
    assert "--amend" not in flags
    assert "--delete" not in flags


def test_lapse_parser_has_no_task_flag() -> None:
    # Cloned from deviate.py minus --task (no plan link) per the plan
    # instruction — pin that it never crept back in.
    p = _lapse_subparser()
    flags = {opt for a in p._actions for opt in (a.option_strings or [])}
    assert "--task" not in flags
    assert "--affects" not in flags


# ── acceptance criterion 4: explain + learn ──────────────────────────────────


def test_explain_lapse_succeeds(capsys) -> None:
    rc = main(["explain", "lapse"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("lapse:")


def test_moves_dict_has_lapse_entry() -> None:
    assert "lapse" in MOVES
    assert isinstance(MOVES["lapse"], str) and MOVES["lapse"]


def test_bare_learn_lists_lapse_move(capsys) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "lapse" in out


def test_bare_learn_json_lists_lapse_move(capsys) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "lapse" in payload["moves"]


# ── acceptance criterion 5: deterministic recording ──────────────────────────


def test_lapse_deterministic_no_subprocess_or_llm(tmp_path, monkeypatch) -> None:
    # Guard against scope creep: recording must never shell out (mirrors
    # test_deviate_deterministic_no_subprocess_or_llm).
    import subprocess

    _seed(monkeypatch, tmp_path)
    called = {"n": 0}
    real_run = subprocess.run

    def _guard(*args, **kwargs):
        called["n"] += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _guard)
    main(["lapse", "no subprocess used", "--code", "grader-unverified"])
    assert called["n"] == 0
