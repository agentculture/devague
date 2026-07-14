# execution seam and deviate

> devague closes the execution seam: a deliverables view answers what we have in the end at the go or no-go, the split plan renders the table humans actually approve, dependency edges can be removed without task recreation, and human-approved deviations become first-class records that connect the plan to the delivery summary

## Audience

- devague operators (the main agent driving the CLI) and the humans at the go or no-go and final-PR gates

## Before → After

- After: after this ships: the go or no-go presents what exists once every task completes, sourced from state alone; deviations from the confirmed plan are recorded with reason, impact, and human approval, and the delivery summary quotes them instead of reconstructing drift from memory; a wrong dependency edge costs one move to fix instead of a task-recreation cascade; and issues 62, 66, and 67 are closed with cited evidence

## Why it matters

- the plan is a contract: without an end-state view the human approves a workforce without seeing the world after the work; without recorded deviations the delivery summary rebuilds drift from unrecorded memory; without edge removal an honest one-word correction costs an unbounded rewrite of dependent tasks

## Requirements

- new read-only `devague plan deliverables` view (name pending q-decision) answers what exists once every task completes, synthesized only from existing state: the frames confirmed announcement, `after_state`, and `success_signal` claims, terminal tasks (tasks no active task depends on) with their acceptance criteria, and surviving parked vagueness; `--json` emits the same structured payload; no mutation, no LLM calls (issues 70 and 20)
  - honesty: verifiable by inspection and test: the deliverables code path performs zero store writes and zero subprocess or network calls; a test renders the view twice and the state files stay byte-identical
- the assign-to-workforce split-plan presentation gains an End state section sourced from the deliverables view, and the skill doc gains one line telling the operator to include it at the go or no-go (issue 70)
  - honesty: the End state section is produced by quoting the CLI deliverables output verbatim, never composed freehand by the operator; the skill doc names the exact move to run
- split-plan renders one markdown table with exactly the columns Wave, Task, Model, Task summary, ordered by wave then task id, real verbatim summaries (truncated when long), and an honest per-row model default instead of the constant cheaper/faster; the go or no-go prompt and the wave listing stay (issue 69)
  - honesty: the rendered table matches the issue 69 ask verbatim: header Wave, Task, Model, Task summary; rows ordered by wave then task id; asserted by a script-level test
- a dependency edge can be removed without recreating tasks; smallest shape is a remove flag on `devague plan depend` (final shape pending q-decision), and removing an edge on a confirmed task flips it to proposed with the same visible note the instruct move prints (issue 68)
  - honesty: after removing an edge the task keeps its summary, acceptance criteria, covers, and instruction unchanged, and converge no longer reports the removed edge; round-trip covered by a test
- culture.yaml declares backend claude, the mesh standard; unblocked because agex-cli issue 46 is closed and devex 0.30.0 maps claude onto claude-code; the agex pr lane is re-verified after the edit (issue 66)
  - honesty: agex pr open succeeds from this repo with backend claude in culture.yaml, verified live before the PR carrying the change merges
- new deterministic `devague deviate` move records a human-approved deviation from the confirmed plan at the moment it happens: the plan item it deviates from, the reason, what it affects, and the approval; llm-recorded deviations land proposed until the user confirms them, per the standing anti-fabrication contract
  - honesty: a deviate record without the explicit approval marker is refused; an llm-origin deviation lands proposed and never counts as approved until the user confirms it
- new sixth origin skill `/deviate`, the execution-time leg in the flow scope, think, spec-to-plan, assign-to-workforce, deviate, summarize: when execution must diverge from the plan it stops the run, gets explicit human approval, records the deviation via the CLI move, and adjusts the affected task briefs
  - honesty: the skill hard rules make the stop-and-get-approval step unskippable: no deviation is recorded that the human did not approve, mirroring the confirm-is-user-only contract
- the summarize-delivery skill consumes recorded deviations: its Drift From Plan and Mid-work Decisions sections quote deviation records verbatim instead of reconstructing drift from memory, making deviate records the connective tissue between the confirmed plan and the delivery summary
  - honesty: the summarize-delivery template names deviation record ids in its Drift From Plan rows, so every drift entry traces to a recorded, approved deviation whenever one exists
- new `devague plan amend` move edits a task summary and replaces or removes acceptance criteria; amending a confirmed task flips it to proposed with the visible re-confirm note (issue 68, resolved q1)
  - honesty: amend round-trips: the summary and criteria change exactly as asked, everything else on the task is untouched, and the flip note appears when the task was confirmed; covered by tests
- moves that demote a confirmed task (`instruct`, `amend`, `depend --remove`) name the confirmed-to-proposed flip on the stdout result line, not only on stderr and in JSON (issue 67 hardening, resolved q4)
  - honesty: a harness reading only stdout still sees the flip: asserted by a test that captures stdout alone
- new deterministic `devague summary [--pr] [--json]` renders a wrap-up from existing state only: the eight-section delivery-summary skeleton pre-filled verbatim from the frame (announcement, after state), the plan (every task id and summary), and approved deviation records, with explicit fill-me placeholders for run status, per-task delivery status, evidence, and claims — nothing ever renders as done from state alone; `--pr` emits a condensed PR-body skeleton for the cicd lane; the summarize-delivery skill starts from this skeleton instead of hand-assembling the baseline (resolves q6)
  - honesty: the skeleton is deterministic and fabrication-free: rendering twice yields identical output, every pre-filled line traces verbatim to frame, plan, or deviation state, no placeholder ever renders as a completed claim, and the PR mode is covered by a stdout-only test

## Honesty conditions

