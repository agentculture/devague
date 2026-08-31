"""``devague learn`` — teach the working-backwards method and the moves."""

from __future__ import annotations

import argparse

from devague import __version__
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._output import emit_result

MOVES = {
    "scope": (
        "Record an explored surface + finding as first-class state (optional "
        "pre-frame leg; --seeds links a finding to the claim ids (c*) or "
        "claim-attached hard-question ids (q*) it seeded; --amend SID --finding "
        "TEXT replaces an entry's finding in place — no revision trail, unlike "
        "claim amend)."
    ),
    "new": "Start a frame from the announcement (pretend it shipped).",
    "capture": "Record and classify a claim (audience, after_state, boundary, ...).",
    "amend": (
        "Correct a claim's text and/or kind without id churn — keeps its honesty "
        "conditions, instruction, and inbound scope --seeds references; a "
        "confirmed claim flips back to proposed on change."
    ),
    "interrogate": (
        "Pressure-test a claim: honesty conditions, hard questions, contradictions; "
        "'interrogate <cN> --resolve <qN> --decision TEXT' closes out a blocking "
        "hard question (a USER decision, like confirm/park --resolve)."
    ),
    "confirm": (
        "Confirm one or more claims/honesty conditions in one transactional call "
        "(user-only — no fabricated rigor), or apply decisions from a "
        "'--from-review' file."
    ),
    "reject": (
        "Reject one or more claims/honesty conditions, transactionally; rejecting "
        "a claim cascades onto its still-live honesty conditions/hard questions "
        "(echoed as '(also rejected: ...)', and as a 'cascaded' key in --json)."
    ),
    "review": (
        "List every proposed (unconfirmed) claim + honesty condition for "
        "human review (read-only)."
    ),
    "question": "Record, list, or resolve a pending user decision (durable working state).",
    "park": (
        "Move uncertainty into first-class open vagueness instead of forcing an "
        "answer, or close a decided one with 'park --resolve VID --decision TEXT'."
    ),
    "converge": "Check whether the frame is solid enough to export a spec.",
    "export": "Write the buildable spec — only once the frame converges.",
    "status": "Report where the frame stands + the recommended next move (read-only).",
    "show": "Render the Announcement Frame.",
    "list": "List frames.",
    "lapse": (
        "File a reasoning-degradation lapse against the current frame "
        "('lapse \"<what>\" --code <code>', --origin llm lands proposed); "
        "'--confirm/--reject <lN>' resolves a proposed one (user-only); "
        "'--list [--json]' shows every filed lapse."
    ),
    "oblige": (
        "File a behavioral obligation against a claim ('oblige <cN> --seam "
        "<seam> --behavior <behavior>', --origin llm lands proposed); "
        "'--confirm/--reject <oN>' resolves a proposed one (user-only); "
        "'--list [--json]' shows every filed obligation, with a drift marker "
        "when the claim's text changed since filing."
    ),
    "evidence": (
        "File an evidence record against the current/named plan's delivery "
        "ledger ('evidence --obligation <oN> --test <ref> --behavior <text> "
        "--contract <text> --type <type> --strength <level> --basis <text> "
        "--outcome pass|fail [--run-commit <sha> --run-timestamp <ts>]', "
        "--origin llm lands proposed); a run reference is required at "
        "execution/sensitivity strength; '--confirm/--reject <eN>' resolves a "
        "proposed one (user-only); '--list [--json]' shows every filed record."
    ),
    "delta": (
        "File, list, supersede, retract, or adjudicate a behavioral delta "
        "against the current/named plan's delivery ledger ('delta --kind "
        "added|amended|removed --behavior <text> --caused-by <ref> "
        "[--caused-by <ref> ...] [--evidence <ref> ...]', --origin llm lands "
        "proposed); --caused-by refs are validated by shape (claim ids "
        "against the live frame, deviation ids against approved deviations, "
        "delta ids against existing deltas — free-form text always passes); "
        "'--supersede <ref> [--replacement <ref>]' and '--retract <ref>' "
        "append supersession events without ever editing a record's content; "
        "'--confirm/--reject <bN>' resolves a proposed delta (user-only); "
        "'--list [--json]' shows every filed delta plus the trailing "
        "supersession-event log."
    ),
    "today": (
        "Project the current behavior of the app from the delivery ledger and "
        "write docs/current-spec.md (read-only over every store; '--json' "
        "emits the structured projection instead of the write confirmation)."
    ),
}

FIRST_QUESTION = "What's the announcement?"
SUPPORTING_PROMPT = (
    "Pretend this shipped successfully. What would you announce to users, "
    "teammates, or yourself?"
)

# The portable, runtime-agnostic operating contract for any assisting model
# (devague#19). The full version lives in the guidance doc; this is the core
# surfaced in every `learn`. These rules are what make convergence mean something.
#
# `docs/` is not shipped in the wheel (only the `devague` package is), and an
# installed devague is operated from an arbitrary repo — so a bare relative path
# wouldn't resolve for most consumers. The portable, always-resolvable reference
# is the canonical URL; the in-repo path is kept for contributors.
GUIDANCE_DOC_URL = "https://github.com/agentculture/devague/blob/main/docs/llm-guidance.md"
GUIDANCE_DOC_REPO_PATH = "docs/llm-guidance.md"

# What devague is NOT — the framing that keeps it from degrading into a form.
NOT_A = (
    "a wizard (no fixed prompt sequence)",
    "a scripted questionnaire (you don't read questions off a form)",
    "a PRD generator (it never invents content to fill a template)",
)

