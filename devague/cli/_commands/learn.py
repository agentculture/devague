"""``devague learn`` — teach the working-backwards method and the moves."""

from __future__ import annotations

import argparse

from devague import __version__
from devague.cli._output import emit_result

MOVES = {
    "new": "Start a frame from the announcement (pretend it shipped).",
    "capture": "Record and classify a claim (audience, after_state, boundary, ...).",
    "interrogate": "Pressure-test a claim: honesty conditions, hard questions, contradictions.",
    "confirm": "Confirm a claim or honesty condition (user-only — no fabricated rigor).",
    "reject": "Reject a claim or honesty condition.",
    "park": "Move uncertainty into first-class open vagueness instead of forcing an answer.",
    "converge": "Check whether the frame is solid enough to export a spec.",
    "export": "Write the buildable spec — only once the frame converges.",
    "show": "Render the Announcement Frame.",
    "list": "List frames.",
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

# The anti-fabrication rules. Agent-agnostic: repo-specific agreements live in
# your agent's main instruction file (AGENTS.md, CLAUDE.md, a system prompt, …),
# not here.
OPERATING_RULES = (
    "LLM proposals stay proposed — capture your own ideas with --origin llm; "
    "never confirm your own proposal. Confirmation is a user-only decision.",
    "Honesty conditions route through the user — propose freely with "
    "'interrogate --honesty'; the user owns whether each one holds.",
    "Park real unknowns instead of papering over them — 'park' a genuine "
    "unknown rather than writing confident prose that hides the gap.",
    "Converge, don't vibe — 'export' is gated on 'converge'; resolve every "
    "listed gap instead of declaring readiness on a hunch.",
    "Order is adaptive — the ten stages are an artifact shape, not a mandatory "
    "conversation order; capture what the user gives you and circle back.",
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

_TEXT = (
    "devague turns a vague idea into a buildable spec by working backwards.\n\n"
    f"First question: {FIRST_QUESTION}\n"
    f"  {SUPPORTING_PROMPT}\n\n"
    "Start from that announcement, then build an Announcement Frame by capturing\n"
    "claims, interrogating them, parking what's still vague, and converging.\n"
    "The arc emerges from the moves; it is not a fixed wizard. You (the agent)\n"
    "choose the next move; devague tracks state. LLM-proposed claims and honesty\n"
    "conditions stay 'proposed' until the user confirms them.\n\n"
    "Guided stages (the recommended sequence — drive them with the moves):\n"
    + "\n".join(
        f"  {i:>2}. {name:<13} {prompt}  [{move}]"
        for i, (name, prompt, move) in enumerate(STAGES, 1)
    )
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
    f"  Main agent: {ASSIGN_TO_WORKFORCE_GUIDANCE['main_agent_merge_gate']}\n"
    f"  TDD: {ASSIGN_TO_WORKFORCE_GUIDANCE['tdd_acceptance_criteria']}\n"
    f"  Scope: {ASSIGN_TO_WORKFORCE_GUIDANCE['not_orchestration']}\n"
    + "\n\nFull portable guidance for any assisting model:\n"
    f"  {GUIDANCE_DOC_URL}\n"
    f"  (in the devague repo: {GUIDANCE_DOC_REPO_PATH})\n"
    "Agent-agnostic; your repo-specific agreements live in your agent's main\n"
    "instruction file — AGENTS.md, CLAUDE.md, a system prompt — not there."
)


def cmd_learn(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
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
                "not_a": list(NOT_A),
                "operating_rules": list(OPERATING_RULES),
                "guidance_doc": GUIDANCE_DOC_URL,
                "guidance_doc_repo_path": GUIDANCE_DOC_REPO_PATH,
                "assign_to_workforce": ASSIGN_TO_WORKFORCE_GUIDANCE,
                "summary": _TEXT,
            },
            json_mode=True,
        )
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("learn", help="Teach devague's working-backwards method.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
