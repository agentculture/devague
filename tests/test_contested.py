"""Tests for the contested-by-deviation derivation (#92, t14).

An approved ``devague deviate`` record can name a confirmed claim in its
``--affects`` list, but until now nothing surfaced that back-reference: the
exported spec, ``devague show``, and ``devague status`` all rendered the
named claim as if execution had never disproved it. Per the #92 maintainer
ruling ("don't change the spec, this is part of the ledger — deviate is the
marking of the change"), the fix is a pure, read-only derivation — never a
rewrite of the claim itself. Acceptance criteria:

1. an approved deviation whose --affects names a confirmed claim yields a
   contested marker on re-export and a contested line in show and status
2. export, show, and status succeed on a frame whose delivery store is
   missing, truncated, or declares a newer schema (three corruption-shape
   tests); frame JSON is byte-identical before and after

Covers claims c14/c21/c34, honesty conditions h14/h17/h27.
"""

from __future__ import annotations

import json

import pytest

from devague import delivery_store, plan_store, store
from devague.cli import main
from devague.contested import (
    ContestedMarker,
    find_contested_markers,
    marker_to_dict,
    sorted_markers,
)
from devague.delivery import DELIVERY_SCHEMA_VERSION, Delivery
from devague.frame import Frame
from devague.plan import Plan, targets_from_frame
from devague.render.spec_md import render_spec

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")


# ── CLI-level fixtures ────────────────────────────────────────────────────────


def _converged_frame_with_requirement(monkeypatch, tmp_path) -> tuple[str, str]:
    """Seed a frame that passes the frame gate and also carries a confirmed
    ``requirement`` claim (Requirements has its own render code path,
    distinct from the generic ``_claim_section``/announcement blockquote).
    Returns ``(slug, requirement_claim_id)``.
    """
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the contested-by-deviation derivation"])  # c1 announcement
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    main(
        [
            "capture",
            "--kind",
            "requirement",
            "native transcripts live in a flat layout",
            "--origin",
            "user",
        ]
    )
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    slug = store.current_slug()
    req = next(c for c in store.load(slug).claims if c.kind == "requirement")
    return slug, req.id


