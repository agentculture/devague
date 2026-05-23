# Build Plan — Devague plans get parallel, TDD-gated, simpler-model implementation via assign-to-workforce

slug: `devague-turns-a-converged-plan-into-parallel-simpl` · status: `exported` · from frame: `devague-turns-a-converged-plan-into-parallel-simpl`

> Devague turns a converged plan into parallel, simpler-model-executable work. /spec-to-plan yields plans whose tasks are independently parallelizable and given TDD acceptance criteria — scoped tightly enough for a cheap model to build test-first. A cited 'assign-to-workforce' skill (shared via 'devague learn') fans out 'devague plan waves' to one subagent per task per wave in isolated git worktrees; the main agent merges each task via TDD (its tests pass before AND after merge), while the human gates the spec, the implementation split plan, and the final PR. The CLI stays deterministic and non-orchestrating (#20).

## Tasks

### t1 — Author the assign-to-workforce skill: SKILL.md + a portable helper script, plus its first-party provenance entry

- covers: c18, c20, h13, h14, h17
- acceptance:
  - SKILL.md documents the full flow: read 'devague plan waves' -> present the implementation split plan (tasks map + per-task subagent+model proposal) -> human go/no-go -> one subagent per task per wave in isolated git worktrees -> main-agent TDD-gated merge (the task's tests pass before AND after merge) -> human gates spec + split-plan + final PR
  - scripts/assign-to-workforce.sh resolves devague portably (mirrors think.sh) and prints the split-plan from 'devague plan waves --json'; on a converged plan it exits 0 and lists the waves
  - docs/skill-sources.md records assign-to-workforce as first-party (origin=devague); the skill states the CLI is never orchestrated by devague (#20)

### t2 — Document the assign-to-workforce convention in CLAUDE.md

- covers: c2, c4, c5, c6, h5, h20, h22
- acceptance:
  - CLAUDE.md gains a 'Subagent-driven implementation (assign-to-workforce)' section stating the three human gates (spec / implementation split plan / final PR), worktree contention safety, the main-agent TDD merge gate (no human per task), and the boundary that the CLI never spawns/orchestrates/marks-done/picks-backend (#20)
  - The section names the operator-agent and human roles and notes today's gap (waves emits the schedule but nothing downstream consumes it)
  - markdownlint-cli2 passes on CLAUDE.md and doc-test-alignment finds the section consistent with the skill

### t3 — Add a deterministic, non-blocking plan_convergence warning for parallel/TDD fitness

- covers: c21, h18, h19
- acceptance:
  - Tests written first: 'devague plan converge --json' emits a non-blocking warnings[] entry for a confirmed task with no acceptance criteria, and for an over-serialized graph (e.g. a needless single-task wave / trivial chain)
  - Warnings never change ready_for_plan/blockers — convergence still passes; a clean plan emits zero warnings
  - A unit test asserts same-wave tasks have no inter-task dependency (within-wave independence holds)

### t4 — Carry assign-to-workforce invocation instructions in 'devague learn' (implements decision c17)

- acceptance:
  - Tests written first: 'devague learn' (and --json) output contains an assign-to-workforce / subagent-driven-development section covering when to fan out, the three gates, and worktree+TDD
  - A unit test asserts the learn text includes the assign-to-workforce guidance

### t5 — Coach /spec-to-plan to yield small, file-disjoint, TDD-accepted (parallelizable) tasks

- covers: c3, h21
- acceptance:
  - spec-to-plan SKILL.md gains guidance: prefer many small, file-disjoint tasks; give each TDD acceptance criteria (tests first); reference the new convergence warning; state that a parallel build must equal a serial build because the tests are the contract
  - markdownlint-cli2 passes; the skill's worked example yields a plan whose waves contain >1 task (demonstrably parallel)

### t6 — Dogfood: run assign-to-workforce on a real converged plan and capture the worked example

- depends on: t1
- covers: h23
- acceptance:
  - A worked example (in the skill or docs/) runs the flow on a real converged plan's waves: split-plan -> parallel subagents in worktrees -> TDD-gated merges, recording the qualitative speed/cost difference vs a serial build, with the TDD gates holding
  - The example is reproducible from the committed plan + 'devague plan waves' output

## Risks

- [unknown_nonblocking] Quantitative speed/cost benchmarking (measured wall-clock/token savings) is out of scope for #13; the win is demonstrated qualitatively via the worked example, not measured (task t6)
- [out_of_scope] A turnkey orchestrator that actually spawns subagents/worktrees is out of scope; assign-to-workforce is operator guidance + a waves/split-plan helper — the operating agent performs the fan-out (CLI stays non-orchestrating, #20) (task t1)
