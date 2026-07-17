# resolve parked vagueness

> devague ships a resolve move for parked vagueness: a blocking park can now be resolved or reclassified through CLI moves alone, closing issues 45, 55, 57, and 60
> instruction: on the shipped build run issue 57's repro: park a blocking unknown, capture the decision, park --resolve it, converge passes, export succeeds — no file edits

## Audience

- operators driving /think and /spec-to-plan (the agents making CLI moves), the humans who own confirms, and the downstream AgentCulture repos that filed the four reports — colleague, lobes-cli, league-of-agents, and devague's own dogfooding

## Before → After

- After: a parked blocking unknown, once decided, is closed through `park --resolve` (frames) or `plan risk --resolve` (plans): the item stays on record with its resolution text, drops out of the convergence gate, the converge hints name executable moves, and no operator ever hand-edits .devague state again

## Why it matters

- four independent reports in five weeks (issues 45, 55, 57, 60) show the method punishing correct behavior: honest parking leads to a permanently blocked frame, and the only escape is the exact out-of-band state mutation the move-driven design exists to prevent — one repo has the hand-edit in committed history (league-of-agents 0c71282)

## Requirements

- the Vagueness dataclass (devague/frame.py:106) gains resolution state — e.g. a resolved flag plus resolution text — kept in frame state for the evidence trail rather than deleted; add_vagueness today only appends and set_status (frame.py:226) routes only claim and honesty ids, so v-ids are unaddressable by any move
  - instruction: extend Vagueness with resolved: bool = False and resolution: str = ""; round-trip tests in tests/test_frame.py and tests/test_store.py
  - honesty: a resolved Vagueness keeps its text, kind, and claim_id plus the resolution on the record, and round-trips save-load identical
- the convergence gate (devague/convergence.py:100-102) stops counting a resolved vagueness as a blocker, and suggest_move (convergence.py:188) names an actually executable move instead of today's 're-park it as non-blocking' hint, which only appends a second item while the first keeps blocking — the acceptance bar issue 45 sets explicitly
  - instruction: in _missing_open_uncertainty skip resolved items; rewrite the suggest_move blocking-vagueness branch (convergence.py:188) to emit the park --resolve syntax; tests in tests/test_convergence.py
  - honesty: after park --resolve, converge no longer lists the item as a blocker and the blocking-vagueness hint names park --resolve verbatim — an executable move, issue 45's acceptance bar
- a new user-only resolve surface for v-ids that mirrors the existing `question --resolve <qid> --decision "<text>"` shape (devague/cli/_commands/question.py) — resolving is a user decision like confirm (issue 55), validated fail-closed with a hint on an unknown v-id, with stdout result, --json, and the existing exit-code contract
  - instruction: add --resolve VID and --decision to park's argparse in cli/_commands/park.py; unknown id raises DevagueError with a 'run devague show' hint; CLI tests in tests/test_cli_moves.py
  - honesty: an unknown v-id is refused with a hint and nothing is persisted; output follows the existing stdout/--json/exit-code contract; resolving stays a user-decided move like confirm
- SCHEMA_VERSION bumps 2 to 3 (devague/frame.py:15) because adding fields to Vagueness breaks old loaders — from_dict does Vagueness(**v) (frame.py:284), so an old CLI reading a new frame raises TypeError; the documented fail-closed policy and the v2 scope_entries precedent both say bump; docs/spec-contract.md's Vagueness entity section gains the resolved state
  - instruction: bump SCHEMA_VERSION to 3 in devague/frame.py; from_dict defaults resolved/resolution for old artifacts; fail-closed + back-compat tests in tests/test_store.py and tests/test_frame_schema_v2.py's pattern
  - honesty: a v3 frame on a v2-only binary fails closed with the schema_version error, never a Vagueness(**v) TypeError; v2 frames without the new fields still load with defaults