# Assign-to-workforce invocation guidance: when and how to fan out a converged
# plan's waves to a workforce. This is a cited skill convention, not an
# orchestration engine (devague#20). The three human gates ensure spec, plan,
# and PR pass human review.
ASSIGN_TO_WORKFORCE_GUIDANCE = {
    "title": "Assign-to-workforce: parallel plan execution",
    "when_to_fan_out": (
        "Once a plan converges (all targets covered, all tasks have acceptance "
        "criteria, dependency graph is acyclic), you can fan out its waves to "
        "parallel agents working in isolated git worktrees."
    ),
    "prerequisites": ("A converged plan with deterministic dependency waves (devague plan waves)."),
    "human_gates": (
        "The human approves at exactly three points: (1) the exported spec, "
        "(2) the implementation split plan (plan/tasks map, per-task "
        "agent/model assignment, go/no-go to workforce), and (3) the final PR. "
        "The human is NOT in the per-task worktree-merge loop."
    ),
    "worktree_isolation": (
        "Each task runs in an isolated git worktree (one per task per wave). "
        "This keeps file-contention safe: overlapping same-file changes "
        "surface as merge conflicts at reconcile time, not live races."
    ),
    "worktree_location": (
        "Put every worktree under one repo-owned root beside the repo "
        "directory: <parent-of-repo>/.worktrees.<repo-name>/agent-<task-id>. "
        "Resolve it, don't hardcode it — both steps, since an undefined "
        'repo_root silently yields the in-repo path "./.worktrees.": '
        'repo_root=$(git rev-parse --show-toplevel) then wt_root="$(dirname '
        '"$repo_root")/.worktrees.$(basename "$repo_root")". A shared '
        "../worktrees/ collides across repos and plans (task ids restart at "
        "t1) and looks deletable to anyone else cleaning up; an in-repo path "
        "gets swept into your PR by git add -A and destroyed by git clean "
        "-fdx. Remove only the worktrees you created — never the root itself."
    ),
    "main_agent_merge_gate": (
        "The main agent gates each subagent worktree merge with TDD: tests "
        "pass before AND after merge. No human per-task merge decision."
    ),
    "tdd_acceptance_criteria": (
        "Each task carries TDD acceptance criteria (tests first) scoped "
        "tightly enough for a simpler/cheaper model to build. The tests "
        "validate that the task was built correctly — no re-deriving the "
        "design needed."
    ),
    "not_orchestration": (
        "devague itself does not orchestrate: it does not spawn subagents, "
        "manage worktrees, mark tasks done, or pick a backend. Orchestration "
        "is a cited skill convention (assign-to-workforce), not part of the "
        "deterministic CLI."
    ),
}

# The progressive evidence strength ladder (weakest first), structurally
# identical to devague.delivery.STRENGTH_LEVELS — kept as a local literal
# rather than an import so `learn` never depends on the delivery module (the
# same reason MOVES/STAGES above are hand-authored rather than introspected).
# The agent assesses which rung a check actually reached; the CLI only
# records what it's told — it never upgrades a rung on its own.
STRENGTH_LADDER = (
    ("coverage", "a test exists that exercises the obligated behavior (no run required)"),
    (
        "fidelity",
        "the test asserts the promised behavior itself, not just that it runs (no run required)",
    ),
    (
        "execution",
        "the test currently passes — requires a run reference (--run-commit/--run-timestamp)",
    ),
    (
        "sensitivity",
        "the test would likely fail if the behavior broke — requires a run reference",
    ),
)

# Behavioral validation: obligations, evidence, deltas, and the today
# projection (bvts). This is the loop that plants a checkable promise on the
# think/plan legs, checks it agent-side once a wave merges (the
# validate-delivery leg — the seventh leg, between deviate and
# summarize-delivery), files what was found with verbatim outcomes, and lets
# the user adjudicate before the current-behavior projection is rendered.
BEHAVIORAL_VALIDATION_GUIDANCE = {
    "title": "Behavioral validation: obligations, evidence, deltas, and today",
    "plant_obligations": (
        "Plant obligations early, while you still remember why they matter — "
        "'oblige <cN> --seam <seam> --behavior <behavior>' ties a claim to a "
        "checkable seam on the think leg; 'plan oblige <tN> --criterion N "
        "--seam <seam> --behavior <behavior>' does the same for a task's "
        "acceptance criterion on the plan leg. Both land 'proposed' under "
        "--origin llm and need an explicit user '--confirm', same as every "
        "other LLM proposal."
    ),
    "run_tests": (
        "Once a wave's worktrees merge (the validate-delivery leg — after "
        "assign-to-workforce, before summarize-delivery), run the confirmed "
        "plan's behavioral tests agent-side. devague itself never runs a test "
        "(#20) — this is read-only against the codebase, and it never edits "
        "code to make a test pass."
    ),
    "file_evidence": (
        "File one evidence record per obligation checked: 'evidence "
        "--obligation <oN> --test <ref> --behavior <text> --contract <text> "
        "--type <type> --strength <level> --basis <text> --outcome pass|fail "
        "[--run-commit <sha> --run-timestamp <ts>]'. A failing outcome is "
        "filed exactly like a passing one — never smoothed, reworded, or "
        "omitted."
    ),
    "file_deltas": (
        "When the merged behavior added, amended, or removed something "
        "relative to the plan, file a delta with provenance: 'delta --kind "
        "added|amended|removed --behavior <text> --caused-by <ref> "
        "[--caused-by <ref> ...] [--evidence <ref> ...]'. --caused-by points "
        "back to the claim, approved deviation, or prior delta that actually "
        "motivated it — never a bare assertion with nothing behind it."
    ),
    "adjudicate": (
        "Obligations, evidence, and deltas all stay 'proposed' under --origin "
        "llm until the user runs '--confirm' or '--reject' on them — the same "
        "anti-fabrication rule as claims and tasks, now applied to what "
        "actually ran, not just what was planned."
    ),
    "render_today": (
        "'devague today' projects the live delivery ledger into "
        "docs/current-spec.md — what the app actually does right now, "
        "read-only over every store. Render it after adjudication so the "
        "projection reflects confirmed evidence and deltas, not proposals "
        "still awaiting a decision."
    ),
    "strength_ladder": STRENGTH_LADDER,
}

