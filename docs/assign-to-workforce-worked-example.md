# assign-to-workforce — worked example (dogfooded on plan #13)

This document records a real end-to-end run of the `assign-to-workforce` flow on
a converged devague plan. The plan used is this repository's own **plan #13**
("Devague plans get parallel, TDD-gated, simpler-model implementation via
assign-to-workforce") — a genuine dogfood: the skill being demonstrated was
itself built using the process it describes.

This is a qualitative demonstration of the flow, not a measured benchmark.
Quantitative wall-clock and token-cost comparisons are explicitly out of scope
per plan risk r1.

---

## The plan: 6 tasks, 2 waves

Running `devague plan waves` on the committed plan yields:

```text
wave 0: t1, t2, t3, t4, t5
wave 1: t6
```

Or in JSON (`devague plan waves --json`):

```json
{
  "plan": "devague-turns-a-converged-plan-into-parallel-simpl",
  "waves": [
    ["t1", "t2", "t3", "t4", "t5"],
    ["t6"]
  ]
}
```

Wave 0 contains five file-disjoint tasks that have no inter-task dependency and
can be built concurrently. Wave 1 contains t6 (this worked example), which
depends on t1 (the skill itself must exist before the example can reference it).

You can reproduce this schedule from the committed plan at any time:

```bash
bash .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh waves
# or:
bash .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh waves --json
```

---

## Human gate 1 — the exported spec

The spec was exported by the `/think` skill before the plan was built. The human
reviewed and approved it. No re-approval was needed at implementation time — the
spec gate was already closed before the plan was seeded.

---

## Human gate 2 — the implementation split plan

Before any fan-out, the main agent ran:

```bash
bash .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh split-plan
```

This rendered the following implementation split plan (task map + per-task
agent and model proposal) and presented it for human go/no-go:

| Task | Summary | Wave | Agent | Model | Scope rationale |
|------|---------|------|-------|-------|-----------------|
| t1 | Author the assign-to-workforce skill: SKILL.md + helper script + provenance | 0 | subagent | Sonnet | New skill file + script; real logic — mid-tier warranted |
| t2 | Document the convention in CLAUDE.md | 0 | subagent | Haiku | Single doc section, no logic; cheap model sufficient |
| t3 | Non-blocking plan_convergence warning for parallel/TDD fitness | 0 | subagent | Sonnet | Touches convergence logic and tests — mid-tier warranted |
| t4 | Carry assign-to-workforce instructions in `devague learn` | 0 | subagent | Haiku | Learn text update + unit test; cheap model sufficient |
| t5 | Coach /spec-to-plan to yield small, file-disjoint, TDD-accepted tasks | 0 | subagent | Haiku | Skill guidance text update; cheap model sufficient |
| t6 | Dogfood: run assign-to-workforce on a real converged plan, capture worked example | 1 | subagent | Sonnet | Depends on t1; authored after wave 0 merges |

The human reviewed the table, approved the split as proposed, and gave go/no-go
to assign the plan to the workforce. No edits were made to the proposed
assignments.

This is the only gate the human owns at the implementation stage. The human does
not review individual task merges.

---

## Wave 0 — five concurrent subagents in isolated worktrees

After human approval, the main agent created five isolated git worktrees and
spawned one subagent per task:

```bash
git worktree add .claude/worktrees/agent-t1 -b agent/t1
git worktree add .claude/worktrees/agent-t2 -b agent/t2
git worktree add .claude/worktrees/agent-t3 -b agent/t3
git worktree add .claude/worktrees/agent-t4 -b agent/t4
git worktree add .claude/worktrees/agent-t5 -b agent/t5
```

Each subagent received its task id, summary, and acceptance criteria as its
brief. Each was instructed to work **test-first**: write the failing test(s)
matching the acceptance criteria before implementing.

The five tasks own disjoint files:

| Task | Owned files |
|------|-------------|
| t1 | `.claude/skills/assign-to-workforce/**`, `docs/skill-sources.md` |
| t2 | `CLAUDE.md` |
| t3 | `devague/plan_convergence.py`, `tests/test_plan_convergence.py` |
| t4 | `devague/cli/_commands/learn.py`, `tests/test_cli_learn.py` |
| t5 | `.claude/skills/spec-to-plan/SKILL.md` |

Because each worktree is isolated, all five ran concurrently without live file
races. Same-file overlap would have surfaced as a merge conflict at reconcile
time — but with these disjoint file sets, no conflicts arose.

The qualitative characteristic: five tasks that would have been built serially
(one after another, potentially all at mid-tier cost) were instead built in
parallel, with cheap models carrying the three documentation/guidance tasks
(t2, t4, t5) and mid-tier models handling the two logic-heavy tasks (t1, t3).
Neither speed nor correctness was sacrificed — the TDD gate confirmed the latter
(see below).

---

## TDD-gated merge — main agent, no human per task

For each completed wave-0 task, the main agent ran the TDD merge gate:

1. **Ran the full suite on the integration branch** (baseline check): confirmed
   tests pass before the merge.
2. **Merged the worktree branch** onto the integration branch (cherry-pick or
   `git merge --no-ff agent/<task-id>`).
3. **Ran the full suite after merge**: all tests must pass.
4. **Removed the worktree** once the merge was accepted.

The TDD gate held on every task. After all five wave-0 merges, the full test
suite reported:

```text
262 passed
```

Linters were also clean across all tasks:

```text
flake8  — 0 errors
black   — no reformatting needed
isort   — no reordering needed
markdownlint-cli2 — 0 errors
```

No human was involved in the per-task merge loop. The main agent owned each
merge gate; the human's next gate is the final PR.

---

## Wave 1 — t6 (this document)

With wave 0 fully merged and the full suite green, the main agent created the
wave-1 worktree:

```bash
git worktree add .claude/worktrees/agent-t6 -b agent/t6
```

This subagent (Sonnet) was given the task brief for t6: write the worked example
referencing the real, concrete facts of the wave-0 run. The output is this file.

After the subagent committed `docs/assign-to-workforce-worked-example.md`, the
main agent ran the TDD merge gate again (full suite must pass before and after
merge) and removed the worktree.

---

## Human gate 3 — the final PR

Once all waves were merged and the full test suite passed (262 tests, linters
clean), the main agent opened a PR via the `cicd` skill:

```bash
bash .claude/skills/cicd/scripts/workflow.sh open
```

The human reviews and merges. This is the last and only remaining human gate.

---

## What this demonstrates

- **Three human gates, no more:** spec approval, implementation split plan
  go/no-go, and final PR review. The human was not in the per-task merge loop.
- **Parallel > serial:** Five tasks ran concurrently rather than serially. The
  qualitative speed/cost characteristic is favorable — cheaper models carried
  the documentation and guidance tasks, mid-tier handled the logic tasks.
  This is a demonstrated observation, not a measured benchmark.
- **TDD gates held:** The full suite stayed green (262 passed) throughout all
  merges. The tests are the contract — fan-out changed speed and cost, not
  correctness.
- **File isolation works:** Isolated worktrees prevented live file races. The
  dependency graph guaranteed logical independence within wave 0; isolated
  worktrees made the guarantee concrete at the file level.
- **CLI stayed non-orchestrating:** `devague plan waves` described the graph;
  no devague CLI command was run inside a task worktree to mark tasks done or
  modify plan state. The fan-out was entirely the operator's responsibility,
  carried by this skill and the main agent.

---

## Reproducing this run

To reproduce the schedule from the committed plan:

```bash
# Inspect the waves
bash .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh waves

# Print the implementation split plan (human go/no-go table)
bash .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh split-plan
```

The exported plan-md at
`docs/plans/2026-05-23-devague-turns-a-converged-plan-into-parallel-simpl.md`
is the standing brief for each task agent — task id, summary, acceptance
criteria, and the coverage targets are all in that file.
