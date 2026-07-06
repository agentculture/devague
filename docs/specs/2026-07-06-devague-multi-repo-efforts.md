# devague multi-repo efforts

> devague supports multi-repo efforts: one effort — frame, plan, and workforce fan-out — can span multiple repositories instead of stopping at the edge of a single repo

## Audience

- the operator agent + user running efforts that span AgentCulture sibling repos (e.g. devague + guildmaster + eidetic-cli), and the workforce subagents briefed per task

## Before → After

- Before: an effort lives in one cwd-relative .devague/ per repo (store.py:1-3 'the frames live in the repo being specced'; plan_store.py:18) — a cross-repo effort must be hand-split into disconnected per-repo frames with no shared convergence gate
- After: one effort spans repos end-to-end: tasks name their target repo, the waves payload briefs the workforce per repo, and the human gates stay explicit across all touched repos

## Why it matters

- the last Colleague-assisted effort showed real efforts scale past one repo; devague's honesty gates should cover the whole effort, not stop at the repo edge

## Requirements

- a plan task can name the repo it targets — devague/plan.py Task carries summary/acceptance/deps/covers today, no repo dimension; the workforce brief needs one
  - honesty: existing single-repo frames/plans load unchanged: repo-less tasks stay valid (fail-closed schema bump, default = the effort's home repo)
- the waves payload carries each task's repo target so the operator creates the worktree in the right repo — cli/_commands/plan.py:326 emits bare task ids today; natural carrier is the #53 t9 enriched payload
  - honesty: the repo field in `waves --json` is descriptive text the operator resolves — devague never validates it against the filesystem
- assign-to-workforce covers the multi-repo fan-out: per-repo worktrees, per-repo TDD gates, and the final-PR gate across every touched repo — SKILL.md today hard-assumes one repo (one `../worktrees` root, one main branch, one final PR)
  - honesty: the TDD gate runs per repo: a task's tests pass before and after the merge in that task's repo; a green suite in one repo never vouches for another

## Honesty conditions

- honest only if a plan whose tasks target >=2 repos converges and exports without hand-editing state JSON
- the multi-repo surface is exercised entirely through the existing operator skills (scope/think/spec-to-plan/assign-to-workforce) — no new privileged tooling beyond what the audience already runs
- verified against the shipped code at 0.15.0: store.py:15-18 and plan_store.py:18-19 are cwd-relative and no repo field exists in frame.py or plan.py
- the four pain points are the user's own report (2026-07-07): no shared convergence, task-to-repo mapping, fan-out mechanics, review across repos — not inferred
- honest only if every element is deliverable by the decided shape: hub-repo state (q2), repo-tagged tasks in one plan (q3), per-repo PRs with worktree-merge dependency ordering (q4)
- a boundary audit (grep/bandit, as in #53 t14) shows this effort added no git plumbing, repo I/O, or subprocess orchestration to the devague package
- the end-to-end run is real (>=2 actual repos, committed as a worked example or e2e evidence), not a single-repo run relabeled

## Success signals

- one real effort touching >=2 repos runs scope -> frame -> plan -> fan-out end-to-end on the shipped surface, with each task built in its target repo and every touched repo getting its reviewed PR

## Scope / boundaries

- the CLI stays deterministic and non-orchestrating (issue 20): multi-repo lands as descriptive metadata only — the CLI never clones a repo, never reads or writes another repo's files, never manages worktrees or backends

## Non-goals

- no change to dependency-wave computation — plan.py:172 dependency_waves layers tasks purely by deps and is already repo-agnostic
- devague is not becoming a workspace manager or monorepo tool: no repo discovery, no checkout management, no cross-repo git plumbing in the CLI

## Assumptions

- multi-repo lands on top of the committed #53 sharper-method plan (t1-t14, unimplemented) without forking it — per-item instructions (t2/t5) and the enriched waves payload (t9) are carriers for repo targets, not competitors
- the motivating Colleague effort is the eidetic 3-layer memory plan spanning eidetic-cli, devague skills, and culture agents (eidetic recall, record of 2026-06-20) — to be confirmed by the user

## Decisions

- pain points (user, 2026-07-07, q1): the Colleague effort lacked shared convergence, task-to-repo mapping, fan-out mechanics, and cross-repo review — all four are the problem to solve
- state home (q2): the effort's hub repo holds the single .devague/ frame+plan; sibling repos are referenced by name in tasks — the cwd-relative store is unchanged
- granularity (q3): one frame + one plan per effort with repo-tagged tasks; one convergence gate and one dependency graph across repos — no meta-frame layer
- human gate 3 (q4): one final PR per touched repo, reviewed together as one effort; a cross-repo dependent task starts when its dependency's worktree merge (main-agent TDD gate) lands, not its PR merge
- sequencing (q5): this effort exports its own spec+plan building on the #53 carriers (per-item instructions t2/t5, enriched waves t9), implemented after t1-t14 — the committed #53 plan is not reopened
