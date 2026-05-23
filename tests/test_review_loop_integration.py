"""Integration checks for the 0.6.0 Human Review Loop (#17), plan task t7.

- c1/h6, c2/h7, c4/h9 — the announcement is literally true of the shipped CLI:
  a proposal-heavy frame is reviewed then bulk-resolved in one pass, with no
  auto-confirm path.
- c7/h12 — boundary: 0.6.0 added only review/confirm UX; the proposed-vs-
  confirmed state vocabulary and claim kinds from #5/#16 are unchanged.
"""

from __future__ import annotations

import json

from devague import frame as frame_mod
from devague import store
from devague.cli import main

_KNOWN_STATUSES = {"proposed", "confirmed", "rejected"}
_CONTRACT_KINDS = {
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "why_it_matters",
    "boundary",
    "success_signal",
    "open_question",
    "non_goal",
    "requirement",
    "assumption",
    "decision",
}


def test_announcement_literally_true_at_scale(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship it"])
    for i in range(10):  # a frame "full of proposals"
        main(["capture", "--kind", "requirement", f"req {i}", "--origin", "llm"])
    capsys.readouterr()
    assert main(["review", "--json"]) == 0  # review exists + un-gated
    proposed = [c["id"] for c in json.loads(capsys.readouterr().out)["proposed_claims"]]
    assert len(proposed) == 10
    # One batched confirm + one batched reject resolve a chosen set; the rest stay proposed.
    assert main(["confirm", *proposed[:6]]) == 0
    assert main(["reject", *proposed[6:8]]) == 0
    statuses = [
        c.status for c in store.load(store.current_slug()).claims if c.kind == "requirement"
    ]
    assert statuses.count("confirmed") == 6
    assert statuses.count("rejected") == 2
    assert statuses.count("proposed") == 2  # untouched — never auto-confirmed


def test_no_new_claim_or_condition_states(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "X"])
    main(["capture", "--kind", "audience", "y", "--origin", "llm"])
    main(["interrogate", "c1", "--honesty", "z"])
    main(["confirm", "c2"])
    main(["reject", "h1"])
    f = store.load(store.current_slug())
    seen = {c.status for c in f.claims}
    seen |= {h.status for c in f.claims for h in c.honesty_conditions}
    assert seen <= _KNOWN_STATUSES  # no new states introduced
    assert set(frame_mod.CLAIM_KINDS) == _CONTRACT_KINDS  # no kinds added/removed
