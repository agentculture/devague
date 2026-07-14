# summarize-delivery skill

> devague closes the loop: after assign-to-workforce executes a plan, the new summarize-delivery skill turns the run into an accountability artifact - planned versus actual delivery, mid-work decisions, plan drift, evidence-backed delivery claims, and remaining work
> instruction: verify the shipped kit: .claude/skills/summarize-delivery/SKILL.md exists, docs/skill-sources.md lists it as the fifth origin skill, and the flow docs name the five-leg flow ending in summarize-delivery

## Audience

- the operator (main agent) closing a workforce run, the human owner at the final PR gate, and any later reader who needs to know what actually shipped without replaying the execution transcript
  - instruction: check SKILL.md names all three readers, and that the artifact is committed (durable) and readable standalone

## Before → After

- Before: what we plan is not always what we deliver: agents make mid-work decisions, discover constraints, cut scope, and make delivery claims that were never in the plan - and the flow has no wrap-up leg to record any of it
  - instruction: grep .claude/skills/ and docs/ for an existing wrap-up or delivery-summary step: none exists today
- After: after an assign-to-workforce run - complete, partial, or failed - the operator produces a delivery summary that separates planned work from actual delivery, records mid-work decisions and plan drift, and states delivery claims with evidence and confidence, plus remaining work
  - instruction: dry-run the skill against a real workforce run (complete and partial): the artifact separates planned from actual, and lists decisions, drift, claims with evidence, and remaining work

## Why it matters

- the plan becomes a contract, not a fiction: the summary records where execution obeyed the contract, where it changed, and what is actually safe to claim as delivered
  - instruction: check the template keys drift and claims to plan task ids so the contract comparison is mechanical, not rhetorical

## Requirements

- invocable after assigned work is completed or partially completed
  - instruction: check SKILL.md: partial and failed runs are named valid inputs; no step requires all waves merged
  - honesty: the skill has no completion precondition: a run that merged zero waves is still a valid input
- distinguishes planned work from actual delivery
  - instruction: check the template: Planned Work and Actual Delivery are separate mandatory sections, and Planned Work quotes the plan (task ids and summaries verbatim) rather than paraphrasing
  - honesty: the Planned Work section quotes the plan verbatim (task ids and summaries), so drift is detected against the contract the user confirmed, not a paraphrase
- explicitly captures mid-work decisions and plan drift, classifying each drift as acceptable, risky, or needs-follow-up
  - instruction: check the template: each drift entry names the plan item it diverges from, the reason, and exactly one classification: acceptable, risky, or needs-follow-up
  - honesty: drift entries are exhaustive relative to the plan: any plan task whose delivery differs appears as a drift entry, never silently normalized
- produces delivery claims with a confidence level (high/medium/low) and evidence pointers - commits, files, PRs, issues, tests, logs, docs - where available
  - instruction: check the template: each delivery claim line carries confidence and evidence fields, and evidence pointers are resolvable (commit SHA, file path, PR or issue number, test node id)
  - honesty: each evidence pointer resolves: the commit exists, the file is at the path, the PR or issue number is real, the test node ran
- avoids overclaiming: a delivery claim without evidence is marked unverified, never asserted as done
  - instruction: check SKILL.md hard rules: no-overclaiming is a hard rule, and the template defaults missing evidence to unverified
  - honesty: the unverified marker survives into the committed artifact - no downstream step upgrades confidence without new evidence
- usable when work is incomplete, failed, or partially delivered - failure is reported faithfully, not smoothed over
  - instruction: dry-run the template against a failed run: no section becomes unwritable; Remaining Work and Drift absorb the failure
  - honesty: a failed run produces a truthful artifact: the failure appears under drift and remaining work with its cause, and no delivery claim says done
- the artifact follows the eight-section shape from the proposal: Intent, Planned Work, Actual Delivery, Mid-work Decisions, Drift From Plan, Evidence, Delivery Claims, and Remaining Work / Follow-up
  - instruction: check the shipped template carries all eight sections; any rename or merge is recorded as drift from this spec in the PR description
  - honesty: the shipped template carries all eight sections and stays writable for partial and failed runs
- summarize-delivery is registered as the fifth origin skill in docs/skill-sources.md (origin devague; guildmaster re-broadcasts to the mesh; never re-vendored back)
  - instruction: check the docs/skill-sources.md origin-skills table gains a summarize-delivery row in the same PR that adds the skill
  - honesty: the skill-sources.md row lands in the same PR as the skill, so provenance never lags the kit

