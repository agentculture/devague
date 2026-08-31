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
# v3 (resolve-parked-vagueness t2) adds PlanRisk.resolved/resolution — the
# plan-side twin of frame.SCHEMA_VERSION's Vagueness.resolved/resolution bump.
# v4 (issue-backlog-sweep t2) is reserved for t9's per-target deferral state; t2
# itself only bumps the number and hardens plan_store.load's check-before-parse
# order (the plan-side twin of the same frame.SCHEMA_VERSION v4 hardening).
# v5 (Reasoning Degradation Ledger, issue #97 t2) adds Plan.obligations /
# CriterionObligation — the plan-side twin of frame.SCHEMA_VERSION v5's
# Frame.lapses / LapseRecord. This DOES need a real bump (mirroring frame.py's
# v5 rationale verbatim): save() re-stamps schema_version and to_dict only
# serializes known dataclass fields, so an older v4-labeled binary reading a
# v5 plan and re-saving it would silently drop every filed obligation.
PLAN_SCHEMA_VERSION = 5

TASK_STATUSES = ("proposed", "confirmed", "rejected")
# Risks reuse the frame's open-vagueness kinds: a plan risk is the task-level peer of
# a frame's open vagueness. (NB: frame `interrogate --risk` records a non-blocking
# hard question on a *claim*; a PlanRisk is first-class and attaches to a *task*.)
RISK_KINDS = VAGUENESS_KINDS

# Criterion obligations (issue #97 t2) reuse the lapse ledger's three-state
# adjudication vocabulary verbatim — see CriterionObligation's docstring for
# why an obligation's status mirrors LapseRecord.status rather than a plain
# task/risk's two-state proposed|confirmed.
OBLIGATION_STATUSES = ("proposed", "approved", "rejected")


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
    # Resolution state (resolve-parked-vagueness t2), the plan-side twin of
    # frame.Vagueness.resolved/resolution — field names are pinned verbatim, since
    # render/deliverables_md.py (t7) reads both models. Empty string means "no
    # resolution recorded"; a resolved risk stays on the record for provenance
    # instead of being deleted (see Plan.resolve_risk).
    resolved: bool = False
    resolution: str = ""

    def __post_init__(self) -> None:
        if self.kind not in RISK_KINDS:
            raise ValueError(f"unknown plan risk kind: {self.kind!r}")


@dataclass
class CriterionObligation:
    """An obligation attached to a task's acceptance criterion (issue #97 t2) —
    the plan-side twin of ``frame.LapseRecord`` (#97 t1): prefix-generic id
    minting via ``Plan._next``, origin-driven initial status, fail-closed
    validation, append-only-ish with ``set_obligation_status`` the only
    post-filing mutator (no amend, no delete — the same c20-style asymmetry
    as the Reasoning Degradation Ledger).

    Unlike a lapse's ``code`` — a vocabulary validated at the filing path
    (``Frame.add_lapse``) precisely because it is expected to retire — an
    obligation's structural link has nothing to retire: it names *which*
    task and *which* acceptance criterion it obligates, and acceptance
    criteria carry no id of their own (they are a plain ``list[str]``, edited
    by position via ``Plan.amend_task``). So the link is ``task_id`` plus a
    1-based ``criterion_index`` (the same indexing convention
    ``amend_task``'s ``accept_replace``/``accept_remove`` already use) —
    validated fail-closed by :meth:`Plan.add_obligation` against the task's
    *live* acceptance-criteria list, mirroring how ``code`` is validated at
    ``add_lapse`` and nowhere else. Because a criterion can later be amended
    or removed out from under an obligation that named it by position,
    ``criterion_snapshot`` captures the criterion's exact text at filing
    time — free-text provenance, like ``LapseRecord.refs``, not a live
    pointer — so the obligation stays legible even if the criterion at that
    index later says something else.

    ``seam`` and ``behavior`` are plain verbatim text: ``seam`` names what
    boundary/interface must be verified (e.g. "cli", "store round-trip"),
    ``behavior`` what it must do — neither is a controlled vocabulary, so
    neither is validated (matching ``LapseRecord.what``/``skipped_check``).
    """

    id: str
    task_id: str
    criterion_index: int
    criterion_snapshot: str
    seam: str
    behavior: str
    origin: str = "user"  # user | llm
    status: str = "approved"  # proposed | approved | rejected

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown obligation origin: {self.origin!r}")
        if self.status not in OBLIGATION_STATUSES:
            raise ValueError(f"unknown obligation status: {self.status!r}")


