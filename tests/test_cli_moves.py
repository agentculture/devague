from __future__ import annotations

import json

from devague import store
from devague.cli import main


def test_new_creates_frame_with_announcement(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["new", "Shipped instant specs", "--json"])
    assert rc == 0
    f = store.load(store.current_slug())
    assert f.claims[0].kind == "announcement"
    assert f.claims[0].status == "confirmed"


def test_new_same_title_does_not_overwrite(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()
    rc = main(["new", "Shipped instant specs", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["slug"] == "shipped-instant-specs-2"  # unique, first frame preserved
    assert sorted(store.list_slugs()) == ["shipped-instant-specs", "shipped-instant-specs-2"]


def test_frame_flag_rejects_path_traversal(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()
    rc = main(["show", "--frame", "../../etc/passwd"])
    assert rc == 1
    assert "slug" in capsys.readouterr().err.lower()


def test_frame_flag_unknown_slug_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()
    rc = main(["show", "--frame", "ghost"])
    assert rc == 1
    assert "no such frame" in capsys.readouterr().err.lower()


def test_load_malformed_frame_errors_cleanly(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()
    # Corrupt the persisted frame with an unknown claim kind.
    p = store.path_for("shipped-instant-specs")
    p.write_text(p.read_text().replace('"announcement"', '"bogus_kind"', 1), encoding="utf-8")
    rc = main(["show"])
    assert rc == 1
    err = capsys.readouterr().err.lower()
    assert "malformed" in err and "traceback" not in err


def test_load_newer_schema_errors_cleanly(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()
    p = store.path_for("shipped-instant-specs")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = 99  # newer than any real SCHEMA_VERSION
    p.write_text(json.dumps(raw), encoding="utf-8")
    rc = main(["show"])
    assert rc == 1
    err = capsys.readouterr().err.lower()
    assert "schema_version" in err and "upgrade" in err


def test_capture_adds_classified_claim(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()  # drain the "new" output before capture
    rc = main(["capture", "--kind", "audience", "developers", "--origin", "llm", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "audience"
    assert payload["status"] == "proposed"


def test_capture_without_frame_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["capture", "--kind", "audience", "devs"])
    assert rc == 1
    assert "no frame selected" in capsys.readouterr().err


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])  # announcement = c1


def test_interrogate_adds_proposed_honesty(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["interrogate", "c1", "--honesty", "must be measurable", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["added"][0]["kind"] == "honesty"
    assert payload["added"][0]["status"] == "proposed"


def test_confirm_and_reject_transition_status(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    assert main(["confirm", "c2"]) == 0
    assert store.load(store.current_slug()).find_claim("c2").status == "confirmed"
    assert main(["reject", "c2"]) == 0
    assert store.load(store.current_slug()).find_claim("c2").status == "rejected"


def test_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["confirm", "zzz"])
    assert rc == 1
    assert "no such" in capsys.readouterr().err


def test_confirm_multiple_ids_in_one_call(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    main(["capture", "--kind", "after_state", "fast", "--origin", "llm"])  # c3 proposed
    assert main(["confirm", "c2", "c3"]) == 0
    f = store.load(store.current_slug())
    assert f.find_claim("c2").status == "confirmed"
    assert f.find_claim("c3").status == "confirmed"


def test_reject_multiple_ids_in_one_call(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2
    main(["capture", "--kind", "after_state", "fast", "--origin", "llm"])  # c3
    assert main(["reject", "c2", "c3"]) == 0
    f = store.load(store.current_slug())
    assert f.find_claim("c2").status == "rejected"
    assert f.find_claim("c3").status == "rejected"


def test_batch_confirm_is_transactional(tmp_path, monkeypatch, capsys) -> None:
    # One unknown id in the batch => resolve NONE (no half-applied state).
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    rc = main(["confirm", "c2", "nope"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such" in err and "nope" in err
    # c2 must be untouched — the batch aborted before applying anything.
    assert store.load(store.current_slug()).find_claim("c2").status == "proposed"


def test_park_adds_vagueness(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park", "scale is unclear", "--kind", "unknown_blocking", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "unknown_blocking"
    assert payload["id"] == "v1"


# --- resolve-parked-vagueness t5: park --resolve VID --decision TEXT ----------


def test_park_create_path_unchanged_without_json(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "parked v1 (unknown_blocking)"


def test_park_bare_without_text_or_resolve_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no text to park" in err and "--resolve" in err


def test_park_create_without_kind_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park", "scale is unclear"])
    assert rc == 1
    assert "--kind" in capsys.readouterr().err


def test_park_resolve_marks_resolved_and_echoes_transition(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["park", "--resolve", "v1", "--decision", "cap at 10k"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "v1 -> resolved"
    f = store.load(store.current_slug())
    v = f.find_vagueness("v1")
    assert v.resolved is True
    assert v.resolution == "cap at 10k"


def test_park_resolve_json_parity(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["park", "--resolve", "v1", "--decision", "cap at 10k", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "v1"
    assert payload["resolved"] is True
    assert payload["resolution"] == "cap at 10k"


def test_park_resolve_without_decision_refused_and_persists_nothing(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed(monkeypatch, tmp_path)
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["park", "--resolve", "v1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--decision" in err and "hint" in err
    f = store.load(store.current_slug())
    assert f.find_vagueness("v1").resolved is False


def test_park_resolve_unknown_id_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park", "--resolve", "v9", "--decision", "x"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown vagueness" in err and "hint" in err


def test_park_resolve_already_resolved_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    main(["park", "--resolve", "v1", "--decision", "cap at 10k"])
    capsys.readouterr()
    rc = main(["park", "--resolve", "v1", "--decision", "cap at 20k"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already" in err and "hint" in err
    f = store.load(store.current_slug())
    assert f.find_vagueness("v1").resolution == "cap at 10k"  # untouched


def test_park_resolve_with_claim_links_deciding_claim(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)  # announcement = c1
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["park", "--resolve", "v1", "--decision", "cap at 10k", "--claim", "c1"])
    assert rc == 0
    f = store.load(store.current_slug())
    assert f.find_vagueness("v1").resolution_claim_id == "c1"


def test_park_resolve_unknown_claim_id_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["park", "--resolve", "v1", "--decision", "cap at 10k", "--claim", "c99"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown claim" in err and "hint" in err
    f = store.load(store.current_slug())
    assert f.find_vagueness("v1").resolved is False


def test_park_positional_text_with_resolve_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["park", "scale is unclear", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["park", "stray text", "--resolve", "v1", "--decision", "cap at 10k"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not both" in err
    f = store.load(store.current_slug())
    assert f.find_vagueness("v1").resolved is False


def test_show_renders_frame_markdown(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["show"])
    assert rc == 0
    assert "# Announcement Frame" in capsys.readouterr().out


def test_show_json_emits_frame_dict(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["show", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["claims"][0]["kind"] == "announcement"


def test_list_marks_current(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "shipped-instant-specs" in out
    assert "*" in out  # current marker


def test_interrogate_hard_question_adds_hard_question(tmp_path, monkeypatch, capsys) -> None:
    """Fix 5: --hard-question adds a hard question entry."""
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain setup output
    rc = main(["interrogate", "c1", "--hard-question", "what if empty?", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["added"][0]["kind"] == "hard_question"


def test_interrogate_risk_adds_non_blocking_hard_question(tmp_path, monkeypatch, capsys) -> None:
    """Fix 5: --risk records a non-blocking hard question."""
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain setup output
    rc = main(["interrogate", "c1", "--risk", "may not scale", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["added"][0]["kind"] == "hard_question"
    assert payload["added"][0]["status"] == "open"


def test_interrogate_contradicts_adds_blocking_hard_question(tmp_path, monkeypatch, capsys) -> None:
    """Fix 5: --contradicts records a blocking hard question."""
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain setup output
    rc = main(["interrogate", "c1", "--contradicts", "c1", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["added"][0]["kind"] == "hard_question"
    assert payload["added"][0]["status"] == "blocking"


def test_interrogate_no_flags_errors(tmp_path, monkeypatch, capsys) -> None:
    """Fix 5: interrogate with no flags returns rc 1 with 'nothing to interrogate' on stderr."""
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain setup output
    rc = main(["interrogate", "c1"])
    assert rc == 1
    assert "nothing to interrogate" in capsys.readouterr().err