- holds only if every leg the announcement names ships in the same release: deliverables view, four-column split-plan table, dependency-edge removal, the deviate move and skill, and the three evidence-based issue closures
- deliverables performs no mutation at all; deviate mutates only its own record; grepping the new code paths finds no agent spawning, no worktree management, no merge gating, and no LLM call
- matches the three-reader model already shipped in the summarize-delivery skill: the operator, the human at the gates, and the later reader who never watched the run
- every element of the after state is checkable from committed artifacts: the view output, the deviation records, a passing edge-removal test, and the issue timelines
- each pain it names traces to a filed issue: 70 for the missing end-state view, 62 plus the deviate gap for drift-from-memory, 68 for the recreation cascade
- the numbers are measurable as written: six of six issues closed on the tracker, zero LLM calls verified by inspection, coverage read from the CI gate at or above 95 percent

## Success signals

- 6 of 6 bundled issues end closed (3 by shipped code, 3 by cited evidence); the deliverables and deviate code paths ship with 0 LLM calls and 0 orchestration, verified by inspection; test coverage stays at or above 95%

## Scope / boundaries

- the CLI stays deterministic and non-orchestrating (issue 20): deliverables and deviate record and describe state; they never spawn agents, mark tasks done, gate merges, or call an LLM

## Non-goals

- no full delivery engine in this release: the third structural peer parked in the summarize-delivery skill stays parked; deviate records are the smallest slice of execution-side state, and where they persist is a pending question

## Assumptions

- persisting deviations or removable edges on the plan JSON bumps PLAN_SCHEMA_VERSION from 2 to 3; the 0.17.0 upgrade-on-write fix means older binaries refuse the newer file instead of silently dropping fields

## Scope exploration

- `s1` — `devague/plan.py + devague/plan_convergence.py`: add_dep is append-only, no removal move exists anywhere in the plan verb set, reject does not prune inbound edges, and dependency_blockers reports depends-on-rejected as an integrity failure, so the issue 68 reject-and-recreate cascade is real; terminal tasks are computable from Task.deps alone, no new state needed
  - seeds: `c5`, `c14`
- `s2` — `devague/cli/_commands/plan.py cmd_plan_instruct + scratchpad repro on 0.17.2`: instruct already prints the flip note on stderr and emits flipped true in JSON, shipped in 0.16.0 commit 92c60ca; an end-to-end repro on 0.17.2 (converged frame, confirmed task, instruct) shows both streams, so issue 67 came from a harness that dropped stderr, not from current code
  - seeds: `c10`
- `s3` — `devague/frame.py CLAIM_KINDS`: announcement, after_state, and success_signal are first-class claim kinds already, so the deliverables view synthesizes from existing frame state with no schema change on the frame side
  - seeds: `c2`
- `s4` — `.claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh split-plan`: split-plan already renders verbatim task summaries from the enriched waves payload since 0.16.0 t13, so the placeholder half of issue 69 is fixed; the remaining delta is table shape: eight columns today with the model column hardcoded to cheaper/faster
  - seeds: `c3`, `c4`
- `s5` — `.claude/skills/summarize-delivery/SKILL.md`: all six issue 62 acceptance criteria are met by the shipped 0.17.0 skill; a future delivery engine is explicitly parked in the doc; the Drift From Plan and Mid-work Decisions sections are the natural consumers of recorded deviations
  - seeds: `c7`, `c8`, `c9`, `c11`, `c13`
- `s6` — `culture.yaml + devex 0.30.0 core/backend.py + closed agex-cli issue 46`: backend claude-code was a stopgap for an agex rejection that upstream has since fixed: devex 0.30.0 maps claude onto claude-code with an explicit comment naming the culture.yaml standard, so the mesh-standard value now works end to end
  - seeds: `c6`
- `s7` — `issue 20 + CLAUDE.md non-orchestration boundary`: the deterministic non-orchestrating contract covers both new moves cleanly: deliverables reads and renders, deviate records state the human approved; neither executes anything
  - seeds: `c12`

## Decisions

- issue 67 is already fixed: plan instruct has warned on the confirmed-to-proposed flip since 0.16.0 (stderr note plus flipped true in JSON), verified empirically on 0.17.2; close it with the repro evidence (whether to also echo the flip on stdout is a pending question)
- issue 62 is already delivered: the summarize-delivery skill shipped in 0.17.0 meeting all six acceptance criteria, with the dogfood artifact docs/deliveries/2026-07-09-sharper-end-to-end-method.md; close it citing the release
- issue 68 ships as two explicit moves: a remove flag on `devague plan depend` to cut a single edge, plus a new `devague plan amend` move to edit a task summary and replace or remove acceptance criteria; reject does not auto-prune edges — every transition stays visible (resolves q1)
- the deliverables view ships as the read-only verb `devague plan deliverables` with `--json`, peer of waves and status; on an unconverged plan it renders with an explicit not-converged banner rather than refusing (resolves q2)
- deviation state lives in a new delivery store under `.devague/deliveries/` keyed by plan slug — the first deterministic slice of the parked delivery engine; the plan JSON stays byte-identical through execution (resolves q3)
- issue 67 closes with the repro evidence plus a one-line hardening: the stdout result line itself names the confirmed-to-proposed flip, because the report proves agent harnesses drop stderr (resolves q4)
- the split-plan table renders strictly Wave, Task, Model, Task summary; the wave-batch listing above it gains per-task has-instruction and acceptance-criteria-count markers (resolves q5)
- this release ships a render-only `devague summary` verb at the top level, pairing with `devague deviate` as the two execution-side verbs over the delivery store; the full delivery engine (delivery-record moves plus a no-overclaim gate) stays parked per the standing non-goal (resolves q6)