# --- `devague learn review` — the reviewer seam (bvts t14) -------------------
#
# Written the same way the `skills` topic is (0.12.0): instructions the
# *reviewing agent* follows. devague itself never reviews anything — it has no
# opinion about a diff, files no finding of its own, and adjudicates nothing
# (#20). Everything below is method the reviewer executes, routed back through
# the same deterministic moves everyone else uses.
#
# Self-containment is a hard requirement, not a nicety: a gate-3 reviewer may
# arrive with no prior devague context at all, so every command the method
# leans on is enumerated in REVIEW_COMMANDS with the exact syntax read off the
# real parsers, and pinned by a test that runs each one's `--help`.

# The reasoning-degradation lapse codes, quoted for the reviewer. Kept as a
# local literal for the same reason STRENGTH_LADDER above is — `learn` never
# imports a domain module — and pinned equal to `devague.frame.LAPSE_CODES` by
# a test, so the two cannot drift silently.
LAPSE_CODES_FOR_REVIEW = (
    "assumption-for-measurement",
    "grader-unverified",
    "control-absent",
    "n-below-claim",
    "instrument-changed-mid-series",
    "provenance-missing",
)

# Every devague command the review method relies on: (argv path, what it is
# for). The argv path is the command only — flags live in the purpose text, so
# the pin can run `<path> --help` verbatim.
REVIEW_COMMANDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("oblige",),
        "'devague oblige --list [--json]' — the frame-side obligations filed "
        "against claims: seam, owed behavior, status, and a 'drifted' marker "
        "when the claim's text changed after the obligation was filed. This "
        "list is the audit checklist.",
    ),
    (
        ("plan", "oblige"),
        "'devague plan oblige --list [--json]' — the plan-side twin: "
        "obligations filed against a task's acceptance criterion. Audit both "
        "lists; a behavior can be obligated on either leg.",
    ),
    (
        ("converge",),
        "'devague converge [--json]' — re-run the frame gate to read its "
        "warnings. An obligation with no approved evidence is reported as "
        "untested, in as many words. Warnings never gate, so the run may have "
        "shipped with them standing: unmet obligations arrive precomputed for "
        "you.",
    ),
    (
        ("plan", "converge"),
        "'devague plan converge [--json]' — the plan-side twin of the same "
        "untested-obligation warning, evaluated against the live frame.",
    ),
    (
        ("evidence",),
        "'devague evidence --list [--json]' — every filed evidence record: "
        "obligation ref, test ref, the recorded behavior text, the contract "
        "text, type, strength, basis, outcome, and the run reference "
        "(--run-commit / --run-timestamp) when one was required.",
    ),
    (
        ("delta",),
        "'devague delta --list [--json]' — every filed behavioral delta "
        "(added / amended / removed) with its --caused-by provenance and any "
        "--evidence refs, plus the trailing supersession-event log written by "
        "'--supersede <ref> [--replacement <ref>]' and '--retract <ref>'.",
    ),
    (
        ("deviate",),
        "'devague deviate --list [--json]' — the approved mid-run departures "
        "from the confirmed plan. A deviation's --affects names the claims "
        "whose earlier evidence may no longer describe what shipped.",
    ),
    (
        ("summary",),
        "'devague summary [--pr] [--json]' — the delivery summary whose "
        "Delivery Claims section renders each claim's confidence as its "
        "strength level, already reduced by any approved lapse that caps it. "
        "Read it as the claim being made, and audit the records behind it.",
    ),
    (
        ("status",),
        "'devague status [--json]' — the frame's standing plus the read-only "
        "staleness findings: deviations whose covered evidence was never "
        "re-validated, and evidence whose obligation no longer resolves.",
    ),
    (
        ("show",),
        "'devague show [--json]' — the frame itself: claims, honesty "
        "conditions, hard questions, parked vagueness, every filed lapse in "
        "any status, and contested-by markers.",
    ),
    (
        ("today",),
        "'devague today [--json]' — the projection of what the app actually "
        "does now, built from the delivery ledger. If it reads better than the "
        "records support, the records are what you audit.",
    ),
    (
        ("lapse",),
        '\'devague lapse "<what>" --code <code> [--ref <ref> ...] --origin '
        "llm' — file a finding as a proposed reasoning-degradation lapse. "
        "Codes: " + ", ".join(LAPSE_CODES_FOR_REVIEW) + ". It lands 'proposed' "
        "and stays there until the human runs '--confirm <lN>' or "
        "'--reject <lN>'.",
    ),
)

