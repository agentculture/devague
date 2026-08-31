"""The Delivery domain model — execution-time deviations from a confirmed plan.

The *delivery store* is the execution-seam peer of the plan engine
(:mod:`devague.plan`): where a Plan is the contract the user confirmed, a
Delivery records where execution actually deviated from it — `devague deviate`
is the CLI move that appends to it. Pure data + transitions, no I/O;
persistence lives in :mod:`devague.delivery_store`.

Each :class:`DeviationRecord` names the plan item it relates to (``task_ref``,
e.g. ``t3``), why the deviation happened (``reason`` — required, never
fabricated), what else it touches (``affects``, repeatable plan-item/coverage
refs), who proposed it, and an optional ``classification`` that feeds the
drift-entry contract consumed by the ``summarize-delivery`` skill.

The behavior-validation seam (bvts t3) adds two more record families to the
same store, on the same chassis: :class:`EvidenceRecord` — an obligation met
by a named test, carrying the asserted-behavior text *and* the claim/criterion
text snapshot so a human validates the link by reading both ends side by side
— and :class:`DeltaRecord`, a behavioral delta with provenance backwards (to
the claim or deviation that caused it) and forwards (to the evidence that
validates it). Both are **append-only**: adjudication (``set_evidence_status``
/ ``set_delta_status``) and the ``superseded`` flag are the only mutations a
filed record ever gets. Supersession and its retraction are themselves
append-only *events* (:class:`SupersessionEvent`) that flip that flag on the
target record, so a reader holding one record can tell it is superseded
without scanning the ledger for inbound links.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

from devague.frame import ORIGINS, parse_schema_version

# Bump when the persisted delivery shape changes incompatibly.
# `delivery_store.load` fails closed on a delivery whose schema_version is
# newer/unknown — the delivery-engine peer of frame.SCHEMA_VERSION /
# plan.PLAN_SCHEMA_VERSION (see #5 / #18 for the frame/plan precedent).
#
# v2 (bvts t3) adds Delivery.evidence / EvidenceRecord, Delivery.deltas /
# DeltaRecord, and Delivery.supersessions / SupersessionEvent. This needs a
# real bump for exactly the reason frame's v4→v5 did (the lapses precedent):
# `delivery_store.save` re-stamps schema_version and `to_dict` only serializes
# the known dataclass fields, so a v1-labeled binary that loaded a v2 ledger
# and re-saved it would silently drop every evidence and delta record —
# the ledger the gate-3 audit is supposed to enumerate. The bump makes that
# older binary refuse the file (`schema_version > DELIVERY_SCHEMA_VERSION`)
# instead of quietly deleting evidence; the check runs against the RAW dict in
# `delivery_store.load` before `from_dict` builds anything, so a genuinely
# newer record shape fails closed with a clear error rather than an opaque
# TypeError. A v1 ledger still loads unchanged: the new families default empty.
DELIVERY_SCHEMA_VERSION = 2

DEVIATION_STATUSES = ("proposed", "approved", "rejected")
# Feeds the drift-entry contract consumed by the summarize-delivery skill.
CLASSIFICATIONS = ("acceptable", "risky", "needs-follow-up")

# Evidence is broader than automated tests: each record states what it actually
# was, so a manual verification is never dressed up as an automated test and
# observation is the recorded floor rather than a rubber stamp (c22).
EVIDENCE_TYPES = ("automated", "integration", "manual", "observation")
# The progressive strength ladder, weakest first: coverage (evidence exists),
# fidelity (it asserts the promised behavior), execution (it currently passes),
# sensitivity (it would likely fail if the behavior broke). The agent assesses
# the level; the CLI only records it, together with the basis (c18).
STRENGTH_LEVELS = ("coverage", "fidelity", "execution", "sensitivity")
# From `execution` upwards a level asserts something about an actual run, so a
# run reference (when, against what commit) is mandatory: "currently passes" is
# never renderable without its when (c21/h17).
RUN_REQUIRED_STRENGTHS = ("execution", "sensitivity")
# A failing outcome is filable and rendered, never suppressed to keep the
# ledger looking green (h2).
EVIDENCE_OUTCOMES = ("pass", "fail")
EVIDENCE_STATUSES = ("proposed", "approved", "rejected")

DELTA_KINDS = ("added", "amended", "removed")
DELTA_STATUSES = ("proposed", "approved", "rejected")

SUPERSESSION_ACTIONS = ("supersede", "retract")


@dataclass
class DeviationRecord:
    id: str
    what: str
    task_ref: str
    reason: str
    affects: list[str] = field(default_factory=list)
    origin: str = "user"  # user | llm
    status: str = "approved"  # proposed | approved | rejected
    classification: Optional[str] = None  # one of CLASSIFICATIONS, or None

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown deviation origin: {self.origin!r}")
        if self.status not in DEVIATION_STATUSES:
            raise ValueError(f"unknown deviation status: {self.status!r}")
        if self.classification is not None and self.classification not in CLASSIFICATIONS:
            raise ValueError(f"unknown deviation classification: {self.classification!r}")


@dataclass
class RunReference:
    """When a piece of evidence last executed, and against what.

    Both halves are mandatory (c21/h17): a run reference exists to make
    "currently passes" checkable at review time — a reviewer re-runs the named
    test and compares ``commit`` against the PR head — so a half-filled
    reference would be worse than none. The values are recorded verbatim from
    the actual run; nothing here is defaulted to "now" or to HEAD, because a
    backfilled reference reads fresher than the evidence really is.
    """

    timestamp: str
    commit: str

    def __post_init__(self) -> None:
        if not self.timestamp:
            raise ValueError("a run reference requires a timestamp")
        if not self.commit:
            raise ValueError("a run reference requires a commit SHA")


@dataclass
class EvidenceRecord:
    """An obligation met by a named test, asserting a named behavior.

    Mirrors :class:`DeviationRecord`'s chassis exactly — prefix-generic id
    minting via ``Delivery._next``, origin-driven initial status, no amend and
    no delete path — with two additions the behavior-validation seam needs:

    * **Text on both ends.** ``behavior_text`` (what the test actually
      asserts, quoted rather than paraphrased) and ``contract_text`` (the
      snapshot of the claim or acceptance criterion at filing time) are the
      payload; ``obligation_ref`` and ``test_ref`` are resolvable pointers,
      not the evidence (c17/h13). A human validates the link by reading the
      two texts side by side, which is impossible if either is absent — so
      both are required at the filing path.
    * **Strength with a recorded basis.** ``strength_basis`` is free text
      recorded *beside* ``strength``, never inferred from it (c18/h14): the
      CLI cannot tell whether a level was earned, so it demands the filer say
      why, and a reviewer accepts no level above its stated basis.

    ``superseded`` is the only content-adjacent field that ever changes after
    filing, and only via :meth:`Delivery.supersede` /
    :meth:`Delivery.retract_supersession`; ``status`` changes only via
    adjudication. Everything else is written once.

    The enum-like fields validate here in ``__post_init__`` (and therefore at
    load time too) — unlike ``frame.LapseRecord.code``, whose vocabulary is
    expected to churn as dogfooding surfaces new degradation shapes. Evidence
    types, strength levels, outcomes and statuses are structural vocabularies
    that do not retire, so re-validating a stored record is correct here.
    """

    id: str
    obligation_ref: str
    test_ref: str
    behavior_text: str
    contract_text: str
    evidence_type: str
    strength: str
    strength_basis: str
    outcome: str
    run: Optional[RunReference] = None
    origin: str = "user"  # user | llm
    status: str = "approved"  # proposed | approved | rejected
    superseded: bool = False

    def __post_init__(self) -> None:
        if self.evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"unknown evidence type: {self.evidence_type!r}")
        if self.strength not in STRENGTH_LEVELS:
            raise ValueError(f"unknown evidence strength: {self.strength!r}")
        if self.outcome not in EVIDENCE_OUTCOMES:
            raise ValueError(f"unknown evidence outcome: {self.outcome!r}")
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown evidence origin: {self.origin!r}")
        if self.status not in EVIDENCE_STATUSES:
            raise ValueError(f"unknown evidence status: {self.status!r}")


@dataclass
class DeltaRecord:
    """One behavioral delta a delivery contributes to the behavior ledger.

    ``behavior_text`` is the payload — the behavior added, amended or removed,
    in readable text. Provenance runs in both directions: ``caused_by`` points
    backwards at the confirmed claim or approved deviation that caused the
    change, and ``evidence_refs`` points forwards at the evidence records that
    validate it. Backward provenance is required at the filing path (a delta
    with no cause is precisely the fabricated-delivery shape gate 3 hunts for);
    forward refs may legitimately be empty, since evidence is often filed
    afterwards.

    Append-only on the same terms as :class:`EvidenceRecord`: adjudication and
    the ``superseded`` flag are the only mutations.
    """

    id: str
    kind: str
    behavior_text: str
    caused_by: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    origin: str = "user"  # user | llm
    status: str = "approved"  # proposed | approved | rejected
    superseded: bool = False

    def __post_init__(self) -> None:
        if self.kind not in DELTA_KINDS:
            raise ValueError(f"unknown delta kind: {self.kind!r}")
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown delta origin: {self.origin!r}")
        if self.status not in DELTA_STATUSES:
            raise ValueError(f"unknown delta status: {self.status!r}")


@dataclass
class SupersessionEvent:
    """A supersede/retract event over an evidence or delta record.

    Deliberately minimal: the event exists so that flipping the ``superseded``
    flag on a target record is itself append-only history rather than an
    unexplained mutation. Correcting a wrong record is *filing a new one and
    superseding the old*, never editing content — the written-late-is-written-
    flattering discipline devague already applies to lapses and deviations.
    ``replacement_ref`` is optional because a behavior can be superseded by
    nothing at all (it simply stopped being claimed).
    """

    id: str
    action: str  # supersede | retract
    target_ref: str
    replacement_ref: Optional[str] = None
    origin: str = "user"  # user | llm

    def __post_init__(self) -> None:
        if self.action not in SUPERSESSION_ACTIONS:
            raise ValueError(f"unknown supersession action: {self.action!r}")
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown supersession origin: {self.origin!r}")


@dataclass
class Delivery:
    plan_slug: str
    schema_version: int = DELIVERY_SCHEMA_VERSION
    created: str = ""
    updated: str = ""
    deviations: list[DeviationRecord] = field(default_factory=list)
    # The behavior-validation record families (bvts t3, schema v2). Both are
    # append-only: no amend, no delete — the only post-filing mutations are
    # set_evidence_status / set_delta_status and the superseded flag, which
    # only supersede()/retract_supersession() touch.
    evidence: list[EvidenceRecord] = field(default_factory=list)
    deltas: list[DeltaRecord] = field(default_factory=list)
    supersessions: list[SupersessionEvent] = field(default_factory=list)

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

    def add_deviation(
        self,
        what: str,
        task_ref: str,
        reason: str,
        affects: Optional[list[str]] = None,
        origin: str = "user",
        classification: Optional[str] = None,
    ) -> DeviationRecord:
        if not reason:
            raise ValueError("a deviation requires a --reason")
        status = "proposed" if origin == "llm" else "approved"
        rec = DeviationRecord(
            id=self._next(self.deviations, "d"),
            what=what,
            task_ref=task_ref,
            reason=reason,
            affects=list(affects) if affects else [],
            origin=origin,
            status=status,
            classification=classification,
        )
        self.deviations.append(rec)
        return rec

    def find_deviation(self, did: str) -> Optional[DeviationRecord]:
        return next((d for d in self.deviations if d.id == did), None)

    def set_status(self, did: str, status: str) -> bool:
        """Set ``did``'s status, failing closed on a typo'd/unknown status.

        Validates ``status`` against :data:`DEVIATION_STATUSES` **before**
        touching the record — an invalid string never mutates anything and
        never gets persisted (a bad status value would otherwise brick the
        ledger on the next fail-closed load, mirroring
        :class:`DeviationRecord`'s own ``__post_init__`` guard). Transition
        legality (e.g. "only a proposed record may be confirmed/rejected") is
        the CLI layer's job (:mod:`devague.cli._commands.deviate`), which can
        report the record's *current* status in its refusal hint; this method
        only guards against garbage status values.
        """
        if status not in DEVIATION_STATUSES:
            raise ValueError(f"unknown deviation status: {status!r}")
        rec = self.find_deviation(did)
        if rec is not None:
            rec.status = status
            return True
        return False

    # ── evidence records (bvts t3) ───────────────────────────────────────────

    def add_evidence(
        self,
        obligation_ref: str,
        test_ref: str,
        behavior_text: str,
        contract_text: str,
        evidence_type: str,
        strength: str,
        strength_basis: str,
        outcome: str,
        run: Optional[RunReference] = None,
        origin: str = "user",
    ) -> EvidenceRecord:
        """File an evidence record.

        Every required field is checked here, at the filing path, with a
        message naming what is missing — the ``add_deviation`` "a deviation
        requires a --reason" pattern. Three checks are load-bearing rather
        than cosmetic:

        * both texts are mandatory, because ids alone are not evidence (h13);
        * ``strength_basis`` is mandatory, because a level without a stated
          basis is a level nobody can check (h14);
        * a run reference is mandatory from ``execution`` upwards, because
          those levels assert something about an actual run (h17).

        ``origin`` drives the initial ``status`` exactly like
        :meth:`add_deviation`: ``llm`` lands ``proposed`` (a human adjudicates),
        ``user`` auto-approves.
        """
        if not obligation_ref:
            raise ValueError("evidence requires an obligation ref")
        if not test_ref:
            raise ValueError("evidence requires a test ref")
        if not behavior_text:
            raise ValueError("evidence requires the asserted behavior text")
        if not contract_text:
            raise ValueError("evidence requires the claim/criterion text snapshot")
        if not strength_basis:
            raise ValueError(f"strength {strength!r} requires a recorded basis")
        if strength in RUN_REQUIRED_STRENGTHS and run is None:
            raise ValueError(f"strength {strength!r} requires a run reference (timestamp + commit)")
        status = "proposed" if origin == "llm" else "approved"
        rec = EvidenceRecord(
            id=self._next(self.evidence, "e"),
            obligation_ref=obligation_ref,
            test_ref=test_ref,
            behavior_text=behavior_text,
            contract_text=contract_text,
            evidence_type=evidence_type,
            strength=strength,
            strength_basis=strength_basis,
            outcome=outcome,
            run=run,
            origin=origin,
            status=status,
        )
        self.evidence.append(rec)
        return rec

    def find_evidence(self, eid: str) -> Optional[EvidenceRecord]:
        return next((r for r in self.evidence if r.id == eid), None)

    def set_evidence_status(self, eid: str, status: str) -> bool:
        """Adjudicate an evidence record — the only mutation it ever gets.

        Validates ``status`` before touching the record, mirroring
        :meth:`set_status`: an invalid value must never reach the file and
        brick the next fail-closed load.
        """
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"unknown evidence status: {status!r}")
        rec = self.find_evidence(eid)
        if rec is not None:
            rec.status = status
            return True
        return False

    # ── behavioral deltas (bvts t3) ──────────────────────────────────────────

    def add_delta(
        self,
        kind: str,
        behavior_text: str,
        caused_by: Optional[list[str]] = None,
        evidence_refs: Optional[list[str]] = None,
        origin: str = "user",
    ) -> DeltaRecord:
        """File a behavioral delta.

        ``caused_by`` is required: a delta that names no claim or deviation
        behind it is an undeclared behavioral change wearing a record's
        clothes. ``evidence_refs`` may be empty — evidence often lands after
        the delta — and is never fabricated to look complete. Refs are stored
        verbatim and are not resolved here; the store has no view of the frame
        or plan (the ``LapseRecord.refs`` precedent, and the cross-store join
        lives in read-only modules like ``contested.py``).
        """
        if not behavior_text:
            raise ValueError("a delta requires the behavior text")
        if not caused_by:
            raise ValueError("a delta requires backward provenance (a claim or deviation ref)")
        status = "proposed" if origin == "llm" else "approved"
        rec = DeltaRecord(
            id=self._next(self.deltas, "b"),
            kind=kind,
            behavior_text=behavior_text,
            caused_by=list(caused_by),
            evidence_refs=list(evidence_refs) if evidence_refs else [],
            origin=origin,
            status=status,
        )
        self.deltas.append(rec)
        return rec

    def find_delta(self, bid: str) -> Optional[DeltaRecord]:
        return next((r for r in self.deltas if r.id == bid), None)

    def set_delta_status(self, bid: str, status: str) -> bool:
        """Adjudicate a delta record — the only mutation it ever gets."""
        if status not in DELTA_STATUSES:
            raise ValueError(f"unknown delta status: {status!r}")
        rec = self.find_delta(bid)
        if rec is not None:
            rec.status = status
            return True
        return False

    # ── supersession (append-only events over both families) ─────────────────

    def find_record(self, ref: str):
        """Resolve ``ref`` to an evidence *or* delta record, or ``None``.

        Id prefixes are disjoint (``e`` / ``b``), so one lookup covers both
        families and supersession needs no per-family entry point.
        """
        return self.find_evidence(ref) or self.find_delta(ref)

    def supersede(
        self,
        target_ref: str,
        replacement_ref: Optional[str] = None,
        origin: str = "user",
    ) -> SupersessionEvent:
        """Mark ``target_ref`` superseded and append the event.

        Two things happen, and neither edits any record's content: the target's
        ``superseded`` flag flips to ``True`` — so a reader holding that record
        knows it is superseded without scanning the ledger for inbound links —
        and a :class:`SupersessionEvent` is appended as the history of why.

        Fails closed before mutating anything: an unknown target or
        replacement, a record superseding itself, or an already-superseded
        target all raise, leaving the ledger untouched.
        """
        target = self.find_record(target_ref)
        if target is None:
            raise ValueError(f"no such record: {target_ref!r}")
        if replacement_ref is not None:
            if replacement_ref == target_ref:
                raise ValueError(f"a record cannot supersede itself: {target_ref!r}")
            if self.find_record(replacement_ref) is None:
                raise ValueError(f"no such record: {replacement_ref!r}")
        if target.superseded:
            raise ValueError(f"record {target_ref!r} is already superseded")
        event = SupersessionEvent(
            id=self._next(self.supersessions, "s"),
            action="supersede",
            target_ref=target_ref,
            replacement_ref=replacement_ref,
            origin=origin,
        )
        target.superseded = True
        self.supersessions.append(event)
        return event

    def retract_supersession(self, target_ref: str, origin: str = "user") -> SupersessionEvent:
        """Clear ``target_ref``'s superseded flag and append the retraction.

        Retraction is a first-class *event*, not the deletion of the original
        supersede event: the ledger keeps both, so the projection can be
        recomputed and the history explains itself.
        """
        target = self.find_record(target_ref)
        if target is None:
            raise ValueError(f"no such record: {target_ref!r}")
        if not target.superseded:
            raise ValueError(f"record {target_ref!r} is not superseded")
        event = SupersessionEvent(
            id=self._next(self.supersessions, "s"),
            action="retract",
            target_ref=target_ref,
            origin=origin,
        )
        target.superseded = False
        self.supersessions.append(event)
        return event


def to_dict(delivery: Delivery) -> dict:
    return dataclasses.asdict(delivery)


def from_dict(d: dict) -> Delivery:
    deviations = [
        DeviationRecord(
            id=r["id"],
            what=r["what"],
            task_ref=r["task_ref"],
            reason=r["reason"],
            affects=list(r.get("affects", [])),
            origin=r.get("origin", "user"),
            status=r.get("status", "approved"),
            classification=r.get("classification"),
        )
        for r in d.get("deviations", [])
    ]
    # Every new family defaults empty, so a v1 ledger loads unchanged.
    evidence = [
        EvidenceRecord(
            id=r["id"],
            obligation_ref=r["obligation_ref"],
            test_ref=r["test_ref"],
            behavior_text=r["behavior_text"],
            contract_text=r["contract_text"],
            evidence_type=r["evidence_type"],
            strength=r["strength"],
            strength_basis=r["strength_basis"],
            outcome=r["outcome"],
            run=RunReference(**r["run"]) if r.get("run") else None,
            origin=r.get("origin", "user"),
            status=r.get("status", "approved"),
            superseded=bool(r.get("superseded", False)),
        )
        for r in d.get("evidence", [])
    ]
    deltas = [
        DeltaRecord(
            id=r["id"],
            kind=r["kind"],
            behavior_text=r["behavior_text"],
            caused_by=list(r.get("caused_by", [])),
            evidence_refs=list(r.get("evidence_refs", [])),
            origin=r.get("origin", "user"),
            status=r.get("status", "approved"),
            superseded=bool(r.get("superseded", False)),
        )
        for r in d.get("deltas", [])
    ]
    supersessions = [
        SupersessionEvent(
            id=r["id"],
            action=r["action"],
            target_ref=r["target_ref"],
            replacement_ref=r.get("replacement_ref"),
            origin=r.get("origin", "user"),
        )
        for r in d.get("supersessions", [])
    ]
    return Delivery(
        plan_slug=d["plan_slug"],
        # A pre-field delivery predates schema_version; treat it as current.
        schema_version=parse_schema_version(d, DELIVERY_SCHEMA_VERSION),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        deviations=deviations,
        evidence=evidence,
        deltas=deltas,
        supersessions=supersessions,
    )