- renderers keep a resolved vagueness on the record as provenance instead of dropping it — render/frame_md.py:56-60 lists every open_vagueness item flat, and render/spec_md.py:111 routes only follow_up/out_of_scope kinds into the spec; a resolved item should render with its resolution text so the exported spec shows the answered unknown (the provenance issue 45's comment asks for)
  - instruction: render resolved items with their resolution in render/frame_md.py and render/spec_md.py; golden updates in tests/goldens plus the markdownlint integration test
  - honesty: an exported spec from a frame with a resolved blocking park renders the unknown together with its resolution text, and the export passes markdownlint
- every surface that teaches park also teaches the resolve close-out: devague/cli/_commands/learn.py (move table line 26, operating rules line 107), docs/llm-guidance.md (park rows in the fabrication table, lines 109-130), and .claude/skills/think/SKILL.md (move table line 82, rules lines 209-210) — otherwise operators keep learning the trap issues 45/55/57/60 all fell into
  - instruction: sweep learn.py (move table + operating rules), docs/llm-guidance.md park rows, and .claude/skills/think/SKILL.md move table and rules; teaching tests in tests/test_cli_learn.py
  - honesty: learn, docs/llm-guidance.md, and the think skill each name park --resolve wherever they teach park; issue 57's prefer-question workaround guidance is retired
- the plan engine ships the twin in the same PR: PlanRisk (devague/plan.py:60) gains the same resolution state, `plan risk --resolve <rN>` the same user-only surface, plan_convergence.py:136 skips resolved risks, the hint at plan_convergence.py:172 names the executable move, and PLAN_SCHEMA_VERSION bumps 2 to 3 (PlanRisk(**r) at plan.py:310 has the same old-loader crash shape as the frame side)
  - instruction: mirror the frame-side change end to end: PlanRisk.resolved/resolution, plan risk --resolve RID --decision, plan_convergence skip + hint, PLAN_SCHEMA_VERSION 3; tests across tests/test_plan.py, test_plan_convergence.py, test_plan_store.py, test_cli_plan.py
  - honesty: plan converge drops a resolved blocking risk; the plan hint at plan_convergence.py:172 names plan risk --resolve verbatim; a v3 plan fails closed on a v2-only binary
- every secondary reader of open vagueness and plan risks handles resolved items consistently, not just the gate: _parked_items in convergence.py:151 and plan_convergence.py:141 (whose output feeds converge/status parked_items), and render/deliverables_md.py:72-81 (plan deliverables' surviving-open-items section, which reads frame.open_vagueness and plan risks directly) — a resolved item must stop being advertised as open everywhere, or status and deliverables contradict the spec
  - instruction: filter (or annotate) resolved items in _parked_items of convergence.py and plan_convergence.py and in deliverables_md's open-items builder; tests in tests/test_convergence.py, test_plan_convergence.py, test_plan_deliverables.py
  - honesty: with a resolved blocking item on a frame and a resolved blocking risk on a plan: converge/status parked_items and plan deliverables' open-items section show neither as open — verified by tests against those exact surfaces

## Honesty conditions

- the shipped release clears a decided blocking park via CLI moves alone — issue 57's repro converges with zero .devague JSON edits
- the diff adds no LLM call and no subprocess to the CLI; resolution text is authored by the user/operator, never generated in-CLI
- devague learn output alone teaches the close-out (park --resolve and plan risk --resolve) — an operator never needs to read source to escape a decided blocking park
- no .devague hand-edit remains necessary anywhere in the vagueness lifecycle: park, decide, resolve, converge, export all work through moves
- each of the four issues is closed with a comment naming the shipped release and the move that replaces its documented workaround
- the stated numbers are verified before close: 4 issues closed, the repro converges with 0 hand-edits, coverage >= 95% in CI

## Success signals

- all 4 issues close against the shipped release; issue 57's repro script (park blocking, decide, resolve, converge) passes through moves alone with 0 hand-edits of .devague state; test coverage stays >= 95%

## Scope / boundaries

- the resolve move is deterministic recording only — no LLM calls in the CLI (issue 20), and hand-editing .devague state stays forbidden; the fix removes the last reason operators had to hand-edit (the workaround all four issues document), it does not legitimize state edits

## Non-goals

- no task-text or claim-text edit verb ships in this fix: issue 60's plan-side half is already shipped as `devague plan amend` (0.18.0, issue 68 — edits a task summary and acceptance criteria, flips confirmed back to proposed), and its floated `devague edit <cN> --text` frame-claim parity is a separate feature, not part of the shared vagueness-resolve gap
- no unresolve move ships: a mistakenly resolved vagueness is recovered by parking a fresh item (append is cheap and keeps provenance), not by reopening the resolved record — avoiding a second one-way-mutation surface in the same PR

## Assumptions

- reclassification ships as two executable moves — `park --resolve <vN>` closing the old item plus a fresh `park --kind <new-kind>` — not an in-place kind mutation; this satisfies issue 45's acceptance (the item stops blocking, stays on record) with cleaner provenance than editing kind in place, and issue 45 offered any-one-of-three shapes

## Scope exploration

- `s1` — `devague/frame.py (Vagueness model, set_status)`: Vagueness has fields id/text/kind/claim_id only — no resolved state; add_vagueness appends with a fresh v-id; set_status routes only c*/h* ids, so no existing move can touch a v-id
  - seeds: `c2`
- `s2` — `devague/convergence.py (gate + suggest_move)`: only kind unknown_blocking blocks (lines 100-102); suggest_move line 188 recommends 'capture+confirm the answer, or re-park it as non-blocking' — neither branch can clear the blocker: capture+confirm never touches the v-item (confirmed live in issue 45's lobes-cli comment) and re-park appends a new id
  - seeds: `c3`
- `s3` — `devague/cli/_commands/park.py + question.py + confirm.py`: park is append-only (cmd_park calls frame.add_vagueness, no flags beyond --kind/--claim); question.py already ships the --resolve/--decision close-out pattern issues 45/57 ask to mirror; confirm.py shows the transactional validate-first, user-only convention the resolve move must follow
  - seeds: `c4`
- `s4` — `docs/spec-contract.md (Vagueness entity, Versioning) + devague/frame.py:15,284`: contract lists Vagueness as id/text/kind/claim_id with no resolved state; SCHEMA_VERSION comment says bump when the persisted shape changes incompatibly; Vagueness(**v) in from_dict means new fields crash old binaries — same shape as the v2 scope_entries bump
  - seeds: `c5`
- `s5` — `devague/render/spec_md.py:111 + render/frame_md.py:56-60`: frame_md renders all open_vagueness as flat '[kind] text' bullets; spec_md renders only follow_up/out_of_scope kinds — neither has a representation for a resolved item, so rendering is a real decision surface, not free
  - seeds: `c6`
- `s6` — `devague/cli/_commands/learn.py + docs/llm-guidance.md + .claude/skills/think/SKILL.md`: all three teach 'park it (blocking or non-blocking)' with no close-out loop; issue 57's interim guidance (prefer question / unknown_nonblocking) exists precisely because the taught path is one-way
  - seeds: `c7`
- `s7` — `devague/cli/_commands/plan.py (amend, instruct, depend --remove)`: plan amend exists since 0.18.0 (issue 68) with the demote-to-proposed echo (issue 67) — issue 60's second complaint (task text immutable after plan task) is already fixed; only its vagueness-resolve half remains live
  - seeds: `c8`
- `s8` — `issue 20 (no-orchestration boundary) + the four issue reports`: issues 45/55/57/60 each document hand-editing .devague/frames/*.json as the only escape — league-of-agents commit 0c71282 has it in committed history; the fix's job is to make the CLI's own contract satisfiable, keeping the deterministic boundary intact
  - seeds: `c9`
- `s9` — `devague/plan.py:60 (PlanRisk) + devague/plan_convergence.py:136,172`: PlanRisk mirrors Vagueness exactly (id/text/kind/task_id, append-only via add_risk, no resolve verb in cli/_commands/plan.py); a blocking plan risk today can only be cleared by covering it with a task — the reclassify/resolve gap is engine-wide, pending the q2 decision
  - seeds: `c10`
- `s10` — `tests/ (test_frame.py, test_convergence.py, test_cli_moves.py, test_contract.py, test_store.py)`: existing park/vagueness coverage lives across these five files; issue 45's acceptance criteria (gate stops listing the item, hint names an executable move, save-load round-trip, valid kinds only) map one-to-one onto them, so the fix lands test-first in the same map
  - seeds: `c2`, `c3`, `c5`
- `s11` — `devague/plan.py:310 + PLAN_SCHEMA_VERSION (plan.py:30) + plan_store.py fail-closed gate`: plan side round-trips risks via PlanRisk(**r) and fails closed on newer schema_version, exactly like the frame side — the twin fix needs its own 2-to-3 bump and mirrors every frame-side piece
  - seeds: `c13`
- `s12` — `challenge pass / adjacent-systems lens: render/deliverables_md.py:72-81 + convergence.py:151 + plan_convergence.py:141`: found two uncovered consumers of open_vagueness/risks beyond the gate and the two renderers the spec already covers: parked_items (status/converge output, both engines) and the deliverables surviving-open-items section — neither was named by any confirmed claim
  - seeds: `c18`
- `s13` — `challenge pass / unstated-assumptions lens: issue 45's reclassify ask vs the c11 decision`: the announcement says 'resolved or reclassified' but no confirmed claim states the reclassify path; c11 chose park --resolve with no --kind flag, so reclassify must be resolve+re-park — made this explicit as a proposed assumption instead of leaving it implied
  - seeds: `c19`
- `s14` — `challenge pass / reversibility lens: the new resolve transition itself`: resolve is one-way by design; recovery from a mistaken resolve exists through a fresh park, so no unresolve verb is needed — recorded as a proposed non-goal so the boundary is explicit
  - seeds: `c20`
- `s15` — `challenge pass / counter-evidence lens: devague/store.py:119-146 fail-closed gate`: verified by reading, not assumed: load raises IncompatibleSchemaError when schema_version exceeds the binary's, and save re-stamps the current version (the comment documents the exact silent-data-loss hazard the re-stamp prevents) — h5's claim holds on the frame side; plan_store mirrors it
  - seeds: `c5`
- `s16` — `challenge pass / concurrency lens: devague/store.py + plan_store.py + delivery_store.py`: clean pass — single-writer CLI, atomic-enough small-file writes, no locking today; resolve adds no new concurrent writer; residual risk only if two agents ever drive the same checkout, which is the standing store-wide posture, not new exposure from this change
- `s17` — `challenge pass / operations lens: mixed-version rollout across downstream repos`: the v2 rollout already produced stale-binary friction reports; v3 repeats that cost by design (fail-closed beats silent data loss) — parked as residual, non-blocking, with the mitigation being the error's own upgrade hint

## Decisions

- user decision (q1, 2026-07-17): the resolve surface is `park --resolve <vN> [--decision "<text>"]` — extend the existing park verb, mirroring `question --resolve`; no new flat verb, no reject-on-v-ids
- user decision (q2, 2026-07-17): the plan-side twin ships in the same PR — `plan risk --resolve <rN>` gains the same close-out for blocking PlanRisks, keeping the engines structural peers
- user decision (q3, 2026-07-17): `park --resolve <vN>` requires `--decision "<text>"` — a bare resolve is refused with a hint; an optional `--claim <cN>` links the deciding claim; the plan-side `plan risk --resolve` carries the same bar

## Hard questions

- what does park --resolve do on an already-resolved v-id — refuse with a hint, or no-op idempotently? (decide in the plan; either is defensible, silence is not)
