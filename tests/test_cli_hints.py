"""Tests for the next-move stderr hint (issue next-leg-hints, task t1).

Covers plan targets: c1 c2 h4 c3 c7 h6 c10 h8 c11 h9 c12 c17 h12 c20 h14.

Two layers:

- A pure, exhaustive parametrized test over :func:`devague.cli._hints.hint_for`
  using constructed ``argparse.Namespace`` stand-ins for every leaf verb the
  real parser registers (introspected via ``_build_parser`` — no hardcoded
  verb list to drift out of sync). This pins the leg-ending vs within-leg
  classification and the exemptions (AC3).
- A real, sequential end-to-end walk that drives every registered verb
  through ``devague.cli.main`` against genuine on-disk state, asserting the
  wired-in dispatch behavior for real: exactly one ``next: ...`` stderr line
  per successful, non-exempt call; zero for ``status`` / ``plan status``
  (AC1), and stdout left untouched (AC4).
- A static check that no command module emits a hint itself (AC2).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest

from devague.cli import _build_parser, main
from devague.cli._hints import hint_for

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / "devague" / "cli" / "_commands"


# ── helpers: introspect the real parser for the full verb table ─────────────


def _leaf_keys() -> list[str]:
    """Every leaf verb key as the hint table addresses it: a flat command
    name as-is, or ``plan:<subverb>`` for the nested plan group — mirrors
    :func:`devague.cli._hints.hint_for`'s own key shape."""
    parser = _build_parser()
    keys: list[str] = []
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, sub in action.choices.items():
            if name != "plan":
                keys.append(name)
                continue
            for sub_action in sub._actions:
                if isinstance(sub_action, argparse._SubParsersAction):
                    keys.extend(f"plan:{pname}" for pname in sub_action.choices)
    return keys


def _ns(command: str, plan_command: str | None = None, **extra) -> argparse.Namespace:
    return argparse.Namespace(command=command, plan_command=plan_command, **extra)


# ── AC3 (+ exemptions): exhaustive, pure parametrized test over the table ───

_ALL_KEYS = _leaf_keys()

# Every filing-mode attribute the multi-mode verbs need set truthy so
# `hint_for` sees a "just filed" call; irrelevant for every other key.
_FILING_ATTRS = {
    "deviate": {"what": "x"},
    "evidence": {"obligation": "o1"},
    "delta": {"kind": "added"},
}

_EXPECTED_LEG_END = {
    "export": "run /challenge or /spec-to-plan",
    "summary": "run /summarize-delivery",
    "today": "commit docs/current-spec.md",
    "deviate": "resume the fan-out",
    "evidence": "run devague summary and /summarize-delivery",
    "delta": "run devague summary and /summarize-delivery",
    "plan:export": "run /assign-to-workforce",
    "plan:waves": "run /assign-to-workforce",
}
_EXEMPT_KEYS = {"status", "plan:status"}


def test_leaf_keys_are_nonempty_and_include_known_verbs() -> None:
    # A basic sanity floor so a parser refactor that silently empties
    # `_leaf_keys()` doesn't make every downstream parametrized test vacuous.
    assert "capture" in _ALL_KEYS
    assert "plan:task" in _ALL_KEYS
    assert "status" in _ALL_KEYS
    assert "plan:status" in _ALL_KEYS


@pytest.mark.parametrize("key", _ALL_KEYS)
def test_hint_for_every_registered_verb(key: str) -> None:
    if key.startswith("plan:"):
        subverb = key.split(":", 1)[1]
        args = _ns("plan", plan_command=subverb)
    else:
        args = _ns(key, **_FILING_ATTRS.get(key, {}))

    text = hint_for(args)

    if key in _EXEMPT_KEYS:
        assert text is None, f"{key} should be exempt from hinting"
        return

    assert text is not None, f"{key} should get a hint"
    if key in _EXPECTED_LEG_END:
        assert text == _EXPECTED_LEG_END[key]
    elif key.startswith("plan:"):
        assert text == "run devague plan status"
    else:
        assert text == "run devague status"