REVIEW_GUIDANCE = {
    "title": "Review as audit: verifying that the filed evidence is honest",
    "premise": (
        "Gate 3 is a code review with a ledger attached. The run has already "
        "filed obligations, evidence, deltas, and lapses; your job is not to "
        "re-derive what should have been tested but to verify that what was "
        "filed is honest. These are instructions for you, the reviewing agent "
        "— the CLI reviews nothing, files no finding of its own, and "
        "adjudicates nothing."
    ),
    "checklist": (
        "Start from the obligations: they are the ready-made checklist. Every "
        "obligation names a seam and the behavior owed at it, so the set of "
        "things this run promised to behave a certain way is already "
        "enumerated for you — on the frame side and on the plan side both. "
        "The unmet ones arrive precomputed: an obligation with no approved "
        "evidence surfaces as a convergence warning that says untested in as "
        "many words, on the frame gate and the plan gate alike. Those "
        "warnings never gate anything, so they can and do survive into a "
        "merged run; reading them is the cheapest part of the audit. That "
        "narrows your job to the expensive part: for the obligations that DO "
        "carry evidence, is the evidence honest? The enumerated records are a "
        "floor, not a ceiling — a behavior nobody obligated, an evidence "
        "record nobody filed, a risk nobody named is still a finding, and you "
        "raise it exactly like the rest."
    ),
    "fidelity_audit": (
        "The heart of the audit is the three-way comparison, run once per "
        "evidence record. Open the test the record names. Behavioral tests are "
        "found by the repo's convention — a pytest marker such as "
        "@pytest.mark.behavioral (run with 'pytest -m behavioral'), or a "
        "dedicated folder such as tests/behavioral/ — and if neither exists "
        "the test ref itself is the locator. Then compare three texts: (1) the "
        "claim text the obligation hangs off, (2) the recorded behavior text "
        "on the evidence record, and (3) what the test source actually "
        "asserts. All three must say the same thing. Recorded behavior text "
        "the test does not support means the record is wrong, whatever its "
        "outcome says — a test that merely imports the module and exits, or "
        "asserts a return code while the record claims a rendered value, is a "
        "coverage-grade test wearing a fidelity-grade description. Read the "
        "test source as it stands in this PR, never the recorded text alone: "
        "the recorded text is the thing under audit, so accepting it as its "
        "own proof is the one move that guarantees you find nothing."
    ),
    "strength_verification": (
        "Check each claimed rung against the basis recorded beside it, one "
        "record at a time: coverage (a test exercising the behavior exists), "
        "fidelity (it asserts the promised behavior itself), execution (it "
        "currently passes), sensitivity (it would fail if the behavior broke). "
        "A level is never accepted above its basis — 'the test exists' does "
        "not earn fidelity, and a passing run does not earn sensitivity "
        "without something showing the test can fail. Re-run what claims "
        "execution rather than trusting the record, and check the run "
        "reference (--run-commit / --run-timestamp) against the PR head: a run "
        "reference behind the PR head for behavior this PR touched demotes the "
        "execution claim, because passing long ago is not passing now. A "
        "failing outcome that was filed as a fail is the ledger working, not a "
        "finding; a failing behavior with a passing record is the finding."
    ),
    "delta_completeness": (
        "Audit deltas in both directions, against the diff and the ledger you "
        "actually read — not against memory of what the plan said. Forward: a "
        "behavioral code change in the diff with no filed delta is an "
        "undeclared behavioral change. Backward: a filed delta with no "
        "corresponding code change in the diff is a fabricated delivery. Both "
        "are findings and both are common — the first from a task that grew in "
        "flight, the second from a record written from intent rather than from "
        "the merge. Check each delta's --caused-by provenance resolves to "
        "something real, and read the supersession-event log: a record marked "
        "superseded still counts, and its replacement is what you audit."
    ),
    "propose_never_confirm": (
        "You propose; the human at gate 3 adjudicates. A finding lands as a PR "
        "comment, as a proposed lapse (--origin llm — 'grader-unverified' when "
        "the pass/fail judgment itself was never verified, "
        "'provenance-missing' when a record's own provenance cannot be "
        "checked), or as a superseding evidence record filed at the strength "
        "you can actually defend. Never confirm your own finding, exactly as "
        "no agent confirms its own claim: an approved reviewer-filed lapse "
        "mechanically caps the affected claim's renderable strength wherever "
        "it is rendered, which is real consequence and therefore a human "
        "decision. Reviewer findings enter the same append-only discipline as "
        "everything else in the ledger — a finding you retract under pushback "
        "is retracted on the record, not deleted, so the retraction is as "
        "readable later as the finding was."
    ),
}


def _review_text() -> str:
    """Render the reviewer-seam topic. Self-contained by contract: it names
    every command it relies on, with the syntax pinned against the real CLI.
    """
    parts = [
        REVIEW_GUIDANCE["title"],
        "=" * len(REVIEW_GUIDANCE["title"]),
        "",
        REVIEW_GUIDANCE["premise"],
        "",
        "1. The checklist is already written (obligations)",
        REVIEW_GUIDANCE["checklist"],
        "",
        "2. The fidelity audit — the three-way comparison",
        REVIEW_GUIDANCE["fidelity_audit"],
        "",
        "3. Strength verification",
        REVIEW_GUIDANCE["strength_verification"],
        "",
        "4. Delta completeness, both directions",
        REVIEW_GUIDANCE["delta_completeness"],
        "",
        "5. Propose, never confirm",
        REVIEW_GUIDANCE["propose_never_confirm"],
        "",
        "Commands this audit uses (every one of them, with its syntax):",
    ]
    for command, purpose in REVIEW_COMMANDS:
        parts.append(f"  {' '.join(command)}")
        parts.append(f"    {purpose}")
    parts += [
        "",
        f"Full portable guidance for any assisting model:\n  {GUIDANCE_DOC_URL}",
    ]
    return "\n".join(parts)


def _review_payload() -> dict[str, object]:
    """Structured reviewer-seam payload for `--json`."""
    return {
        **dict(REVIEW_GUIDANCE),
        "commands": [
            {"command": list(command), "purpose": purpose} for command, purpose in REVIEW_COMMANDS
        ],
        "summary": _review_text(),
    }


# The anti-fabrication rules. Agent-agnostic: repo-specific agreements live in
# your agent's main instruction file (AGENTS.md, CLAUDE.md, a system prompt, …),
# not here.
OPERATING_RULES = (
    "LLM proposals stay proposed — capture your own ideas with --origin llm; "
    "never confirm your own proposal. Confirmation is a user-only decision.",
    "Honesty conditions route through the user — propose freely with "
    "'interrogate --honesty'; the user owns whether each one holds.",
    "Park real unknowns instead of papering over them — 'park' a genuine "
    "unknown rather than writing confident prose that hides the gap. Once it's "
    "decided, close it out with 'park --resolve VID --decision TEXT' instead of "
    "leaving it parked or hand-editing state — the item stays on record with "
    "its resolution and drops out of the gate.",
    "Blocking hard questions route through the user too — a hard question "
    "raised 'blocking' via interrogate stays open until decided; close it out "
    "with 'interrogate CID --resolve QID --decision TEXT' (the claim-level twin "
    "of 'park --resolve') instead of deleting the question or hand-editing state.",
    "Converge, don't vibe — 'export' is gated on 'converge'; resolve every "
    "listed gap instead of declaring readiness on a hunch.",
    "Order is adaptive — the ten stages are an artifact shape, not a mandatory "
    "conversation order; capture what the user gives you and circle back.",
    "Obligations and evidence follow claims and honesty conditions into the "
    "same proposed/confirmed lifecycle — 'oblige' and 'evidence' under "
    "--origin llm land 'proposed' and need an explicit user '--confirm'; never "
    "self-confirm an obligation or evidence record you filed.",
    "Evidence outcomes are recorded verbatim — a failing test is filed as "
    "'--outcome fail', exactly as filed, never smoothed into a pass, reworded "
    "softer, or left out of the run's evidence entirely. Strength (coverage / "
    "fidelity / execution / sensitivity) is what you actually assessed and the "
    "CLI records beside it — never claim a higher rung than the check you ran, "
    "and never skip the run reference execution/sensitivity require.",
    "Unmet is unmet, and warnings never gate — an obligation with no approved "
    "evidence surfaces as a convergence warning on the frame or plan, never a "
    "blocker; it does not stop 'export', 'plan converge', or 'plan export'. "
    "The fix is filing real evidence, never silencing or rationalizing away "
    "the warning.",
)

