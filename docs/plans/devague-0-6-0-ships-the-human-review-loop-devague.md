# Build Plan — devague 0.6.0 ships the Human Review Loop: 'devague review' surfaces every unconfirmed LLM proposal in one pass, and confirm/reject now take many ids at once — so honest human review scales to frames full of proposals without ever auto-confirming anything

slug: `devague-0-6-0-ships-the-human-review-loop-devague` · status: `exported` · from frame: `devague-0-6-0-ships-the-human-review-loop-devague`

> devague 0.6.0 ships the Human Review Loop: 'devague review' surfaces every unconfirmed LLM proposal in one pass, and confirm/reject now take many ids at once — so honest human review scales to frames full of proposals without ever auto-confirming anything.

## Tasks

### t1 — Multi-id, transactional confirm/reject

- covers: c14, h3
- acceptance:
  - confirm and reject accept multiple ids (nargs+) in a single invocation
  - batch is transactional: if any id is unknown/invalid, resolve none and exit non-zero with a hint (decision c17)
  - an all-valid batch resolves every listed id; existing single-id behaviour is unchanged

### t2 — 'devague review' lists proposed items, un-gated, with no mutation (+ --json)

- covers: c12, h1
- acceptance:
  - review lists every proposed claim and proposed honesty condition with their ids
  - review runs on a NON-converged frame, exits 0, and never invokes the convergence gate
  - review never mutates any claim/condition state; review --json emits the same set structured

### t3 — Non-authoritative review artifact at `.devague/reviews/<slug>.md`

- depends on: t2
- covers: c13, h2
- acceptance:
  - review writes `.devague/reviews/<slug>.md` carrying an explicit 'nothing confirmed yet — non-authoritative' banner
  - the path is distinct from docs/specs/ so it cannot be mistaken for the buildable spec
  - devague ensures .devague/reviews/ is git-ignored so it is uncommitted working state by default (decision c19)

### t4 — `confirm --from-review <file>` apply path + documented round-trippable format

- depends on: t1, t2, t3
- covers: c21, h13
- acceptance:
  - the review artifact format is documented and round-trippable: review -> edit decisions -> apply
  - confirm --from-review parses confirm/reject decisions per id and applies them via the transactional path (t1)
  - applying a from-review file auto-confirms nothing the file did not mark confirmed; proven by a round-trip test

### t5 — Pending questions as durable `.devague/questions/<slug>.md` working state

- covers: c15, h4
- acceptance:
  - a CLI move writes `.devague/questions/<slug>.md` that persists across runs and owns the format (decision c20)
  - devague ensures .devague/questions/ is git-ignored — uncommitted working state by default (decision c19)
  - a documented path exists to apply a confirmed decision from the questions file back into the frame

### t6 — Verification test suite for the review loop

- depends on: t1, t2, t3, t4, t5
- covers: c16, h5, c6, h11, c5, h10, c3, h8
- acceptance:
  - a test asserts NO review-flow command (review, multi-id confirm/reject, --from-review, any --json path) confirms an llm-origin proposed item without an explicit user confirm naming that id (c16/h5)
  - tests prove review export works before convergence, multi-id confirm/reject works, and the from-review round-trip applies exactly the file's decisions (c6/h11)
  - an end-to-end test demonstrates one 'review' + one batched confirm/reject resolving a chosen set on a non-converged frame (c3/h8), and that the anti-fabrication guarantee is preserved (c5/h10)

### t7 — Docs, .gitignore/working-state guidance, version bump to 0.6.0 + CHANGELOG

- depends on: t6
- covers: c1, h6, c2, h7, c4, h9, c7, h12
- acceptance:
  - docs explain which .devague/ files are local working state vs artifacts intentionally promoted to docs, and document the review-file format + apply-back path
  - an integration check confirms the shipped 0.6.0 CLI makes the announcement literally true: 'devague review' exists and a proposal-heavy frame is reviewed then bulk-resolved with no auto-confirm path (c1/h6, c2/h7, c4/h9)
  - verify ONLY review/confirm UX was added — no new claim/condition states and the #5/#16 convergence gate is unchanged (c7/h12); bump version to 0.6.0 and prepend a CHANGELOG entry

## Risks

- [unknown_nonblocking] Exact review-file markers for the --from-review round-trip (e.g. checkbox vs CONFIRM/REJECT tokens, how ids are anchored) are unsettled — to be pinned during implementation of t4. (task t4)