def test_bare_plan_group_is_exempt_like_help() -> None:
    # `devague plan` with no subverb only prints help; nothing to hint about.
    assert hint_for(_ns("plan", plan_command=None)) is None


def test_command_none_is_exempt() -> None:
    # Defensive: main() never reaches _dispatch when args.command is None
    # (it prints help and returns), but hint_for should still be inert here.
    assert hint_for(_ns(None)) is None  # type: ignore[arg-type]


# ── r1: multi-mode verbs only leg-end on their *filing* path ────────────────


@pytest.mark.parametrize(
    ("command", "filing_kwargs", "listing_kwargs"),
    [
        ("deviate", {"what": "it changed"}, {"what": None, "list": True}),
        ("evidence", {"obligation": "o1"}, {"obligation": None, "list": True}),
        ("delta", {"kind": "added"}, {"kind": None, "list": True}),
    ],
)
def test_multi_mode_verbs_leg_end_only_on_filing(command, filing_kwargs, listing_kwargs) -> None:
    filed = hint_for(_ns(command, **filing_kwargs))
    assert filed == _EXPECTED_LEG_END[command]

    listed = hint_for(_ns(command, **listing_kwargs))
    assert listed == "run devague status"

    confirmed = hint_for(_ns(command, **{**listing_kwargs, "confirm": "d1", "list": False}))
    assert confirmed == "run devague status"


# ── AC2: no command module emits a hint itself ───────────────────────────────


