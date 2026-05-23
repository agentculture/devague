# Devague plans get parallel, TDD-gated, simpler-model implementation via assign-to-workforce

> Devague turns a converged plan into parallel, simpler-model-executable work. /spec-to-plan yields plans whose tasks are independently parallelizable and given TDD acceptance criteria — scoped tightly enough for a cheap model to build test-first. A cited 'assign-to-workforce' skill (shared via 'devague learn') fans out 'devague plan waves' to one subagent per task per wave in isolated git worktrees; the main agent merges each task via TDD (its tests pass before AND after merge), while the human gates the spec, the implementation split plan, and the final PR. The CLI stays deterministic and non-orchestrating (#20).

## Audience

- The devague/AgentCulture operator agent that implements a converged plan, plus the human who owns the merge gate. Per-task work may be delegated to cheaper/simpler models.

## Before → After

- Before: 'devague plan waves' emits the schedule, but there is no devague convention for who fans it out, how files stay contention-safe, how a task is accepted, or how plans should be authored to be parallel- and simple-model-friendly.
- After: A converged plan can be built by fanning out independent tasks to parallel subagents — including a simpler model per task — instead of one agent building serially.

## Why it matters

- Parallel + cheap-model execution makes plans much faster and cheaper to build and forces tighter task scoping — but only pays off if it stays safe and reviewable.

## Requirements

- /spec-to-plan yields plans whose tasks are independently parallelizable AND given TDD acceptance criteria — tests specified first, scoped tightly enough that a simpler/cheaper model can build each one test-first and have its output validated by those tests.
  - honesty: Within-wave independence is real: same-wave tasks have no inter-task dependency and can be built concurrently.
  - honesty: 'Scoped for a simpler model' is operational via TDD, not a vibe: each task ships with tests crisp enough to validate a cheap model's output (the tests pass) without re-deriving the design.

## Honesty conditions

- Each named audience really interacts with the flow: the operator agent drives waves and merges, the human owns the three gates (spec / split plan / PR), and cheaper models execute individual tasks — no silent fourth approver.
- The parallel + cheap-model build yields the same result as a serial build would — fan-out changes speed and cost, not correctness; the merged result passes the same TDD tests.
- Today there genuinely is no devague convention for fan-out / contention / acceptance: 'devague plan waves' (#20) emits the schedule but stops at description, and nothing downstream consumes it yet.
- The speed/cost win is real, not assumed: parallel waves plus cheap per-task models cut wall-clock and token cost versus one serial agent, while the TDD gates keep quality from dropping.
- This work adds no LLM calls and no orchestration to the devague CLI.
- The assign-to-workforce skill is cited (copied), not imported, with provenance recorded in docs/skill-sources.md (cite-don't-import).
- Same-wave tasks touching the same file are made safe by isolated worktrees — the dependency graph alone does NOT guarantee file-disjointness; overlaps reconcile at merge.
- Per-task merges need no human: the main agent gates each subagent's worktree merge with TDD (tests pass before and after merge). The human's three gates are the spec, the implementation split plan (plan map + assignments + go/no-go to workforce), and the final PR.
- Per-task acceptance is the main agent's (TDD tests + the task's acceptance criteria), recorded as non-authoritative working state; the authoritative human gates are the spec, the implementation split plan, and the final PR.
- End-to-end the flow runs on a real converged plan — 'devague plan waves' -> human approves the implementation split plan (plan map, per-task subagent/model assignment, go/no-go to workforce) -> one subagent per task per wave in isolated worktrees -> main-agent TDD-gated merges (tests pass before and after merge; no human per task) -> human spec & final-PR gates — without adding any orchestration or LLM call to the devague CLI.

## Success signals

- An operator takes a converged plan, runs 'devague plan waves', and presents the implementation split plan for the human to approve — the plan/tasks map, the per-task subagent + model assignment, and the go/no-go on assigning the plan to the workforce. Approved waves fan out to subagents in isolated worktrees with no live file races; the main agent merges each task's worktree gated by TDD (tests pass before and after merge) — no human per task. The human's remaining gates are the exported spec and the final PR.

## Scope / boundaries

- Devague's CLI does not orchestrate: it does not spawn subagents, manage worktrees, mark tasks done, or pick a backend (#20 stands). This work is a convention + cited skill, not new CLI and not a CI/CD runner.

## Decisions

- File-contention safety: each subagent runs in an isolated git worktree, so same-file overlap surfaces as a merge conflict at reconcile time rather than a live race. (resolves q1)
- Parallel/simple-model fitness is enforced two ways: /spec-to-plan skill guidance for small, parallel, crisply-accepted tasks, PLUS a deterministic NON-blocking plan_convergence warning (e.g. missing acceptance criteria, over-serialized waves). No hard gate, no LLM in the CLI. (resolves q2)
- The plan stays model-agnostic; per-task subagent assignment (scope + chosen model) is the resident agent's proposal, presented as a clear, editable table the human approves or edits, and the human decides whether to run subagent-driven at all. Devague does not pick a backend (#20). (resolves q4)
- Orchestration lives in a cited, devague-specific skill named 'assign-to-workforce' (citing superpowers:subagent-driven-development) plus a CLAUDE.md convention — not in the deterministic CLI. The name is deliberately broader than 'subagents' to leave room for teammate agents and generalist agents in future.
- The assign-to-workforce skill and any skill changes are shared via 'devague learn' — 'devague learn' carries the instructions for how to invoke subagent-driven-development / assign-to-workforce (how to fan out a converged plan's waves).
- The human's gates are exactly three: (1) the exported spec, (2) the implementation split plan — the plan/tasks map, the per-task subagent + model assignment, and the go/no-go on assigning the plan to the workforce — and (3) the final PR. The human is NOT in the per-task worktree-merge loop: the main/operating agent gates each merge with TDD (tests pass before and after merge) against the task's acceptance criteria. Per-task acceptance is uncommitted working state (mirroring the #17 Human Review Loop).
