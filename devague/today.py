"""The today-spec projection — the current behavior of the app, derived (bvts t9).

Dated exported specs are process history: each says what was *promised* at one
moment, and (per the #92 ruling, restated as claim c8) none of them is ever
rewritten. That leaves nobody able to answer "what does this app do *today*"
without archaeology across a decade of `docs/specs/`. This module answers it —
read-only, deterministically, and without touching a single stored file.

**What it projects over.** Not a merge of frame claims: a merge would have to
invent a precedence rule between sibling frames, which claim c9 says does not
exist and honesty condition h3 forbids inferring from dates or slugs. Instead
the projection walks the **behavior ledger** — the :class:`~devague.delivery.
DeltaRecord` entries every delivery contributes (claim c7). Each approved delta
is one explicit statement about behavior:

* ``added`` introduces a behavior;
* ``amended`` restates the behavior it names (superseding the prior statement);
* ``removed`` retires the behavior it names.

**How statements are ordered.** Only ever explicitly. A delta stops counting
when its ``superseded`` flag is set, and that flag is only ever set by an
append-only :class:`~devague.delivery.SupersessionEvent` (which a retraction can
clear again — both are replayed here, in file order). Nothing in this module
orders two statements by date, by slug, or by position in a list. Where the
ledger does not say which of two live statements wins, the projection says so
out loud (:class:`ConflictItem`) and projects *neither* — claim c12: a conflict
not covered by a supersedes link is a human decision, never auto-resolution.

**Lineages.** Deltas that reference each other form a *lineage*: one behavior's
history. A delta names its predecessor either through the supersession event
that replaced it (``replacement_ref``) or through a ``caused_by`` ref pointing
at another delta. Refs resolve within the filing ledger by bare id (``b3``) and
across ledgers by the qualified form ``<plan-slug>:<id>`` — the same shape the
keys in this module's output use, so a cross-repo-cycle amendment is
expressible without inventing a new store. An unresolvable delta-shaped ref is
a diagnostic, never a silent drop.

Within one lineage:

* exactly one live delta of kind ``added``/``amended`` -> it projects, carrying
  the whole lineage as its history;
* exactly one live delta of kind ``removed`` that names a predecessor -> the
  behavior is retired and projects nothing;
* exactly one live ``removed`` naming nothing -> :data:`CONFLICT_UNANCHORED_REMOVAL`;
* two or more live deltas -> :data:`CONFLICT_COMPETING`;
* no live delta at all -> retired (something superseded it with no replacement).

**Fail-open, like** :mod:`devague.contested` (honesty condition h7). A missing,
truncated, or newer-than-supported frame, plan, or delivery file is skipped with
a human-readable diagnostic on the result — never a crash, and never a silent
omission. A plan that will not load is a special case worth naming: the plan
file only supplies the *frame link*, so its ledger is still walked (with an
empty ``frame_slug``) rather than dropping real ledgered behavior on the floor.

**Coverage span** (claim c23 / honesty condition h19). The projection is
complete only over ledgered behavior; anything predating devague adoption is
absent by construction. So it computes its own boundary rather than letting a
renderer hand-write optimism: the earliest and latest ledgered delivery — by
the delivery's own ``created`` stamp, falling back to its plan's, ties broken by
plan slug — and every frame slug with no delta records at all.

Nothing here renders: :mod:`devague.render` (t10) consumes
:class:`ProjectionResult`. Nothing here writes: every call into a store is
``list_slugs``/``load``, never ``save`` (claim c8 / honesty condition h8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from devague import delivery_store, plan_store, store
from devague.delivery import STRENGTH_LEVELS, Delivery, DeltaRecord, EvidenceRecord
from devague.frame import Frame
from devague.plan import Plan

__all__ = [
    "CONFLICT_COMPETING",
    "CONFLICT_REASONS",
    "CONFLICT_UNANCHORED_REMOVAL",
    "ConflictItem",
    "ConflictParty",
    "CoverageSpan",
    "DeliveryStamp",
    "FrameRef",
    "LedgerSource",
    "LoadedState",
    "ProjectedBehavior",
    "ProjectedEvidence",
    "ProjectionResult",
    "load_state",
    "project",
    "project_today",
    "result_to_dict",
]

# Two live statements about one behavior with no supersession link ordering
# them — two amendments of the same predecessor, or an addition its removal
# never superseded. The ledger genuinely does not say which wins.
CONFLICT_COMPETING = "competing-live-deltas"
# A removal naming no behavior it removes: it retires nothing, and filing it
# against the wrong predecessor is exactly the mistake a human must catch.
CONFLICT_UNANCHORED_REMOVAL = "unanchored-removal"
CONFLICT_REASONS = (CONFLICT_COMPETING, CONFLICT_UNANCHORED_REMOVAL)

# The delta kinds that assert a behavior exists (as opposed to retiring one).
_ASSERTING_KINDS = ("added", "amended")


# ── the loaded-state shapes ──────────────────────────────────────────────────


@dataclass(frozen=True)
class FrameRef:
    """One frame the walk saw. ``title`` is empty when the frame would not load."""

    slug: str
    title: str
    readable: bool


@dataclass(frozen=True)
class LedgerSource:
    """One delivery ledger plus the plan/frame context needed to place it.

    ``frame_slug`` is empty when the plan file was unreadable — the ledger is
    still projected (its behaviors are real), it just cannot be attributed to a
    frame for the coverage boundary.
    """

    plan_slug: str
    frame_slug: str
    plan_created: str
    delivery: Delivery


@dataclass(frozen=True)
class LoadedState:
    """Everything :func:`project` needs, already read off disk.

    Separating the walk from the projection is what makes criterion 2's
    determinism testable: the same ``LoadedState`` always yields the same
    :class:`ProjectionResult`, and the walk itself is the only part that can
    fail (and does so open, into ``diagnostics``).
    """

    frames: tuple[FrameRef, ...]
    sources: tuple[LedgerSource, ...]
    plan_count: int
    diagnostics: tuple[str, ...]


# ── the projected shapes ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProjectedEvidence:
    """One evidence record a projected behavior points forward at.

    Every resolved record is carried, including proposed, rejected and
    superseded ones: dropping them would make a behavior look *unevidenced*
    rather than *awaiting adjudication*, and h1 forbids smoothing either way.
    Only approved, non-superseded, passing records feed
    :attr:`ProjectedBehavior.best_strength`.
    """

    key: str
    obligation_ref: str
    test_ref: str
    evidence_type: str
    strength: str
    strength_basis: str
    outcome: str
    status: str
    superseded: bool
    run_timestamp: str
    run_commit: str


@dataclass(frozen=True)
class ProjectedBehavior:
    """One behavior the app has today, and the ledger entry that says so."""

    key: str
    kind: str
    behavior_text: str
    plan_slug: str
    frame_slug: str
    # Backward provenance, verbatim: the claim or deviation refs the delta
    # named. Never resolved here — a frame outlives its plan and this module
    # deliberately does not join back onto claim text (that is t10/t11's call).
    caused_by: tuple[str, ...]
    # Forward provenance, verbatim, plus what those refs resolved to.
    evidence_refs: tuple[str, ...]
    evidence: tuple[ProjectedEvidence, ...]
    unresolved_evidence_refs: tuple[str, ...]
    best_strength: Optional[str]
    has_failing_evidence: bool
    # Every delta key in this behavior's history, oldest-known first.
    lineage: tuple[str, ...]


@dataclass(frozen=True)
class ConflictParty:
    """One live delta on either side of a conflict."""

    key: str
    kind: str
    behavior_text: str
    plan_slug: str
    caused_by: tuple[str, ...]


@dataclass(frozen=True)
class ConflictItem:
    """A human-decision item: the ledger does not say what the behavior is.

    No member of a conflicted lineage projects as current behavior. Picking a
    winner by recency, slug order, or file order is precisely what claim c12
    and honesty condition h3 forbid.
    """

    reason: str
    lineage_key: str
    parties: tuple[ConflictParty, ...]


@dataclass(frozen=True)
class DeliveryStamp:
    """One end of the coverage span: a ledgered delivery and when it began."""

    plan_slug: str
    created: str


@dataclass(frozen=True)
class CoverageSpan:
    """What the projection is complete over — and, by omission, what it is not."""

    earliest: Optional[DeliveryStamp]
    latest: Optional[DeliveryStamp]
    ledgered_plan_slugs: tuple[str, ...]
    frames_absent_from_ledger: tuple[str, ...]
    total_frames: int
    total_plans: int


@dataclass(frozen=True)
class ProjectionResult:
    """The whole projection: what the app does today, what is unresolved, and
    what the answer is complete over.

    The counts are deliberately on the result rather than dropped: a ledger
    carrying unadjudicated or rejected deltas is a different situation from an
    empty one, and a renderer that cannot tell them apart would show a thinner
    app than the record supports.
    """

    behaviors: tuple[ProjectedBehavior, ...]
    conflicts: tuple[ConflictItem, ...]
    coverage: CoverageSpan
    diagnostics: tuple[str, ...]
    proposed_delta_count: int
    rejected_delta_count: int
    retired_lineage_count: int


# ── small helpers ────────────────────────────────────────────────────────────


def _numeric_suffix(item_id: str) -> int:
    """The trailing digits of an id (``b14`` -> 14), so ``b2`` sorts before
    ``b10``. Non-numeric input sorts as 0; this only ever drives display and
    tie-break order, never identity.
    """
    digits = "".join(ch for ch in item_id if ch.isdigit())
    return int(digits) if digits else 0


def _key(plan_slug: str, record_id: str) -> str:
    """The projection's global record key: ``<plan-slug>:<record-id>``."""
    return f"{plan_slug}:{record_id}"


