# Build Plan — Devague now ships a documented spec contract: every frame is a durable, reloadable artifact, and converge returns a structured result (ready_for_spec, blockers, warnings, parked_items, required_next_moves) instead of prose-only advice

_slug: devague-now-ships-a-documented-spec-contract-every · status: exported · from frame: devague-now-ships-a-documented-spec-contract-every_

> Devague now ships a documented spec contract: every frame is a durable, reloadable artifact, and converge returns a structured result (ready_for_spec, blockers, warnings, parked_items, required_next_moves) instead of prose-only advice

## Tasks

### t1 — Define the contract entity model: add claim types non_goal/requirement/assumption/decision and a schema_version field

- covers: c13, c14, c15
- acceptance:
  - CLAIM_KINDS gains non_goal, requirement, assumption, decision; Frame carries schema_version; dataclasses validate kind/state/origin against their enums

### t2 — Implement schema_version write-on-save + validate-on-load with fail-closed versioning and lossless round-trip

- depends on: t1
- covers: h1, h4, h15
- acceptance:
  - save writes schema_version; load rejects unknown/newer version with a clear error; save then load yields an identical frame including new types + schema_version; existing 0.4.0 frames still load

### t3 — Add load-time validation that rejects schema-violating frames with clear, actionable errors

- depends on: t1
- covers: c3, c11
- acceptance:
  - a malformed or enum-violating frame raises a DevagueError with an actionable message on load (no silent accept); create/load/mutate/show round-trip under validation

### t4 — Replace converge output with the structured result (ready_for_spec, blockers, warnings, parked_items, required_next_moves) as a hard break

- depends on: t1
- covers: c9, h9, c5, h5
- acceptance:
  - converge --json emits only the new structured shape; ready_for_spec gates export; blockers block convergence and warnings do not; the gate is computed only from confirmed claims and conditions; required_next_moves is derived from blockers

### t5 — Implement convergence-gate semantics for the new claim types

- depends on: t4
- covers: c14, h14
- acceptance:
  - requirement is spec-affecting (needs a confirmed honesty condition); non_goal and decision are descriptive (non-blocking); an unconfirmed assumption surfaces as a warning, not a blocker; each rule has a test

### t6 — Update the /think and /spec-to-plan status helpers to consume the new structured converge payload

- depends on: t4
- covers: h9
- acceptance:
  - both status helpers read ready_for_spec/blockers/warnings/required_next_moves and no longer depend on {passed, missing}; status output distinguishes blockers from warnings

### t7 — Give every move a documented JSON I/O contract (input, output, state transition, validation errors)

- covers: c2, h2
- acceptance:
  - each move supports --json with a documented input/output/state-transition/validation-error shape; the strict stdout/stderr split holds; an LLM can drive devague from JSON without guessing internal state

### t8 — Guarantee all contract operations run fully offline

- covers: c7, h7
- acceptance:
  - create/load/mutate/show/converge/export perform zero network calls; a test asserts no network or socket access

### t9 — Enforce and preserve anti-fabrication and the move-driven model

- covers: c8, h8, c6, h6
- acceptance:
  - claims/conditions with origin=llm persist as proposed; confirm is the only transition to confirmed; no code path auto-confirms; no fixed prompt sequence is added (the CLI stays a move-driven state tracker)

### t10 — Write the documented spec contract with a worked, round-trippable frame example

- depends on: t1, t2, t4, t7
- covers: c1, c4, h3, c10, h10, h13
- acceptance:
  - a committed contract doc is the source of truth for kinds/states/fields/transitions and per-move I/O; it documents the shipped (state x origin) vocabulary and maps the issue's proposed names onto it; it states the current 0.4.0 reality (passed/missing, no prior doc); it includes at least one worked frame example the CLI round-trips

### t11 — Add the contract test suite

- depends on: t1, t2, t3, t4, t5, t9
- covers: c11, h11, c12, h12
- acceptance:
  - tests cover claim provenance, honesty-condition confirmation, parking vagueness, and convergence failure; plus lossless round-trip, multi-version load, and the structured-result fields; all green in CI

## Risks

- [unknown_nonblocking] Whether to also ship a formal machine-readable JSON Schema file alongside the dataclasses (frame follow-up v1) — affects the doc scope in t10
- [unknown_nonblocking] Whether requirement-type claims should carry acceptance criteria like plan tasks (frame follow-up v2) — overlaps the spec-to-plan leg
