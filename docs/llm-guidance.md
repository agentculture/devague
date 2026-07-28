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

Three legs share one chassis (the third optional):

- **Scope (idea → explored scope, optional).** The `/scope` skill's pre-frame
  survey: `ScopeEntry` records (`surface` explored, `finding`, and the ids it
  `seeds` — claim ids `c*` or claim-attached hard-question ids `q*`) that
  ground the frame in what was actually looked at, instead of generic
  disclaimers. Small ideas skip straight to the frame — this leg is optional by
  size, never a mandatory first stage. Both the state (`Frame.scope_entries`)
  and the `devague scope` move that writes it have shipped; `scope --amend
  <sN> --finding "<text>"` corrects a finding in place.
- **Frame (idea → spec).** Claims (each with a *kind* — `announcement`,
  `audience`, `after_state`, `before_state`, `why_it_matters`, `boundary`,
  `success_signal`, `open_question`, `non_goal`, `requirement`, `assumption`,
  `decision`); honesty conditions and hard questions attached to claims; and
  **open vagueness** (parked unknowns, kinds `unknown_nonblocking` /
  `unknown_blocking` / `out_of_scope` / `follow_up`). A parked item is not
  stuck once decided: `park --resolve <vN> --decision "<text>" [--claim <cN>]`
  closes it out — it stays on record with its resolution, drops out of the
  convergence gate, and never requires hand-editing `.devague` state. A
  blocking **hard question** has the same exit: `interrogate <cN> --resolve
  <qN> --decision "<text>"`. A claim whose text or kind is wrong is corrected
  with `amend <cN>`, keeping its id and everything attached to it.
- **Plan (spec → plan).** Coverage targets (derived from a converged frame,
  each of which may be deliberately `defer`red out of this plan's gate with a
  reason), tasks (with acceptance criteria, dependencies, and the targets they
  cover), and first-class plan risks.

Every element carries two orthogonal axes:

- **origin** — `user` or `llm` (who proposed it);
- **status** — `proposed`, `confirmed`, or `rejected`.

`origin` and `status` are independent. An `llm`-proposed claim is *proposed*
until a human acts on it; a `user`-provided claim is *confirmed* on arrival.
Keeping these distinct is the whole point of the tool — see §4.

Claims, honesty conditions, and plan tasks also carry an optional
**`instruction`** — verbatim text on how to verify or implement that item,
`""` by default (never fabricated to fill the gap). Setting or changing an
instruction on an already-`confirmed` item flips its status back to
`proposed` — it re-enters the user-confirm loop like any other content change.
The moves that set it (`capture --instruction` / `interrogate --instruction`
on the frame side, `plan task --instruction` / `plan instruct <tN>` on the plan
side) are landing in #53 tasks t4/t5; see [`spec-contract.md`](spec-contract.md)
for the full field contract.

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

An optional scope-exploration stage can precede all of this when the idea
touches an existing codebase: survey the surfaces it touches, then seed the
frame's `boundary` / `non_goal` / `assumption` claims with what was actually
found — provenance, not a generic disclaimer. It's optional by size: skip
straight to `new` for a small idea; nothing about it is a fixed first stage.

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
  prose that hides the gap. Blocking vagueness holds back convergence by
  design — and once it is decided, close it out with `park --resolve <vN>
  --decision "<text>"` (plan side: `plan risk --resolve <rN> --decision
  "<text>"`) rather than leaving it parked forever or hand-editing state; the
  resolved item stays on record with its resolution and stops blocking.
- **Blocking hard questions route through the user too.** A question raised
  `--blocking` holds convergence back until it is *decided*, not until you talk
  yourself out of it. Close it out with `interrogate <cN> --resolve <qN>
  --decision "<text>"` — the claim-level twin of `park --resolve`, and a
  **user-only** decision like `confirm`. The question stays on record with its
  answer and stops blocking; deleting it or hand-editing state does not.
- **Correct in place; never churn ids to fix wrong content.** A claim whose
  text or kind is wrong is `amend`ed (`amend <cN> --text … --kind … --reason
  …`), not rejected and recaptured: the id survives, so its honesty
  conditions, hard questions, `instruction`, and inbound `scope --seeds`
  references keep pointing at something real, the superseded value is kept as
  an evidence trail, and a confirmed claim flips back to `proposed` for the
  user to re-confirm. Same shape on the other two: `scope --amend <sN>
  --finding "<text>"` and `plan risk --amend <rN> --text "<text>"`.