def _sort_key(key: str) -> tuple[str, int, str]:
    plan_slug, _, record_id = key.partition(":")
    return (plan_slug, _numeric_suffix(record_id), record_id)


def _resolve_ref(ref: str, plan_slug: str) -> str:
    """Qualify ``ref``: bare ids belong to the filing ledger, ``a:b`` is global."""
    return ref if ":" in ref else _key(plan_slug, ref)


def _looks_like_delta_ref(ref: str) -> bool:
    """Whether ``ref`` is shaped like a delta id (``b7`` / ``slug:b7``).

    ``caused_by`` mixes backward provenance (``c7``, ``d2``) with lineage links,
    so an unresolvable ref is only worth a diagnostic when it *claims* to be a
    delta — a claim id that does not resolve here is not an error, it is simply
    a claim id.
    """
    tail = ref.rpartition(":")[2]
    return tail.startswith("b") and tail[1:].isdigit()


# ── the fail-open walk ───────────────────────────────────────────────────────


def _load_frame_safely(slug: str) -> tuple[Optional[Frame], Optional[str]]:
    """Best-effort frame load: ``(frame, diagnostic)``, never raises."""
    try:
        return store.load(slug), None
    except FileNotFoundError:
        return None, None
    except store.IncompatibleSchemaError as exc:
        return None, (
            f"today: frame {slug!r} uses a schema this devague can't read, skipped ({exc})"
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return None, f"today: frame {slug!r} is unreadable, skipped ({exc})"


def _load_plan_safely(slug: str) -> tuple[Optional[Plan], Optional[str]]:
    """Best-effort plan load: ``(plan, diagnostic)``, never raises."""
    try:
        return plan_store.load(slug), None
    except FileNotFoundError:
        return None, None
    except plan_store.IncompatiblePlanSchemaError as exc:
        return None, (
            f"today: plan {slug!r} uses a schema this devague can't read, skipped ({exc})"
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return None, f"today: plan {slug!r} is unreadable, skipped ({exc})"


def _load_delivery_safely(slug: str) -> tuple[Optional[Delivery], Optional[str]]:
    """Best-effort delivery-ledger load: ``(delivery, diagnostic)``, never raises.

    A plan that never had a record filed against it has no ledger file at all;
    that is the normal case, not a diagnostic (mirrors
    :func:`devague.delivery_store.load_or_new`).
    """
    try:
        return delivery_store.load(slug), None
    except FileNotFoundError:
        return None, None
    except delivery_store.IncompatibleDeliverySchemaError as exc:
        return None, (
            f"today: delivery ledger for plan {slug!r} uses a schema this "
            f"devague can't read, skipped ({exc})"
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return None, f"today: delivery ledger for plan {slug!r} is unreadable, skipped ({exc})"


def _walk_frames(diagnostics: list[str]) -> list[FrameRef]:
    try:
        slugs = store.list_slugs()
    except OSError as exc:
        diagnostics.append(f"today: could not list frames ({exc}); coverage boundary is partial")
        return []
    refs: list[FrameRef] = []
    for slug in slugs:
        frame, diagnostic = _load_frame_safely(slug)
        if diagnostic:
            diagnostics.append(diagnostic)
        refs.append(
            FrameRef(slug=slug, title=frame.title if frame else "", readable=frame is not None)
        )
    return refs


def _walk_ledgers(diagnostics: list[str]) -> tuple[list[LedgerSource], int]:
    try:
        slugs = plan_store.list_slugs()
    except OSError as exc:
        diagnostics.append(f"today: could not list plans ({exc}); no behaviors projected")
        return [], 0
    sources: list[LedgerSource] = []
    for slug in slugs:
        plan, plan_diagnostic = _load_plan_safely(slug)
        if plan_diagnostic:
            diagnostics.append(plan_diagnostic)
        delivery, delivery_diagnostic = _load_delivery_safely(slug)
        if delivery_diagnostic:
            diagnostics.append(delivery_diagnostic)
        if delivery is None:
            continue
        # An unreadable plan costs the frame link, not the ledger: dropping the
        # ledger too would be the silent omission h7 forbids.
        sources.append(
            LedgerSource(
                plan_slug=slug,
                frame_slug=plan.frame_slug if plan else "",
                plan_created=plan.created if plan else "",
                delivery=delivery,
            )
        )
    return sources, len(slugs)


def load_state() -> LoadedState:
    """Read every frame, plan, and delivery ledger, fail-open (honesty condition h7).

    Never raises and never writes. Slugs are walked in ``list_slugs`` order
    (already sorted), so the diagnostics list is itself deterministic.
    """
    diagnostics: list[str] = []
    frames = _walk_frames(diagnostics)
    sources, plan_count = _walk_ledgers(diagnostics)
    return LoadedState(
        frames=tuple(frames),
        sources=tuple(sources),
        plan_count=plan_count,
        diagnostics=tuple(diagnostics),
    )


# ── the pure projection ──────────────────────────────────────────────────────


class _Index:
    """The ledger, keyed globally: approved deltas, evidence, and live links."""

    def __init__(self, state: LoadedState) -> None:
        self.deltas: dict[str, tuple[LedgerSource, DeltaRecord]] = {}
        self.delta_status: dict[str, str] = {}
        self.evidence: dict[str, tuple[LedgerSource, EvidenceRecord]] = {}
        # replacement key -> the keys it was recorded as superseding.
        self.supersedes: dict[str, set[str]] = {}
        self.proposed_deltas = 0
        self.rejected_deltas = 0

        for source in state.sources:
            for delta in source.delivery.deltas:
                key = _key(source.plan_slug, delta.id)
                self.delta_status[key] = delta.status
                if delta.status == "approved":
                    self.deltas[key] = (source, delta)
                elif delta.status == "proposed":
                    self.proposed_deltas += 1
                else:
                    self.rejected_deltas += 1
            for record in source.delivery.evidence:
                self.evidence[_key(source.plan_slug, record.id)] = (source, record)
            self._replay_supersessions(source)

    def _replay_supersessions(self, source: LedgerSource) -> None:
        """Rebuild the live supersedes links from the append-only event log.

        Events are replayed in file order because a retraction only means
        anything relative to the supersede it undoes — this is bookkeeping over
        an explicit log, not an inference of precedence from ordering.
        """
        links: dict[str, str] = {}
        for event in source.delivery.supersessions:
            target = _resolve_ref(event.target_ref, source.plan_slug)
            if event.action == "supersede":
                if event.replacement_ref:
                    links[target] = _resolve_ref(event.replacement_ref, source.plan_slug)
                else:
                    links.pop(target, None)
            else:  # retract
                links.pop(target, None)
        for target, replacement in links.items():
            self.supersedes.setdefault(replacement, set()).add(target)


def _predecessors(key: str, index: _Index, diagnostics: list[str]) -> set[str]:
    """The delta keys ``key`` is recorded as acting on.

    Two explicit channels, never an inference: the supersession event that named
    this delta as a replacement, and any ``caused_by`` ref pointing at another
    delta.
    """
    source, delta = index.deltas[key]
    found = {ref for ref in index.supersedes.get(key, set()) if ref in index.deltas}
    for ref in delta.caused_by:
        resolved = _resolve_ref(ref, source.plan_slug)
        if resolved == key:
            continue
        if resolved in index.deltas:
            found.add(resolved)
        elif resolved in index.delta_status:
            diagnostics.append(
                f"today: {key} references {resolved}, which is "
                f"{index.delta_status[resolved]} and not part of the ledger"
            )
        elif _looks_like_delta_ref(ref):
            diagnostics.append(f"today: {key} references unknown delta {ref!r}")
    return found


def _lineages(index: _Index, diagnostics: list[str]) -> list[list[str]]:
    """Group delta keys into behavior lineages via their explicit links.

    A union-find whose root is always the smallest key by :func:`_sort_key`, so
    the grouping (and therefore the whole projection) does not depend on which
    delta happened to be walked first.
    """
    parent = {key: key for key in index.deltas}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            return
        if _sort_key(right_root) < _sort_key(left_root):
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root

    for key in sorted(index.deltas, key=_sort_key):
        for predecessor in sorted(_predecessors(key, index, diagnostics), key=_sort_key):
            union(key, predecessor)

    groups: dict[str, list[str]] = {}
    for key in sorted(index.deltas, key=_sort_key):
        groups.setdefault(find(key), []).append(key)
    return [groups[root] for root in sorted(groups, key=_sort_key)]


def _project_evidence(
    delta: DeltaRecord, source: LedgerSource, index: _Index
) -> tuple[tuple[ProjectedEvidence, ...], tuple[str, ...], Optional[str], bool]:
    """Resolve a delta's forward provenance into records, gaps, and strength."""
    resolved: list[ProjectedEvidence] = []
    unresolved: list[str] = []
    for ref in delta.evidence_refs:
        entry = index.evidence.get(_resolve_ref(ref, source.plan_slug))
        if entry is None:
            unresolved.append(ref)
            continue
        _, record = entry
        resolved.append(
            ProjectedEvidence(
                key=_resolve_ref(ref, source.plan_slug),
                obligation_ref=record.obligation_ref,
                test_ref=record.test_ref,
                evidence_type=record.evidence_type,
                strength=record.strength,
                strength_basis=record.strength_basis,
                outcome=record.outcome,
                status=record.status,
                superseded=record.superseded,
                run_timestamp=record.run.timestamp if record.run else "",
                run_commit=record.run.commit if record.run else "",
            )
        )

    # Only an approved, un-superseded, *passing* record can raise the strength
    # this behavior renders at: a failing execution-level record proves the
    # behavior does not currently hold, and counting it would be exactly the
    # flattering read h1 rules out. Failures stay visible via the flag below.
    live = [e for e in resolved if e.status == "approved" and not e.superseded]
    passing = [e for e in live if e.outcome == "pass"]
    best = (
        max(passing, key=lambda e: STRENGTH_LEVELS.index(e.strength)).strength if passing else None
    )
    failing = any(e.outcome == "fail" for e in live)
    return tuple(resolved), tuple(unresolved), best, failing


def _party(key: str, index: _Index) -> ConflictParty:
    source, delta = index.deltas[key]
    return ConflictParty(
        key=key,
        kind=delta.kind,
        behavior_text=delta.behavior_text,
        plan_slug=source.plan_slug,
        caused_by=tuple(delta.caused_by),
    )


def _behavior(key: str, lineage: list[str], index: _Index) -> ProjectedBehavior:
    source, delta = index.deltas[key]
    evidence, unresolved, best, failing = _project_evidence(delta, source, index)
    return ProjectedBehavior(
        key=key,
        kind=delta.kind,
        behavior_text=delta.behavior_text,
        plan_slug=source.plan_slug,
        frame_slug=source.frame_slug,
        caused_by=tuple(delta.caused_by),
        evidence_refs=tuple(delta.evidence_refs),
        evidence=evidence,
        unresolved_evidence_refs=unresolved,
        best_strength=best,
        has_failing_evidence=failing,
        lineage=tuple(lineage),
    )


def _resolve_lineage(
    lineage: list[str], index: _Index
) -> tuple[Optional[ProjectedBehavior], Optional[ConflictItem], bool]:
    """Decide one lineage: ``(behavior, conflict, retired)`` — at most one set.

    The whole ordering discipline lives here, and it is deliberately blunt:
    liveness comes from the ``superseded`` flag alone, so a lineage with two
    live statements is unresolved *as a matter of record* and neither statement
    projects. Nothing picks a winner.
    """
    live = [key for key in lineage if not index.deltas[key][1].superseded]
    if not live:
        # Everything was superseded with no surviving replacement: the behavior
        # simply stopped being claimed.
        return None, None, True
    if len(live) > 1:
        conflict = ConflictItem(
            reason=CONFLICT_COMPETING,
            lineage_key=lineage[0],
            parties=tuple(_party(key, index) for key in live),
        )
        return None, conflict, False

    key = live[0]
    delta = index.deltas[key][1]
    if delta.kind in _ASSERTING_KINDS:
        return _behavior(key, lineage, index), None, False
    if len(lineage) > 1:
        return None, None, True
    conflict = ConflictItem(
        reason=CONFLICT_UNANCHORED_REMOVAL,
        lineage_key=key,
        parties=(_party(key, index),),
    )
    return None, conflict, False


def _coverage(state: LoadedState, diagnostics: list[str]) -> CoverageSpan:
    """The projection's own boundary statement (claim c23 / honesty condition h19).

    "Ledgered" means *a delta record was filed*, whatever its status: the
    boundary is about what the ledger covers, not about what survived
    adjudication. The span is stamped from the delivery's own ``created``,
    falling back to its plan's; a ledger with neither is excluded and named in a
    diagnostic rather than sorted to one end by an empty string.
    """
    ledgered: list[str] = []
    stamps: list[DeliveryStamp] = []
    ledgered_frames: set[str] = set()
    for source in state.sources:
        if not source.delivery.deltas:
            continue
        ledgered.append(source.plan_slug)
        if source.frame_slug:
            ledgered_frames.add(source.frame_slug)
        created = source.delivery.created or source.plan_created
        if created:
            stamps.append(DeliveryStamp(plan_slug=source.plan_slug, created=created))
        else:
            diagnostics.append(
                f"today: delivery ledger for plan {source.plan_slug!r} is undated; "
                f"excluded from the coverage span"
            )
    stamps.sort(key=lambda s: (s.created, s.plan_slug))
    return CoverageSpan(
        earliest=stamps[0] if stamps else None,
        latest=stamps[-1] if stamps else None,
        ledgered_plan_slugs=tuple(sorted(ledgered)),
        frames_absent_from_ledger=tuple(
            sorted(ref.slug for ref in state.frames if ref.slug not in ledgered_frames)
        ),
        total_frames=len(state.frames),
        total_plans=state.plan_count,
    )


def project(state: LoadedState) -> ProjectionResult:
    """Project ``state``'s behavior ledger into the current behavior of the app.

    Pure: it reads no file, writes no file, and mutates neither ``state`` nor
    anything reachable from it. The same ``LoadedState`` always yields an equal
    ``ProjectionResult`` (honesty condition h7) — every ordering decision runs
    through :func:`_sort_key`, never through list position or wall-clock time.
    """
    diagnostics = list(state.diagnostics)
    index = _Index(state)

    behaviors: list[ProjectedBehavior] = []
    conflicts: list[ConflictItem] = []
    retired = 0
    for lineage in _lineages(index, diagnostics):
        behavior, conflict, was_retired = _resolve_lineage(lineage, index)
        if behavior is not None:
            behaviors.append(behavior)
        if conflict is not None:
            conflicts.append(conflict)
        retired += int(was_retired)

    behaviors.sort(key=lambda b: _sort_key(b.key))
    conflicts.sort(key=lambda c: _sort_key(c.lineage_key))
    return ProjectionResult(
        behaviors=tuple(behaviors),
        conflicts=tuple(conflicts),
        coverage=_coverage(state, diagnostics),
        diagnostics=tuple(diagnostics),
        proposed_delta_count=index.proposed_deltas,
        rejected_delta_count=index.rejected_deltas,
        retired_lineage_count=retired,
    )


def project_today() -> ProjectionResult:
    """Walk every store fail-open and project it. Read-only end to end."""
    return project(load_state())


# ── the JSON shape (t10's renderer and any --json surface consume this) ──────


def _evidence_to_dict(evidence: ProjectedEvidence) -> dict:
    return {
        "key": evidence.key,
        "obligation": evidence.obligation_ref,
        "test": evidence.test_ref,
        "type": evidence.evidence_type,
        "strength": evidence.strength,
        "strength_basis": evidence.strength_basis,
        "outcome": evidence.outcome,
        "status": evidence.status,
        "superseded": evidence.superseded,
        "run_timestamp": evidence.run_timestamp,
        "run_commit": evidence.run_commit,
    }


def _behavior_to_dict(behavior: ProjectedBehavior) -> dict:
    return {
        "key": behavior.key,
        "kind": behavior.kind,
        "behavior_text": behavior.behavior_text,
        "plan": behavior.plan_slug,
        "frame": behavior.frame_slug,
        "caused_by": list(behavior.caused_by),
        "evidence_refs": list(behavior.evidence_refs),
        "evidence": [_evidence_to_dict(e) for e in behavior.evidence],
        "unresolved_evidence_refs": list(behavior.unresolved_evidence_refs),
        "best_strength": behavior.best_strength,
        "has_failing_evidence": behavior.has_failing_evidence,
        "lineage": list(behavior.lineage),
    }


def _conflict_to_dict(conflict: ConflictItem) -> dict:
    return {
        "reason": conflict.reason,
        "lineage": conflict.lineage_key,
        "parties": [
            {
                "key": party.key,
                "kind": party.kind,
                "behavior_text": party.behavior_text,
                "plan": party.plan_slug,
                "caused_by": list(party.caused_by),
            }
            for party in conflict.parties
        ],
    }


def _stamp_to_dict(stamp: Optional[DeliveryStamp]) -> Optional[dict]:
    if stamp is None:
        return None
    return {"plan": stamp.plan_slug, "created": stamp.created}


def result_to_dict(result: ProjectionResult) -> dict:
    """The JSON-friendly shape of a projection, for ``--json`` and t10/t11."""
    return {
        "behaviors": [_behavior_to_dict(b) for b in result.behaviors],
        "conflicts": [_conflict_to_dict(c) for c in result.conflicts],
        "coverage": {
            "earliest": _stamp_to_dict(result.coverage.earliest),
            "latest": _stamp_to_dict(result.coverage.latest),
            "ledgered_plans": list(result.coverage.ledgered_plan_slugs),
            "frames_absent_from_ledger": list(result.coverage.frames_absent_from_ledger),
            "total_frames": result.coverage.total_frames,
            "total_plans": result.coverage.total_plans,
        },
        "diagnostics": list(result.diagnostics),
        "proposed_delta_count": result.proposed_delta_count,
        "rejected_delta_count": result.rejected_delta_count,
        "retired_lineage_count": result.retired_lineage_count,
    }