# The canonical guided sequence (devague#4). The engine is move-driven, not a
# rigid wizard — this is the recommended arc, with the move that advances each.
STAGES = [
    ("Announcement", "what are we saying shipped?", "new"),
    ("Audience", "who needs this?", "capture --kind audience"),
    ("After", "what changed for them?", "capture --kind after_state"),
    ("Matter", "why is it worth doing?", "capture --kind why_it_matters"),
    ("Before", "what pain made this necessary?", "capture --kind before_state"),
    ("Honest", "what must be true for the announcement to be honest?", "interrogate --honesty"),
    ("FAQ", "what hard questions remain?", "interrogate --hard-question"),
    ("Boundaries", "what are we not promising?", "capture --kind boundary"),
    ("Success", "how will we know?", "capture --kind success_signal"),
    ("Spec", "what should be built?", "converge -> export"),
]

# The optional pre-frame exploration lead-in (#53 t3/t10). It precedes the ten
# numbered stages above rather than replacing one of them — optional-but-
# recommended, not mandatory: recommended when the idea touches an existing
# codebase, freely skippable for a small idea (the method's recorded non-goal:
# devague never becomes a wizard with a fixed first stage).
SCOPE_STAGE = {
    "name": "Scope (optional, before Announcement)",
    "prompt": "what does this idea touch, and what should it not touch?",
    "move": 'scope "<surface>" --finding "<text>" [--seeds <claim-id-or-hard-question-id> ...]',
    "loop": (
        "Explore read-only first (no CLI moves while surveying), then record "
        "each surveyed surface + finding with 'devague scope'; pass --seeds "
        "with the claim ids (c*) or claim-attached hard-question ids (q*) a "
        "finding goes on to seed so the frame's boundary / non_goal / assumption "
        "claims cite what was actually explored. 'scope --amend SID --finding "
        "TEXT' corrects an entry's finding in place afterward."
    ),
    "fan_out": (
        "How to explore: 4 or fewer candidate surfaces — explore them yourself, "
        "inline, serially. 5 or more — fan out one read-only exploration "
        "subagent per surface (or tight cluster), defaulting every subagent to "
        "the smaller tier, sonnet. Subagents explore and report; they never run "
        "a devague move — the main agent alone runs every capture/scope/"
        "question/park call, from the subagents' reported evidence, so "
        "provenance stays in one place."
    ),
    "recommended_when": (
        "Recommended when the idea touches an existing codebase or ecosystem — "
        "grounds convergence in explored territory instead of guesses."
    ),
    "optional_by_size": (
        "Optional-by-size, not a mandatory first stage: a small idea can skip "
        "straight to 'new' (recorded non-goal — devague never becomes a wizard)."
    ),
}

# The optional --instruction flags (frame side: #53 t4; plan side: #53 t5) ride
# alongside the capture/interrogate stages above and carry through to the plan
# handoff verbatim — noted once here rather than cluttering every stage line.
INSTRUCTION_FLAGS_NOTE = (
    "Any claim or honesty condition can also carry an optional --instruction —\n"
    '  capture --kind <kind> "<text>" --instruction "<text>"\n'
    '  interrogate <id> --honesty "<text>" --instruction "<text>"\n'
    "verbatim text on how to verify or implement it; leave it empty rather than\n"
    "invent one to fill a gate warning. It carries to the plan handoff:\n"
    '  devague plan task "<summary>" --instruction "<text>"    (at creation)\n'
    '  devague plan instruct <tN> "<text>"                     (on an existing task)\n'
    "so a task's working guidance reaches the workforce brief unchanged."
)