- **Defer honestly; don't fake coverage.** If a coverage target genuinely
  belongs to a later milestone, `plan defer <target-id> --reason "<why>"` — a
  documented exclusion that stays visible in `parked_items` and in the
  exported plan. Never write a task that merely *names* a target so the
  coverage gate goes green.
- **Converge, don't vibe.** `export` is gated on `converge` passing. Never
  declare a frame or plan "ready" on a hunch — run `converge` and resolve every
  listed gap first.
- **Instructions are optional and verbatim — never fabricated.** Leave
  `instruction` empty rather than invent one just to satisfy a gate warning
  (the structural sharpness warnings, #53 t7/t8). Changing an
  instruction on an already-confirmed item deliberately demotes it back to
  `proposed` — that is the same anti-fabrication contract catching a
  late-arriving field, not a bug.

## 5. Good vs. bad operator behavior

| Situation | ❌ Bad (fabricating) | ✅ Good (honest) |
|-----------|---------------------|------------------|
| You have a strong guess at the audience | `capture --kind audience … --origin user` (passing your guess off as the user's) | `capture --kind audience … --origin llm`, then ask the user to `confirm` |
| You proposed an honesty condition | `confirm h3` yourself so the gate passes | leave `h3` proposed; surface it for the user to confirm |
| A key detail is genuinely unknown | invent a plausible answer to keep momentum | `park "<the unknown>" --kind unknown_blocking` |
| A blocking park just got decided | leave it parked forever, or hand-edit `.devague` state to unblock convergence | `park --resolve <vN> --decision "<the decision>"` |
| A blocking hard question just got decided | argue it is "not really blocking", or hand-edit the frame JSON | `interrogate <cN> --resolve <qN> --decision "<how it was decided>"` (user-only) |
| A confirmed claim's text turns out to be wrong | `reject` it and `capture` a replacement, orphaning its honesty conditions and scope seeds | `amend <cN> --text "<corrected>" --reason "<why>"`; the user re-confirms |
| A coverage target belongs to a later milestone | add a task that name-drops the target so `plan converge` passes | `plan defer <target-id> --reason "<why it is out of scope here>"` |
| User asks "is this ready?" | "Yes, looks solid." | run `converge`; report the actual blockers/warnings |
| The user skipped a stage | march through the stages in order anyway | capture what they gave you; let the arc fill in adaptively |
| Plan: a task has no clear acceptance test | mark it confirmed and move on | leave it without criteria (the gate blocks it) or `park` the risk |
| A gate warns a claim/task has no instruction (#53 t7/t8) | invent a generic instruction just to silence the warning | leave it empty, or write a real one and let the user confirm it |

## 6. The forward leg (spec → plan), in brief

The plan engine is the structural peer of the frame engine and obeys the same
spirit:

- **Seed from a converged spec only** — `plan new` refuses an unconverged frame.
- **LLM-proposed tasks stay proposed**; the user confirms them.
- **Cover every target, criteria on every task** — the gate requires it, unless
  a target is deliberately `plan defer`red with a reason.
- **Keep the dependency graph honest** — real task ids, acyclic.
- **Park genuine unknowns as risks** (`unknown_blocking` holds convergence
  back); close a decided one out with `plan risk --resolve <rN> --decision
  "<text>"` rather than leaving it parked or hand-editing plan state.
- **Converge against the live frame** — `converge`/`export` re-load the source
  frame; if it regressed below convergence, re-converge the spec first.
- **Instructions ride along to the workforce.** A task's optional
  `instruction` (landing #53 t5) is meant to reach `assign-to-workforce`'s
  per-subagent brief verbatim — no operator paraphrasing (#53 t9/t13).

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
- **Authoring the operator skills:** [`skills.md`](skills.md), or run `devague
  learn skills` — how to create the `think` / `spec-to-plan` /
  `assign-to-workforce` skills in your own runtime (with user consent).
- **Repo-specific working agreements:** your agent's main instruction file
  (`AGENTS.md`, `CLAUDE.md`, system prompt, …) — not this document.
