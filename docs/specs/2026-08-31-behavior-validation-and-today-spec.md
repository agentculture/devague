# behavior validation and today spec

> devague proves the behavior a spec claims is actually tested — planted test obligations met by filed test evidence, both carried as readable text — and renders the today spec, a read-only culmination of every exported spec and delivery that defines the app right now

## Audience

- operators (the main agent driving the CLI move by move), the humans owning the three gates who adjudicate obligations and read evidence, and anyone — human or agent — who needs the current definition of the app and reads the today spec instead of archaeology over dated exports

## Before → After

- Before: validating behavior is manual archaeology: the TDD merge gate proves the suite passes, never which claimed behavior is proven; evidence is unjoined prose in delivery summaries; in the embodiment cycle four graders failed and none by a test failing; the app's current definition lives nowhere — only ten dated point-in-time specs
- After: every confirmed claim and acceptance criterion can carry a planted test obligation in readable text; delivery files evidence records beside deviations, met or unmet is computable; devague renders an undated today spec aggregating all frames, plans, and deliveries via supersedes links, with unresolved conflicts flagged for human decision

## Requirements

- test obligations are planted at spec or plan time — a structured declaration naming the seam to test and the behavior to assert, snapshotting the claim or criterion text it derives from; extends the covers plus CoverageTarget snapshot pattern in devague/plan.py, and revives what issue 10 proposed as TestIntention and never built
  - honesty: an obligation names a specific seam and a specific behavior, snapshotting its source text at planting time — a generic add-tests-for-this string is not an obligation, and drift between snapshot and live claim text is visible, never silently stale
- a record-only evidence move files: obligation met by this test, asserting this behavior, outcome pass or fail — the agent runs the tests, the CLI records the fact deterministically, mirroring the lapse and deviate filing pattern where llm origin lands proposed
  - honesty: an evidence record is filed only after the named test actually ran, and the outcome is recorded verbatim — a failing outcome is filable and rendered, never suppressed to keep the ledger looking green
- evidence records carry actual text on both ends — the claim or criterion text and the test's asserted behavior text — so a human validates the link by reading test and claim side by side; ids are resolvable pointers, not the payload
  - honesty: behavior text is quoted from what the test actually asserts, not paraphrased to match the claim — if reading the test does not support its recorded behavior text, the evidence record is wrong and says so via the existing lapse or deviate paths
- an unmet test obligation surfaces as a non-gating convergence warning, following the S1 and S2 structural-sharpness precedent in devague/convergence.py — warnings only, `ready_for_spec` untouched, no previously-converging frame is newly blocked
  - honesty: the warning derives only from obligation and evidence state — never from lapse records, preserving the pinned never-gates exclusion in tests/`test_convergence.py`