def test_no_hint_call_sites_in_commands_package() -> None:
    offenders = []
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "_hints" in text or "emit_next_hint" in text or re.search(r'"next: ', text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"hint call sites found outside cli/__init__.py: {offenders}"


def test_dispatch_is_the_only_import_site_of_emit_next_hint() -> None:
    init_text = (REPO_ROOT / "devague" / "cli" / "__init__.py").read_text(encoding="utf-8")
    assert "emit_next_hint" in init_text
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        assert "emit_next_hint" not in path.read_text(encoding="utf-8")


# ── real end-to-end walk: every registered verb, driven through main() ──────


def _call(argv: list[str], capsys) -> tuple[int, str, str]:
    rc = main(argv)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _assert_hinted(err: str, *, exempt: bool) -> None:
    lines = [ln for ln in err.splitlines() if ln]
    next_lines = [ln for ln in lines if ln.startswith("next:")]
    if exempt:
        assert next_lines == [], f"expected no hint, got: {next_lines!r}\nfull stderr: {err!r}"
    else:
        assert len(next_lines) == 1, f"expected exactly one hint line, got: {err!r}"


@pytest.mark.parametrize("exempt_key", sorted(_EXEMPT_KEYS))
def test_exempt_keys_are_recognized_as_exempt(exempt_key: str) -> None:
    # Cheap belt-and-suspenders check that the exempt set used by the real
    # walk below matches what hint_for itself considers exempt.
    if exempt_key.startswith("plan:"):
        args = _ns("plan", plan_command=exempt_key.split(":", 1)[1])
    else:
        args = _ns(exempt_key)
    assert hint_for(args) is None


def test_end_to_end_every_verb_hints_exactly_once_on_success(tmp_path, monkeypatch, capsys) -> None:
    """AC1: drive every registered verb through a real, successful call and
    assert the stderr hint contract holds. AC4: stdout stays clean of hint
    text and every ``--json`` payload still parses.

    This is a single long sequential walk (not independent
    ``pytest.mark.parametrize`` cases) because most verbs are stateful —
    ``plan task`` needs a plan, ``plan confirm`` needs a task, etc. Every
    step below is still keyed to a verb table entry and asserted the same
    way, so it exercises the full table exhaustively even though it isn't a
    literal ``@pytest.mark.parametrize``.
    """
    monkeypatch.chdir(tmp_path)
    seen: set[str] = set()

    def step(key: str, argv: list[str], *, json_mode: bool = False) -> dict | str:
        rc, out, err = _call(argv, capsys)
        assert rc == 0, f"{argv!r} failed: {err!r}"
        exempt = key in _EXEMPT_KEYS
        _assert_hinted(err, exempt=exempt)
        assert "next:" not in out  # AC4: stdout never carries the hint
        seen.add(key)
        if json_mode:
            payload = json.loads(out)  # AC4: JSON stdout still parses cleanly
            return payload
        return out

    # ── frame side ───────────────────────────────────────────────────────
    created = step(
        "new", ["new", "Ship next-leg hints", "--title", "nlh-t1", "--json"], json_mode=True
    )
    slug = created["slug"]

    required = ("audience", "after_state", "before_state", "boundary", "success_signal")
    for kind in required:
        step("capture", ["capture", "--kind", kind, f"{kind} text", "--origin", "user"])

    llm_claim = step(
        "capture",
        [
            "capture",
            "--kind",
            "assumption",
            "an llm-proposed assumption",
            "--origin",
            "llm",
            "--json",
        ],
        json_mode=True,
    )
    step("confirm", ["confirm", llm_claim["id"]])

    reject_claim = step(
        "capture",
        ["capture", "--kind", "non_goal", "throwaway non-goal", "--origin", "llm", "--json"],
        json_mode=True,
    )
    step("reject", ["reject", reject_claim["id"]])

    shown = step("show", ["show", "--json"], json_mode=True)
    claim_ids = [c["id"] for c in shown["claims"]]
    first_claim = claim_ids[0]
    step("amend", ["amend", first_claim, "--text", "corrected text", "--reason", "typo"])
    step("confirm", ["confirm", first_claim])  # amend flips confirmed -> proposed; re-confirm

    for cid in claim_ids:
        step("interrogate", ["interrogate", cid, "--honesty", "must hold", "--origin", "user"])

    interrogated = step(
        "interrogate",
        ["interrogate", first_claim, "--hard-question", "is this really true?", "--json"],
        json_mode=True,
    )
    qid = interrogated["added"][0]["id"]
    step(
        "interrogate",
        ["interrogate", first_claim, "--resolve", qid, "--decision", "yes, confirmed", "--json"],
        json_mode=True,
    )

    step("review", ["review", "--no-write"])

    questioned = step("question", ["question", "a pending decision", "--json"], json_mode=True)
    qid2 = questioned["id"] if "id" in questioned else questioned.get("recorded")
    if qid2 is None:
        # question's json payload shape isn't asserted elsewhere in this
        # walk beyond parsing; fall back to a plain-text parse if needed.
        out = step("question", ["question", "another pending decision"])
        match = re.search(r"recorded (\S+)", out)
        assert match
        qid2 = match.group(1)
    step("question", ["question", "--resolve", qid2, "--decision", "decided"])

    parked = step(
        "park",
        ["park", "some open vagueness", "--kind", "unknown_nonblocking", "--json"],
        json_mode=True,
    )
    step(
        "park",
        ["park", "--resolve", parked["id"], "--decision", "resolved", "--json"],
        json_mode=True,
    )

    step(
        "scope",
        ["scope", "the cli chassis", "--finding", "found something", "--json"],
        json_mode=True,
    )

    step("converge", ["converge"])
    step("export", ["export"])

    # ── plan side ────────────────────────────────────────────────────────
    step("plan:new", ["plan", "new", "--frame", slug])

    plan_shown = step("plan:show", ["plan", "show", "--json"], json_mode=True)
    target_ids = [t["id"] for t in plan_shown["targets"]]
    assert target_ids, "expected at least one coverage target"

    task1 = step(
        "plan:task",
        ["plan", "task", "cover everything", "--accept", "every target covered", "--json"],
        json_mode=True,
    )
    t1 = task1["id"]
    for tid in target_ids:
        step("plan:cover", ["plan", "cover", t1, "--target", tid])

    step("plan:instruct", ["plan", "instruct", t1, "run the tests"])
    step("plan:accept", ["plan", "accept", t1, "a second acceptance criterion"])
    step("plan:amend", ["plan", "amend", t1, "--summary", "cover everything (amended)"])

    task2 = step("plan:task", ["plan", "task", "a dependent task", "--json"], json_mode=True)
    t2 = task2["id"]
    step("plan:depend", ["plan", "depend", t2, "--on", t1])
    step("plan:depend", ["plan", "depend", t2, "--on", t1, "--remove"])
    step("plan:accept", ["plan", "accept", t2, "an acceptance criterion"])

    step("plan:defer", ["plan", "defer", target_ids[0], "--reason", "belongs to a later plan"])
    step("plan:defer", ["plan", "defer", target_ids[0], "--undo"])
    step("plan:cover", ["plan", "cover", t2, "--target", target_ids[0]])

    task3 = step("plan:task", ["plan", "task", "a throwaway task", "--json"], json_mode=True)
    t3 = task3["id"]
    step("plan:reject", ["plan", "reject", t3])

    step("plan:confirm", ["plan", "confirm", t1])
    step("plan:confirm", ["plan", "confirm", t2])

    risk1 = step(
        "plan:risk",
        ["plan", "risk", "a real unknown", "--kind", "unknown_nonblocking", "--json"],
        json_mode=True,
    )
    step(
        "plan:risk",
        ["plan", "risk", "--resolve", risk1["id"], "--decision", "resolved it", "--json"],
        json_mode=True,
    )
    risk2 = step(
        "plan:risk",
        ["plan", "risk", "another unknown", "--kind", "unknown_nonblocking", "--json"],
        json_mode=True,
    )
    step(
        "plan:risk",
        ["plan", "risk", "--amend", risk2["id"], "--text", "corrected risk text", "--json"],
        json_mode=True,
    )

    step(
        "plan:oblige",
        [
            "plan",
            "oblige",
            t1,
            "--criterion",
            "1",
            "--seam",
            "cli",
            "--behavior",
            "the task actually covers the target",
            "--json",
        ],
        json_mode=True,
    )
    step("plan:oblige", ["plan", "oblige", "--list"])

    step("plan:converge", ["plan", "converge"])
    step("plan:export", ["plan", "export"])
    step("plan:waves", ["plan", "waves"])
    step("plan:deliverables", ["plan", "deliverables"])
    step("plan:list", ["plan", "list"])
    step("plan:learn", ["plan", "learn"])
    step("plan:explain", ["plan", "explain", "task"])

    # ── delivery ledger (frame-side oblige/lapse + plan-scoped deviate/evidence/delta) ──
    frame_oblige = step(
        "oblige",
        [
            "oblige",
            first_claim,
            "--seam",
            "cli",
            "--behavior",
            "the claim actually holds",
            "--json",
        ],
        json_mode=True,
    )
    step("oblige", ["oblige", "--list"])

    step(
        "evidence",
        [
            "evidence",
            "--obligation",
            frame_oblige["id"],
            "--test",
            "tests/test_cli_hints.py::test_end_to_end_every_verb_hints_exactly_once_on_success",
            "--behavior",
            "the claim actually holds",
            "--contract",
            "the claim actually holds",
            "--type",
            "automated",
            "--strength",
            "coverage",
            "--basis",
            "this very test exercises it",
            "--outcome",
            "pass",
        ],
    )
    step("evidence", ["evidence", "--list"])

    step(
        "deviate",
        [
            "deviate",
            "swapped task order",
            "--task",
            t1,
            "--reason",
            "dependency turned out reversed",
        ],
    )
    step("deviate", ["deviate", "--list"])

    step(
        "delta",
        [
            "delta",
            "--kind",
            "added",
            "--behavior",
            "next-move hints appear on stderr",
            "--caused-by",
            first_claim,
        ],
    )
    step("delta", ["delta", "--list"])

    step("lapse", ["lapse", "skipped a real check", "--code", "assumption-for-measurement"])
    step("lapse", ["lapse", "--list"])

    step("summary", ["summary"])
    step("today", ["today"])

    step("list", ["list"])
    step("learn", ["learn"])
    step("explain", ["explain", "capture"])

    # ── exempt verbs: no hint, but still a successful, real call ─────────
    step("status", ["status"])
    step("plan:status", ["plan", "status"])

    # Every leaf key this task's table covers was actually exercised above
    # (belt-and-suspenders on the hand-written walk).
    missing = set(_ALL_KEYS) - seen
    assert not missing, f"verb table keys never exercised by the walk: {sorted(missing)}"
