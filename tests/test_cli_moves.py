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
    p.write_text(p.read_text().replace('"schema_version": 1', '"schema_version": 99'), encoding="utf-8")
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


def test_park_adds_vagueness(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park", "scale is unclear", "--kind", "unknown_blocking", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "unknown_blocking"
    assert payload["id"] == "v1"


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
