from __future__ import annotations

import pytest

from devague.frame import Frame
from devague.plan import (
    PLAN_SCHEMA_VERSION,
    Plan,
    PlanRisk,
    Task,
    dependency_waves,
    from_dict,
    targets_from_frame,
    to_dict,
)


def _plan() -> Plan:
    return Plan(slug="demo", title="Demo", frame_slug="demo")


def test_next_allocates_sequential_ids() -> None:
    p = _plan()
    t1 = p.add_task("first")
    t2 = p.add_task("second")
    assert (t1.id, t2.id) == ("t1", "t2")
    r1 = p.add_risk("a risk", "unknown_nonblocking")
    assert r1.id == "r1"


def test_origin_drives_initial_status() -> None:
    p = _plan()
    assert p.add_task("user task").status == "confirmed"
    assert p.add_task("llm task", origin="llm").status == "proposed"


def test_find_task_and_target() -> None:
    p = _plan()
    t = p.add_task("x")
    assert p.find_task("t1") is t
    assert p.find_task("nope") is None
    assert p.find_target("c1") is None


def test_add_acceptance_dep_cover_dedup() -> None:
    p = _plan()
    t = p.add_task("x")
    p.add_acceptance(t, "criterion one")
    p.add_dep(t, "t2")
    p.add_dep(t, "t2")  # dedup
    p.add_cover(t, "c1")
    p.add_cover(t, "c1")  # dedup
    assert t.acceptance_criteria == ["criterion one"]
    assert t.deps == ["t2"]
    assert t.covers == ["c1"]


def test_add_risk_rejects_unknown_kind() -> None:
    p = _plan()
    with pytest.raises(ValueError):
        p.add_risk("bad", "not_a_kind")


def test_set_status_transitions_and_reports_unknown() -> None:
    p = _plan()
    p.add_task("x")
    assert p.set_status("t1", "rejected") is True
    assert p.find_task("t1").status == "rejected"
    assert p.set_status("tX", "confirmed") is False


def test_plan_carries_schema_version() -> None:
    p = _plan()
    assert p.schema_version == PLAN_SCHEMA_VERSION
    assert to_dict(p)["schema_version"] == PLAN_SCHEMA_VERSION
    assert from_dict(to_dict(p)).schema_version == PLAN_SCHEMA_VERSION


def test_legacy_plan_without_schema_version_loads() -> None:
    # A pre-0.7.0 plan has no schema_version key — it must still load.
    p = from_dict({"slug": "s", "title": "t", "frame_slug": "s", "tasks": []})
    assert p.schema_version == PLAN_SCHEMA_VERSION


def test_dataclasses_validate_enums() -> None:
    with pytest.raises(ValueError):
        Task(id="t1", summary="x", origin="alien")
    with pytest.raises(ValueError):
        Task(id="t1", summary="x", status="weird")
    with pytest.raises(ValueError):
        PlanRisk(id="r1", text="x", kind="nope")


def test_from_dict_rejects_malformed_enum_values() -> None:
    # The load path reconstructs via from_dict, so a hand-edited bad value is caught.
    with pytest.raises(ValueError):
        from_dict(
            {
                "slug": "s",
                "title": "t",
                "frame_slug": "s",
                "tasks": [{"id": "t1", "summary": "x", "origin": "alien"}],
            }
        )


@pytest.mark.parametrize("bad", [1.9, True, "1", None])
def test_from_dict_rejects_non_integer_schema_version(bad) -> None:
    # int() would silently coerce 1.9->1 / True->1; a malformed type must raise.
    with pytest.raises(ValueError, match="schema_version"):
        from_dict({"slug": "s", "title": "t", "frame_slug": "s", "schema_version": bad})


def test_roundtrip_preserves_nested_fields() -> None:
    p = _plan()
    t = p.add_task("core", origin="llm")
    p.add_acceptance(t, "works")
    p.add_dep(t, "t9")
    p.add_cover(t, "h2")
    p.add_risk("scope?", "unknown_blocking", task_id="t1")
    p.targets.append(targets_from_frame(_seed_frame())[0])
    restored = from_dict(to_dict(p))
    assert restored == p


