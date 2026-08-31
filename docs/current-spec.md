# Current spec — what the app does today

## Coverage boundary

This projection is complete only over the behavior ledger: 1 of 11 plan have a ledgered delivery (`behavior-validation-and-today-spec`), spanning `2026-08-31T18:27:51Z` (plan `behavior-validation-and-today-spec`) through `2026-08-31T18:27:51Z` (plan `behavior-validation-and-today-spec`).
10 of 11 frames have no ledgered delivery at all (`challenge-skill`, `devague-0-6-0-ships-the-human-review-loop-devague`, `devague-now-ships-a-documented-spec-contract-every`, `devague-ships-a-sharper-end-to-end-method-a-guided`, `devague-turns-a-converged-plan-into-parallel-simpl`, `execution-seam-and-deviate`, `issue-backlog-sweep`, `reasoning-degradation-ledger`, `resolve-parked-vagueness`, `summarize-delivery-skill`) — nothing in this document reflects them.
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

## Ledger status

- proposed deltas awaiting adjudication: 0
- rejected deltas (excluded from this projection): 0
- retired lineages (superseded with no live replacement): 0