@dataclass
class CoverageTarget:
    """A requirement the plan must cover, derived from a confirmed frame element.

    ``id`` mirrors the frame id verbatim (``c3``, ``h2``) so a task's ``covers``
    refs stay stable against the source frame.
    """

    id: str
    kind: str  # a claim kind, or "honesty" for an honesty condition
    text: str
    # Per-target deferral (issue #85, schema v4): a coverage target the operator
    # has deliberately excluded from THIS plan's gate — typically because it
    # belongs to a later milestone plan — with the reason recorded so the
    # exclusion is visible in the exported artifact instead of silently implied
    # by absence. False/"" means "not deferred"; never fabricated when absent.
    # Set/cleared only via ``Plan.defer_target`` / ``Plan.undefer_target``.
    deferred: bool = False
    deferred_reason: str = ""


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
    # The plan-side twin of Frame.lapses (issue #97 t2, schema v5). Append-only-ish:
    # no amend, no delete — the only post-filing mutation is set_obligation_status.
    obligations: list[CriterionObligation] = field(default_factory=list)

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

    def find_risk(self, rid: str) -> Optional[PlanRisk]:
        return next((r for r in self.risks if r.id == rid), None)

    def resolve_risk(self, rid: str, resolution: str) -> PlanRisk:
        """Close out a risk with a decision (resolve-parked-vagueness t2 — the
        plan-side twin of ``Frame.resolve_vagueness``).

        The risk stays on the record with its resolution text for the evidence
        trail instead of being deleted; it is the convergence gate (t4) that stops
        counting a resolved risk as a blocker. Raises ``ValueError`` on an unknown
        id or on an id that is already resolved — mirroring the frame-side error
        contract exactly, so both engines refuse the same way. The caller (the
        CLI ``plan risk --resolve`` move, t6) is responsible for requiring
        ``--decision`` up front and translating this into a user-facing refusal.
        """
        risk = self.find_risk(rid)
        if risk is None:
            raise ValueError(f"unknown risk id: {rid!r}")
        if risk.resolved:
            raise ValueError(f"risk already resolved: {rid!r}")
        risk.resolved = True
        risk.resolution = resolution
        return risk

    def amend_risk(self, rid: str, text: str) -> PlanRisk:
        """Correct a risk's ``text`` in place (issue #84 comment): the common
        case is a risk whose prose names a task id that later rotated (the
        referenced task was rejected and recreated with a new id during a
        scope change) — the risk is still substantively correct, only the id
        it mentions went stale.

        Preserves ``id``, ``kind``, ``task_id``, AND resolution state
        (``resolved``/``resolution``) verbatim — a resolved risk that gets
        its text corrected stays resolved; only ``text`` changes. Unlike
        ``Frame.amend_claim`` (the frame-side sibling move, #84 t6), this is
        a plain in-place replace with no revision trail: this engine's own
        precedent for editing an already-recorded entity, ``amend_task``,
        does not keep one either, and a ``PlanRisk`` has no honesty
        conditions / hard questions / scope-entry seeds pointing at it the
        way a ``Claim`` does — ``task_id`` is its only structural link, and
        that is left untouched by design.

        Raises ``ValueError`` on an unknown risk id — mirroring
        ``resolve_risk``'s fail-closed contract.
        """
        risk = self.find_risk(rid)
        if risk is None:
            raise ValueError(f"unknown risk id: {rid!r}")
        risk.text = text
        return risk

    def find_target(self, target_id: str) -> Optional[CoverageTarget]:
        return next((tg for tg in self.targets if tg.id == target_id), None)

    def defer_target(self, target_id: str, reason: str) -> CoverageTarget:
        """Deliberately exclude ``target_id`` from this plan's coverage gate (issue
        #85): a milestone-scoped plan should not have to fake coverage of a target
        that genuinely belongs to a later plan just to satisfy the gate.

        Mirrors ``resolve_risk``'s / ``Frame.resolve_vagueness``'s fail-closed
        contract: an unknown target id raises, and deferring an already-deferred
        target raises rather than silently overwriting its recorded reason — call
        ``undefer_target`` first to change your mind, so the reversal is itself an
        explicit, auditable move rather than a quiet edit. The caller (the CLI
        ``plan defer`` move) is responsible for validating ``target_id`` against
        the live frame first (the same seam ``cover`` already uses), so by the
        time this runs the target is guaranteed to exist in ``self.targets``.
        """
        target = self.find_target(target_id)
        if target is None:
            raise ValueError(f"unknown coverage target: {target_id!r}")
        if target.deferred:
            raise ValueError(f"coverage target {target_id!r} is already deferred")
        target.deferred = True
        target.deferred_reason = reason
        return target

    def undefer_target(self, target_id: str) -> CoverageTarget:
        """Reverse a prior ``defer_target`` call, returning the target to the
        active coverage gate.

        Fails closed on an unknown id and on a target that was never deferred —
        the same "no silent no-op" contract as every other resolve/undo move here.
        """
        target = self.find_target(target_id)
        if target is None:
            raise ValueError(f"unknown coverage target: {target_id!r}")
        if not target.deferred:
            raise ValueError(f"coverage target {target_id!r} is not deferred")
        target.deferred = False
        target.deferred_reason = ""
        return target

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

    def add_obligation(
        self,
        task_id: str,
        criterion_index: int,
        seam: str,
        behavior: str,
        origin: str = "user",
    ) -> CriterionObligation:
        """File an obligation against one of ``task_id``'s acceptance criteria
        (issue #97 t2, the plan-side twin of ``Frame.add_lapse``).

        Both halves of the link are validated fail-closed here, at the filing
        path, before any record is minted: an unknown ``task_id`` raises, and
        ``criterion_index`` is validated the same way ``amend_task`` already
        validates its indices (:meth:`_validate_acceptance_index`) — 1-based,
        against the task's *current* acceptance-criteria list. The criterion's
        text at that index is captured verbatim into
        ``CriterionObligation.criterion_snapshot`` so the obligation stays
        legible even if the criterion is later amended or removed out from
        under it.

        ``origin`` drives the initial ``status`` exactly like
        ``Frame.add_lapse``: ``llm`` lands ``proposed`` (needs a human
        ``set_obligation_status`` to approve), ``user`` auto-approves.
        """
        task = self.find_task(task_id)
        if task is None:
            raise ValueError(f"unknown task id: {task_id!r}")
        self._validate_acceptance_index(task, criterion_index)
        snapshot = task.acceptance_criteria[criterion_index - 1]
        status = "proposed" if origin == "llm" else "approved"
        rec = CriterionObligation(
            id=self._next(self.obligations, "o"),
            task_id=task_id,
            criterion_index=criterion_index,
            criterion_snapshot=snapshot,
            seam=seam,
            behavior=behavior,
            origin=origin,
            status=status,
        )
        self.obligations.append(rec)
        return rec

    def find_obligation(self, oid: str) -> Optional[CriterionObligation]:
        return next((o for o in self.obligations if o.id == oid), None)

    def set_obligation_status(self, oid: str, status: str) -> bool:
        """Set an obligation's status, failing closed on a typo'd/unknown value.

        The only mutator a filed obligation ever gets — mirrors
        ``Frame.set_lapse_status`` exactly: validates ``status`` against
        :data:`OBLIGATION_STATUSES` *before* touching the record, so an
        invalid string never mutates anything.
        """
        if status not in OBLIGATION_STATUSES:
            raise ValueError(f"unknown obligation status: {status!r}")
        rec = self.find_obligation(oid)
        if rec is not None:
            rec.status = status
            return True
        return False

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


