# Build Plan — resolve parked vagueness

slug: `resolve-parked-vagueness` · status: `exported` · from frame: `resolve-parked-vagueness`

> devague ships a resolve move for parked vagueness: a blocking park can now be resolved or reclassified through CLI moves alone, closing issues 45, 55, 57, and 60

## Tasks

### t1 — Frame-side model: Vagueness resolution state + schema v3

- instruction: extend Vagueness in devague/frame.py with resolved: bool = False and resolution: str = ''; add Frame.resolve_vagueness(vid: str, resolution: str); bump SCHEMA_VERSION to 3; default the new keys in from_dict for v2 artifacts; keep set_status untouched — v-ids stay out of confirm/reject per decision c11; field names are pinned (resolved, resolution) — t2 and t7 read them verbatim
- covers: c2, h2, c5, h5
- acceptance:
  - Vagueness gains resolved: bool = False and resolution: str = '' with id/text/kind/claim_id unchanged; Frame.resolve_vagueness(vid, resolution) marks it resolved and raises ValueError on an unknown or already-resolved id
  - SCHEMA_VERSION == 3; a v2 frame JSON without the new keys loads with defaults; save-load round-trips a resolved item identical (tests/test_frame.py, tests/test_store.py)
  - store.load still fails closed with the upgrade hint when schema_version exceeds 3

### t2 — Plan-side model: PlanRisk resolution state + plan schema v3

- instruction: mirror t1 exactly in devague/plan.py: PlanRisk.resolved/resolution, Plan.resolve_risk, PLAN_SCHEMA_VERSION = 3, from_dict defaults for v2 artifacts; field names must match t1 verbatim (resolved, resolution) — deliverables_md reads both models
- covers: c13, h9
- acceptance:
  - PlanRisk gains resolved: bool = False and resolution: str = '' with id/text/kind/task_id unchanged; Plan.resolve_risk(rid, resolution) mirrors the frame-side error contract (ValueError on unknown or already-resolved)
  - PLAN_SCHEMA_VERSION == 3; a v2 plan JSON loads with defaults; save-load round-trips a resolved risk identical (tests/test_plan.py, tests/test_plan_store.py)

### t3 — Frame gate: skip resolved vagueness, executable hint, parked_items

- instruction: in devague/convergence.py: filter v.resolved in _missing_open_uncertainty and _parked_items; rewrite the blocking-vagueness branch of suggest_move (line 188) to emit the park --resolve move; plain CLI text, stdout only — renderer changes are t7, not here
- depends on: t1
- covers: c3, h3, c18, h14
- acceptance:
  - _missing_open_uncertainty skips resolved items: a resolved unknown_blocking no longer appears in blockers (tests/test_convergence.py)
  - suggest_move for a blocking-vagueness blocker names the executable syntax verbatim: park --resolve VID --decision TEXT
  - _parked_items excludes resolved items, so converge/status parked_items stops advertising a closed item as open

### t4 — Plan gate: skip resolved risks, executable hint, parked_items

- instruction: mirror t3 in devague/plan_convergence.py: filter r.resolved in _missing_risks and _parked_items; rewrite the blocking-risk hint branch to emit the plan risk --resolve move
- depends on: t2
- covers: c13, h9, c18, h14
- acceptance:
  - a resolved unknown_blocking risk no longer blocks plan convergence (tests/test_plan_convergence.py)
  - the blocking-risk hint at plan_convergence.py:172 names the executable syntax verbatim: plan risk --resolve RID --decision TEXT
  - plan-side _parked_items excludes resolved risks

### t5 — CLI: park --resolve VID --decision TEXT

- instruction: in devague/cli/_commands/park.py make the positional text optional (nargs='?') the way question.py does; add --resolve VID, --decision TEXT, --claim CN; require --decision whenever --resolve is passed; route through Frame.resolve_vagueness and translate ValueError into DevagueError with a run-devague-show hint; fail-closed refusal for already-resolved ids, consistent with the store posture
- depends on: t1
- covers: c4, h4
- acceptance:
  - park --resolve VID --decision TEXT marks the item resolved, echoes the transition on stdout, and has --json parity
  - a bare park --resolve VID without --decision is refused with a hint and persists nothing (decision c21); unknown and already-resolved ids are refused with a hint, exit 1 (answers the frame hard question: refuse, not no-op)
  - --claim CN links the deciding claim and an unknown claim id is refused; passing positional text together with --resolve is refused; the park-create path is unchanged (tests/test_cli_moves.py)

