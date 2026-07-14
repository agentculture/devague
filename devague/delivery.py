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
DELIVERY_SCHEMA_VERSION = 1

DEVIATION_STATUSES = ("proposed", "approved", "rejected")
# Feeds the drift-entry contract consumed by the summarize-delivery skill.
CLASSIFICATIONS = ("acceptable", "risky", "needs-follow-up")


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
class Delivery:
    plan_slug: str
    schema_version: int = DELIVERY_SCHEMA_VERSION
    created: str = ""
    updated: str = ""
    deviations: list[DeviationRecord] = field(default_factory=list)

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
    return Delivery(
        plan_slug=d["plan_slug"],
        # A pre-field delivery predates schema_version; treat it as current.
        schema_version=parse_schema_version(d, DELIVERY_SCHEMA_VERSION),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        deviations=deviations,
    )
