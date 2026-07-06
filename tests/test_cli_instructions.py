"""``--instruction`` on ``capture``/``interrogate``, and ``review`` listing it.

Task t4 (#53): capture/interrogate store a verbatim, optional per-item
instruction; changing the instruction on a CONFIRMED claim or honesty
condition flips it back to `proposed` for re-confirmation (never silently
kept confirmed); `devague review` lists each proposed item's instruction
alongside it.
"""

from __future__ import annotations

import json

from devague import store
from devague.cli import main


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship sharper method"])  # c1 announcement, origin=user -> confirmed


# ---------------------------------------------------------------------------
# capture --instruction
# ---------------------------------------------------------------------------


def test_capture_instruction_stored_verbatim(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(
        [
            "capture",
            "--kind",
            "requirement",
            "must support `<id>` lookups",
            "--instruction",
            "verify via `devague show --json`",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["instruction"] == "verify via `devague show --json`"
    f = store.load(store.current_slug())
    claim = f.find_claim(payload["id"])
    assert claim.instruction == "verify via `devague show --json`"


def test_capture_without_instruction_defaults_empty(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["capture", "--kind", "audience", "devs", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["instruction"] == ""
    f = store.load(store.current_slug())
    assert f.find_claim(payload["id"]).instruction == ""


# ---------------------------------------------------------------------------
# interrogate --instruction — standalone, on a claim
# ---------------------------------------------------------------------------


def test_interrogate_instruction_standalone_on_claim(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    # c1 was auto-confirmed (origin=user) by `new` — changing its instruction
    # must flip it back to proposed (re-confirm rule).
    rc = main(["interrogate", "c1", "--instruction", "verify against the exported spec"])
    assert rc == 0
    f = store.load(store.current_slug())
    claim = f.find_claim("c1")
    assert claim.instruction == "verify against the exported spec"
    assert claim.status == "proposed"


def test_interrogate_instruction_alone_does_not_error_as_nothing_to_interrogate(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["interrogate", "c1", "--instruction", "x"])
    assert rc == 0
    assert "nothing to interrogate" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# interrogate --instruction — on an honesty condition id (h*)
# ---------------------------------------------------------------------------


def test_interrogate_instruction_on_honesty_condition_id(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    main(
        ["interrogate", "c1", "--honesty", "must be measurable", "--origin", "user"]
    )  # h1 confirmed
    capsys.readouterr()
    rc = main(["interrogate", "h1", "--instruction", "check the release notes"])
    assert rc == 0
    f = store.load(store.current_slug())
    h = f.find_honesty("h1")
    assert h.instruction == "check the release notes"
    assert h.status == "proposed"  # was confirmed (origin=user) -> flips back
    # The claim itself is untouched.
    assert f.find_claim("c1").instruction == ""


def test_interrogate_instruction_combined_with_honesty_sets_claim_not_new_honesty(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(
        [
            "interrogate",
            "c1",
            "--honesty",
            "must be true",
            "--instruction",
            "verify via test",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    kinds = {a["kind"]: a for a in payload["added"]}
    assert "honesty" in kinds and "instruction" in kinds
    f = store.load(store.current_slug())
    claim = f.find_claim("c1")
    new_honesty = f.find_honesty(kinds["honesty"]["id"])
    assert claim.instruction == "verify via test"  # set on the claim
    assert new_honesty.instruction == ""  # NOT on the freshly-added honesty condition


# ---------------------------------------------------------------------------
# Re-confirm rule: confirmed -> proposed on instruction change; proposed stays
# ---------------------------------------------------------------------------


def test_interrogate_instruction_flip_emits_stderr_note(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["interrogate", "c1", "--instruction", "verify manually"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "c1" in err
    assert "confirmed" in err.lower()
    assert "proposed" in err.lower()


def test_interrogate_instruction_on_proposed_claim_leaves_status_as_is(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    capsys.readouterr()
    rc = main(["interrogate", "c2", "--instruction", "verify with a survey"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "confirmed" not in err.lower()  # no flip note — it was already proposed
    f = store.load(store.current_slug())
    claim = f.find_claim("c2")
    assert claim.status == "proposed"
    assert claim.instruction == "verify with a survey"


def test_interrogate_instruction_changing_twice_keeps_flipping_rule_honest(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    main(["interrogate", "c1", "--instruction", "first draft"])  # confirmed -> proposed
    main(["confirm", "c1"])  # user re-confirms
    capsys.readouterr()
    rc = main(["interrogate", "c1", "--instruction", "revised draft"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "proposed" in err.lower()  # flips again
    f = store.load(store.current_slug())
    claim = f.find_claim("c1")
    assert claim.instruction == "revised draft"
    assert claim.status == "proposed"


# ---------------------------------------------------------------------------
# Validation: --honesty/--hard-question/--risk/--contradicts require a claim id
# ---------------------------------------------------------------------------


def test_interrogate_claim_only_flags_reject_honesty_id(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["interrogate", "c1", "--honesty", "must be measurable"])  # h1 proposed
    capsys.readouterr()
    rc = main(["interrogate", "h1", "--hard-question", "what if it's false?"])
    assert rc == 1
    err = capsys.readouterr().err.lower()
    assert "honesty condition" in err


def test_interrogate_unknown_id_with_instruction_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["interrogate", "zzz", "--instruction", "x"])
    assert rc == 1
    assert "no such" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------------------
# devague review lists instructions alongside their items
# ---------------------------------------------------------------------------


def test_review_lists_claim_instruction(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(
        [
            "capture",
            "--kind",
            "audience",
            "devs",
            "--origin",
            "llm",
            "--instruction",
            "confirm with the PM",
        ]
    )  # c2 proposed, with instruction
    capsys.readouterr()
    assert main(["review"]) == 0
    out = capsys.readouterr().out
    assert "c2" in out
    assert "confirm with the PM" in out


def test_review_lists_honesty_instruction(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    main(["interrogate", "c2", "--honesty", "must be true"])  # h1 proposed
    main(["interrogate", "h1", "--instruction", "check with support logs"])
    capsys.readouterr()
    assert main(["review"]) == 0
    out = capsys.readouterr().out
    assert "h1" in out
    assert "check with support logs" in out


def test_review_item_without_instruction_renders_nothing_extra(
    tmp_path, monkeypatch, capsys
) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2, no instruction
    capsys.readouterr()
    assert main(["review"]) == 0
    out = capsys.readouterr().out
    assert "instruction" not in out.lower()


def test_review_json_includes_instruction_fields(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(
        [
            "capture",
            "--kind",
            "audience",
            "devs",
            "--origin",
            "llm",
            "--instruction",
            "confirm with the PM",
        ]
    )  # c2
    main(["interrogate", "c2", "--honesty", "must be true"])  # h1
    main(["interrogate", "h1", "--instruction", "check with support logs"])
    capsys.readouterr()
    assert main(["review", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    claim_entry = next(c for c in payload["proposed_claims"] if c["id"] == "c2")
    assert claim_entry["instruction"] == "confirm with the PM"
    honesty_entry = next(h for h in payload["proposed_honesty"] if h["id"] == "h1")
    assert honesty_entry["instruction"] == "check with support logs"


def test_review_json_instruction_empty_when_absent(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2, no instruction
    capsys.readouterr()
    assert main(["review", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    claim_entry = next(c for c in payload["proposed_claims"] if c["id"] == "c2")
    assert claim_entry["instruction"] == ""
