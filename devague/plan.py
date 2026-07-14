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

from devague.frame import (
    ORIGINS,
    SPEC_AFFECTING_KINDS,
    VAGUENESS_KINDS,
    Frame,
    parse_schema_version,
)

# Bump when the persisted plan shape changes incompatibly. `plan_store.load`
# fails closed on a plan whose schema_version is newer/unknown (see #18; the
# plan-engine peer of frame.SCHEMA_VERSION). v2 (#53 t2) adds Task.instruction.
PLAN_SCHEMA_VERSION = 2

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
    # Optional verbatim operator/user-authored working instruction (#53 t2); "" means
    # "no instruction" — never fabricated, rendered/serialized only as given.
    instruction: str = ""

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

    def remove_dep(self, task: Task, dep_id: str) -> bool:
        """Cut a single dependency edge (#53-esd t1, issue #68's edge-removal escape hatch).

        Returns whether ``dep_id`` was actually present. Everything else on the task —
        summary, acceptance criteria, covers, instruction — is untouched; the caller
        (the CLI ``depend --remove`` move) is responsible for the re-confirm rule when
        the task was confirmed.
        """
        if dep_id in task.deps:
            task.deps.remove(dep_id)
            return True
        return False

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

    @staticmethod
    def _validate_acceptance_index(task: Task, index: int) -> None:
        if not 1 <= index <= len(task.acceptance_criteria):
            raise ValueError(
                f"acceptance criterion index out of range: {index} "
                f"(task {task.id} has {len(task.acceptance_criteria)})"
            )

    def amend_task(
        self,
        task: Task,
        *,
        summary: Optional[str] = None,
        accept_replace: Optional[list[tuple[int, str]]] = None,
        accept_remove: Optional[list[int]] = None,
    ) -> None:
        """The ``amend`` transition (#53-esd t1, issue #68): edit a summary and/or
        acceptance criteria in place.

        Scoped deliberately narrow — deps, covers, and instruction are untouched here;
        they each already have their own move (``depend``, ``cover``, ``instruct``).
        ``accept_replace``/``accept_remove`` index criteria 1-based (matching how they
        are listed to the user). Replacements are applied first, against the *current*
        list; removals are then applied in descending index order within this call, so
        several ``--accept-remove`` indices always refer to the pre-call list rather
        than shifting under each other. Raises ``ValueError`` on an out-of-range index
        — the caller (the CLI ``amend`` move) is responsible for the re-confirm rule
        when the task was confirmed, and for refusing a rejected task outright.
        """
        accept_replace = list(accept_replace or [])
        accept_remove = list(accept_remove or [])
        # Validate every index against the pre-call list before mutating anything, so a
        # single bad index in a multi-item batch never leaves a partial edit behind.
        for index, _text in accept_replace:
            self._validate_acceptance_index(task, index)
        for index in accept_remove:
            self._validate_acceptance_index(task, index)
        if summary is not None:
            task.summary = summary
        for index, text in accept_replace:
            task.acceptance_criteria[index - 1] = text
        for index in sorted(set(accept_remove), reverse=True):
            del task.acceptance_criteria[index - 1]

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


def dependency_waves(tasks: list[Task]) -> list[list[str]]:
    """Layer active (non-rejected) tasks into deterministic dependency waves.

    Wave 0 is every active task with no unsatisfied dependency; each later wave is the
    tasks whose deps are all satisfied by earlier waves — the parallel batches an
    external operator *could* fan out (Devague describes the graph; it does not run it).
    Within a wave ids keep stored order, so the layering is deterministic for a given
    plan.

    Rejected tasks are excluded entirely. A dependency on a task outside the active set
    (unknown, or rejected) is treated as already satisfied here so the function stays
    **total**: those dangling edges are integrity failures surfaced separately by the
    plan-convergence gate (:func:`devague.plan_convergence.dependency_blockers`), not
    scheduling facts. The graph is assumed acyclic; any tasks left unplaceable by a
    cycle are appended as a final wave so this never loops forever.

    This is the wave-grouped peer of ``render.plan_md._topo_order`` (which flattens a
    *greedy* topological order for the exported plan); the two intentionally differ in
    grouping, so they are kept as separate functions.
    """
    active = [t for t in tasks if t.status != "rejected"]
    by_id = {t.id: t for t in active}
    placed: set[str] = set()
    remaining = list(active)
    waves: list[list[str]] = []
    progress = True
    while remaining and progress:
        ready = [t for t in remaining if all(d in placed or d not in by_id for d in t.deps)]
        progress = bool(ready)
        if ready:
            waves.append([t.id for t in ready])
            placed.update(t.id for t in ready)
            remaining = [t for t in remaining if t.id not in placed]
    if remaining:  # cycle leftover — the caller should have blocked this
        waves.append([t.id for t in remaining])
    return waves


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
            instruction=t.get("instruction", ""),
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
        schema_version=parse_schema_version(d, PLAN_SCHEMA_VERSION),
        status=d.get("status", "drafting"),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        targets=targets,
        tasks=tasks,
        risks=risks,
    )
