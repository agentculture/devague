# Operating Devague — portable guidance for assisting models

This is the **portable, runtime-agnostic contract** for any LLM or agent that
operates Devague. It does not assume a particular agent runtime (Claude Code,
a Codex/`AGENTS.md` agent, Copilot, an ACP host, a bare system prompt, …). It
complements — it does **not** replace — your agent's own main instruction file
(`AGENTS.md`, `CLAUDE.md`, a system prompt, or equivalent), which carries the
repo-specific working agreements. Where the two overlap, this document is the
authority on *how Devague itself must be driven*.

The authoritative entity model and the per-move input/output/transition
contract live in [`spec-contract.md`](spec-contract.md). For the live shape of
any move, run it with `--json`, or run `devague learn` / `devague explain
<move>`.

## 1. What Devague is — and is not

Devague is a **deterministic, move-driven state machine** over claims, honesty
conditions, open vagueness, and a convergence gate. There are **no LLM calls
inside the CLI** — it only records moves and reports what is still missing. The
intelligence is *you*, the operating model.

It is **not**:

- **not a wizard** — there is no fixed sequence of prompts to march through;
- **not a scripted questionnaire** — you do not read questions off a form;
- **not a PRD generator** — it will not invent content to fill a template.

You choose each move from the live state; the CLI tracks state and tells you
what remains before a spec (or plan) can be exported.

## 2. The state you operate on

Two legs share one chassis:

- **Frame (idea → spec).** Claims (each with a *kind* — `announcement`,
  `audience`, `after_state`, `before_state`, `why_it_matters`, `boundary`,
  `success_signal`, `open_question`, `non_goal`, `requirement`, `assumption`,
  `decision`); honesty conditions and hard questions attached to claims; and
  **open vagueness** (parked unknowns, kinds `unknown_nonblocking` /
  `unknown_blocking` / `out_of_scope` / `follow_up`).
- **Plan (spec → plan).** Coverage targets (derived from a converged frame),
  tasks (with acceptance criteria, dependencies, and the targets they cover),
  and first-class plan risks.

Every element carries two orthogonal axes:

- **origin** — `user` or `llm` (who proposed it);
- **status** — `proposed`, `confirmed`, or `rejected`.

`origin` and `status` are independent. An `llm`-proposed claim is *proposed*
until a human acts on it; a `user`-provided claim is *confirmed* on arrival.
Keeping these distinct is the whole point of the tool — see §4.

## 3. You choose the move; order is adaptive

The moves are `new`, `capture`, `interrogate`, `confirm`, `reject`, `review`,
`question`, `park`, `converge`, `export`, `show`, `list` (plus the `plan …`
moves for the forward leg). Pick the move that fits the live state — not a
predetermined script.

When unsure what to do next, ask the gate, don't guess: run `converge --json`
(it returns `{ready_for_spec, blockers, warnings, parked_items,
required_next_moves}`; plans return `ready_for_plan`) and act on the first
blocker.

The canonical **ten-stage arc** (announcement → audience → after → matter →
before → honest → FAQ → boundaries → success → spec) that `devague learn`
prints is an **artifact shape and a recommended arc — not a mandatory
conversation order**. If the user hands you the audience and the success signal
before the announcement is crisp, capture those now and circle back. Drive
toward the shape; do not impose a sequence on the user.

## 4. Hard rules — the anti-fabrication contract

These are not style preferences. Convergence is only meaningful if these hold.

- **LLM proposals stay proposed.** Capture your own ideas freely with `--origin
  llm` (claims) or by attaching honesty conditions; they land as `proposed`.
  **Never `confirm` your own proposal.** Confirmation is a **user-only**
  decision. Surface the proposal and let the user confirm or reject it — proposed
  content must never silently become an authoritative requirement.
- **Honesty conditions route through the user.** Propose them generously with
  `interrogate --honesty`; the user owns whether each one actually holds.
- **Park real unknowns; do not paper over them.** If something is genuinely
  unknown, `park` it (blocking or non-blocking) instead of writing confident
  prose that hides the gap. Blocking vagueness holds back convergence by design.
- **Converge, don't vibe.** `export` is gated on `converge` passing. Never
  declare a frame or plan "ready" on a hunch — run `converge` and resolve every
  listed gap first.

## 5. Good vs. bad operator behavior

| Situation | ❌ Bad (fabricating) | ✅ Good (honest) |
|-----------|---------------------|------------------|
| You have a strong guess at the audience | `capture --kind audience … --origin user` (passing your guess off as the user's) | `capture --kind audience … --origin llm`, then ask the user to `confirm` |
| You proposed an honesty condition | `confirm h3` yourself so the gate passes | leave `h3` proposed; surface it for the user to confirm |
| A key detail is genuinely unknown | invent a plausible answer to keep momentum | `park "<the unknown>" --kind unknown_blocking` |
| User asks "is this ready?" | "Yes, looks solid." | run `converge`; report the actual blockers/warnings |
| The user skipped a stage | march through the stages in order anyway | capture what they gave you; let the arc fill in adaptively |
| Plan: a task has no clear acceptance test | mark it confirmed and move on | leave it without criteria (the gate blocks it) or `park` the risk |

## 6. The forward leg (spec → plan), in brief

The plan engine is the structural peer of the frame engine and obeys the same
spirit:

- **Seed from a converged spec only** — `plan new` refuses an unconverged frame.
- **LLM-proposed tasks stay proposed**; the user confirms them.
- **Cover every target, criteria on every task** — the gate requires it.
- **Keep the dependency graph honest** — real task ids, acyclic.
- **Park genuine unknowns as risks** (`unknown_blocking` holds convergence back).
- **Converge against the live frame** — `converge`/`export` re-load the source
  frame; if it regressed below convergence, re-converge the spec first.

## 7. Output contract

Results go to **stdout**; diagnostics and errors go to **stderr** — a strict
split you can parse. Pass `--json` to any move for a structured payload on the
same stream. Exit code is `0` on success, non-zero on user error (with a
`hint:` line and no Python traceback). Frames and plans persist under
`.devague/` in the current directory.

## 8. Where authority lives

- **Entity model + per-move contract:** [`spec-contract.md`](spec-contract.md).
- **Live shape of any move:** run it with `--json`, or `devague learn` /
  `devague explain <move>`.
- **Repo-specific working agreements:** your agent's main instruction file
  (`AGENTS.md`, `CLAUDE.md`, system prompt, …) — not this document.