_TEXT = (
    "devague turns a vague idea into a buildable spec by working backwards.\n\n"
    f"First question: {FIRST_QUESTION}\n"
    f"  {SUPPORTING_PROMPT}\n\n"
    "Start from that announcement, then build an Announcement Frame by capturing\n"
    "claims, interrogating them, parking what's still vague, and converging.\n"
    "The arc emerges from the moves; it is not a fixed wizard. You (the agent)\n"
    "choose the next move; devague tracks state. LLM-proposed claims and honesty\n"
    "conditions stay 'proposed' until the user confirms them.\n\n"
    "This serves two audiences: the operator (you) driving devague move by move,\n"
    "and the human who owns every confirm/reject decision — on claims, on\n"
    "obligations, on evidence outcomes, on deltas — and the go/no-go at each gate.\n\n"
    "Optional lead-in — scope exploration (recommended when the idea touches an\n"
    "existing codebase; skip freely for small ideas — not a mandatory first stage):\n"
    f"  {SCOPE_STAGE['prompt']}  [devague {SCOPE_STAGE['move']}]\n"
    f"  {SCOPE_STAGE['loop']}\n"
    f"  {SCOPE_STAGE['fan_out']}\n\n"
    "Guided stages (the recommended sequence — drive them with the moves):\n"
    + "\n".join(
        f"  {i:>2}. {name:<13} {prompt}  [{move}]"
        for i, (name, prompt, move) in enumerate(STAGES, 1)
    )
    + "\n\n"
    + INSTRUCTION_FLAGS_NOTE
    + "\n\nMoves:\n"
    + "\n".join(f"  {name:<11} {desc}" for name, desc in MOVES.items())
    + "\n\ndevague is NOT:\n"
    + "\n".join(f"  - {n}" for n in NOT_A)
    + "\n\nOperating rules (the anti-fabrication contract — do not violate):\n"
    + "\n".join(f"  - {r}" for r in OPERATING_RULES)
    + "\n\n"
    + "Assign-to-workforce: parallel plan execution via subagent-driven development\n"
    f"  When: {ASSIGN_TO_WORKFORCE_GUIDANCE['when_to_fan_out']}\n"
    f"  Prerequisites: {ASSIGN_TO_WORKFORCE_GUIDANCE['prerequisites']}\n"
    f"  Human gates (3): {ASSIGN_TO_WORKFORCE_GUIDANCE['human_gates']}\n"
    f"  Safety: {ASSIGN_TO_WORKFORCE_GUIDANCE['worktree_isolation']}\n"
    f"  Worktree location: {ASSIGN_TO_WORKFORCE_GUIDANCE['worktree_location']}\n"
    f"  Main agent: {ASSIGN_TO_WORKFORCE_GUIDANCE['main_agent_merge_gate']}\n"
    f"  TDD: {ASSIGN_TO_WORKFORCE_GUIDANCE['tdd_acceptance_criteria']}\n"
    f"  Scope: {ASSIGN_TO_WORKFORCE_GUIDANCE['not_orchestration']}\n"
    + "\n\n"
    + f"{BEHAVIORAL_VALIDATION_GUIDANCE['title']}\n"
    f"  Plant obligations: {BEHAVIORAL_VALIDATION_GUIDANCE['plant_obligations']}\n"
    f"  Run tests: {BEHAVIORAL_VALIDATION_GUIDANCE['run_tests']}\n"
    f"  File evidence: {BEHAVIORAL_VALIDATION_GUIDANCE['file_evidence']}\n"
    f"  File deltas: {BEHAVIORAL_VALIDATION_GUIDANCE['file_deltas']}\n"
    f"  Adjudicate: {BEHAVIORAL_VALIDATION_GUIDANCE['adjudicate']}\n"
    f"  Render today: {BEHAVIORAL_VALIDATION_GUIDANCE['render_today']}\n"
    "  Strength ladder (weakest first — assessed by you, recorded verbatim, "
    "never inflated):\n"
    + "\n".join(f"    - {level}: {desc}" for level, desc in STRENGTH_LADDER)
    + "\n\nReviewing a run (gate 3): 'devague learn review' emits the audit method —\n"
    "obligations as the checklist, the three-way fidelity comparison, strength\n"
    "verification against recorded bases and the PR head, delta completeness in\n"
    "both directions, and how a reviewer files findings without confirming them.\n"
    + "\nFull portable guidance for any assisting model:\n"
    f"  {GUIDANCE_DOC_URL}\n"
    f"  (in the devague repo: {GUIDANCE_DOC_REPO_PATH})\n"
    "Agent-agnostic; your repo-specific agreements live in your agent's main\n"
    "instruction file — AGENTS.md, CLAUDE.md, a system prompt — not there."
)


# --- Authoring the eight operator skills (devague#34, #53 esd, #73, bvts t14) -
#
# `devague learn` knows the operator skills exist but never taught an agent how
# to *author* them. This section closes that gap: it is written as instructions
# the assisting agent follows — devague itself never writes skill files (it stays
# deterministic and non-orchestrating, #20); the agent does, with user consent.
#
# As with GUIDANCE_DOC_URL, neither `docs/` nor `.claude/skills/` ship in the
# wheel, so the canonical source is referenced by URL — always resolvable for an
# agent operating an installed devague from an arbitrary repo.
SKILLS_DOC_URL = "https://github.com/agentculture/devague/blob/main/docs/skills.md"
SKILLS_DOC_REPO_PATH = "docs/skills.md"
_SKILLS_BROWSE = "https://github.com/agentculture/devague/blob/main/.claude/skills"
_SKILLS_RAW = "https://raw.githubusercontent.com/agentculture/devague/main/.claude/skills"

# Consent + no-clobber rules — the agent behavior `learn` enforces.
SKILLS_CONSENT = (
    "These are instructions for you, the assisting agent — not a CLI side effect. "
    "devague never writes skill files; you do.",
    "If the user explicitly asked you to set up or learn the operator skills, "
    "create them now using the recipe and per-skill sources below.",
    "If you reached this by default (e.g. a bare 'devague learn'), ASK the user "
    "for permission before creating anything.",
    "Never overwrite an existing skill of the same name — if <skills>/<name>/ "
    "already exists, stop and surface the conflict instead of clobbering it.",
)

# The authoring recipe. Structured so `--json` can carry it verbatim.
SKILL_AUTHORING = {
    "layout": (
        "Each skill is one directory in your runtime's skills folder "
        "(Claude Code: .claude/skills/<name>/). Two shapes ship in this repo:\n"
        "  CLI-driving (think, spec-to-plan, assign-to-workforce):\n"
        "    <skills>/<name>/SKILL.md           frontmatter + the operating doc\n"
        "    <skills>/<name>/scripts/<name>.sh  portable CLI resolver (executable)\n"
        "  Method-only (scope, challenge, deviate, validate-delivery,\n"
        "  summarize-delivery):\n"
        "    <skills>/<name>/SKILL.md           frontmatter + the operating doc — "
        "no scripts/ directory; the skill invokes the devague CLI directly."
    ),
    "frontmatter": (
        "SKILL.md opens with YAML frontmatter (all eight skills):\n"
        "  name: <name>\n"
        "  description: >\n"
        "    one paragraph — what it does, when to use it, and that it is\n"
        "    authored in agentculture/devague.\n"
        "  type: command    # REQUIRED by culture/agex backends; a SKILL.md\n"
        "                   # without it is SILENTLY SKIPPED. Harmless on claude-code."
    ),
    "resolver": (
        "scripts/<name>.sh applies to the CLI-driving skills only (think, "
        "spec-to-plan, assign-to-workforce) — it resolves the devague CLI "
        "portably and forwards every move verbatim:\n"
        "  1. an installed 'devague' on PATH (the normal case);\n"
        "  2. else 'uv run devague' when inside a devague checkout;\n"
        "  3. else print the hint 'uv tool install devague' and exit non-zero.\n"
        "Copy the exact script from the per-skill source below — don't hand-write it.\n"
        "The method-only skills (scope, challenge, deviate, validate-delivery, "
        "summarize-delivery) have "
        "no scripts/ resolver at all — SKILL.md invokes the devague CLI directly."
    ),
    "contract": (
        "The skill drives the deterministic CLI and adds no logic of its own:\n"
        "  - drive devague through its moves; never edit .devague/ state by hand;\n"
        "  - LLM-proposed claims/honesty conditions stay 'proposed' — the user confirms;\n"
        "  - three human gates only — the exported spec, the implementation split\n"
        "    plan, and the final PR. devague never orchestrates (#20)."
    ),
}

