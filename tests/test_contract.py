"""Cross-cutting contract tests for the documented devague spec contract (#5).

Pins the guarantees that span the whole surface: every move speaks JSON (t7),
LLM proposals never auto-confirm (t9), and the four acceptance areas — claim
provenance, honesty-condition confirmation, parking vagueness, and convergence
failure (t11) — each have an explicit test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from devague import store
from devague.cli import _build_parser, main
from devague.convergence import evaluate
from devague.frame import Frame, from_dict, to_dict

CONTRACT_EXAMPLE = (
    Path(__file__).resolve().parent.parent / "docs" / "examples" / "contract-example.json"
)


def _leaf_parsers(parser: argparse.ArgumentParser, prefix: str = "") -> dict:
    out: dict = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                nested = _leaf_parsers(sub, f"{prefix}{name} ")
                out.update(nested or {f"{prefix}{name}".strip(): sub})
    return out


def _has_json(parser: argparse.ArgumentParser) -> bool:
    return any("--json" in (a.option_strings or []) for a in parser._actions)


# --- t7: every move speaks JSON (c2, h2) -------------------------------------


def test_every_move_supports_json() -> None:
    leaves = _leaf_parsers(_build_parser())
    missing = sorted(name for name, p in leaves.items() if not _has_json(p))
    assert missing == [], f"moves missing --json: {missing}"
    assert len(leaves) >= 24  # the full frame + plan surface is present


# --- t9: anti-fabrication — LLM proposals stay proposed (c8, h8) --------------


def test_llm_claim_and_honesty_stay_proposed() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("requirement", "must round-trip", origin="llm")
    h = f.add_honesty(c, "is testable", origin="llm")
    assert c.status == "proposed" and h.status == "proposed"


def test_evaluating_never_confirms_a_proposal(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped X"])
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    capsys.readouterr()
    evaluate(store.load(store.current_slug()))  # evaluating must not mutate
    assert store.load(store.current_slug()).find_claim("c2").status == "proposed"
    main(["confirm", "c2"])  # only an explicit user confirm flips it
    assert store.load(store.current_slug()).find_claim("c2").status == "confirmed"


# --- t11: the four named acceptance areas (c12, h12) -------------------------


def _seed(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped X"])  # c1 announcement (confirmed, user origin)


def test_area_claim_provenance(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    main(["capture", "--kind", "audience", "devs", "--origin", "llm", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["origin"] == "llm" and payload["status"] == "proposed"


def test_area_honesty_confirmation(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["interrogate", "c1", "--honesty", "announcement is true", "--origin", "llm"])
    capsys.readouterr()
    f = store.load(store.current_slug())
    hid = f.claims[0].honesty_conditions[0].id
    assert f.claims[0].honesty_conditions[0].status == "proposed"
    main(["confirm", hid])
    f2 = store.load(store.current_slug())
    assert f2.claims[0].honesty_conditions[0].status == "confirmed"


def test_area_parking_vagueness(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    main(["park", "scale?", "--kind", "unknown_blocking", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "unknown_blocking"
    res = evaluate(store.load(store.current_slug()))
    assert res.ready is False and any("blocking vagueness" in b for b in res.blockers)


def test_area_convergence_failure_is_structured(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    res = evaluate(store.load(store.current_slug()))
    assert res.ready is False
    assert res.blockers  # structured blockers, not prose-only advice
    assert res.required_next_moves  # with a derived next move per blocker


# --- t10: the documented contract's worked example round-trips + converges ---


def test_contract_example_round_trips_and_converges() -> None:
    raw = json.loads(CONTRACT_EXAMPLE.read_text(encoding="utf-8"))
    frame = from_dict(raw)
    # Lossless round-trip through the dataclasses.
    assert to_dict(from_dict(to_dict(frame))) == to_dict(frame)
    # The worked example is a *converged* frame (an unconfirmed assumption is
    # only a warning, so it does not block).
    result = evaluate(frame)
    assert result.ready is True
    assert any(c.kind == "requirement" for c in frame.claims)  # exercises a new kind
    assert result.warnings  # the stated-assumption warning is surfaced