- the today spec (the derived current spec) is a projection of an explicit behavior ledger — each delivery contributes behavioral deltas (added, amended, removed) carrying provenance back to the spec claim or approved deviation that caused them and forward to the evidence that validates them; the projection stays read-only and fail-open (contested.py's load-safely template), rendered to a single undated artifact by a sibling module beside the stores
  - honesty: the aggregate is deterministic and fail-open: same stores in, same artifact out; a corrupt or newer-schema file is skipped with a visible diagnostic, never a crash and never a silent omission
- behavior is the primary contract and evidence is broader than automated tests — automated, integration or e2e, manual verification, and observation are all filable evidence types, each recorded with its type (issue 107)
  - honesty: an evidence type is recorded as what it actually was — a manual verification is never dressed up as an automated test, and observation is the recorded floor, not a rubber stamp
- evidence records carry a strength level from a progressive vocabulary — coverage (evidence exists), fidelity (it asserts the promised behavior), execution (it currently passes), sensitivity (it would likely fail if the behavior broke) — the agent assesses strength, the CLI records it deterministically (issue 107)
  - honesty: strength levels are never inflated: fidelity requires the behavior text to be supported by reading the evidence, execution requires an actual run, sensitivity requires an actual demonstration — each level's basis is recorded with it
- staleness surfaces in both directions: an approved deviation whose affected behavioral evidence was never updated, and evidence asserting behavior no longer in the current contract, both render as visible findings — never silently dropped (issue 107)
  - honesty: staleness detection is a deterministic join over recorded state (deviation affects vs evidence refs, ledger deltas vs evidence) — no semantic guessing inside the CLI
- a validate-delivery step lands in the flow between execution and summarize-delivery — method-side like the other legs, driving record-only CLI moves; its output feeds the summary's Delivery Claims table (issue 107)
  - honesty: validate-delivery reports faithfully on partial and failed runs too — unmet obligations summarize as unmet, never smoothed over
- evidence records carry a run reference — when the evidence last executed and against what (timestamp and commit SHA) — and every renderer shows evidence age; execution strength decays the moment it is filed, so 'currently passes' is never rendered without its when
  - honesty: a run reference names a commit that exists and a time that is the actual run's — never backfilled to look fresher
- every store gaining a new record family bumps its schema version fail-closed, per the lapses v4-to-v5 precedent — frame (claim obligations), plan (criterion obligations), delivery (evidence and behavioral deltas); an older binary must refuse the newer file, never silently drop records on re-save
  - honesty: the bump decision is argued per store from the data-loss test (would an older binary re-saving drop records), not applied by reflex
- the flow renumbering ships with the feature: validate-delivery makes the seven-leg flow eight, so devague learn, README, CLAUDE.md, docs/skills.md, and the skill kit guildmaster re-broadcasts are all swept in the same release, per the 0.19.0 seventh-leg precedent
  - honesty: the sweep is verified by grepping the shipped docs for the old seven-leg wording — zero stale mentions is the bar
- gate 3 review becomes an audit of enumerable records, not open-ended discovery: obligations are the reviewer's ready-made checklist, unmet obligations arrive precomputed and visibly untested, and the reviewer's job narrows to verifying that filed evidence is honest
  - honesty: the checklist is a floor, not a ceiling — review-as-audit never suppresses review-as-judgment, and a finding outside the enumerated records is still a finding
- the fidelity audit is the heart of gate 3: for each evidence record the reviewer opens the named test — findable by the behavioral-test convention, tag or folder — and runs the three-way text comparison: claim text vs recorded behavior text vs what the test actually asserts; recorded text the test does not support means the record is wrong
  - honesty: the comparison reads the test source as it stands in the PR, never the recorded text alone — trusting the record defeats the audit
- strength verification at review: each claimed ladder level is checked against its recorded basis — execution re-run, its run reference checked against the PR head — and a level is never accepted above its basis
  - honesty: a stale run reference — behind the PR head for touched behavior — demotes an execution claim; passing long ago is not passing now
- delta completeness is reviewed in both directions: a behavioral code change with no filed delta is an undeclared behavioral change; a filed delta with no corresponding code change is a fabricated delivery — both are findings
  - honesty: both directions derive from the diff and the ledger actually read — neither direction is waved through on the other's cleanliness
- devague learn is refreshed to teach the new surface — obligations, evidence records, behavioral deltas, the strength ladder, and the today spec — how to use each move, in the same self-contained style as the existing learn topics
  - honesty: learn output describes only shipped moves, verified against the real CLI surface — never aspirational verbs
- a reviewer seam ships as a learn topic (e.g. devague learn review): a self-contained explanation a coder or reviewer agent consumes to run the gate-3 audit with these artifacts — the checklist, the three-way fidelity comparison, strength bases, delta completeness both directions, and propose-never-confirm — the reviewer-facing peer of devague learn skills
  - honesty: the review topic is self-contained: an agent with no prior devague context can run the audit from it alone — the bar devague learn skills set

## Honesty conditions

- the validation is honest only if an obligation without evidence renders as visibly untested — never dropped, never smoothed into a passing look; and the today spec never claims behavior that no approved evidence or confirmed claim backs
- no code path this feature introduces writes into docs/specs/ or mutates a stored frame, plan, or delivery — the today spec writes only its own artifact
- supersedes links are authored by a human or land proposed — the aggregator never infers supersession from dates or slugs
- the today spec is readable standalone — a reader needs no frame JSON, no CLI knowledge, and no other artifact open to understand what the app does today and what is proven
- the before-state is cited from the record — issue 97's quoted evidence and the placeholder render sites in `summary_md.py` — not reconstructed from memory
- met or unmet is computable from stored state alone by a pure deterministic function — no LLM judgment anywhere in the computation
- the signal is measured by running the real commands against this repo's real state — warning counts and evidence rows counted from actual output, never estimated
- the coverage boundary statement is derived from the ledger's actual span, not hand-written optimism
- if planting turns out to need demotion semantics after all, that is a spec change adjudicated by the human — never a silent implementation choice
- reviewer findings enter the same append-only discipline as everything else — a finding retracted under pushback is retracted on the record, not deleted

## Success signals

- on this repo's own ten frames: converge emits an unmet-obligation warning count that reaches zero when obligations are filed against evidence; summary's Delivery Claims renders one evidence-backed row per met obligation; the today-spec verb runs clean over all existing state without touching any stored file

## Scope / boundaries

- exported dated specs are never rewritten — the issue 92 ruling and the lapse-ledger spec pin that process history points forward and the spec is not rewritten; the today spec is a derived artifact that cites specs and deliveries, never a mutation of any of them
- the today spec is complete only over ledgered behavior — behavior predating devague adoption or shipped outside the flow is absent by construction; the artifact renders its own coverage boundary visibly, never implying it is the whole app
- a reviewer agent proposes, never confirms: findings land as PR comments, proposed lapses (grader-unverified, provenance-missing), or superseding evidence records — the gate-3 human adjudicates, and an approved reviewer-filed lapse mechanically caps the affected claim's renderable strength via the v2 resolution

## Non-goals

- the CLI never runs pytest or any test suite — issue 20 draws the line at execution (devague describes, an external operator executes; docs/skills.md: not in the CLI and not in a CI runner); test execution stays agent-side in assign-to-workforce's TDD merge gate

## Assumptions

- no cross-frame semantics exist today — no supersedes or replaces field, no precedence rule between sibling frames' claims, no repo-level index beyond bare slugs — so the today spec requires a genuinely new reconciliation rule
- planting an obligation on a confirmed claim is additive — it does not demote the claim to proposed, unlike instruction changes; the obligation itself carries proposed status when llm-origin, so adjudication lives on the obligation, not the claim

## Scope exploration

- `s1` — `devague/frame.py + docs/spec-contract.md (frame engine)`: no evidence field exists on Claim, HonestyCondition, or HardQuestion; instruction is prescriptive (how to verify), not evidentiary; LapseRecord.refs is free-text testimony, deliberately not a join; `SCHEMA_VERSION` 5, fail-closed raw-dict check, so a weighty new evidence field warrants a bump per the lapses precedent
  - seeds: `c2`, `c4`
- `s2` — `devague/plan.py + plan_convergence.py (plan engine)`: Task has no test-reference field; `acceptance_criteria` is unstructured prose gated on presence only; the covers-to-CoverageTarget chain (live re-derivation, snapshot persistence, deferred-state merge) is the built traceability pattern a criterion-to-test link should imitate; TDD language in `_tdd_fitness_warnings` is advisory strings only
  - seeds: `c2`, `q1` (question, resolved)
- `s3` — `devague/delivery.py + render/summary_md.py + contested.py (delivery seam)`: no evidence or test-result concept on the delivery model; summary's Delivery Claims table is a hardcoded placeholder while `_lapse_evidence_lines` is the template for an approved-gated per-claim evidence table; contested.py's enumerate-plans, filter-by-frame-slug, load-safely join is directly reusable for a claims-to-tests join
  - seeds: `c3`, `q2` (question, resolved)
- `s4` — `devague/store.py + cli/_paths.py + render registry (stores and export)`: everything is single-frame: one current pointer, render registry typed Frame to str, `dated_name` exports overwrite in place by design; ten frames, ten plans, four delivery ledgers exist and nothing loads more than one frame; a today spec needs a list-of-frames renderer and an undated single-file convention — both new territory
  - seeds: `c7`, `c9`, `q3` (question, resolved)
- `s5` — `docs/spec-contract.md issue-20 boundary + .claude/skills (assign-to-workforce, summarize-delivery)`: test running is agent-side (TDD gate: tests before and after merge, main agent runs them); a CLI verb running pytest would violate issue 20, while a record-only evidence verb fits the lapse and deviate precedent exactly; summarize-delivery's evidence bar (resolvable pointer or explicit unverified) is prose-only today, unjoined to any state
  - seeds: `c5`, `c3`
- `s6` — `prior art: issues 10, 97, 92, 70 + docs/specs/2026-07-29-reasoning-degradation-ledger.md`: issue 10 proposed TestIntention with `derived_from_claim_ids` and was closed unbuilt (zero code hits); issue 97's motivating evidence — four graders failed, none by a test failing — is the strongest motivation on record; the issue 92 ruling pins that the spec is not rewritten, so a today spec must be derived, not a rewrite; plan deliverables (70) is the nearest read-only aggregate but single-plan and pre-execution
  - seeds: `c8`, `c2`
- `s7` — `devague/convergence.py structural-sharpness warnings (S1, S2)`: warnings are a free list of strings computed by pure predicates, never touching `ready_for_spec`; the S1 and S2 soft-rollout pattern is the precedented slot for an unmet-obligation warning; the lapse ledger's never-gates exclusion is pinned by tests and must not be silently crossed if obligations derive from lapse data
  - seeds: `c6`
- `s8` — `issue agentculture/devague#107 (open suggestion, re-assessment)`: independently proposes both halves: behavior as primary contract with four evidence types, a progressive strength ladder (coverage, fidelity, execution, sensitivity), staleness surfacing in both directions, a validate-delivery step before summarization, and the current spec as a materialized projection of a behavior ledger of per-delivery deltas with two-way provenance — explicitly keeping semantic test understanding out of the CLI, matching issue 20
  - seeds: `c7`, `c17`, `c18`, `c19`, `c20`
- `s9` — `challenge pass / adjacent-systems lens: the seven-leg flow (README, CLAUDE.md, docs/skills.md, devague learn, guildmaster kit)`: validate-delivery makes the seven-leg flow eight; every doc and the learn verb teach seven, and guildmaster re-broadcasts the kit — renumbering is a shipping surface, not an afterthought
  - seeds: `c25`, `c20`
- `s10` — `challenge pass / migration lens: store.py, plan_store.py, delivery_store.py schema versions`: three stores gain record families (frame obligations, plan criterion obligations, delivery evidence plus deltas); the lapses v4-to-v5 precedent requires fail-closed bumps wherever an older binary re-saving would silently drop records
  - seeds: `c22`
- `s11` — `challenge pass / counter-evidence lens: ten existing frames vs the repo's actual history`: devague was adopted mid-life — behavior predating any frame never enters the ledger, so 'what defines our app' is honestly 'what the ledger covers'; no backfill path is specced
  - seeds: `c23`
- `s12` — `challenge pass / unstated-assumptions lens: frame.py instruction-demotion semantics`: instruction changes demote a confirmed claim to proposed; obligations planted after confirmation must not inherit that semantics or planting becomes punitive — unstated in the spec until this pass
  - seeds: `c24`
- `s13` — `challenge pass / lifecycle lens: c18 execution strength + summary_md render sites`: execution-level evidence decays the moment it is filed; without a run reference the today spec would render stale executions as currently proven
  - seeds: `c21`
- `s14` — `challenge pass / concurrency lens: single-writer CLI, fail-open projection reads`: clean pass — one writer per checkout, projection reads fail open per h7; residual risk only if two agents ever share a checkout, a repo-wide standing condition not specific to this feature
- `s15` — `challenge pass / security and reversibility lens: append-only ledgers, read-only projection`: clean on the execution surface — the CLI never runs tests (c5) and the projection is read-only (h8); reversibility residue routed to parks v1 and v2 (supersedes retraction, strength-vs-confidence interaction)
- `s16` — `gate 3 / code-reviewer workflow (session synthesis over the obligations, evidence, delta, and cap decisions c2-c28)`: the reviewer audits enumerable records: fidelity via three-way text comparison using the behavioral-test convention, strength via recorded bases and run references, delta completeness both directions, and proposes-never-confirms with approved lapses capping strength — matching issue 107's line that semantic test judgment stays agent-side
  - seeds: `c29`, `c30`, `c31`, `c32`, `c33`

## Decisions

- test obligations attach at both legs — planted on frame claims at the think leg, and updated or added on plan acceptance criteria at the plan leg (resolves q1)
- evidence records live alongside the deviation ledger in the per-plan delivery store — one execution-history store per plan, not a new store family (resolves q2)
- the today spec reconciles frames via explicit supersedes links; any conflict not covered by a supersedes link is surfaced for human decision, never auto-resolved (resolves q3)
- behavioral deltas are filed by a new flat verb at delivery time, sibling to deviate — and can also be drawn from the test surface: behavioral tests are identifiable by convention, tagged (e.g. a pytest marker) or in a dedicated folder such as behavioral-tests, from which the agent proposes deltas and evidence (resolves q4)
- evidence records are append-only — adjudication is the only mutation, the lapse and deviate discipline; a wrong record is superseded by filing a correct one, never edited (resolves q5)
- the today spec is a committed first-class artifact in the repo, peer of exported specs — not gitignored working state (resolves q6)

## Hard questions

- do test obligations attach to frame claims, plan acceptance criteria, or both — and at which leg are they planted (think, spec-to-plan, or challenge)? (resolved: both legs: obligations are planted on frame claims at the think leg AND updated or added on plan acceptance criteria at the plan leg)
- where do evidence records live — the existing per-plan delivery store, a new evidence store keyed by plan slug, or on the plan itself? (resolved: evidence records live along with delivery — the per-plan delivery store)
- are evidence records append-only with adjudication as the only mutation (the lapse and deviate discipline), or amendable? written-late-is-written-flattering applies to evidence exactly as it does to lapses (resolved: append-only — adjudication (confirm or reject) is the only mutation an evidence record ever gets, the lapse and deviate discipline)
- which move files a behavioral delta — a new flat verb at delivery time, a side effect of the evidence move, or derived at summary time from plan deliverables plus approved deviations? c7 assumes deltas exist but nothing says how they are created (resolved: a new flat verb files behavioral deltas at delivery time, sibling to deviate — never derived at summary time from memory; deltas and evidence can also be drawn from the test surface itself, where behavioral tests are identifiable by convention: tagged (e.g. a pytest marker) or in a dedicated folder such as behavioral-tests)
- where does the today-spec artifact live and is it committed — e.g. docs/current-spec.md beside docs/specs/, or uncommitted working state like reviews and questions? (resolved: committed — the today spec lives in the repo as a first-class artifact (e.g. docs/current-spec.md), like exported specs, not gitignored working state)
- what is the precedence rule when two frames' confirmed claims conflict — latest frame wins, explicit supersedes links, or per-conflict human adjudication? (resolved: explicit supersedes links between frames; a conflict without a supersedes link requires a human decision, never auto-resolution)

## Resolved vagueness

- [unknown_nonblocking] whether a human-authored supersedes link can be retracted after adjudication, and what a projection already derived from it does then — resolved: retraction is a first-class append-only event, never an edit; supersession also adds state to the superseded record itself — a superseded flag flipped on the target — so any reader can tell a record is superseded without scanning the ledger for inbound links; the projection recomputes deterministically on render, and the committed artifact's git history is the audit trail of past projections
- [unknown_nonblocking] how the evidence-strength ladder interacts with summarize-delivery's existing confidence vocabulary and lapse-driven confidence caps — undesigned; risks two competing confidence scales in one summary — resolved: one scale, not two: the evidence-strength ladder is the confidence vocabulary in the summary's Delivery Claims, and approved lapses act as caps on that ladder — e.g. an approved grader-unverified lapse caps renderable strength below execution regardless of what was filed