def _seed_frame() -> Frame:
    f = Frame(slug="demo", title="Demo")
    # confirmed spec-affecting claim with a confirmed honesty condition
    c = f.add_claim("announcement", "shipped X", origin="user")
    f.add_honesty(c, "it is true", origin="user")
    # a proposed claim and a rejected claim — neither should become a target
    f.add_claim("audience", "maybe", origin="llm")  # proposed
    rej = f.add_claim("boundary", "no", origin="user")
    rej.status = "rejected"
    # an open_question claim — excluded as non-spec-affecting
    f.add_claim("open_question", "what about Y?", origin="user")
    # a confirmed claim with a *proposed* honesty condition — claim is a target, honesty is not
    c2 = f.add_claim("success_signal", "users adopt it", origin="user")
    f.add_honesty(c2, "metric rises", origin="llm")  # proposed
    return f


def test_targets_from_frame_includes_only_confirmed_spec_elements() -> None:
    targets = targets_from_frame(_seed_frame())
    by_id = {t.id: t for t in targets}
    assert "c1" in by_id and by_id["c1"].kind == "announcement"
    assert "h1" in by_id and by_id["h1"].kind == "honesty"
    assert "c5" in by_id  # success_signal claim is confirmed -> a target
    # excluded: proposed claim (c2), rejected (c3), open_question (c4), proposed honesty (h2)
    assert "c2" not in by_id
    assert "c3" not in by_id
    assert "c4" not in by_id
    assert "h2" not in by_id


# ── dependency waves (#20) ────────────────────────────────────────────────────
def _waves_plan(specs: list[tuple[str, list[str], str]]) -> Plan:
    """Build a plan from ``(summary, deps, status)`` rows; ids are t1.. in order."""
    p = Plan(slug="w", title="W", frame_slug="w")
    for summary, deps, status in specs:
        t = p.add_task(summary)
        t.deps = list(deps)
        t.status = status
    return p


def test_waves_linear_chain() -> None:
    p = _waves_plan(
        [("a", [], "confirmed"), ("b", ["t1"], "confirmed"), ("c", ["t2"], "confirmed")]
    )
    assert dependency_waves(p.tasks) == [["t1"], ["t2"], ["t3"]]


def test_waves_parallel_fan_out() -> None:
    p = _waves_plan(
        [
            ("root", [], "confirmed"),
            ("a", ["t1"], "confirmed"),
            ("b", ["t1"], "confirmed"),
            ("c", ["t1"], "confirmed"),
        ]
    )
    assert dependency_waves(p.tasks) == [["t1"], ["t2", "t3", "t4"]]


def test_waves_join() -> None:
    p = _waves_plan(
        [("a", [], "confirmed"), ("b", [], "confirmed"), ("join", ["t1", "t2"], "confirmed")]
    )
    assert dependency_waves(p.tasks) == [["t1", "t2"], ["t3"]]


def test_waves_independent_tasks_share_one_wave_in_stored_order() -> None:
    p = _waves_plan([("a", [], "confirmed"), ("b", [], "confirmed"), ("c", [], "confirmed")])
    assert dependency_waves(p.tasks) == [["t1", "t2", "t3"]]


def test_waves_exclude_rejected_tasks() -> None:
    p = _waves_plan([("a", [], "confirmed"), ("dead", [], "rejected"), ("b", ["t1"], "confirmed")])
    waves = dependency_waves(p.tasks)
    assert waves == [["t1"], ["t3"]]
    assert "t2" not in [tid for w in waves for tid in w]


def test_waves_deterministic_across_calls() -> None:
    p = _waves_plan(
        [("root", [], "confirmed"), ("a", ["t1"], "confirmed"), ("b", ["t1"], "confirmed")]
    )
    assert dependency_waves(p.tasks) == dependency_waves(p.tasks)


def test_waves_empty_plan_is_empty() -> None:
    assert dependency_waves(Plan(slug="w", title="W", frame_slug="w").tasks) == []


def test_waves_dep_on_rejected_is_ignored_by_pure_layering() -> None:
    # The pure function treats a dep outside the active set as satisfied (it is total);
    # the *integrity error* for that dangling edge is the CLI/gate's job, not here.
    p = _waves_plan([("dead", [], "rejected"), ("b", ["t1"], "confirmed")])
    assert dependency_waves(p.tasks) == [["t2"]]


def test_waves_cycle_leftover_appended_without_hanging() -> None:
    # Callers gate cycles via convergence blockers; the pure fn must stay total and
    # surface the unplaceable tasks as a trailing wave rather than loop forever.
    p = _waves_plan([("a", ["t2"], "confirmed"), ("b", ["t1"], "confirmed")])
    waves = dependency_waves(p.tasks)
    assert [tid for w in waves for tid in w] == ["t1", "t2"]
