# Build Plan — devague ships a sharper end-to-end method: a guided scope-exploration stage before the announcement frame, per-item instructions on every claim and task, sharper spec and plan exports, and a guided plan-to-fanout leg that carries those instructions to the workforce.

slug: `devague-ships-a-sharper-end-to-end-method-a-guided` · status: `exported` · from frame: `devague-ships-a-sharper-end-to-end-method-a-guided`

> devague ships a sharper end-to-end method: a guided scope-exploration stage before the announcement frame, per-item instructions on every claim and task, sharper spec and plan exports, and a guided plan-to-fanout leg that carries those instructions to the workforce.

## Tasks

### t1 — Frame schema: scope entries + per-item instruction fields (frame.py, store.py)

- covers: c10, h3, c4, h9
- acceptance:
  - a frame with scope entries and per-item instructions on claims/honesty conditions saves and loads identical (round-trip test)
  - loading a pre-existing frame without the new fields succeeds with empty defaults; schema_version bumped once, fail-closed

### t2 — Plan schema: per-task instruction field (plan.py, plan_store.py)

- covers: c10
- acceptance:
  - a plan task with an instruction round-trips verbatim through save/load; schema_version bumped once
  - pre-existing plans load with no instruction and no error

### t3 — New CLI move: devague scope (cli/_commands/scope.py + registration)

- depends on: t1
- covers: c9, h2, c6, c4, h9
- acceptance:
  - devague scope records an explored surface + finding as first-class state with provenance and optional --seeds <claim-id> links; unknown claim id refused with a hint
  - scope --list and --json render the recorded entries; the move is deterministic — no LLM calls, no subprocess

### t4 — Instruction flags on frame moves: capture/interrogate --instruction (capture.py, interrogate.py)

- depends on: t1
- covers: c10
- acceptance:
  - capture --instruction and interrogate --instruction store the instruction verbatim on the item; devague review lists instructions alongside their items
  - adding or changing an instruction on a confirmed claim/honesty condition flips it back to proposed — the user re-confirms (user decision, gate-2 review)

### t5 — Instruction flags on plan moves: plan task --instruction + instruct <tN> (cli/_commands/plan.py)

- depends on: t2
- covers: c10
- acceptance:
  - plan task --instruction stores verbatim; a new instruct move adds/updates an instruction on an existing task; plan show --json includes it
  - adding or changing an instruction on a confirmed task flips it back to proposed — the user re-confirms (user decision, gate-2 review)

### t6 — Sharper frame renderers: instruction blocks + scope provenance (render/spec_md.py, render/frame_md.py)

- depends on: t1
- covers: c11, h4, h3, c8, h12, c3, h2
- acceptance:
  - exported spec-md renders each item's instruction block verbatim and a scope-provenance section citing explored surfaces; items without instructions render nothing (golden-file test)
  - renderer change lands against the user-confirmed definition of sharper (decision c14)

### t7 — Frame gate tightening: deterministic structural sharpness checks (convergence.py)

- depends on: t1
- covers: c5, h10, h6
- acceptance:
  - gate emits structural warnings — spec-affecting claim without instruction, missing measurable success signal — via explicit documented rules, never LLM judgment
  - existing converged frames still converge: new checks land as warnings first (soft rollout per parked v2)

### t8 — Plan gate tightening: instruction warnings (plan_convergence.py)

- depends on: t2
- covers: h6
- acceptance:
  - plan gate warns when a confirmed task lacks an instruction; existing plans converge unchanged

### t9 — Sharper plan renderer + enriched waves payload (render/plan_md.py, waves output)

- depends on: t2, t5
- covers: c12, c11, h3, c8, h12
- acceptance:
  - exported plan-md renders a per-task instruction block verbatim; tasks without instructions render nothing (golden-file test)
  - plan waves --json payload carries each task's summary, instruction, acceptance criteria, and covered targets — enough for a subagent brief with no external context

### t10 — Teaching surface: learn/explain/status know the scope stage (learn.py, explain.py, cli/_status.py)

- depends on: t3, t4, t5
- covers: c9
- acceptance:
  - devague learn presents the scope-exploration stage in the arc as optional-but-recommended (non_goal c7: small ideas may skip it)
  - devague explain scope and devague explain question both work (question is unknown to explain today)

### t11 — Operator skills teach the new surface (/think and /spec-to-plan SKILL.md)

- depends on: t3, t4, t5
- covers: c9
- acceptance:
  - /think documents the scope stage and --instruction flags with a worked example; /spec-to-plan documents task instructions and the enriched waves payload

### t12 — Docs: spec-contract, llm-guidance, skills.md cover scope entity + instruction fields

- depends on: t1, t2
- covers: c9
- acceptance:
  - docs/spec-contract.md documents the scope entity, instruction fields, both schema bumps, and the new gate rules; docs/llm-guidance.md and docs/skills.md updated to match

### t13 — assign-to-workforce consumes the enriched waves payload as the subagent brief

- depends on: t9
- covers: c12, h5, c8, h12, h7, c6, c4, h9
- acceptance:
  - the skill's per-subagent brief quotes the task's instruction and acceptance criteria verbatim from waves --json — the operator-paraphrase step is gone from the skill text

### t14 — Dogfooded end-to-end run + boundary audit

- depends on: t6, t7, t8, t9, t10, t11, t13
- covers: c1, h1, c2, h7, c3, h8, h11
- acceptance:
  - one real idea runs scope -> frame -> sharper spec -> plan -> fanout brief using only the shipped surface, committed as an e2e test or worked example
  - audit shows no LLM calls, no subagent spawning, no worktree management anywhere in the devague package (grep/bandit evidence)

## Risks

- [unknown_nonblocking] which exact deterministic structural-sharpness rules land first, and the false-positive story when they misfire on legitimate prose (soft rollout as warnings mitigates) (task t7)
- [follow_up] confirm-loop ergonomics when every claim and task can carry an LLM-proposed instruction — batch-confirm UX may be needed as a follow-up (task t4)
