"""Tests for ``devague oblige`` — file/list/adjudicate a behavioral obligation
against a frame claim (bvts t4).

``devague oblige`` is the CLI twin of ``devague lapse``
(:mod:`devague.cli._commands.lapse`), with the record-mode arguments swapped:
a lapse's free-text ``code`` positional becomes a required claim id
positional (validated against the live frame) plus required ``--seam``/
``--behavior``. Acceptance criteria (verbatim from the confirmed plan):

1. ``devague oblige cN --seam --behavior`` files a frame-claim obligation and
   echoes the new obligation id
2. llm-origin obligations land proposed with confirm and reject adjudication;
   unknown claim ids are refused with an actionable hint
3. show and list render obligations with drift markers when the snapshot no
   longer matches live text
"""

from __future__ import annotations

import argparse
import json

import pytest

from devague import store
from devague.cli import _build_parser, main
from devague.cli._commands.learn import MOVES
from devague.render.frame_md import render_frame


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the obligation ledger", "--title", "oblige-plan"])


def _seed_with_claim(monkeypatch, tmp_path) -> str:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "boundary", "scope is X only", "--origin", "user"])
    frame = store.load(store.current_slug())
    return frame.claims[-1].id


# ── CLI: recording (acceptance criterion 1) ──────────────────────────────────


def test_oblige_records_entry_round_trip(tmp_path, monkeypatch) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    slug = store.current_slug()
    rc = main(["oblige", cid, "--seam", "cli", "--behavior", "rejects bad input"])
    assert rc == 0
    frame = store.load(slug)
    assert len(frame.obligations) == 1
    rec = frame.obligations[0]
    assert rec.id == "o1"
    assert rec.claim_id == cid
    assert rec.seam == "cli"
    assert rec.behavior == "rejects bad input"
    assert rec.source_text == "scope is X only"


def test_oblige_user_origin_auto_approves_end_to_end(tmp_path, monkeypatch) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    rc = main(["oblige", cid, "--seam", "cli", "--behavior", "rejects bad input"])
    assert rc == 0
    assert store.load(store.current_slug()).obligations[0].status == "approved"


def test_oblige_llm_origin_lands_proposed_end_to_end(tmp_path, monkeypatch) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    rc = main(
        [
            "oblige",
            cid,
            "--seam",
            "cli",
            "--behavior",
            "rejects bad input",
            "--origin",
            "llm",
        ]
    )
    assert rc == 0
    assert store.load(store.current_slug()).obligations[0].status == "proposed"


def test_oblige_json_shape_on_record(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["oblige", cid, "--seam", "store", "--behavior", "round-trips", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "id": "o1",
        "claim_id": cid,
        "seam": "store",
        "behavior": "round-trips",
        "source_text": "scope is X only",
        "origin": "user",
        "status": "approved",
    }


def test_oblige_missing_seam_and_behavior_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    rc = main(["oblige", cid])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--seam" in err
    assert "--behavior" in err
    assert "hint:" in err
    assert store.load(store.current_slug()).obligations == []


def test_oblige_missing_behavior_only_errors(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    rc = main(["oblige", cid, "--seam", "cli"])
    assert rc == 1
    err = capsys.readouterr().err
    message = err.split("hint:")[0]
    assert "--behavior" in message
    assert "--seam" not in message


def test_oblige_frame_flag_targets_named_frame(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "First idea", "--title", "first-idea"])
    main(["capture", "--kind", "boundary", "first boundary", "--origin", "user"])
    capsys.readouterr()
    main(["new", "Second idea", "--title", "second-idea"])
    capsys.readouterr()
    rc = main(
        [
            "oblige",
            "c1",
            "--seam",
            "cli",
            "--behavior",
            "x",
            "--frame",
            "first-idea",
        ]
    )
    assert rc == 0
    assert len(store.load("first-idea").obligations) == 1
    assert store.load("second-idea").obligations == []


def test_oblige_no_frame_selected_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["oblige", "c1", "--seam", "cli", "--behavior", "x"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no frame selected" in err
    assert "hint:" in err


# ── CLI: acceptance criterion 2 — unknown claim id / adjudication ───────────


def test_oblige_unknown_claim_id_refused_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["oblige", "c99", "--seam", "cli", "--behavior", "x"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown claim id" in err
    assert "hint:" in err
    assert store.load(store.current_slug()).obligations == []


def test_oblige_confirm_marks_approved(tmp_path, monkeypatch) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "x", "--origin", "llm"])
    assert store.load(store.current_slug()).obligations[0].status == "proposed"
    rc = main(["oblige", "--confirm", "o1"])
    assert rc == 0
    assert store.load(store.current_slug()).obligations[0].status == "approved"


def test_oblige_reject_marks_rejected(tmp_path, monkeypatch) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "x", "--origin", "llm"])
    rc = main(["oblige", "--reject", "o1"])
    assert rc == 0
    assert store.load(store.current_slug()).obligations[0].status == "rejected"


