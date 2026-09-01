# Current spec — what the app does today

## Coverage boundary

This projection is complete only over the behavior ledger: 2 of 12 plans have a ledgered delivery (`behavior-validation-and-today-spec`, `next-leg-hints`), spanning `2026-08-31T18:27:51Z` (plan `behavior-validation-and-today-spec`) through `2026-08-31T21:32:17Z` (plan `next-leg-hints`).
10 of 12 frames have no ledgered delivery at all (`challenge-skill`, `devague-0-6-0-ships-the-human-review-loop-devague`, `devague-now-ships-a-documented-spec-contract-every`, `devague-ships-a-sharper-end-to-end-method-a-guided`, `devague-turns-a-converged-plan-into-parallel-simpl`, `execution-seam-and-deviate`, `issue-backlog-sweep`, `reasoning-degradation-ledger`, `resolve-parked-vagueness`, `summarize-delivery-skill`) — nothing in this document reflects them.
Anything predating this boundary, or belonging to an unledgered frame, is not reflected here by construction.

## Current behavior

- converge and plan converge warn on behavioral obligations with no approved evidence — visibly untested, never gating (`behavior-validation-and-today-spec:b1`, added)
  - provenance: caused by `c6` — plan `behavior-validation-and-today-spec`, frame `behavior-validation-and-today-spec`
  - proof: best strength `execution`
    - evidence: automated — execution: pass (run 2026-08-31 @ 3945fb7)
- devague today projects the behavior ledger across all frames, plans, and deliveries into the committed docs/current-spec.md, fail-open and read-only over stores (`behavior-validation-and-today-spec:b2`, added)
  - provenance: caused by `c7` — plan `behavior-validation-and-today-spec`, frame `behavior-validation-and-today-spec`
  - proof: best strength `execution`
    - evidence: automated — execution: pass (run 2026-08-31 @ 3945fb7)
- devague summary's Delivery Claims table renders per-claim evidence strength on the coverage/fidelity/execution/sensitivity ladder, capped by approved lapses (`behavior-validation-and-today-spec:b3`, added)
  - provenance: caused by `c20` — plan `behavior-validation-and-today-spec`, frame `behavior-validation-and-today-spec`
  - proof: best strength `execution`
    - evidence: automated — execution: pass (run 2026-08-31 @ 3945fb7)
- every successful non-exempt devague verb now emits one next: stderr progression hint, overrideable via tool.devague in pyproject.toml or `DEVAGUE_HINTS` (`next-leg-hints:b1`, added)
  - provenance: caused by `c11` — plan `next-leg-hints`, frame `next-leg-hints`
  - proof: best strength `execution`
    - evidence: automated — execution: pass (run 2026-08-31 @ 052af63)
- assign-to-workforce split-plan --write now captures plan show --json stderr separately instead of merging it into the parsed stdout - previously silently safe only while stderr was empty (`next-leg-hints:b2`, amended)
  - provenance: caused by `d2` — plan `next-leg-hints`, frame `next-leg-hints`
  - ⚠ unproven: no passing evidence on record
    - evidence: none on record
- devague explain deviate and devague explain summary now succeed with real move documentation - both previously failed with unknown move (`next-leg-hints:b3`, added)
  - provenance: caused by `d3` — plan `next-leg-hints`, frame `next-leg-hints`
  - ⚠ unproven: no passing evidence on record
    - evidence: none on record

## Ledger status

- proposed deltas awaiting adjudication: 0
- rejected deltas (excluded from this projection): 0
- retired lineages (superseded with no live replacement): 0
