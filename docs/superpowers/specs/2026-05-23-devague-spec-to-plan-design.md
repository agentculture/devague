# devague — spec→plan engine (`/think` + `/spec-to-plan`)

**Date:** 2026-05-23
**Status:** Approved (design) — implemented in 0.4.0
**Design input:** user request to reframe the single `/devague` skill into a
clearer two-skill pipeline and formalize the next leg (spec → plan).

## Context

devague's first engine — the **frame engine** (see
`2026-05-23-devague-working-backwards-design.md`) — turns a vague idea into a
buildable **spec** by working backwards, and deliberately stops at `export`,
handing off to `superpowers:writing-plans`. This design adds the **forward** leg
as a structural peer: a deterministic **plan engine** that turns a converged spec
into a buildable **plan**, and reframes the operator skills so the pipeline reads
clearly:

```
vague idea ──/think──▶ buildable spec ──/spec-to-plan──▶ buildable plan ──▶ build
           (frame engine)               (plan engine, this design)
```

Locked decisions:

- **Two skills, matched verbs.** `/devague` → `/think` (idea→spec); add
  `/spec-to-plan` (spec→plan). The skill could **not** be named `/plan` — that
  collides with the existing `plan` skill Claude Code and other agents use. The
  product / CLI / repo stays **`devague`**; only the *skill* identity changes.
  The CLI group is `devague plan <move>` (a subcommand, not a shared skill — no
  collision).
- **A real engine**, not a wrapper around `superpowers:writing-plans`.
- **Seeded from a converged frame** (`devague plan new --frame <slug>`). External
  markdown-spec ingestion is deferred.
- **Hard rename** of the published skill (steward relearns the name downstream).

## Goals / non-goals

**Goals**
- Turn a converged spec into a clear, covered, acyclic, buildable plan.
- Make "no fabricated rigor" enforceable in code, exactly as the frame engine
  does: LLM-proposed tasks stay `proposed` until the user confirms them.
- Gate plan export on a convergence gate that *means something*.
- Keep the plan engine a clean peer: deterministic, zero-runtime-dep, fully
  unit-testable; reuse the existing CLI chassis, store conventions, and
  `ConvergenceResult` shape.

**Non-goals**
- Not a project manager: no scheduling, estimation, or assignee tracking.
- Not a spec parser (v1): the plan is seeded from the structured frame, not from
  free-form markdown.
- Do not reimplement superpowers; the exported plan-md can still feed it.

## Architecture

Mirror the frame engine 1:1. No LLM calls inside the CLI → fully unit-testable;
the resident agent chooses moves.

| Layer | Frame engine | Plan engine (this design) |
|---|---|---|
| Domain | `devague/frame.py` | `devague/plan.py` |
| Gate | `devague/convergence.py` | `devague/plan_convergence.py` (reuses `ConvergenceResult`) |
| Store | `devague/store.py` (`.devague/frames/`) | `devague/plan_store.py` (`.devague/plans/`) |
| Render | `devague/render/spec_md.py` | `devague/render/plan_md.py` |
| Resolver | `devague/cli/_frames.py` | `devague/cli/_plans.py` |
| CLI | flat verbs | nested group `devague plan <move>` |

### Domain model — the Plan

One Plan per converged frame; **slug == frame slug** (1:1 link, separate
directories so no collision). Source of truth: JSON at `.devague/plans/<slug>.json`.

```
Plan
  meta: { slug, title, frame_slug, status: drafting|converged|exported, created, updated }
  targets: [ CoverageTarget ]   # snapshot of what the plan must satisfy
  tasks:   [ Task ]
  risks:   [ PlanRisk ]

CoverageTarget        # derived from the converged frame; id mirrors the frame id
  id                  # c3 / h2 (claim id, or honesty-condition id)
  kind                # a claim kind, or "honesty"
  text

Task
  id                  # t1, t2
  summary
  origin              # user | llm
  status              # proposed | confirmed | rejected   (user-only confirm)
  acceptance_criteria: [ str ]
  deps:               [ task-id ]   # tasks that must precede it
  covers:             [ target-id ] # the c*/h* it satisfies

PlanRisk              # first-class, task-level peer of the frame's open vagueness
  id                  # r1
  text
  kind                # unknown_nonblocking | unknown_blocking | out_of_scope | follow_up
  task_id?            # optional link to a task
```

`targets_from_frame(frame)` derives the targets: every **confirmed**
spec-affecting claim plus the **confirmed** honesty conditions hanging off it.
Confirmation rules match the frame engine: `origin=llm` tasks are born
`proposed`; only an explicit user `confirm`/`reject` transitions them.

### Moves → CLI verbs (nested group, all support `--json`)