# The eight operator skills, in eight-leg workflow order (devague#73, bvts t14):
#   scope -> think -> challenge -> spec-to-plan -> assign-to-workforce -> deviate
#   -> validate-delivery -> summarize-delivery
# `method_only` marks the five that ship a SKILL.md and NO scripts/<name>.sh
# resolver (scope, challenge, deviate, validate-delivery, summarize-delivery) —
# they invoke the
# devague CLI directly rather than going through the portable resolver script.
OPERATOR_SKILLS = (
    {
        "name": "scope",
        "leg": "idea -> explored scope (the optional opening leg)",
        "role": (
            "Surveys what an idea touches — code, docs, skills, CI, sibling repos — "
            "read-only, then records each finding with 'devague scope' and seeds the "
            "coming frame's boundary/non_goal/assumption claims with provenance. "
            "Optional-by-size and freely skippable for a small idea."
        ),
        "method_only": True,
    },
    {
        "name": "think",
        "leg": "idea -> spec (working backwards)",
        "role": (
            "Drives the flat devague verbs. Start from the announcement, capture "
            "and classify claims, interrogate them, park open vagueness, and export "
            "a spec only once the frame converges."
        ),
        "method_only": False,
    },
    {
        "name": "challenge",
        "leg": "spec (third leg): a risk-scaled blind-spot discovery pass",
        "role": (
            "Pressure-tests the converged, exported frame before 'devague plan new' "
            "for blind spots a risk-scaled pass would catch. Findings route back "
            "through existing deterministic moves (capture / interrogate / question / "
            "park / scope entries / plan risk) and reopen-reconverge-re-export the "
            "frame. On a clean pass it records examined surfaces plus residual "
            "uncertainty — never claiming there are no unknown unknowns."
        ),
        "method_only": True,
    },
    {
        "name": "spec-to-plan",
        "leg": "spec -> plan (working forwards)",
        "role": (
            "Drives the 'devague plan' group. Seed a plan from a converged frame, "
            "cover every target with TDD-accepted tasks in an acyclic order, and "
            "export a plan only once it converges."
        ),
        "method_only": False,
    },
    {
        "name": "assign-to-workforce",
        "leg": "plan -> parallel implementation",
        "role": (
            "Reads 'devague plan waves' and fans out one agent per task per wave in "
            "isolated git worktrees, all under the repo-owned root "
            "'<parent-of-repo>/.worktrees.<repo-name>/' (never a shared "
            "'../worktrees/', never in-repo), with main-agent TDD-gated merges. "
            "Three human gates; devague never orchestrates (#20)."
        ),
        "method_only": False,
    },
    {
        "name": "deviate",
        "leg": "execution-time: record human-approved departures from the confirmed plan",
        "role": (
            "Stops an in-flight assign-to-workforce run the moment execution must "
            "diverge from the confirmed plan, gets explicit human approval for the "
            "departure, and records it via 'devague deviate' before resuming. "
            "llm-origin records land 'proposed' — the user confirms, same "
            "anti-fabrication rule as claims and tasks."
        ),
        "method_only": True,
    },
    {
        "name": "validate-delivery",
        "leg": "execution -> evidence (run the plan's behavioral tests, file what was found)",
        "role": (
            "Runs the confirmed plan's behavioral tests agent-side once "
            "assign-to-workforce merges its waves and before summarize-delivery "
            "closes the loop, then files what was found: evidence records for what "
            "was checked (verbatim pass/fail outcomes, a strength level no higher "
            "than the check actually reached) and behavioral deltas for what the "
            "run added, amended, or removed. The CLI never runs a test (#20), and "
            "a failing or partial outcome is filed exactly as it happened."
        ),
        "method_only": True,
    },
    {
        "name": "summarize-delivery",
        "leg": "execution -> committed accountability artifact (the closure leg)",
        "role": (
            "Closes the loop after an assign-to-workforce run: turns what actually "
            "happened into a committed accountability artifact — planned vs actual "
            "delivery, mid-work decisions, plan drift, and remaining work. A "
            "delivery claim without evidence stays 'unverified' — never asserted "
            "as done."
        ),
        "method_only": True,
    },
)

_SKILL_NAMES = tuple(s["name"] for s in OPERATOR_SKILLS)


def _skill_source(name: str, *, method_only: bool = False) -> dict[str, str]:
    """Canonical, always-resolvable source locations for one skill's files.

    Method-only skills (scope, challenge, deviate, validate-delivery,
    summarize-delivery) ship no
    scripts/<name>.sh — omit 'script_raw' rather than emit a URL that 404s.
    """
    src = {
        "browse": f"{_SKILLS_BROWSE}/{name}/SKILL.md",
        "skill_md_raw": f"{_SKILLS_RAW}/{name}/SKILL.md",
        "repo_path": f".claude/skills/{name}/",
    }
    if not method_only:
        src["script_raw"] = f"{_SKILLS_RAW}/{name}/scripts/{name}.sh"
    return src