def test_oblige_confirm_json_shape(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "x", "--origin", "llm"])
    capsys.readouterr()
    rc = main(["oblige", "--confirm", "o1", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"id": "o1", "status": "approved"}


def test_oblige_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["oblige", "--confirm", "o99"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such obligation" in err
    assert "hint:" in err


def test_oblige_confirm_already_approved_is_refused(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "x"])  # user origin -> approved
    capsys.readouterr()
    rc = main(["oblige", "--confirm", "o1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already approved" in err
    assert "hint:" in err


def test_oblige_reject_already_rejected_is_refused(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "x", "--origin", "llm"])
    main(["oblige", "--reject", "o1"])
    capsys.readouterr()
    rc = main(["oblige", "--reject", "o1"])
    assert rc == 1
    assert "already rejected" in capsys.readouterr().err


# ── CLI: conflicting flags refused, never silently resolved ─────────────────


def test_oblige_confirm_and_reject_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["oblige", "--confirm", "o1", "--reject", "o1"])
    assert exc.value.code == 1


def test_oblige_confirm_and_list_are_mutually_exclusive(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["oblige", "--confirm", "o1", "--list"])
    assert exc.value.code == 1


def test_oblige_confirm_with_positional_claim_id_is_refused(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    rc = main(["oblige", cid, "--confirm", "o1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --confirm/--reject" in err
    assert "hint:" in err


def test_oblige_list_with_positional_claim_id_is_refused(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    rc = main(["oblige", cid, "--list"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot combine --list" in err
    assert "hint:" in err


def test_oblige_record_flags_without_claim_id_are_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["oblige", "--seam", "cli", "--behavior", "x"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "without a positional" in err
    assert "hint:" in err
    assert store.load(store.current_slug()).obligations == []


# ── CLI: list (acceptance criterion 3) ───────────────────────────────────────


def test_oblige_list_text_output_empty(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["oblige", "--list"])
    assert rc == 0
    assert "no obligations filed yet" in capsys.readouterr().out


def test_oblige_bare_invocation_lists(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "rejects bad input"])
    capsys.readouterr()
    rc = main(["oblige"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "o1" in out
    assert "cli" in out
    assert "rejects bad input" in out
    assert "approved" in out


def test_oblige_list_json_shape(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "x"])
    capsys.readouterr()
    rc = main(["oblige", "--list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frame"] == store.current_slug()
    assert len(payload["obligations"]) == 1
    rec = payload["obligations"][0]
    assert rec["id"] == "o1"
    assert rec["claim_id"] == cid
    assert rec["drift"] is None


def test_oblige_list_and_show_render_drift_marker_when_claim_text_changes(
    tmp_path, monkeypatch, capsys
) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["oblige", cid, "--seam", "cli", "--behavior", "rejects bad input"])
    capsys.readouterr()

    # Drift the claim's text out from under the obligation via amend.
    main(["amend", cid, "--text", "scope now covers X and Y"])
    capsys.readouterr()

    rc = main(["oblige", "--list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["obligations"][0]["drift"] is not None

    rc = main(["oblige", "--list"])
    assert rc == 0
    assert "drifted" in capsys.readouterr().out

    frame = store.load(slug)
    out = render_frame(frame)
    assert "⚠ drifted" in out


# ── acceptance criterion 3: show renders obligations under their claim ──────


def test_frame_show_renders_obligation_under_its_claim(tmp_path, monkeypatch, capsys) -> None:
    cid = _seed_with_claim(monkeypatch, tmp_path)
    main(["oblige", cid, "--seam", "cli", "--behavior", "rejects bad input"])
    capsys.readouterr()
    rc = main(["show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "obligation:" in out
    assert "o1" in out
    assert "cli" in out
    assert "rejects bad input" in out
    assert "⚠ drifted" not in out


def test_export_spec_md_never_gains_obligations_section(tmp_path, monkeypatch, capsys) -> None:
    """The exported spec-md overwrites the same dated file on every re-export;
    obligations rendering there would rewrite the what-to-build artifact,
    mirroring the lapse ledger's exact restriction."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the widget", "--title", "oblige-export"])
    main(["capture", "--kind", "audience", "developers", "--origin", "user"])
    main(["capture", "--kind", "after_state", "ships cleanly", "--origin", "user"])
    main(["capture", "--kind", "before_state", "was messy", "--origin", "user"])
    main(["capture", "--kind", "boundary", "scope is X only", "--origin", "user"])
    main(["capture", "--kind", "success_signal", "tests pass", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    cid = frame.claims[-1].id
    main(["oblige", cid, "--seam", "cli", "--behavior", "rejects bad input"])
    capsys.readouterr()
    rc = main(["converge"])
    capsys.readouterr()
    if rc == 0:
        main(["export"])
        out_dir = tmp_path / "docs" / "specs"
        assert out_dir.exists()
        for f in out_dir.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            assert "obligation" not in text.lower()
            assert "o1" not in text


# ── acceptance criterion: no amend or delete flag on the parser ─────────────


def _oblige_subparser() -> argparse.ArgumentParser:
    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices["oblige"]
    raise AssertionError("oblige subparser not registered")


def test_oblige_parser_has_no_amend_or_delete_flag() -> None:
    p = _oblige_subparser()
    flags = {opt for a in p._actions for opt in (a.option_strings or [])}
    assert "--amend" not in flags
    assert "--delete" not in flags


# ── explain + learn ───────────────────────────────────────────────────────────


def test_explain_oblige_succeeds(capsys) -> None:
    rc = main(["explain", "oblige"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("oblige:")


def test_moves_dict_has_oblige_entry() -> None:
    assert "oblige" in MOVES
    assert isinstance(MOVES["oblige"], str) and MOVES["oblige"]


def test_bare_learn_lists_oblige_move(capsys) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "oblige" in out


# ── deterministic recording ───────────────────────────────────────────────────


def test_oblige_deterministic_no_subprocess_or_llm(tmp_path, monkeypatch) -> None:
    import subprocess

    cid = _seed_with_claim(monkeypatch, tmp_path)
    called = {"n": 0}
    real_run = subprocess.run

    def _guard(*args, **kwargs):
        called["n"] += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _guard)
    main(["oblige", cid, "--seam", "cli", "--behavior", "no subprocess used"])
    assert called["n"] == 0