## Honesty conditions

- running the skill after a real workforce run yields an artifact a human can audit without reading the execution transcript
- the summary is producible from durable inputs (plan state, git history, PR links, test output) - it never depends on unrecorded memory of the run
- the gap is real: no existing skill or doc in the kit defines a wrap-up step (verified against .claude/skills/ and docs/skills.md)
- every delivery claim in the artifact traces back to a plan task or an explicit drift entry - the plan-versus-actual comparison is mechanical
- the artifact is committed and self-contained, so the final-PR reviewer can use it as the review map
- a summarize-delivery run leaves .devague/ state byte-identical
- both counts are checkable by inspection of the artifact alone, with no hidden context

## Success signals

- in an exported delivery summary, 100% of plan tasks are accounted for (delivered, partial, dropped, or blocked) and every delivery claim carries a confidence level plus at least 1 evidence pointer or an explicit unverified marker
  - instruction: auditable from the artifact alone: count plan tasks versus accounted rows; scan every claim line for confidence plus evidence-or-unverified

## Scope / boundaries

- delivery-side closure only: the skill summarizes and cross-references after execution - it does not orchestrate work, gate merges (assign-to-workforce owns the TDD gate), mark plan tasks done, or mutate devague state; reads of plan and frame state are read-only (issue 20)
  - instruction: grep the shipped SKILL.md: the only devague moves it documents are read-only (plan show, plan waves, scope --list, show, status)

## Non-goals

- not a polite progress report and not a restatement of the plan - it is an accountability artifact

## Assumptions

- when the run was devague-driven, plan state (tasks, acceptance criteria, waves) and the exported plan-md are available as the planned-work baseline; when absent, the skill degrades to git and PR history and says so in the artifact

## Scope exploration

- `s1` — `.claude/skills/assign-to-workforce/SKILL.md`: the upstream leg read end-to-end: three human gates, TDD-gated merges, per-task acceptance kept as uncommitted working state, final PR via cicd - the end state summarize-delivery must summarize; its verbatim-brief rule motivates quoting the plan verbatim in Planned Work
  - seeds: `c2`, `c7`, `c14`
- `s2` — `.claude/skills/scope/SKILL.md`: the chassis precedent: scope shipped method-only in 0.15.0 (no script, no CLI verb) with the CLI move landing later via the issue 53 build plan - summarize-delivery v1 copies that shape
  - seeds: `c19`
- `s3` — `docs/skill-sources.md`: origin-skills table: devague is upstream for scope, think, spec-to-plan, assign-to-workforce; a fifth origin row is where summarize-delivery registers; guildmaster re-broadcasts and never re-vendors back
  - seeds: `c17`
- `s4` — `devague plan waves --json (as documented in assign-to-workforce SKILL.md)`: the deterministic planned-work baseline: tasks keyed by id with verbatim summary, instruction, acceptance criteria, and covered targets - the contract actuals are compared against
  - seeds: `c12`, `c7`
- `s5` — `.devague/ and docs/ layout`: two artifact tiers observed: .devague reviews and questions are uncommitted non-authoritative working state; docs/specs and docs/plans are committed buildable artifacts - an accountability artifact belongs in the committed tier
  - seeds: `c20`

## Decisions

- the skill is named summarize-delivery: a verb-phrase name like assign-to-workforce; plan-to-delivery would misname the leg because assign-to-workforce is what takes the plan to delivery - this skill summarizes it
- v1 is method-only like scope at birth: SKILL.md with the output template, no entry-point script, no new CLI verb; the deterministic CLI surface is unchanged (issue 20); a future delivery engine is parked as follow-up
- the summary is a committed, durable artifact at `docs/deliveries/<created-date>-<slug>.md` - the structural peer of docs/specs/ and docs/plans/; uncommitted .devague/ working state stays for non-authoritative drafts
- the skill may run read-only verification (test suite, linters, git log) to substantiate a delivery claim before writing it; it never mutates code or state; a claim it cannot verify stays unverified

## Open / follow-up

- a future devague delivery engine - a third structural peer (delivery store, per-task accounting, deterministic no-overclaim gate) - deferred until dogfooding the method-only skill shows machine state is needed
