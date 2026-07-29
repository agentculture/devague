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
# Claim.revisions (t6, issue #84 — the `amend` move) is added WITHOUT a bump:
# it is purely additive with a `default_factory=list`, and `from_dict` below
# loads it tolerantly (`c.get("revisions", [])`), so a v4 frame written before
# t6 still loads cleanly with an empty revision trail.
# v5 (issue #97 t1) adds Frame.lapses / LapseRecord — the Reasoning Degradation
# Ledger. This DOES need a real bump (unlike Claim.revisions above): save()
# re-stamps schema_version and to_dict only serializes known dataclass fields,
# so an older v4-labeled binary reading a v5 frame and re-saving it would
# silently drop every filed lapse (the scope_entries v2 precedent, c17/h12).
SCHEMA_VERSION = 5

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

# The Reasoning Degradation Ledger's starting vocabulary (issue #97 t1). Unlike
# every other vocabulary tuple above, this one is expected to grow/retire over
# time as dogfooding surfaces new degradation shapes — see LapseRecord's
# __post_init__ docstring for why that means `code` is validated at the filing
# path (Frame.add_lapse), never here at load/construction time.
LAPSE_CODES = (
    "assumption-for-measurement",
    "grader-unverified",
    "control-absent",
    "n-below-claim",
    "instrument-changed-mid-series",
    "provenance-missing",
)
LAPSE_STATUSES = ("proposed", "approved", "rejected")


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
class ClaimRevision:
    """A superseded ``(text, kind)`` pair, recorded when a claim is amended.

    ``amend`` corrects a claim WITHOUT churning its id (issue #84) — but the
    frame is meant to be an evidence trail, so the value it had before the
    amend is kept here rather than silently overwritten. This is
    deliberately a *lightweight* marker, not a full audit log: it captures
    only the two fields ``Frame.amend_claim`` can change, plus an optional
    operator-authored ``reason``, and carries no timestamp or actor (no
    other Frame entity does either). A full revision history keyed by time
    would be a schema change; this is not one — it is a plain list field
    with a ``default_factory``, so older frames simply load with ``[]``.
    """

    text: str
    kind: str
    reason: str = ""


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
    # Prior (text, kind) pairs superseded by `Frame.amend_claim` (t6, #84), in
    # chronological order (most recent supersession last). Empty for a claim
    # that has never been amended — the common case, and every claim
    # predating t6.
    revisions: list[ClaimRevision] = field(default_factory=list)

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
class LapseRecord:
    """A filed reasoning-degradation lapse (issue #97) — the Reasoning
    Degradation Ledger's record shape, mirroring ``DeviationRecord``
    (:mod:`devague.delivery`): prefix-generic id minting via ``Frame._next``,
    origin-driven initial status, append-only with no delete path.

    ``code`` deliberately refines that chassis pattern (c21): it is validated
    at the *filing* path (``Frame.add_lapse``), NOT here in
    ``__post_init__``. Every other enum-like field in this module validates
    in ``__post_init__``, which also means it validates at *load* time
    (``from_dict`` constructs the dataclass directly) — correct for
    ``kind``/``origin``/``status`` vocabularies that never retire, but wrong
    for lapse codes: retiring a code after a dogfood cycle must not brick
    every frame that ever filed it. ``status`` and ``origin`` still validate
    here — they never retire.

    ``refs`` is stored verbatim as free text (task/claim ids, prose, or
    nothing) and is never validated — unlike ``ScopeEntry.seeds``, which
    checks its ids against the frame.
    """

    id: str
    code: str
    what: str
    skipped_check: str = ""
    refs: list[str] = field(default_factory=list)
    origin: str = "user"  # user | llm
    status: str = "approved"  # proposed | approved | rejected

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"unknown lapse origin: {self.origin!r}")
        if self.status not in LAPSE_STATUSES:
            raise ValueError(f"unknown lapse status: {self.status!r}")
        # `code` is NOT validated here on purpose — see the class docstring
        # and Frame.add_lapse.


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
    # The Reasoning Degradation Ledger (issue #97 t1, schema v5). Append-only:
    # no amend, no delete — the only post-filing mutation is set_lapse_status.
    lapses: list[LapseRecord] = field(default_factory=list)

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

    def amend_claim(
        self,
        claim_id: str,
        *,
        text: Optional[str] = None,
        kind: Optional[str] = None,
        reason: str = "",
    ) -> tuple[Claim, bool]:
        """Correct a claim's ``text`` and/or ``kind`` in place (issue #84).

        Unlike reject-and-recapture, amending never changes the claim's id,
        so its honesty conditions, hard questions, ``instruction``, and any
        scope-entry ``seeds`` that cite this id all keep pointing at
        something real — the whole point of the move. ``origin`` is never
        touched here: correcting what a claim says is not the same fact as
        who originally proposed it, and there is no flag that can reach it.

        Amending a claim that is currently ``confirmed`` flips it back to
        ``proposed`` — the same re-confirm rule ``interrogate --instruction``
        already applies to a change of that weight (the issue calls this
        "good behaviour and the right precedent"). Returns ``(claim,
        flipped)`` so the caller can echo the transition the same way
        ``interrogate.py``'s ``_apply_instruction`` does; ``flipped`` is
        ``False`` for a claim that was already ``proposed``/``rejected``.

        The superseded ``(text, kind)`` pair is appended to
        ``claim.revisions`` (with ``reason``, if given) rather than
        discarded — the frame is an evidence trail, not just current state.

        Raises ``ValueError`` if the claim id is unknown, if neither
        ``text`` nor ``kind`` is given (nothing to amend), or if ``kind``
        names an unknown claim kind.
        """
        claim = self.find_claim(claim_id)
        if claim is None:
            raise ValueError(f"unknown claim id: {claim_id!r}")
        if text is None and kind is None:
            raise ValueError("amend requires a new text and/or a new kind")
        if kind is not None and kind not in CLAIM_KINDS:
            raise ValueError(f"unknown claim kind: {kind!r}")
        claim.revisions.append(ClaimRevision(text=claim.text, kind=claim.kind, reason=reason))
        if text is not None:
            claim.text = text
        if kind is not None:
            claim.kind = kind
        flipped = claim.status == "confirmed"
        if flipped:
            claim.status = "proposed"
        return claim, flipped

    def find_honesty(self, hid: str) -> Optional[HonestyCondition]:
        return next((h for h in self._all_honesty() if h.id == hid), None)

    def find_hard_question(self, qid: str) -> Optional[HardQuestion]:
        """Look up a claim-attached hard question by id, across every claim.

        Mirrors ``find_claim``/``find_honesty`` — added so ``add_scope_entry``
        can validate a ``q*`` seed and ``render.spec_md`` can render one
        (issue #84's "smaller, related gap": ``scope --seeds`` refused
        question ids even though the ``/scope`` routing table sends a
        "needs a user decision" finding to ``question`` rather than
        ``capture``, leaving that branch's provenance unlinkable). Two
        independent things mint ``qN`` ids in this tool — claim-attached
        hard questions (this method) and the separate durable
        ``.devague/questions/`` artifact driven by ``devague question`` —
        and they can collide (both start counting at ``q1``) because they
        are independent counters. This method only ever searches
        ``Frame.claims[*].hard_questions``, the same restriction
        ``resolve_hard_question`` documents; it cannot disambiguate the two
        namespaces, only search the one it is documented to search.
        """
        return next((q for q in self._all_hard_questions() if q.id == qid), None)

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
        """Record a scope-exploration finding, optionally citing what it seeded.

        ``seeds`` may name a claim id (``c*``) or a claim-attached hard
        question id (``q*``, issue #84's "smaller, related gap") —
        validated against :meth:`find_claim` first and
        :meth:`find_hard_question` second, so an id resolving to either is
        accepted. This is the branch the ``/scope`` skill's routing table
        sends a "genuinely unknown, needs a user decision" finding down (the
        ``question`` move rather than ``capture``); before this, that
        finding's provenance link was unrecordable. Any id resolving to
        neither is refused (the error text says "claim" for both cases —
        this is the one seam that already validated seed ids before ``q*``
        was accepted, and the CLI's accompanying hint, "run 'devague show'
        to see valid claim ids", is unchanged).
        """
        seed_ids = list(seeds) if seeds else []
        for sid in seed_ids:
            if self.find_claim(sid) is None and self.find_hard_question(sid) is None:
                raise ValueError(f"unknown seed claim id: {sid!r}")
        entry = ScopeEntry(
            id=self._next(self.scope_entries, "s"),
            surface=surface,
            finding=finding,
            seeds=seed_ids,
        )
        self.scope_entries.append(entry)
        return entry

    def find_scope_entry(self, sid: str) -> Optional[ScopeEntry]:
        return next((e for e in self.scope_entries if e.id == sid), None)

    def amend_scope_entry(self, entry_id: str, finding: str) -> ScopeEntry:
        """Replace a scope entry's ``finding`` in place (issue #84).

        Before this move, correcting a scope finding meant recording a
        *second* entry that says "supersedes s18" — the exported spec then
        carries both the wrong entry and its correction, and the reader has
        to notice the word "supersedes". Amending replaces the finding in
        place instead: same id, same ``surface``, same ``seeds`` — nothing
        else about the entry changes. (Unlike ``amend_claim``, a scope entry
        carries no ``status``/``origin`` to protect and nothing else in the
        method's contract calls for a revision trail here — see the CLI
        module for that decision.)

        Raises ``ValueError`` if the entry id is unknown or ``finding`` is
        empty.
        """
        entry = self.find_scope_entry(entry_id)
        if entry is None:
            raise ValueError(f"unknown scope entry id: {entry_id!r}")
        if not finding:
            raise ValueError("amend requires a new finding")
        entry.finding = finding
        return entry

    def add_lapse(
        self,
        code: str,
        what: str,
        skipped_check: str = "",
        refs: Optional[list[str]] = None,
        origin: str = "user",
    ) -> LapseRecord:
        """File a reasoning-degradation lapse (issue #97).

        ``code`` is validated here — the filing path — against
        :data:`LAPSE_CODES`, fail-closed with a clear error naming the
        unknown code. This is deliberately NOT in ``LapseRecord.__post_init__``
        (see that class's docstring): a code retired after this call already
        succeeded must still be loadable via ``from_dict``, which constructs
        ``LapseRecord`` directly and never goes through this method.

        ``origin`` drives the initial ``status`` exactly like
        ``Delivery.add_deviation``: ``llm`` lands ``proposed`` (needs a human
        ``set_lapse_status`` to approve), ``user`` auto-approves. ``refs`` is
        stored verbatim free text, never validated (unlike
        :meth:`add_scope_entry`'s seed ids).
        """
        if code not in LAPSE_CODES:
            raise ValueError(f"unknown lapse code: {code!r}")
        status = "proposed" if origin == "llm" else "approved"
        rec = LapseRecord(
            id=self._next(self.lapses, "l"),
            code=code,
            what=what,
            skipped_check=skipped_check,
            refs=list(refs) if refs else [],
            origin=origin,
            status=status,
        )
        self.lapses.append(rec)
        return rec

    def find_lapse(self, lid: str) -> Optional[LapseRecord]:
        return next((r for r in self.lapses if r.id == lid), None)

    def set_lapse_status(self, lid: str, status: str) -> bool:
        """Set a lapse record's status, failing closed on a typo'd/unknown value.

        The only mutator a filed lapse ever gets — there is no amend or
        delete API (c20): a wrong lapse is rejected and refiled, never
        edited in place. Mirrors :meth:`devague.delivery.Delivery.set_status`:
        validates ``status`` against :data:`LAPSE_STATUSES` *before* touching
        the record, so an invalid string never mutates anything.
        """
        if status not in LAPSE_STATUSES:
            raise ValueError(f"unknown lapse status: {status!r}")
        rec = self.find_lapse(lid)
        if rec is not None:
            rec.status = status
            return True
        return False

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
            revisions=[
                ClaimRevision(
                    text=r["text"],
                    kind=r["kind"],
                    reason=r.get("reason", ""),
                )
                # Pre-t6 frames (#84) predate this field entirely; default to
                # an empty trail, the same tolerant pattern as hard_questions
                # above.
                for r in c.get("revisions", [])
            ],
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
    lapses = [
        LapseRecord(
            id=r["id"],
            code=r["code"],
            what=r["what"],
            skipped_check=r.get("skipped_check", ""),
            refs=list(r.get("refs", [])),
            origin=r.get("origin", "user"),
            status=r.get("status", "approved"),
        )
        # Pre-v5 frames predate this field entirely (issue #97 t1); default to
        # an empty ledger. `code` is deliberately NOT re-validated here — a
        # retired code must still load (see LapseRecord's docstring).
        for r in d.get("lapses", [])
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
        # v5 frames only (issue #97 t1); default to no lapses.
        lapses=lapses,
    )
