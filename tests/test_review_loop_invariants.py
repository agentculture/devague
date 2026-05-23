"""Cross-cutting invariants for the Human Review Loop (#17), plan task t6.

These map directly onto the spec's honesty conditions:
- c16/h5  — no review-flow command auto-confirms a proposed item.
- c3/h8   — one `review` shows every proposed item; one batched confirm/reject
            resolves a chosen set, on a NON-converged frame.
- c5/h10  — anti-fabrication preserved: an llm proposal stays proposed until an
            explicit user confirm naming that id.
"""

from __future__ import annotations

import json

from devague import store
from devague.cli import main


def _frame_with_proposals(monkeypatch, tmp_path) -> str:
    monkeypatch.chdir(tmp_path)
    main(["new", "Human review loop"])  # c1 confirmed announcement
    main(["capture", "--kind", "audience", "ops + llm", "--origin", "llm"])  # c2 proposed
    main(["capture", "--kind", "after_state", "one-pass review", "--origin", "llm"])  # c3 proposed
    main(["interrogate", "c1", "--honesty", "announcement true at release"])  # h1 proposed
    main(["interrogate", "c1", "--honesty", "no auto-confirm path"])  # h2 proposed
    return store.current_slug()


def _statuses(slug: str) -> tuple[dict, dict]:
    f = store.load(slug)
    claims = {c.id: c.status for c in f.claims}
    honesty = {h.id: h.status for c in f.claims for h in c.honesty_conditions}
    return claims, honesty


def test_review_flow_never_auto_confirms(tmp_path, monkeypatch) -> None:
    slug = _frame_with_proposals(monkeypatch, tmp_path)
    before = _statuses(slug)
    main(["review"])
    main(["review", "--json"])
    # An all-`pending` review file confirms nothing (errors, mutates nothing).
    main(["confirm", "--from-review", str(store.review_path(slug))])
    assert _statuses(slug) == before
    claims, honesty = _statuses(slug)
    assert claims["c2"] == "proposed" and claims["c3"] == "proposed"
    assert honesty["h1"] == "proposed" and honesty["h2"] == "proposed"


def test_one_pass_review_then_batch_resolve(tmp_path, monkeypatch, capsys) -> None:
    slug = _frame_with_proposals(monkeypatch, tmp_path)
    capsys.readouterr()
    assert main(["review", "--json"]) == 0  # un-gated: frame is nowhere near converged
    payload = json.loads(capsys.readouterr().out)
    ids = [c["id"] for c in payload["proposed_claims"]]
    ids += [h["id"] for h in payload["proposed_honesty"]]
    assert set(ids) == {"c2", "c3", "h1", "h2"}
    # One batched confirm + one batched reject resolve a chosen set in two calls.
    assert main(["confirm", "c2", "h1"]) == 0
    assert main(["reject", "c3"]) == 0
    claims, honesty = _statuses(slug)
    assert claims["c2"] == "confirmed" and honesty["h1"] == "confirmed"
    assert claims["c3"] == "rejected"
    assert honesty["h2"] == "proposed"  # unnamed => untouched


def test_llm_proposal_stays_proposed_until_user_confirm(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "X"])
    main(["capture", "--kind", "audience", "y", "--origin", "llm"])  # c2 proposed
    assert store.load(store.current_slug()).find_claim("c2").status == "proposed"
    main(["confirm", "c2"])  # only an explicit user action flips it
    assert store.load(store.current_slug()).find_claim("c2").status == "confirmed"
