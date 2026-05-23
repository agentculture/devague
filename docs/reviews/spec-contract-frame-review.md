# Review — Announcement Frame for the Devague spec contract (issue #5)

> **Purpose of this file.** This is a *review artifact*, not an exported spec.
> The frame has **not** converged and **nothing is confirmed** yet. Every
> honesty condition below was **proposed by the LLM** (`origin = llm`,
> `state = proposed`) while working backwards from the announcement. Per
> devague's hard rule, **only you (the user) can confirm them** — they must not
> silently become authoritative requirements.
>
> Review each one and decide **Confirm / Reject / Edit**. Then reply with your
> decisions (e.g. "confirm all except h9 and h14; reject h14; edit h9 to keep
> aliases") and the agent will apply them, run `converge`, and `export` the
> buildable spec.

- **Frame slug:** `devague-now-ships-a-documented-spec-contract-every`
- **Source issue:** [agentculture/devague#5 — Define the Devague spec contract](https://github.com/agentculture/devague/issues/5)
- **Status:** drafting (not converged)
- **Claims:** 15 (all structural kinds present) · **Proposed honesty conditions:** 15 · **Parked open vagueness:** 2

## The announcement (auto-confirmed — it came from you)

> Devague now ships a documented spec contract: every frame is a durable,
> reloadable artifact, and `converge` returns a structured result
> (`ready_for_spec`, `blockers`, `warnings`, `parked_items`,
> `required_next_moves`) instead of prose-only advice.

## Decisions already made (via the working-backwards Q&A)

1. **Keep shipped vocabulary**, document it — `state ∈ {proposed, confirmed, rejected, parked}` × `origin ∈ {user, llm}`. No rename, no migration of existing frames.
2. **Add all four** new claim types — `non_goal`, `requirement`, `assumption`, `decision` (gate impact proposed in **h14**, below).
3. **Hard-break** `converge` JSON to the new structured shape; update the skill's `status` helper in the same change (no `passed`/`missing` aliases).
4. **`schema_version` now** — first-class field, validated on load.

## Honesty conditions to review (h1–h15)

Each row: the **claim** (already confirmed, since it came from you or your
decisions) and the **proposed honesty condition** (what must be true for the
claim to be honest) that needs **your** verdict.

### h1 — claim c1 (announcement)

- **Claim:** Devague now ships a documented spec contract; every frame is a durable, reloadable artifact; `converge` returns a structured result instead of prose-only advice.
- **Proposed honesty condition:** A frame round-trips losslessly (save then load yields an identical frame) including `schema_version`, the new claim types, and the structured convergence payload; existing 0.4.0 frames still load.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h2 — claim c2 (audience)

- **Claim:** Devague and the assisting LLM that drives it — they coordinate around structured feature-framing state without a rigid wizard.
- **Proposed honesty condition:** Every move accepts and emits documented JSON, and the contract spells out per-move input / output / state-transition / validation-errors so an LLM can drive devague without guessing internal state.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h3 — claim c3 (after_state)

- **Claim:** A vague idea becomes a claim-based, pressure-tested, buildable spec held in a durable, reloadable artifact whose entities are validated.
- **Proposed honesty condition:** Matches shipped 0.4.0 reality — `converge --json` emits `{passed, missing}` today and no contract doc is committed (verifiable in the repo before relying on it).
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h4 — claim c4 (before_state)

- **Claim:** Framing state is partly implicit and undocumented; `converge` returns prose-only advice (`{passed, missing}`); there is no documented contract an LLM can rely on.
- **Proposed honesty condition:** The contract is enforced by validation on load: a schema-violating frame is rejected with a clear, actionable error rather than silently accepted.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h5 — claim c5 (why_it_matters)

- **Claim:** An LLM and devague can only coordinate reliably around a contract that is documented, validated, and machine-readable — convergence must mean something, not vibes.
- **Proposed honesty condition:** Convergence stays evidence-based and `export` stays gated on `converge` passing; the gate is computed only from confirmed claims and confirmed honesty conditions, never a hunch.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h6 — claim c6 (boundary)

- **Claim:** Not a full PRD generator and not a fixed wizard; the move-driven, deterministic model stays.
- **Proposed honesty condition:** The deterministic move-driven model is preserved: no fixed prompt sequence is added; the CLI stays a state tracker and the LLM still chooses the next move.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h7 — claim c7 (boundary)

- **Claim:** The local contract requires no GitHub, agents, or external services.
- **Proposed honesty condition:** Every contract operation (create / load / mutate / show / converge / export) runs fully offline against local `.devague/` state with zero network calls.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h8 — claim c8 (boundary)

- **Claim:** Convergence is never claimed on vibes, and LLM-proposed content is never silently promoted to confirmed truth.
- **Proposed honesty condition:** LLM-proposed claims and honesty conditions persist as `proposed` (`origin=llm`) and require an explicit user `confirm` before they affect convergence — nothing auto-confirms.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h9 — claim c9 (success_signal)

- **Claim:** `converge` returns a structured result (`ready_for_spec`, `blockers`, `warnings`, `parked_items`, `required_next_moves`) with blockers instead of prose-only advice.
- **Proposed honesty condition:** `converge --json` emits ONLY the new structured shape (hard break); the skill's `status` helper is updated in the same change; blockers block convergence and warnings do not.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________
- **Note:** If you'd rather keep `passed`/`missing` as back-compat aliases (the non-breaking option), edit this condition — it currently encodes the hard-break decision.

### h10 — claim c10 (success_signal)

- **Claim:** A documented spec contract exists in the repo, with worked contract examples for at least one feature frame.
- **Proposed honesty condition:** The committed contract doc is the source of truth for kinds / states / fields / transitions and includes at least one worked frame example the CLI can actually round-trip.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h11 — claim c11 (success_signal)

- **Claim:** The CLI can create, load, mutate, and display a frame locally; core entities are validated.
- **Proposed honesty condition:** create / load / mutate / show round-trip through the JSON store under validation, and the demonstrated operations are covered by passing tests.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h12 — claim c12 (success_signal)

- **Claim:** Tests cover claim provenance, honesty-condition confirmation, parking vagueness, and convergence failure.
- **Proposed honesty condition:** Each of the four areas (provenance, honesty-condition confirmation, parking vagueness, convergence failure) has at least one test asserting the contract behavior, all green in CI.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h13 — claim c13 (boundary)

- **Claim:** The contract formalizes 0.4.0's shipped vocabulary as canonical — `state ∈ {proposed,confirmed,rejected,parked}` × `origin ∈ {user,llm}`; no rename and no migration of existing frames.
- **Proposed honesty condition:** The doc maps the issue's proposed names (`llm_proposed`, `user_confirmed`, `intentionally_out_of_scope`, …) onto the shipped (state × origin) model so no information is lost and no rename is required.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

### h14 — claim c14 (success_signal)

- **Claim:** The claim-type vocabulary adds `non_goal`, `requirement`, `assumption`, and `decision` to the shipped set, each with a documented convergence-gate impact.
- **Proposed honesty condition:** Each new type's gate impact is documented and tested: `requirement` is spec-affecting (needs a confirmed honesty condition like other claims); `non_goal` and `decision` are descriptive (non-blocking); an unconfirmed `assumption` surfaces as a *warning*, not a blocker.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________
- **Note:** This is the proposed gate semantics for the four new types — the part the Q&A left to you. Edit if you want different blocking rules.

### h15 — claim c15 (success_signal)

- **Claim:** Every frame carries a `schema_version` field; load validates by version so existing frames keep loading as the schema grows.
- **Proposed honesty condition:** `schema_version` is written on every save and checked on load; an unknown or newer version fails closed with a clear error rather than corrupting state.
- **Your verdict:** ☐ Confirm  ☐ Reject  ☐ Edit → ____________________

## Parked open vagueness (non-blocking follow-ups)

These are genuine unknowns parked as first-class objects rather than guessed.
They do **not** block convergence.

- **v1 (`follow_up`):** Whether to also publish a formal machine-readable JSON Schema file alongside the prose contract doc + dataclasses, or treat the dataclasses as the schema of record.
- **v2 (`follow_up`):** Whether `requirement`-type claims should eventually carry acceptance criteria like plan tasks do (overlaps the spec→plan leg), or stay prose-only in the frame.

## How to respond after review

Reply to the agent with your verdicts, for example:

- "Confirm all 15." — fastest path; the agent runs `confirm h1…h15`, then `converge`, then `export`.
- "Confirm all except h9; edit h9 to keep `passed`/`missing` as aliases." — agent re-interrogates c9 with the revised condition, then confirms.
- "Reject h14; I want all four new types non-blocking." — agent rejects and re-proposes.

Once your confirmed honesty conditions cover every spec-affecting claim and no
blocking vagueness remains, the frame converges and `devague export` writes the
buildable spec to `docs/specs/`.