### t6 — CLI: plan risk --resolve RID --decision TEXT

- instruction: mirror t5 on the risk subcommand in devague/cli/_commands/plan.py: positional text becomes optional, add --resolve RID and --decision TEXT with the same refusal semantics; no --claim analog (risks link tasks via --task); route through Plan.resolve_risk
- depends on: t2
- covers: c13, h9
- acceptance:
  - plan risk --resolve RID --decision TEXT resolves the risk with stdout echo and --json parity; bare resolve without --decision refused; unknown and already-resolved ids refused with hint, exit 1 (tests/test_cli_plan.py)
  - the risk-create path (positional text --kind K --task TN) is unchanged

### t7 — Renderers: resolved items render with resolution; deliverables excludes them

- instruction: frame_md: keep the flat Open vagueness list for open items and render resolved ones as '- [kind] text — resolved: TEXT'; spec_md: render resolved items of any kind with their resolution under the existing structure (a Resolved vagueness subsection is acceptable); deliverables_md: filter on the resolved flag from both models; update tests/goldens accordingly
- depends on: t1, t2
- covers: c6, h6, c18, h14
- acceptance:
  - frame_md and spec_md render a resolved item with its resolution text verbatim; an exported spec from a frame with a resolved blocking park passes markdownlint (integration test + goldens)
  - deliverables_md surviving-open-items excludes resolved frame vagueness and resolved plan risks (tests/test_plan_deliverables.py)

### t8 — Teaching + contract docs sweep: the close-out loop everywhere park is taught

- instruction: sweep devague/cli/_commands/learn.py (move table + operating rules), docs/llm-guidance.md park rows, .claude/skills/think/SKILL.md move table and rules, and docs/spec-contract.md (entities, move tables, Versioning); match the exact flag names t5/t6 shipped; markdownlint everything touched
- depends on: t5, t6
- covers: c7, h7, c14, h10, c5
- acceptance:
  - devague learn and devague plan learn name park --resolve / plan risk --resolve wherever park/risk are taught (tests/test_cli_learn.py asserts the strings)
  - docs/spec-contract.md documents resolved/resolution on Vagueness and PlanRisk, the resolve move rows, and schema_version 3 for both engines
  - docs/llm-guidance.md and .claude/skills/think/SKILL.md teach the close-out loop; the taught prefer-question workaround framing is retired

### t9 — E2E repro + quality gates: issue 57 lifecycle through the real CLI, both engines

- instruction: new tests/test_e2e_resolve.py exercising devague.cli main() end to end for both engines; keep it hermetic in tmp_path working dirs; verify the exported spec passes the existing markdownlint integration harness
- depends on: t3, t4, t5, t6, t7
- covers: c1, h1, c15, h11, c9, h8, c17, h13
- acceptance:
  - a new e2e test drives the installed entry point through issue 57's repro: park blocking, capture the decision claim, park --resolve with --decision and --claim, converge passes, export succeeds — zero direct edits of .devague files; a plan-side twin e2e does the same through plan risk --resolve
  - coverage stays at 95 percent or higher; flake8, black, isort, bandit all clean
  - the resolve code paths add no LLM call and no subprocess usage inside the devague package (boundary h8) — asserted by inspection of the diff, not assumed

### t10 — Release + close-out: 0.20.0, CHANGELOG, PR, close the four issues

- instruction: minor bump (new CLI surface); PR via the cicd skill / agex pr open, linking the spec and plan artifacts; issue-close comments quote the exact replacing move per issue (park --resolve for 45/55/57; both moves plus the existing plan amend pointer for 60)
- depends on: t8, t9
- covers: c16, h12, c17, h13
- acceptance:
  - pyproject.toml bumps 0.19.1 to 0.20.0 with a prepended CHANGELOG.md entry naming issues 45, 55, 57, 60; CI version-check passes
  - after merge, each of issues 45, 55, 57, 60 is closed with a comment naming the shipped release and the move that replaces its documented workaround, signed per convention

## Risks

- [follow_up] the updated think skill reaches downstream mesh repos only on guildmaster's next re-broadcast sync — until then vendored copies still teach the one-way park; known cadence cost, not a blocker
