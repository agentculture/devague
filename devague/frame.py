"""The Frame domain model — claims, honesty conditions, hard questions, vagueness.

Pure data + transitions, no I/O. Persistence lives in :mod:`devague.store`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

# Bump when the persisted shape changes incompatibly. `store.load` fails closed
# on a frame whose schema_version is newer/unknown (see #5, honesty condition h15).
# v2 (#53 t1) adds Frame.scope_entries and Claim/HonestyCondition.instruction.
# v3 (resolve-parked-vagueness t1) adds Vagueness.resolved / Vagueness.resolution.
# v4 (issue-backlog-sweep t2) is reserved for t4's HardQuestion resolution field;
# t2 itself only bumps the number, hardens store.load's check-before-parse order,
# and makes HardQuestion/Vagueness loading tolerant of unknown keys like Claim.
SCHEMA_VERSION = 4

CLAIM_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "why_it_matters",
    "boundary",
    "success_signal",
    "open_question",
    # Added for the documented spec contract (#5).
    "non_goal",
    "requirement",
    "assumption",
    "decision",
)
# Spec-affecting claims must be confirmed and carry a confirmed honesty condition
# to converge. `requirement` joins the original set; `non_goal`/`decision`/
# `open_question` are descriptive, and `assumption` is soft (an unconfirmed one is
# a convergence *warning*, not a blocker — see convergence.py).
SPEC_AFFECTING_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "why_it_matters",
    "boundary",
    "success_signal",
    "requirement",
)
DESCRIPTIVE_KINDS = ("open_question", "non_goal", "decision")
VAGUENESS_KINDS = (
    "unknown_nonblocking",
    "unknown_blocking",
    "out_of_scope",
    "follow_up",
)
CLAIM_STATUSES = ("proposed", "confirmed", "rejected")
HONESTY_STATUSES = ("proposed", "confirmed", "rejected")
ORIGINS = ("user", "llm")


@dataclass
class HonestyCondition:
    id: str
    text: str
    status: str = "proposed"  # proposed | confirmed | rejected
    # Optional verbatim operator/user-authored text: how to verify this
    # condition. Empty string means "no instruction" — never fabricated or
    # defaulted to prose (#53 t1, c10/h3).
    instruction: str = ""

    def __post_init__(self) -> None:
        if self.status not in HONESTY_STATUSES:
            raise ValueError(f"unknown honesty status: {self.status!r}")


@dataclass
class HardQuestion:
    id: str
    text: str
    resolved: bool = False
    blocking: bool = False
    # v3 frames (and earlier) predate this field (issue-backlog-sweep t4, #48/#52);
    # default to "" for a not-yet-resolved (or resolved-with-no-note) question.
    # Set only via Frame.resolve_hard_question — mirrors Vagueness.resolution.
    resolution: str = ""


@dataclass
class Claim:
    id: str
    kind: str
    text: str
    origin: str = "user"  # user | llm
    status: str = "confirmed"  # proposed | confirmed | rejected
    honesty_conditions: list[HonestyCondition] = field(default_factory=list)
    hard_questions: list[HardQuestion] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    # Optional verbatim operator/user-authored text: how to verify or
    # implement this claim. Empty string means "no instruction" — never
    # fabricated or defaulted to prose (#53 t1, c10/h3).
    instruction: str = ""

    def __post_init__(self) -> None:
        if self.kind not in CLAIM_KINDS:
            raise ValueError(f"unknown claim kind: {self.kind!r}")
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown claim origin: {self.origin!r}")
        if self.status not in CLAIM_STATUSES:
            raise ValueError(f"unknown claim status: {self.status!r}")


@dataclass
class Vagueness:
    id: str
    text: str
    kind: str
    claim_id: Optional[str] = None
    # v2 frames predate these fields (resolve-parked-vagueness t1); default to
    # "not yet resolved". Set only via Frame.resolve_vagueness — v-ids stay out
    # of confirm/reject (decision c11), so set_status must not touch them.
    resolved: bool = False
    resolution: str = ""
    # v2/early-v3 frames predate this field (resolve-parked-vagueness t5); the
    # *deciding* claim recorded at resolve time — distinct from claim_id, the
    # *owning* claim set at park time, which resolve_vagueness never touches.
    resolution_claim_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in VAGUENESS_KINDS:
            raise ValueError(f"unknown vagueness kind: {self.kind!r}")


@dataclass
class ScopeEntry:
    """A recorded scope-exploration finding: a surface explored, and what was
    learned — the optional pre-frame leg (`/scope`, #53). ``seeds`` links this
    finding to the claim ids it seeded, if any.
    """

    id: str
    surface: str
    finding: str
    seeds: list[str] = field(default_factory=list)


@dataclass
class Frame:
    slug: str
    title: str
    schema_version: int = SCHEMA_VERSION
    status: str = "drafting"  # drafting | converged | exported
    created: str = ""
    updated: str = ""
    claims: list[Claim] = field(default_factory=list)
    open_vagueness: list[Vagueness] = field(default_factory=list)
    scope_entries: list[ScopeEntry] = field(default_factory=list)

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

    def add_vagueness(self, text: str, kind: str, claim_id: Optional[str] = None) -> Vagueness:
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

    def find_vagueness(self, vid: str) -> Optional[Vagueness]:
        return next((v for v in self.open_vagueness if v.id == vid), None)

    def resolve_vagueness(
        self, vid: str, resolution: str, claim_id: Optional[str] = None
    ) -> Vagueness:
        """Close out a parked item without routing it through confirm/reject.

        v-ids stay out of set_status (decision c11) — this is the only mutator
        for Vagueness.resolved/resolution. Fails closed on an unknown id and on
        an already-resolved one, rather than silently no-op'ing (issue #57).
        ``claim_id``, if given, must name an existing claim (validated here,
        the same seam as :meth:`add_scope_entry`'s seed-id check) and is
        recorded as ``resolution_claim_id`` — the *deciding* claim, which
        never overwrites ``claim_id``, the *owning* claim set at park time.
        """
        v = self.find_vagueness(vid)
        if v is None:
            raise ValueError(f"unknown vagueness id: {vid!r}")
        if v.resolved:
            raise ValueError(f"vagueness {vid!r} is already resolved")
        if claim_id is not None and self.find_claim(claim_id) is None:
            raise ValueError(f"unknown claim id: {claim_id!r}")
        v.resolved = True
        v.resolution = resolution
        v.resolution_claim_id = claim_id
        return v

    def resolve_hard_question(self, claim_id: str, qid: str, resolution: str = "") -> HardQuestion:
        """Mark a claim's hard question resolved — a USER decision, like confirm.

        Owned by ``devague interrogate <cN> --resolve <qN> [--decision TEXT]``
        (decision c36, issues #48/#52): claim-attached hard questions and the
        durable ``.devague/questions/`` file independently assign their own
        ``qN`` ids, so the claim id is what disambiguates which one is meant —
        this method only ever searches ``claim_id``'s own ``hard_questions``.
        Fails closed on an unknown claim id, a question id that doesn't exist
        (or doesn't belong to that claim), and an already-resolved question,
        rather than silently no-op'ing — the same contract as
        :meth:`resolve_vagueness`. ``resolution`` is optional free text (unlike
        ``park --resolve``'s required ``--decision``) recorded verbatim on
        ``HardQuestion.resolution``.
        """
        claim = self.find_claim(claim_id)
        if claim is None:
            raise ValueError(f"unknown claim id: {claim_id!r}")
        q = next((q for q in claim.hard_questions if q.id == qid), None)
        if q is None:
            raise ValueError(f"no such hard question {qid!r} on claim {claim_id!r}")
        if q.resolved:
            raise ValueError(f"hard question {qid!r} is already resolved")
        q.resolved = True
        q.resolution = resolution
        return q

    def add_scope_entry(
        self, surface: str, finding: str, seeds: Optional[list[str]] = None
    ) -> ScopeEntry:
        seed_ids = list(seeds) if seeds else []
        for sid in seed_ids:
            if self.find_claim(sid) is None:
                raise ValueError(f"unknown seed claim id: {sid!r}")
        entry = ScopeEntry(
            id=self._next(self.scope_entries, "s"),
            surface=surface,
            finding=finding,
            seeds=seed_ids,
        )
        self.scope_entries.append(entry)
        return entry

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

    def reject(self, item_id: str) -> list[str]:
        """Reject a claim or honesty condition, cascading a claim's rejection
        onto its still-live attachments (issue #83).

        Rejected content must never keep looking "live": rendering already
        excludes a rejected claim's attachments (spec-md), and the
        convergence gate already stops treating a rejected claim's unresolved
        blocking hard question as an open blocker. This method closes the
        remaining gap — the review pool and the honesty condition's own
        recorded status — by flipping every honesty condition still attached
        to the claim (``status != "rejected"``) to ``"rejected"`` too, so
        ``devague review`` (which only lists ``proposed`` items) stops
        surfacing them as awaiting a decision that no longer matters.

        Hard questions have no independent status field to flip (only
        ``resolved``/``resolution``, a genuine answer — not the same thing as
        "the parent claim was rejected"), so this leaves them structurally
        untouched; every call site that matters already keys off the parent
        claim's own ``status`` (``convergence._missing_open_uncertainty``,
        ``render.spec_md._hard_questions``).

        Returns the ids of honesty conditions and hard questions this call
        swept along, in "what it took with it" order (honesty ids first,
        then hard-question ids, each in their claim's own attachment order) —
        for the caller to echo (e.g. ``c21 -> rejected (also rejected: h3,
        q1)``). The cascade fires only on the transition *into* ``rejected``:
        rejecting an already-rejected claim again returns ``[]`` rather than
        re-claiming credit for a cascade a prior call already performed
        (idempotent, no double-reporting — the ids "already rejected" stay
        that way whether or not this call runs). Rejecting a bare honesty
        condition id is a plain status flip with no cascade (honesty
        conditions carry no sub-attachments of their own) and also returns
        ``[]``. Raises ``ValueError`` if ``item_id`` names neither a claim
        nor a honesty condition — callers are expected to pre-validate the id
        first (mirrors ``set_status``'s bool-return contract; see
        ``cli/_commands/confirm.py``'s ``_exists`` pre-check, which every
        current caller already runs before touching the frame).
        """
        claim = self.find_claim(item_id)
        if claim is not None:
            cascaded: list[str] = []
            if claim.status != "rejected":
                for h in claim.honesty_conditions:
                    if h.status != "rejected":
                        h.status = "rejected"
                        cascaded.append(h.id)
                cascaded += [q.id for q in claim.hard_questions if not q.resolved]
            claim.status = "rejected"
            return cascaded
        honesty = self.find_honesty(item_id)
        if honesty is not None:
            honesty.status = "rejected"
            return []
        raise ValueError(f"unknown claim or honesty id: {item_id!r}")


def to_dict(frame: Frame) -> dict:
    return dataclasses.asdict(frame)


def parse_schema_version(d: dict, default: int) -> int:
    """Read a persisted ``schema_version`` strictly.

    A missing key means a pre-field artifact → treat as ``default`` (back-compat).
    A present value must be a real ``int`` — ``bool`` and non-int types (float,
    str, ``None``) are rejected rather than silently coerced (e.g. plain
    ``int(1.9)`` would truncate to ``1`` and ``int(True)`` would yield ``1``), so
    a malformed version surfaces as a clean error instead of loading as current.
    Shared by the frame and plan engines (the persistence twins).
    """
    if "schema_version" not in d:
        return default
    v = d["schema_version"]
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"schema_version must be an integer, got {v!r}")
    return v


def from_dict(d: dict) -> Frame:
    claims = [
        Claim(
            id=c["id"],
            kind=c["kind"],
            text=c["text"],
            origin=c.get("origin", "user"),
            status=c.get("status", "confirmed"),
            honesty_conditions=[
                HonestyCondition(
                    id=h["id"],
                    text=h["text"],
                    status=h.get("status", "proposed"),
                    instruction=h.get("instruction", ""),
                )
                for h in c.get("honesty_conditions", [])
            ],
            hard_questions=[
                HardQuestion(
                    id=q["id"],
                    text=q["text"],
                    resolved=q.get("resolved", False),
                    blocking=q.get("blocking", False),
                    resolution=q.get("resolution", ""),
                )
                # Tolerant of unknown keys the same way Claim is above (t2, issue
                # #53 issue-backlog-sweep): a v3-or-older frame predates
                # ``resolution`` (t4) and must not raw-TypeError on load.
                for q in c.get("hard_questions", [])
            ],
            links=list(c.get("links", [])),
            # v1 frames predate this field (#53 t1); default to "no instruction".
            instruction=c.get("instruction", ""),
        )
        for c in d.get("claims", [])
    ]
    vag = [
        Vagueness(
            id=v["id"],
            text=v["text"],
            kind=v["kind"],
            claim_id=v.get("claim_id"),
            resolved=v.get("resolved", False),
            resolution=v.get("resolution", ""),
            resolution_claim_id=v.get("resolution_claim_id"),
        )
        # Tolerant of unknown keys the same way Claim is above (t2) — see the
        # hard_questions comment just above for why this matters.
        for v in d.get("open_vagueness", [])
    ]
    scope_entries = [
        ScopeEntry(
            id=s["id"],
            surface=s["surface"],
            finding=s["finding"],
            seeds=list(s.get("seeds", [])),
        )
        for s in d.get("scope_entries", [])
    ]
    return Frame(
        slug=d["slug"],
        title=d["title"],
        # A 0.4.0 frame predates the field; treat it as the current schema.
        schema_version=parse_schema_version(d, SCHEMA_VERSION),
        status=d.get("status", "drafting"),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        claims=claims,
        open_vagueness=vag,
        # v1 frames predate this field (#53 t1); default to no scope entries.
        scope_entries=scope_entries,
    )
