# Build Plan — devague multi-repo efforts

slug: `devague-multi-repo-efforts` · status: `exported` · from frame: `devague-multi-repo-efforts`

> devague supports multi-repo efforts: one effort — frame, plan, and workforce fan-out — can span multiple repositories instead of stopping at the edge of a single repo

## Tasks

### t1 — Plan schema: optional repo target on Task (plan.py, plan_store.py)

- covers: c6, h2
- acceptance:
  - a task with a repo target round-trips save/load verbatim; the field is descriptive text (a repo name), owned by plan.py + plan_store.py only
  - pre-existing plans and repo-less tasks load with no error — an absent repo means the effort's home repo (h2); plan schema_version bumped once, fail-closed, on top of the #53 t2 bump

### t2 — CLI: `plan task --repo <name>` flag + `retarget <tN> --repo <name>` move (cli/_commands/plan.py)

- depends on: t1
- covers: c6
- acceptance:
  - `plan task --repo <name>` stores the repo target verbatim and `plan show --json` includes it per task
  - a new `retarget <tN> --repo <name>` move sets or updates the target on an existing task and flips a confirmed task back to proposed — the user re-confirms (mirrors the #53 instruction re-confirm rule)

### t3 — Waves: repo target in the enriched `waves --json` payload (cli/_commands/plan.py)

- depends on: t1, t2
- covers: c7, h3
- acceptance:
  - every task entry in `waves --json` carries its repo target verbatim as descriptive text the operator resolves — no filesystem validation anywhere (h3); repo-less tasks emit the home-repo default
  - output stays deterministic and read-only; the dependency-wave computation itself is untouched (frame non-goal c10)

### t4 — Docs: spec-contract + hub-repo state model (docs/spec-contract.md, docs/llm-guidance.md, docs/skills.md)

- depends on: t1
- covers: c3, h8
- acceptance:
  - docs/spec-contract.md documents the task repo target, the hub-repo state home (the cwd-relative store — store.py:15-18, plan_store.py:18-19 — stays unchanged, cited), and the plan schema bump
  - docs/llm-guidance.md and docs/skills.md updated to match; the single-repo default is described as the unchanged base case (h8)

### t5 — assign-to-workforce: multi-repo fan-out method (SKILL.md)

- depends on: t3
- covers: c8, h4
- acceptance:
  - SKILL.md documents per-repo worktrees (one per task, created in that task's target repo), the per-repo TDD gate — a task's tests pass before and after the merge in that task's repo; a green suite in one repo never vouches for another (h4)
  - gate 3 documented as one final PR per touched repo, reviewed together as one effort; cross-repo deps are satisfied at worktree-merge time, not PR-merge time (decision c18); the single-repo flow reads unchanged

### t6 — split-plan script: repo column from the enriched payload (assign-to-workforce.sh)

- depends on: t3, t5
- covers: c8, c2
- acceptance:
  - split-plan renders each task's repo target from `waves --json` in the implementation split table; single-repo plans render unchanged
  - the script stays skill-side — no CLI change, no orchestration added to the devague package

### t7 — Operator skills + CLI teaching surface (/spec-to-plan, /think, /scope SKILL.md; learn.py, explain.py)

- depends on: t2, t3
- covers: c2, h7
- acceptance:
  - /spec-to-plan documents `--repo <name>` and `retarget <tN>` with a worked multi-repo example; /think and /scope document the hub-repo state home for a multi-repo effort
  - `devague plan learn` and `devague plan explain` cover the repo target; the whole surface is exercised through the four existing operator skills — no new privileged tooling (h7)

### t8 — E2E dogfood across >=2 real repos + boundary audit

- depends on: t4, t6, t7
- covers: c1, h1, c4, h9, c5, h10, c9, h5, c14, h6
- acceptance:
  - one real effort touching >=2 actual repos (hub: this repo; candidate sibling: guildmaster or eidetic-cli) runs scope -> frame -> plan -> fan-out on the shipped surface, committed as a worked example or e2e evidence (h6), converging and exporting without hand-editing state JSON (h1)
  - boundary audit (grep/bandit, the #53 t14 pattern) shows no git plumbing, repo I/O, or subprocess orchestration added to the devague package (c9/h5)
  - the worked example demonstrably addresses the four user-reported pain points — shared convergence, task-to-repo mapping, fan-out mechanics, cross-repo review (c4/h9) — in the decided shape: hub-repo state, repo-tagged tasks, per-repo PRs (c5/h10)

## Risks

- [follow_up] external precondition: the #53 build (t2/t5/t9 there — instruction fields + enriched waves payload) lands before this plan's t1/t3; a dependency on another plan's tasks cannot be recorded in this graph (decision c19) (task t1)
- [unknown_nonblocking] the e2e run needs a second real repo willing to take a dogfood PR — candidate guildmaster or eidetic-cli; pick at execution time (task t8)
- [follow_up] `plan confirm` takes one id per call (no transactional multi-id parity with the frame engine yet — recorded follow-up in #53); batch-confirming multi-repo plans stays manual until then
