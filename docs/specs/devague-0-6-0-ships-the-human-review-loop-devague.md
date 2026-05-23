# devague 0.6.0 ships the Human Review Loop: 'devague review' surfaces every unconfirmed LLM proposal in one pass, and confirm/reject now take many ids at once — so honest human review scales to frames full of proposals without ever auto-confirming anything

> devague 0.6.0 ships the Human Review Loop: 'devague review' surfaces every unconfirmed LLM proposal in one pass, and confirm/reject now take many ids at once — so honest human review scales to frames full of proposals without ever auto-confirming anything.

## Audience

- The human operator driving devague who must review and confirm/reject LLM-proposed claims and honesty conditions, plus the assisting LLM agent that produces those proposals.

## Before → After

- Before: Review was ad-hoc (hand-rolled from show / show --json) and confirmation was one id per command, so a frame with ~15 proposed conditions meant 15 sequential commands — pushing toward rubber-stamping instead of genuine review (surfaced dogfooding /think on #5).
- After: In one pass the operator sees every unconfirmed proposal (proposed claims + proposed honesty conditions) without the frame needing to converge, then confirms or rejects many in a single command; pending design questions persist as durable .devague working state to decide later.

## Why it matters

- The user-only confirmation step is devague's whole anti-fabrication guarantee; it must be ergonomic enough to do honestly at scale and support out-of-band review (read proposals somewhere comfortable like NotebookLM or a shared doc, then apply decisions), or it gets skipped or rubber-stamped.

## Requirements / honesty conditions

- At 0.6.0 release the announcement is literally true of the shipped CLI: 'devague review' exists, and a frame full of proposed items can be reviewed then bulk confirmed/rejected in one pass with no path that auto-confirms.
- Both audiences are served: the operator gets a single review + bulk-decide path, and the LLM agent's proposals stay visibly 'proposed' until the operator explicitly acts.
- On a non-converged frame, one 'review' shows every proposed item and one 'confirm'/'reject' call resolves a chosen set — demonstrable end-to-end in a test.
- The before-state pain is real and removed: the pre-0.6.0 flow needed N commands for N conditions with no review artifact; 0.6.0 replaces that with one review plus one bulk decision.
- The anti-fabrication guarantee is preserved exactly: ergonomics improve but no proposal becomes authoritative without an explicit user action, asserted by test.
- The success signals are verified by the committed test suite, not asserted by hand.
- 0.6.0 adds only review/confirm UX; the proposed-vs-confirmed state model and convergence gate from #5/#16 are unchanged — no new claim or condition states are introduced.
- Running 'devague review' on a frame that has NOT converged still exits 0 and lists every proposed claim and proposed honesty condition with ids; it never invokes the convergence gate nor mutates any claim/condition state.
- The review artifact carries an explicit 'nothing confirmed yet — non-authoritative' banner and is written to a path under `.devague/reviews/<slug>.md`, distinct from docs/specs/, so it cannot be mistaken for the buildable spec.
- 'devague confirm a b c' resolves every listed id in a single call (and 'reject a b c' likewise), and the handling of a batch containing an invalid/unknown id follows one defined, tested rule.
- A pending question the CLI writes persists across runs under `.devague/questions/<slug>.md`, is treated as uncommitted working state by default, and a documented path exists to apply a confirmed decision back into the frame.
- An automated test asserts that no review-flow command (review, multi-id confirm/reject, any --json path) transitions an llm-origin proposed item to confirmed without an explicit user confirm naming that id.
- A review artifact emitted by 'devague review' can be edited with confirm/reject decisions and fed to `devague confirm --from-review <file>` to apply exactly those decisions — proven by a round-trip test — and applying it still auto-confirms nothing the file did not mark confirmed.

## Success signals

- A frame with many proposed items is reviewed and resolved in a single 'devague review' plus one batched confirm/reject, and the test suite proves: review export works before convergence, multi-id confirm/reject works, and no review-flow command auto-confirms a proposal.

## Scope / boundaries

- Scope is the review/confirm UX layered over the existing proposed-vs-confirmed contract (#5/#16); it does not change the state model itself — proposals still only become authoritative by explicit user action.

## Non-goals

- Does not generate a polished buildable spec from unconfirmed review output — review output stays explicitly non-authoritative, distinct from what 'export' produces post-convergence.
- Does not auto-resolve questions and does not auto-confirm any LLM-proposed content anywhere in the review flow.
- The CLI does not call an LLM.
- Does not require GitHub, NotebookLM, or any external service.

## Decisions

- Batch confirm/reject is TRANSACTIONAL: validate all ids first; if any id is unknown/invalid, resolve none and exit non-zero with a hint — never a half-applied batch.
- `devague confirm --from-review <file>` IS in scope for 0.6.0: it parses a reviewed decision set (confirm/reject per id) from the review artifact and applies it, so the review artifact format must be documented and round-trippable.
- devague manages .gitignore: it ensures .devague/reviews/ and .devague/questions/ are git-ignored so review/question state is uncommitted working state by default; the user opts in to promote one into docs.
- Pending questions/decisions are produced by a CLI move that writes `.devague/questions/<slug>.md` and owns the format (first-class + unit-testable), not a hand-written skill artifact.