def terminal_tasks(tasks: list[Task]) -> list[Task]:
    """Active (non-rejected) tasks that no other active task depends on.

    These are the leaves of the dependency graph — the tasks whose output nothing
    downstream consumes — used by the read-only ``deliverables`` view (#70) to answer
    "what exists once every task completes" without re-deriving the whole graph. A
    task with no dependents is terminal even if it itself has deps of its own; a plan
    with no tasks at all yields an empty (vacuously total) list. Order is stored
    order (stable), not topological — the caller decides how to present them.

    Only *active* tasks are consulted on both sides: a rejected task is never
    terminal (it is not part of "what ships"), and a rejected task's ``deps`` entry
    naming another task does not keep that other task off the terminal list — a
    dependency edge only "uses up" a task's terminal status when another *active*
    task still depends on it.
    """
    active = [t for t in tasks if t.status != "rejected"]
    depended_on = {d for t in active for d in t.deps}
    return [t for t in active if t.id not in depended_on]


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
    obligations = [
        CriterionObligation(
            id=o["id"],
            task_id=o["task_id"],
            criterion_index=o["criterion_index"],
            criterion_snapshot=o.get("criterion_snapshot", ""),
            seam=o.get("seam", ""),
            behavior=o.get("behavior", ""),
            origin=o.get("origin", "user"),
            status=o.get("status", "approved"),
        )
        # Pre-v5 plans predate this field entirely (issue #97 t2); default to
        # an empty ledger — the plan-side twin of frame.from_dict's `lapses`.
        for o in d.get("obligations", [])
    ]
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
        obligations=obligations,
    )