| Verb | Effect |
|------|--------|
| `devague plan new --frame <slug>` | Seed a plan from a **converged** frame; derive coverage targets. Refuses an unconverged frame; refuses to clobber an existing plan. |
| `devague plan task "<summary>" [--accept … --dep … --covers … --origin]` | Add a task; inline acceptance criteria / deps / coverage. |
| `devague plan accept <tN> "<crit>"` / `depend <tN> --on <tM>` / `cover <tN> --target <c*/h*>` | Incrementally enrich a task. |
| `devague plan confirm <tN>` / `reject <tN>` | User-only status transitions. |
| `devague plan risk "<text>" --kind <…> [--task <tN>]` | Record first-class plan risk. |
| `devague plan converge` | Evaluate the gate against the **live** frame; report gaps. |
| `devague plan export [--format plan-md]` | Emit the buildable plan — only if `converge` passes; writes `docs/plans/<slug>.md`. |
| `devague plan show` / `list` | Render the plan / list plans. |
| `devague plan learn` / `explain <move>` | Teach the method / a move. |

Nested via `add_subparsers(parser_class=_DevagueArgumentParser)` so argparse
errors still route through the structured `emit_error` path; bare `devague plan`
prints group help (rc 0) via a `func` default.

### Convergence gate (`plan_convergence.evaluate`)

A plan converges when each failure names what's missing:

- ≥1 task exists;
- every coverage target is covered by ≥1 **confirmed** task;
- every confirmed task has ≥1 acceptance criterion;
- no task is still `proposed`;
- every `dep` references a real task, and the dependency graph is **acyclic**
  (cycle reported as a deterministic id path, e.g. `t1 -> t2 -> t1`);
- no `unknown_blocking` risk remains.

`export` refuses (with the gap list) until the gate passes.

### Frame drift

`converge`/`export` re-load the source frame and **re-derive** targets every
time (the stored `targets` snapshot is a `show`-only cache). They refuse if the
frame was deleted, has an invalid slug, or has **regressed below convergence** —
the agent must re-converge the spec first. This is the one piece of machinery
with no frame-engine analog; it has dedicated tests.

### Output layer

`plan-md` renders the buildable plan: tasks topologically ordered by deps (stable
fallback on a cycle so rendering never crashes), each with acceptance criteria
and the targets it covers, then a risks section. It is **not** registered in the
`render` registry (which is `Callable[[Frame], str]`); the export command calls
`render_plan(plan, frame)` directly.

## Operator skills

- `/think` (`.claude/skills/think/`, `scripts/think.sh`) — renamed from
  `/devague`; drives the flat frame verbs; portable wrapper + `status` helper.
- `/spec-to-plan` (`.claude/skills/spec-to-plan/`, `scripts/spec-to-plan.sh`) —
  forwards every move to `devague plan <move>`; portable wrapper + `status`
  helper over the plan gate.

Both are first-party (origin = devague), dogfooded, and re-vendored by steward to
the mesh — see `docs/skill-sources.md`.

## Testing

Deterministic throughout, mirroring `tests/`:
- plan model: id allocation, transitions, dedup, `targets_from_frame` inclusion
  rules, JSON round-trip;
- gate: a case per `_missing_*` helper, incl. a deterministic cycle path;
- store: round-trip + `current_plan`, tampered-slug rejection, frame coexistence;
- renderer: topo order, acceptance/covers, risks, missing-frame degrade;
- CLI: each move (text + `--json`), unconverged/missing/collision refusals, bare
  group help, unknown sub-move, export gating, frame-drift guards, learn/explain;
- both skill wrappers: bash validity, forwarding, `status`, install-hint.

Coverage stays above `fail_under = 95`.

## Acceptance criteria

- `devague plan new --frame <converged>` → `task`/`accept`/`depend`/`cover`/
  `risk` → user `confirm` → `converge` → `export` writes `docs/plans/<slug>.md`,
  and `export` is refused (with the gap list) before convergence.
- `plan new` refuses an unconverged frame; `converge`/`export` refuse a
  deleted/regressed source frame.
- LLM-origin tasks require explicit user confirmation.
- All moves support `--json`; bare `devague plan` prints help.
- `/devague` skill renamed to `/think`; `/spec-to-plan` added; both wrappers pass
  `bash -n` and their smoke tests; `git grep skills/devague` finds only history.
- Suite green (pytest-xdist), coverage ≥ 95%; flake8 / black / isort /
  markdownlint clean.

## Deferred

- External markdown-spec ingestion (`plan new --spec <path>`): seam is the
  `targets_from_frame` boundary; a markdown parser can produce targets later.
- Effort/sequencing/assignee metadata on tasks.
- Additional plan renderers (HTML, issue-tracker export) behind a future seam.
- Auto-suggesting tasks/coverage from the spec (an agent affordance, not CLI).