def _skills_payload(names: tuple[str, ...]) -> dict[str, object]:
    """Structured skills-authoring payload for the selected skill names."""
    return {
        "consent": list(SKILLS_CONSENT),
        "authoring": SKILL_AUTHORING,
        "operator_skills": [
            {**s, **_skill_source(s["name"], method_only=s.get("method_only", False))}
            for s in OPERATOR_SKILLS
            if s["name"] in names
        ],
        "doc_url": SKILLS_DOC_URL,
        "doc_repo_path": SKILLS_DOC_REPO_PATH,
    }


def _skills_text(names: tuple[str, ...], *, full: bool) -> str:
    """Render the skills-authoring section. `full` adds per-skill source URLs."""
    parts = [
        "Authoring your operator skills (create them with user consent)",
        "=============================================================",
        "",
        "devague is driven by eight operator skills — three CLI-driving (a "
        "scripts/<name>.sh resolver) and five method-only (SKILL.md only, no "
        "resolver script). Recreate them in your own runtime so you can drive "
        "devague the same way everywhere.",
        "",
        "Consent — read before creating anything:",
    ]
    parts += [f"  - {c}" for c in SKILLS_CONSENT]
    parts += [
        "",
        "Recipe:",
        SKILL_AUTHORING["layout"],
        "",
        SKILL_AUTHORING["frontmatter"],
        "",
        SKILL_AUTHORING["resolver"],
        "",
        SKILL_AUTHORING["contract"],
        "",
        "The eight skills (eight-leg workflow order):",
    ]
    for s in OPERATOR_SKILLS:
        if s["name"] not in names:
            continue
        method_only = s.get("method_only", False)
        label = " (method-only)" if method_only else ""
        parts.append(f"  {s['name']}{label}  [{s['leg']}]")
        parts.append(f"    {s['role']}")
        if full:
            src = _skill_source(s["name"], method_only=method_only)
            parts.append(f"    SKILL.md:  {src['skill_md_raw']}")
            if method_only:
                parts.append(
                    "    script:    method-only — no scripts/ resolver; "
                    "SKILL.md invokes the devague CLI directly"
                )
            else:
                parts.append(f"    script:    {src['script_raw']}")
            parts.append(f"    browse:    {src['browse']}")
        parts.append("")
    if not full:
        parts.append(
            "Run 'devague learn skills:all' for the source URLs of all eight, or "
            "'devague learn skills:<name>' for one."
        )
        parts.append("")
    parts += [
        f"Full authoring guide: {SKILLS_DOC_URL}",
        f"  (in the devague repo: {SKILLS_DOC_REPO_PATH})",
    ]
    return "\n".join(parts)


def _resolve_topic(topic: str | None) -> tuple[str, tuple[str, ...]]:
    """Map a learn topic to (mode, skill-names). Raises on an unknown topic."""
    if topic is None:
        return "bare", _SKILL_NAMES
    if topic == "review":
        return "review", _SKILL_NAMES
    if topic == "skills":
        return "skills", _SKILL_NAMES
    if topic.startswith("skills:"):
        sub = topic.split(":", 1)[1]
        if sub == "all":
            return "skills_all", _SKILL_NAMES
        if sub in _SKILL_NAMES:
            return "skill", (sub,)
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown skill: {sub}",
            "skills: " + ", ".join(_SKILL_NAMES) + ", or 'all'",
        )
    raise DevagueError(
        EXIT_USER_ERROR,
        f"unknown learn topic: {topic}",
        "topics: review, skills, skills:all, skills:<name>",
    )


def cmd_learn(args: argparse.Namespace) -> int:
    mode, names = _resolve_topic(getattr(args, "topic", None))
    json_mode = getattr(args, "json", False)

    if mode == "bare":
        if json_mode:
            emit_result(
                {
                    "tool": "devague",
                    "version": __version__,
                    "first_question": FIRST_QUESTION,
                    "supporting_prompt": SUPPORTING_PROMPT,
                    "stages": [
                        {"step": i, "name": name, "prompt": prompt, "move": move}
                        for i, (name, prompt, move) in enumerate(STAGES, 1)
                    ],
                    "moves": list(MOVES),
                    "scope_stage": SCOPE_STAGE,
                    "instruction_flags": INSTRUCTION_FLAGS_NOTE,
                    "not_a": list(NOT_A),
                    "operating_rules": list(OPERATING_RULES),
                    "guidance_doc": GUIDANCE_DOC_URL,
                    "guidance_doc_repo_path": GUIDANCE_DOC_REPO_PATH,
                    "assign_to_workforce": ASSIGN_TO_WORKFORCE_GUIDANCE,
                    "behavioral_validation": BEHAVIORAL_VALIDATION_GUIDANCE,
                    "strength_ladder": [
                        {"level": level, "description": desc} for level, desc in STRENGTH_LADDER
                    ],
                    "skills": _skills_payload(names),
                    "summary": _TEXT,
                },
                json_mode=True,
            )
        else:
            emit_result(_TEXT + "\n\n" + _skills_text(names, full=False), json_mode=False)
    elif mode == "review":
        # The reviewer seam (bvts t14): a self-contained gate-3 audit topic,
        # emitted on its own — a reviewer arriving cold needs the audit method,
        # not the authoring method.
        if json_mode:
            emit_result(
                {
                    "tool": "devague",
                    "version": __version__,
                    "topic": "review",
                    "review": _review_payload(),
                },
                json_mode=True,
            )
        else:
            emit_result(_review_text(), json_mode=False)
    else:
        # A skills topic: emit just the authoring section. The JSON envelope
        # carries the same tool/version identity as the bare payload so the
        # whole `learn` command family shares one schema (Qodo PR #35).
        full = mode in ("skills_all", "skill")
        if json_mode:
            emit_result(
                {
                    "tool": "devague",
                    "version": __version__,
                    "topic": getattr(args, "topic", None),
                    **_skills_payload(names),
                },
                json_mode=True,
            )
        else:
            emit_result(_skills_text(names, full=full), json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("learn", help="Teach devague's method and how to author its skills.")
    p.add_argument(
        "topic",
        nargs="?",
        default=None,
        help=(
            "Optional: 'review' for the gate-3 audit method, or 'skills' / "
            "'skills:all' / 'skills:<name>' to teach skill authoring."
        ),
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