def _converged_plan_covering_all_targets(monkeypatch, tmp_path) -> tuple[str, str]:
    """Seed a converged frame + a converged plan (single task ``t1`` covering
    every target). Returns ``(slug, requirement_claim_id)``.
    """
    slug, req_id = _converged_frame_with_requirement(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    p = plan_store.load(slug)
    args = ["plan", "task", "cover everything", "--accept", "all targets satisfied"]
    for tg in p.targets:
        args += ["--covers", tg.id]
    main(args)
    return slug, req_id


# ── acceptance criterion 1: end-to-end across export/show/status ────────────


def test_export_show_status_render_contested_marker_end_to_end(
    tmp_path, monkeypatch, capsys
) -> None:
    slug, req_id = _converged_plan_covering_all_targets(monkeypatch, tmp_path)
    reason = "measured 408 of 695 files (59%) below the depth the walker searches"
    rc = main(
        [
            "deviate",
            "walk transcripts recursively",
            "--task",
            "t1",
            "--reason",
            reason,
            "--affects",
            "c1",
            "--affects",
            req_id,
            "--classification",
            "risky",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    # export: a rich per-claim marker under BOTH the announcement blockquote
    # (c1) and the Requirements block (its own separate render code path).
    rc = main(["export"])
    assert rc == 0
    capsys.readouterr()
    spec_files = list((tmp_path / "docs" / "specs").glob("*.md"))
    assert len(spec_files) == 1
    spec_text = spec_files[0].read_text(encoding="utf-8")
    assert f"> ⚠ contested by `d1` (risky): {reason}" in spec_text
    assert f"  - ⚠ contested by `d1` (risky): {reason}" in spec_text

    # show (text): a summary contested line, one per (claim, deviation).
    rc = main(["show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"contested: c1 by d1 (risky): {reason}" in out
    assert f"contested: {req_id} by d1 (risky): {reason}" in out

    # show --json: the same information, structured.
    rc = main(["show", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contested"] == [
        {
            "claim": "c1",
            "deviation": "d1",
            "what": "walk transcripts recursively",
            "reason": reason,
            "classification": "risky",
            "plan": slug,
        },
        {
            "claim": req_id,
            "deviation": "d1",
            "what": "walk transcripts recursively",
            "reason": reason,
            "classification": "risky",
            "plan": slug,
        },
    ]

    # status (text + json): same signal, different surface.
    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"contested: c1 by d1 (risky): {reason}" in out

    rc = main(["status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert {"claim": "c1", "deviation": "d1"}.items() <= payload["contested"][0].items()
    assert len(payload["contested"]) == 2


def test_plan_status_never_carries_a_contested_key(tmp_path, monkeypatch, capsys) -> None:
    # Scope discipline: only the FRAME engine's status/show derive this — the
    # plan engine's own status must stay exactly as it was (no "contested" key
    # at all, not even an empty one), so plan-status consumers are never told
    # about a feature that doesn't apply to them.
    slug, req_id = _converged_plan_covering_all_targets(monkeypatch, tmp_path)
    main(
        [
            "deviate",
            "swap",
            "--task",
            "t1",
            "--reason",
            "why",
            "--affects",
            "c1",
        ]
    )
    capsys.readouterr()
    rc = main(["plan", "status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "contested" not in payload


def test_a_deviation_affecting_only_task_ids_yields_no_markers_end_to_end(
    tmp_path, monkeypatch, capsys
) -> None:
    # Mirrors this repo's own committed `.devague/deliveries/issue-backlog-sweep.json`
    # d1: a real approved deviation whose --affects names only task ids. It must
    # never produce a contested marker anywhere.
    slug, _ = _converged_plan_covering_all_targets(monkeypatch, tmp_path)
    p = plan_store.load(slug)
    p.add_task("second task")  # t2
    plan_store.save(p)
    rc = main(
        [
            "deviate",
            "reorder waves",
            "--task",
            "t1",
            "--reason",
            "dependency graph under-specified execution order",
            "--affects",
            "t1",
            "--affects",
            "t2",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = main(["show", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contested"] == []

    rc = main(["status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contested"] == []


# ── acceptance criterion 2: fail-open on a corrupt delivery store ────────────


def _corrupt_missing(slug: str) -> None:
    pass  # never create a delivery file at all -- the common, silent case


def _corrupt_truncated(slug: str) -> None:
    delivery_store.save(Delivery(plan_slug=slug))
    p = delivery_store.path_for(slug)
    p.write_text("{not valid json", encoding="utf-8")


def _corrupt_newer_schema(slug: str) -> None:
    delivery_store.save(Delivery(plan_slug=slug))
    p = delivery_store.path_for(slug)
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = DELIVERY_SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")


@pytest.mark.parametrize(
    "corrupt, diag_snippet",
    [
        pytest.param(_corrupt_missing, None, id="missing"),
        pytest.param(_corrupt_truncated, "unreadable", id="truncated"),
        pytest.param(_corrupt_newer_schema, "schema", id="newer-schema"),
    ],
)
def test_export_show_status_fail_open_on_corrupt_delivery_store(
    tmp_path, monkeypatch, capsys, corrupt, diag_snippet
) -> None:
    slug, _ = _converged_plan_covering_all_targets(monkeypatch, tmp_path)
    corrupt(slug)
    frame_path = store.path_for(slug)
    before_bytes = frame_path.read_bytes()
    capsys.readouterr()

    # show: read-only -- frame JSON must be byte-identical before and after.
    rc = main(["show"])
    assert rc == 0
    err = capsys.readouterr().err
    if diag_snippet:
        assert diag_snippet in err
        assert "contested" in err
    assert frame_path.read_bytes() == before_bytes

    # status: same contract.
    rc = main(["status"])
    assert rc == 0
    err = capsys.readouterr().err
    if diag_snippet:
        assert diag_snippet in err
    assert frame_path.read_bytes() == before_bytes

    # export: must still succeed (never a refused export, never a traceback).
    before_claims = [(c.id, c.kind, c.text, c.status) for c in store.load(slug).claims]
    rc = main(["export"])
    assert rc == 0
    err = capsys.readouterr().err
    if diag_snippet:
        assert diag_snippet in err
    # export legitimately flips frame.status/updated on every successful
    # export (pre-existing contract, unrelated to #92) -- what must stay
    # unchanged is the claim content itself: no id churn, no text mutation.
    after_claims = [(c.id, c.kind, c.text, c.status) for c in store.load(slug).claims]
    assert after_claims == before_claims


# ── module-level unit tests: devague.contested ───────────────────────────────


def _bare_frame_and_plan(monkeypatch, tmp_path, slug: str = "demo") -> Frame:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug=slug, title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")  # c1
    store.save(frame)
    plan = Plan(slug=slug, title="Demo Plan", frame_slug=slug)
    plan.targets = targets_from_frame(frame)
    plan.add_task("first task")  # t1
    plan_store.save(plan)
    return frame


def test_find_contested_markers_no_plans_at_all(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")
    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert diagnostics == []


def test_find_contested_markers_ignores_plan_with_different_frame_slug(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    frame = _bare_frame_and_plan(monkeypatch, tmp_path, slug="demo")
    other = Plan(slug="unrelated", title="Other", frame_slug="other-frame")
    other.add_task("t1")
    plan_store.save(other)
    d = Delivery(plan_slug="unrelated")
    d.add_deviation("x", "t1", "why", affects=["c1"], origin="user")
    delivery_store.save(d)

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert diagnostics == []


def test_find_contested_markers_missing_delivery_is_silent(tmp_path, monkeypatch) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert diagnostics == []


def test_find_contested_markers_truncated_delivery_degrades_with_diagnostic(
    tmp_path, monkeypatch
) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    delivery_store.save(Delivery(plan_slug="demo"))
    p = delivery_store.path_for("demo")
    p.write_text("{not valid json", encoding="utf-8")

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert len(diagnostics) == 1
    assert "demo" in diagnostics[0]
    assert "unreadable" in diagnostics[0]


def test_find_contested_markers_newer_schema_delivery_degrades_with_diagnostic(
    tmp_path, monkeypatch
) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    delivery_store.save(Delivery(plan_slug="demo"))
    p = delivery_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = DELIVERY_SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert len(diagnostics) == 1
    assert "demo" in diagnostics[0]
    assert "schema" in diagnostics[0]


def test_find_contested_markers_unreadable_plan_is_skipped_with_diagnostic(
    tmp_path, monkeypatch
) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    p = plan_store.path_for("demo")
    p.write_text("{not valid json", encoding="utf-8")

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert len(diagnostics) == 1
    assert "unreadable" in diagnostics[0]


def test_find_contested_markers_newer_schema_plan_is_skipped_with_diagnostic(
    tmp_path, monkeypatch
) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    p = plan_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = raw["schema_version"] + 99
    p.write_text(json.dumps(raw), encoding="utf-8")

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert len(diagnostics) == 1
    assert "schema" in diagnostics[0]


def test_proposed_deviation_is_not_contested_until_approved(tmp_path, monkeypatch) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    d.add_deviation("x", "t1", "why", affects=["c1"], origin="llm")  # lands proposed
    delivery_store.save(d)

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert diagnostics == []


def test_affects_naming_a_rejected_claim_is_not_marked(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    c = frame.add_claim("boundary", "will be rejected", origin="user")
    frame.set_status(c.id, "rejected")
    store.save(frame)
    plan = Plan(slug="demo", title="Demo Plan", frame_slug="demo")
    plan.add_task("t1")
    plan_store.save(plan)
    d = Delivery(plan_slug="demo")
    d.add_deviation("x", "t1", "why", affects=[c.id], origin="user")
    delivery_store.save(d)

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert diagnostics == []


def test_deviation_affecting_only_task_ids_yields_no_markers(tmp_path, monkeypatch) -> None:
    # The shape of this repo's own committed d1 on issue-backlog-sweep: names
    # only task ids, never a claim -- a good regression guard that a real,
    # ordinary deviation produces zero markers.
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    plan = plan_store.load("demo")
    plan.add_task("second task")  # t2
    plan_store.save(plan)
    d = Delivery(plan_slug="demo")
    d.add_deviation("reordered execution", "t1", "why", affects=["t1", "t2"], origin="user")
    delivery_store.save(d)

    markers, diagnostics = find_contested_markers(frame)
    assert markers == {}
    assert diagnostics == []


def test_multiple_plans_for_the_same_frame_are_all_joined(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")  # c1
    store.save(frame)
    plan_a = Plan(slug="demo-a", title="A", frame_slug="demo")
    plan_a.add_task("t1")
    plan_store.save(plan_a)
    plan_b = Plan(slug="demo-b", title="B", frame_slug="demo")
    plan_b.add_task("t1")
    plan_store.save(plan_b)
    d_a = Delivery(plan_slug="demo-a")
    d_a.add_deviation("x", "t1", "why a", affects=["c1"], origin="user")
    delivery_store.save(d_a)
    d_b = Delivery(plan_slug="demo-b")
    d_b.add_deviation("y", "t1", "why b", affects=["c1"], origin="user")
    delivery_store.save(d_b)

    markers, diagnostics = find_contested_markers(frame)
    assert diagnostics == []
    assert [m.plan_slug for m in markers["c1"]] == ["demo-a", "demo-b"]

    # An unrelated plan (different frame_slug) must never leak in.
    plan_c = Plan(slug="unrelated", title="C", frame_slug="other-frame")
    plan_c.add_task("t1")
    plan_store.save(plan_c)
    d_c = Delivery(plan_slug="unrelated")
    d_c.add_deviation("z", "t1", "why c", affects=["c1"], origin="user")
    delivery_store.save(d_c)

    markers2, _ = find_contested_markers(frame)
    assert len(markers2["c1"]) == 2


def test_find_contested_markers_never_writes_any_store(tmp_path, monkeypatch) -> None:
    frame = _bare_frame_and_plan(monkeypatch, tmp_path)
    d = Delivery(plan_slug="demo")
    d.add_deviation("x", "t1", "why", affects=["c1"], origin="user")
    delivery_store.save(d)

    def _boom(*_a, **_kw):
        raise AssertionError("contested derivation must never write any store")

    monkeypatch.setattr(store, "save", _boom)
    monkeypatch.setattr(plan_store, "save", _boom)
    monkeypatch.setattr(delivery_store, "save", _boom)

    markers, diagnostics = find_contested_markers(frame)
    assert diagnostics == []
    assert markers  # sanity: the derivation still actually ran and found d1


def test_sorted_markers_is_numeric_aware_and_deterministic() -> None:
    # Fabricate ids out of numeric order to prove the sort is numeric, not
    # lexicographic (which would put "d10" before "d2").
    m1 = ContestedMarker("c1", "d10", "x", "reason ten", None, "demo")
    m2 = ContestedMarker("c1", "d2", "y", "reason two", None, "demo")
    flat = sorted_markers({"c1": [m1, m2]})
    assert [m.deviation_id for m in flat] == ["d2", "d10"]


def test_marker_to_dict_shape() -> None:
    m = ContestedMarker("c1", "d1", "what happened", "why", "risky", "demo")
    assert marker_to_dict(m) == {
        "claim": "c1",
        "deviation": "d1",
        "what": "what happened",
        "reason": "why",
        "classification": "risky",
        "plan": "demo",
    }


# ── module-level unit tests: render_spec(frame, contested=...) ──────────────


def test_render_spec_marks_contested_confirmed_requirement() -> None:
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")
    req = frame.add_claim("requirement", "flat transcript layout", origin="user")
    marker = ContestedMarker(
        claim_id=req.id,
        deviation_id="d8",
        what="walk recursively",
        reason="measured 408 of 695 files (59%) below the depth the walker searches",
        classification="risky",
        plan_slug="demo",
    )
    out = render_spec(frame, contested={req.id: [marker]})
    assert "## Requirements" in out
    assert (
        "  - ⚠ contested by `d8` (risky): measured 408 of 695 files "
        "(59%) below the depth the walker searches" in out
    )


def test_render_spec_marks_contested_announcement_claim() -> None:
    frame = Frame(slug="demo", title="Demo")
    ann = frame.add_claim("announcement", "ship it", origin="user")
    marker = ContestedMarker(
        claim_id=ann.id,
        deviation_id="d1",
        what="x",
        reason="drifted",
        classification=None,
        plan_slug="demo",
    )
    out = render_spec(frame, contested={ann.id: [marker]})
    assert "> ⚠ contested by `d1`: drifted" in out
    # No classification -> no empty parens.
    assert "()" not in out


def test_render_spec_marks_contested_claim_in_a_generic_section() -> None:
    # Boundary claims go through the generic `_claim_section`/`_claim_bullets`
    # path, distinct from both the announcement blockquote and Requirements.
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")
    b = frame.add_claim("boundary", "flat layout only", origin="user")
    marker = ContestedMarker(
        claim_id=b.id,
        deviation_id="d8",
        what="x",
        reason="wrong about the world",
        classification="risky",
        plan_slug="demo",
    )
    out = render_spec(frame, contested={b.id: [marker]})
    assert "## Scope / boundaries" in out
    assert "- ⚠ contested by `d8` (risky): wrong about the world" in out


def test_render_spec_without_contested_arg_is_unaffected() -> None:
    frame = Frame(slug="demo", title="Demo")
    frame.add_claim("announcement", "ship it", origin="user")
    out = render_spec(frame)
    assert "contested" not in out


def test_render_spec_never_marks_a_claim_not_named_in_contested() -> None:
    frame = Frame(slug="demo", title="Demo")
    c1 = frame.add_claim("announcement", "ship it", origin="user")
    frame.add_claim("boundary", "stays clean", origin="user")
    marker = ContestedMarker(
        claim_id=c1.id,
        deviation_id="d1",
        what="x",
        reason="y",
        classification=None,
        plan_slug="demo",
    )
    out = render_spec(frame, contested={c1.id: [marker]})
    boundary_section = out.split("## Scope / boundaries")[1]
    assert "contested" not in boundary_section


def test_render_spec_never_mutates_frame_state() -> None:
    # #92's derivation must be presentational only -- pin this the same way
    # test_render.py's own mutation-safety test does for parks/hard questions.
    frame = Frame(slug="demo", title="Demo")
    c1 = frame.add_claim("announcement", "ship it", origin="user")
    before = [(c.id, c.kind, c.text, c.status) for c in frame.claims]
    marker = ContestedMarker(
        claim_id=c1.id,
        deviation_id="d1",
        what="x",
        reason="y",
        classification=None,
        plan_slug="demo",
    )
    render_spec(frame, contested={c1.id: [marker]})
    after = [(c.id, c.kind, c.text, c.status) for c in frame.claims]
    assert before == after
