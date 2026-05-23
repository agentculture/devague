from __future__ import annotations

from devague.convergence import ConvergenceResult
from devague.plan import CoverageTarget, Plan
from devague.plan_convergence import evaluate


def _converging() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [
        CoverageTarget(id="c1", kind="announcement", text="shipped"),
        CoverageTarget(id="h1", kind="honesty", text="true"),
    ]
    t = p.add_task("do the thing")  # confirmed
    p.add_acceptance(t, "it works")
    p.add_cover(t, "c1")
    p.add_cover(t, "h1")
    return p


def test_full_plan_converges() -> None:
    res = evaluate(_converging())
    assert isinstance(res, ConvergenceResult)
    assert res.passed is True and res.missing == []


def test_no_tasks_blocks() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    res = evaluate(p)
    assert res.passed is False
    assert any("no tasks" in m for m in res.missing)


def test_uncovered_target_blocks() -> None:
    p = _converging()
    p.targets.append(CoverageTarget(id="c2", kind="audience", text="who"))
    res = evaluate(p)
    assert any("c2" in m and "no confirmed task" in m for m in res.missing)


def test_confirmed_task_without_acceptance_blocks() -> None:
    p = _converging()
    extra = p.add_task("uncriteria'd")  # confirmed, no acceptance
    extra  # noqa: B018 - referenced for clarity
    res = evaluate(p)
    assert any("t2" in m and "acceptance" in m for m in res.missing)


def test_proposed_task_blocks() -> None:
    p = _converging()
    p.add_task("speculative", origin="llm")  # proposed
    res = evaluate(p)
    assert any("t2" in m and "still proposed" in m for m in res.missing)


def test_dangling_dependency_blocks() -> None:
    p = _converging()
    p.add_dep(p.find_task("t1"), "t99")
    res = evaluate(p)
    assert any("unknown task t99" in m for m in res.missing)


def test_cycle_blocks_with_deterministic_path() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    a = p.add_task("a")
    b = p.add_task("b")
    p.add_dep(a, "t2")
    p.add_dep(b, "t1")
    res = evaluate(p)
    assert "dependency cycle: t1 -> t2 -> t1" in res.missing


def test_self_loop_cycle() -> None:
    p = _converging()
    p.add_dep(p.find_task("t1"), "t1")
    res = evaluate(p)
    assert "dependency cycle: t1 -> t1" in res.missing


def test_blocking_risk_blocks() -> None:
    p = _converging()
    p.add_risk("unknown scaling", "unknown_blocking")
    res = evaluate(p)
    assert any("blocking risk" in m for m in res.missing)


def test_nonblocking_risk_does_not_block() -> None:
    p = _converging()
    p.add_risk("minor", "unknown_nonblocking")
    assert evaluate(p).passed is True


def test_live_targets_override_snapshot() -> None:
    p = _converging()
    # snapshot is satisfied, but a live extra target is not covered
    live = p.targets + [CoverageTarget(id="c9", kind="boundary", text="non-goal")]
    res = evaluate(p, targets=live)
    assert any("c9" in m for m in res.missing)
