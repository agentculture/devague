"""The Plan domain model — tasks, acceptance criteria, dependencies, risks.

The *plan engine* is the structural peer of the *frame engine* (:mod:`devague.frame`):
where a Frame turns a vague idea into a buildable spec, a Plan turns that converged
spec into a buildable plan. Pure data + transitions, no I/O — persistence lives in
:mod:`devague.plan_store`, the convergence gate in :mod:`devague.plan_convergence`.

A Plan is seeded from a converged Frame: :func:`targets_from_frame` derives the
**coverage targets** (the frame's confirmed spec-affecting claims and confirmed
honesty conditions) that every task collectively must cover before the plan converges.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

from devague.frame import ORIGINS, SPEC_AFFECTING_KINDS, VAGUENESS_KINDS, Frame

# Bump when the persisted plan shape changes incompatibly. `plan_store.load`
# fails closed on a plan whose schema_version is newer/unknown (see #18; the
# plan-engine peer of frame.SCHEMA_VERSION).
PLAN_SCHEMA_VERSION = 1

TASK_STATUSES = ("proposed", "confirmed", "rejected")
# Risks reuse the frame's open-vagueness kinds: a plan risk is the task-level peer of
# a frame's open vagueness. (NB: frame `interrogate --risk` records a non-blocking
# hard question on a *claim*; a PlanRisk is first-class and attaches to a *task*.)
RISK_KINDS = VAGUENESS_KINDS


@dataclass
class Task:
    id: str
    summary: str
    origin: str = "user"  # user | llm
    status: str = "confirmed"  # proposed | confirmed | rejected
    acceptance_criteria: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)  # task ids this task depends on
    covers: list[str] = field(default_factory=list)  # frame claim/honesty ids (c*/h*)

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown task origin: {self.origin!r}")
        if self.status not in TASK_STATUSES:
            raise ValueError(f"unknown task status: {self.status!r}")


@dataclass
class PlanRisk:
    id: str
    text: str
    kind: str  # one of RISK_KINDS
    task_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in RISK_KINDS:
            raise ValueError(f"unknown plan risk kind: {self.kind!r}")


@dataclass
class CoverageTarget:
    """A requirement the plan must cover, derived from a confirmed frame element.

    ``id`` mirrors the frame id verbatim (``c3``, ``h2``) so a task's ``covers``
    refs stay stable against the source frame.
    """

    id: str
    kind: str  # a claim kind, or "honesty" for an honesty condition
    text: str


@dataclass
class Plan:
    slug: str
    title: str
    frame_slug: str
    schema_version: int = PLAN_SCHEMA_VERSION
    status: str = "drafting"  # drafting | converged | exported
    created: str = ""
    updated: str = ""
    targets: list[CoverageTarget] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    risks: list[PlanRisk] = field(default_factory=list)

    @staticmethod
    def _next(items: list, prefix: str) -> str:
        n = 0
        for it in items:
            if it.id.startswith(prefix):
                try:
                    n = max(n, int(it.id[len(prefix) :]))
                except ValueError:
                    pass
        return f"{prefix}{n + 1}"

    def add_task(self, summary: str, origin: str = "user") -> Task:
        status = "proposed" if origin == "llm" else "confirmed"
        task = Task(
            id=self._next(self.tasks, "t"),
            summary=summary,
            origin=origin,
            status=status,
        )
        self.tasks.append(task)
        return task

    def find_task(self, tid: str) -> Optional[Task]:
        return next((t for t in self.tasks if t.id == tid), None)

    def add_acceptance(self, task: Task, text: str) -> None:
        task.acceptance_criteria.append(text)

    def add_dep(self, task: Task, dep_id: str) -> None:
        if dep_id not in task.deps:
            task.deps.append(dep_id)

    def add_cover(self, task: Task, target_id: str) -> None:
        if target_id not in task.covers:
            task.covers.append(target_id)

    def add_risk(self, text: str, kind: str, task_id: Optional[str] = None) -> PlanRisk:
        if kind not in RISK_KINDS:
            raise ValueError(f"unknown risk kind: {kind}")
        r = PlanRisk(
            id=self._next(self.risks, "r"),
            text=text,
            kind=kind,
            task_id=task_id,
        )
        self.risks.append(r)
        return r

    def find_target(self, target_id: str) -> Optional[CoverageTarget]:
        return next((tg for tg in self.targets if tg.id == target_id), None)

    def set_status(self, task_id: str, status: str) -> bool:
        task = self.find_task(task_id)
        if task is not None:
            task.status = status
            return True
        return False


def targets_from_frame(frame: Frame) -> list[CoverageTarget]:
    """Derive the coverage targets a plan must satisfy from a converged frame.

    Targets are the frame's confirmed spec-affecting claims plus the confirmed
    honesty conditions hanging off them — exactly the elements the spec asserts and
    therefore the plan must build toward. Proposed/rejected claims and
    ``open_question`` claims are excluded.
    """
    targets: list[CoverageTarget] = []
    for claim in frame.claims:
        if claim.status != "confirmed" or claim.kind not in SPEC_AFFECTING_KINDS:
            continue
        targets.append(CoverageTarget(id=claim.id, kind=claim.kind, text=claim.text))
        for h in claim.honesty_conditions:
            if h.status == "confirmed":
                targets.append(CoverageTarget(id=h.id, kind="honesty", text=h.text))
    return targets


def to_dict(plan: Plan) -> dict:
    return dataclasses.asdict(plan)


def from_dict(d: dict) -> Plan:
    tasks = [
        Task(
            id=t["id"],
            summary=t["summary"],
            origin=t.get("origin", "user"),
            status=t.get("status", "confirmed"),
            acceptance_criteria=list(t.get("acceptance_criteria", [])),
            deps=list(t.get("deps", [])),
            covers=list(t.get("covers", [])),
        )
        for t in d.get("tasks", [])
    ]
    targets = [CoverageTarget(**tg) for tg in d.get("targets", [])]
    risks = [PlanRisk(**r) for r in d.get("risks", [])]
    return Plan(
        slug=d["slug"],
        title=d["title"],
        frame_slug=d["frame_slug"],
        # A pre-0.7.0 plan predates the field; treat it as the current schema.
        schema_version=int(d.get("schema_version", PLAN_SCHEMA_VERSION)),
        status=d.get("status", "drafting"),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        targets=targets,
        tasks=tasks,
        risks=risks,
    )
