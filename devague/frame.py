"""The Frame domain model — claims, honesty conditions, hard questions, vagueness.

Pure data + transitions, no I/O. Persistence lives in :mod:`devague.store`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

CLAIM_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "why_it_matters",
    "boundary",
    "success_signal",
    "open_question",
)
SPEC_AFFECTING_KINDS = tuple(k for k in CLAIM_KINDS if k != "open_question")
VAGUENESS_KINDS = (
    "unknown_nonblocking",
    "unknown_blocking",
    "out_of_scope",
    "follow_up",
)
CLAIM_STATUSES = ("proposed", "confirmed", "rejected", "parked")


@dataclass
class HonestyCondition:
    id: str
    text: str
    status: str = "proposed"  # proposed | confirmed | rejected


@dataclass
class HardQuestion:
    id: str
    text: str
    resolved: bool = False
    blocking: bool = False


@dataclass
class Claim:
    id: str
    kind: str
    text: str
    origin: str = "user"  # user | llm
    status: str = "confirmed"  # proposed | confirmed | rejected | parked
    honesty_conditions: list[HonestyCondition] = field(default_factory=list)
    hard_questions: list[HardQuestion] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


@dataclass
class Vagueness:
    id: str
    text: str
    kind: str
    claim_id: Optional[str] = None


@dataclass
class Frame:
    slug: str
    title: str
    status: str = "drafting"  # drafting | converged | exported
    created: str = ""
    updated: str = ""
    claims: list[Claim] = field(default_factory=list)
    open_vagueness: list[Vagueness] = field(default_factory=list)

    @staticmethod
    def _next(items: list, prefix: str) -> str:
        n = 0
        for it in items:
            if it.id.startswith(prefix):
                try:
                    n = max(n, int(it.id[len(prefix):]))
                except ValueError:
                    pass
        return f"{prefix}{n + 1}"

    def _all_honesty(self) -> list[HonestyCondition]:
        return [h for c in self.claims for h in c.honesty_conditions]

    def _all_hard_questions(self) -> list[HardQuestion]:
        return [q for c in self.claims for q in c.hard_questions]

    def add_claim(self, kind: str, text: str, origin: str = "user") -> Claim:
        if kind not in CLAIM_KINDS:
            raise ValueError(f"unknown claim kind: {kind}")
        status = "proposed" if origin == "llm" else "confirmed"
        claim = Claim(
            id=self._next(self.claims, "c"),
            kind=kind,
            text=text,
            origin=origin,
            status=status,
        )
        self.claims.append(claim)
        return claim

    def find_claim(self, cid: str) -> Optional[Claim]:
        return next((c for c in self.claims if c.id == cid), None)

    def find_honesty(self, hid: str) -> Optional[HonestyCondition]:
        return next((h for h in self._all_honesty() if h.id == hid), None)

    def add_honesty(self, claim: Claim, text: str, origin: str = "llm") -> HonestyCondition:
        status = "confirmed" if origin == "user" else "proposed"
        h = HonestyCondition(
            id=self._next(self._all_honesty(), "h"),
            text=text,
            status=status,
        )
        claim.honesty_conditions.append(h)
        return h

    def add_hard_question(self, claim: Claim, text: str, blocking: bool = False) -> HardQuestion:
        q = HardQuestion(
            id=self._next(self._all_hard_questions(), "q"),
            text=text,
            blocking=blocking,
        )
        claim.hard_questions.append(q)
        return q

    def add_vagueness(
        self, text: str, kind: str, claim_id: Optional[str] = None
    ) -> Vagueness:
        if kind not in VAGUENESS_KINDS:
            raise ValueError(f"unknown vagueness kind: {kind}")
        v = Vagueness(
            id=self._next(self.open_vagueness, "v"),
            text=text,
            kind=kind,
            claim_id=claim_id,
        )
        self.open_vagueness.append(v)
        return v

    def set_status(self, item_id: str, status: str) -> bool:
        claim = self.find_claim(item_id)
        if claim is not None:
            claim.status = status
            return True
        honesty = self.find_honesty(item_id)
        if honesty is not None:
            honesty.status = status
            return True
        return False


def to_dict(frame: Frame) -> dict:
    return dataclasses.asdict(frame)


def from_dict(d: dict) -> Frame:
    claims = [
        Claim(
            id=c["id"],
            kind=c["kind"],
            text=c["text"],
            origin=c.get("origin", "user"),
            status=c.get("status", "confirmed"),
            honesty_conditions=[HonestyCondition(**h) for h in c.get("honesty_conditions", [])],
            hard_questions=[HardQuestion(**q) for q in c.get("hard_questions", [])],
            links=list(c.get("links", [])),
        )
        for c in d.get("claims", [])
    ]
    vag = [Vagueness(**v) for v in d.get("open_vagueness", [])]
    return Frame(
        slug=d["slug"],
        title=d["title"],
        status=d.get("status", "drafting"),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        claims=claims,
        open_vagueness=vag,
    )
