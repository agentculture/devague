# reasoning-degradation ledger

> devague gains a deterministic move that records degradations of the reasoning process — moments where an assumption was silently substituted for a check — as first-class append-only ledger entries filed when they happen: the reasoning-side twin of deviate, never gating convergence

## Audience

- operators — the main agent driving the CLI mid-run — plus the humans who own gate 2 and the final PR, and downstream method consumers (embodiment) whose delivery summaries cite ledger entries as confidence evidence

## Before → After

- Before: corrections records are reconstructed at the end, from memory, shaped by how the story turned out — in the embodiment cycle four graders failed, every one found by reading data afterwards, none by a test failing, and one nearly shipped a false safety claim
- After: a degradation is filed in seconds at the moment an assumption substitutes for a check; the delivery summary confidence column cites entry ids instead of end-of-run memory, and recovering a transition no longer costs hours of reading raw data afterwards

## Why it matters

- written late is written flattering: a ledger entry at the moment of the transition costs seconds, recovering it afterwards costs hours — so the recording move must be cheap enough that filing mid-flight actually happens

## Requirements

- the move reuses the deviate chassis: prefix-generic id minting (`Delivery._next`, devague/delivery.py:63-72), origin-driven initial status (llm-origin lands proposed, delivery.py:85), fail-closed enum validation in `__post_init__`, and append-only records with no delete path
  - honesty: the new record type reuses `_next`, origin-driven initial status, and fail-closed `__post_init__` validation rather than re-implementing them — checked in review of the shipping diff
- devague summary consumes approved ledger entries as evidence for the Delivery Claims confidence column, following the Mid-work Decisions and Drift From Plan render pattern (render/`summary_md.py`:205-244); the high/medium/low/unverified vocabulary lives only in the summarize-delivery skill today, not in code
  - honesty: devague summary renders approved entries only; proposed entries render as visibly pending (mirroring the deviation pattern); a missing ledger degrades to the existing empty-state line, never an error
- the closed move enumerations in the producer and consumer skills are amended to name the new move: the challenge routing rule (findings route through existing deterministic moves only — nothing else, challenge/SKILL.md:204-208) has no row shaped like a degradation that already happened, and the summarize-delivery read-only move table (SKILL.md:282-296) is likewise closed
  - honesty: the challenge and summarize-delivery closed move enumerations name the new move in the same PR that ships the verb — no doc-drift window
- the move lands in the MOVES dict in learn.py (today only 15 entries — deviate, summary, and plan are already absent, so `devague explain deviate` fails), the per-move contract tables in docs/spec-contract.md, README.md, and docs/skills.md, plus a CHANGELOG entry and the CI-enforced version bump
  - honesty: `devague explain <verb>` works for the new verb in the shipping PR — the MOVES dict entry is test-pinned — and the pre-existing deviate/summary/plan explain gap is filed as its own issue
- adding the lapses list bumps `SCHEMA_VERSION` 4 to 5: without the bump an older installed binary loads a lapse-bearing frame tolerantly and its next save silently drops every filed lapse (save re-stamps the current version and `to_dict` writes only known fields) — the `scope_entries` v2 precedent; the fail-closed version check is what turns silent data loss into a version hint
  - honesty: a v4-reading binary pointed at a v5 frame fails closed with the version hint instead of silently dropping lapse records on save — pinned by a reject-newer store test
- adjudication is on the verb, mirroring deviate: `devague lapse --confirm <lN>` / `--reject <lN>` (confirm and reject keep taking only c\* and h\* ids); statuses are proposed/approved/rejected, and a user-origin filing lands approved immediately — the deviate origin contract
  - honesty: an llm-origin lapse never becomes citable without a human --confirm; devague summary renders it as visibly pending until then — no path upgrades it automatically
- lapses render in devague show (`frame_md`) and the delivery summary; the exported spec-md never grows a lapse section — export overwrites the same dated file, so execution-time lapses would rewrite the what-to-build artifact on re-export; the contested-marker philosophy applies: process history points forward, the spec is not rewritten
  - honesty: re-exporting the spec after filing lapses produces a byte-identical spec-md — pinned by a test that files a lapse and diffs the export
- code validation is fail-closed at filing time but tolerant at load time: retiring a dead code after the dogfood cycle must never brick an existing frame — probe-confirmed: an unknown kind raises ValueError at construction, and `from_dict` constructs at load, so a closed load-time enum would refuse to load any frame that ever filed the retired code
  - honesty: a frame holding a lapse with a retired code still loads and renders after the code leaves the filing enum — pinned by a test that files, retires, reloads

## Honesty conditions

- filing an entry is one deterministic CLI call — no LLM, no subprocess — and converge output is byte-identical before and after filing, pinned by a test
- assign-to-workforce SKILL.md generalizes its worktree prohibition to name the new verb, not just `devague plan` commands
- no new human workflow is introduced: the same humans who own gate 2 and the final PR adjudicate ledger entries, inside gates that already exist
- in the dogfood cycle no single filing costs the operator more than a minute — otherwise the cheap-enough-to-use-mid-flight premise is false
- the embodiment corrections record and its four grader failures are real committed artifacts quoted in issue 97, not a reconstruction made for this spec
- at least one transition in the embodiment cycle was recoverable only because raw data happened to be committed — the near-miss is documented, not anecdotal
- a code with zero filings after the dogfood cycle is actually removed from the enum, not kept as documentation — covered is distinguished from reachable
- no CLI path mutates a lapse record after filing except the status transition — pinned by the argument surface (no amend flag) and a test

## Success signals

- in >= 1 dogfooded embodiment cycle, every degradation entry is filed mid-flight (0 reconstructed in the retrospective) and 0 codes ship without a named producer moment — codes with zero filings are dropped before the vocabulary freezes

## Scope / boundaries

- fan-out subagents never file ledger entries — only the main agent runs devague moves; a degradation noticed inside a task worktree is reported in the task-agent transcript and recorded by the main agent (assign-to-workforce SKILL.md:320-322 currently forbids only `devague plan` commands by name)
- lapse records are append-only in the strong sense: no amend and no delete — unlike scope entries, which amend in place with no trail; a wrong lapse is rejected and refiled, because an editable lapse re-enables written-late-is-written-flattering

## Non-goals

- the ledger never gates: no participation in blockers, warnings, or `parked_items` — both convergence gates iterate hand-written allowlists (frame.claims and frame.`open_vagueness` in convergence.py; plan.tasks and plan.risks in `plan_convergence.py`), so a new list field is invisible to them by default, the `scope_entries` precedent

## Assumptions

- degradation codes ship as a closed enum validated fail-closed at construction, like every existing kind vocabulary (`CLAIM_KINDS`, `VAGUENESS_KINDS`, and CLASSIFICATIONS — the nearest precedent: an optional single code per record, delivery.py:32); the six codes in issue 97 are the starting set, not the contract
- lapse refs are free text and never validated — the deviate comparison in decision c14 is imprecise: deviate validates id-shaped affects refs against the plan and its live frame (deviate.py:78-113), which a frame-side lapse cannot do for tN refs before a plan exists; the record is testimony, not a join

## Scope exploration

- `s1` — `agentculture/devague#97 (issue body)`: the evidence base: a 21-task, 7-wave embodiment run whose corrections record was reconstructed from memory at the end; four graders failed, all caught by reading data afterwards, none by a test failing; three explicit non-asks — not a gate, no new engine if a move on existing state suffices, no automation
  - seeds: `c1`
- `s2` — `devague/delivery.py + delivery_store.py + cli/_commands/deviate.py`: DeviationRecord is the direct template (append-only, origin-driven status, fail-closed enums, prefix-generic `_next`); but the store is keyed 1:1 by plan slug and every entry point resolves a plan first, failing closed with `no plan selected` — pre-plan degradations have nowhere to land without generalizing the keying
  - seeds: `c2`, `q1` (question, resolved)
- `s3` — `devague/frame.py + plan.py + store.py + plan_store.py + docs/spec-contract.md`: id prefixes c, h, q, v, s, t, r, d are taken (per-list prefix-generic `_next`); a new optional list field loads tolerantly without a schema bump (the `Claim.revisions` precedent) though new top-level lists have bumped by convention (`scope_entries`, v2); every kind vocabulary is a closed enum validated in `__post_init__` — no free-string kinds exist
  - seeds: `c8`, `q2` (question, resolved)
- `s4` — `devague/convergence.py + plan_convergence.py`: both gates are hand-written allowlists over named fields — frame.claims and frame.`open_vagueness`, plan.tasks and plan.risks, nothing else; `scope_entries` appears nowhere in convergence.py (grep-confirmed) — the shipped precedent that a new list field is recorded, visible in renders, and never gates by default
  - seeds: `c3`
- `s5` — `devague/render/summary_md.py + _md_safety.py + cli/_commands/summary.py`: the Delivery Claims section renders a bare `<fill: confidence>` placeholder — the high/medium/low/unverified vocabulary exists only in summarize-delivery SKILL.md, not in code; approved deviations render in exactly two sections (Mid-work Decisions, Drift From Plan); a new verbatim render site needs `md_safe_text` plus table-cell escaping
  - seeds: `c4`
- `s6` — `.claude/skills/{challenge,deviate,summarize-delivery,assign-to-workforce}/SKILL.md`: the deviate method gates the recording itself behind explicit human approval (the one non-negotiable step); the challenge routing table has no row for a degradation that already happened and its hard rule is a closed nothing-else enumeration; the summarize-delivery read-only move table is likewise closed; assign-to-workforce forbids subagents only `devague plan` commands by name
  - seeds: `c5`, `c6`, `q3` (question, resolved)
- `s7` — `devague/cli/__init__.py + cli/_commands/learn.py + README.md + docs/skills.md`: a new verb is one `_commands/` module exposing register() plus two lines in `_build_parser` (cli/`__init__.py`:73-127); the MOVES dict in learn.py holds only 15 of 20 verbs — deviate, summary, and plan are absent, so `devague explain deviate` fails today, a live gap the new move must not repeat; version-check CI blocks merge without a pyproject bump
  - seeds: `c7`, `q2` (question, resolved)
- `s8` — `challenge pass / adjacent-systems lens: devague/store.py + frame.py tolerant load`: an older binary loads a frame carrying an unknown list tolerantly and re-saves without it — silent loss of filed lapses unless `SCHEMA_VERSION` bumps; `scope_entries` shipped with the v2 bump for exactly this reason
  - seeds: `c17`
- `s9` — challenge pass / failure-mode lens: frame.py `__post_init__` validation at load (probe): probe: a Claim with kind bogus-kind raises ValueError at construction; `from_dict` constructs at load — so retiring a lapse code from a closed enum bricks loading of frames that filed it; write-closed load-tolerant validation is what makes the h11 dead-code removal safe
  - seeds: `c21`
- `s10` — `challenge pass / lifecycle lens: export overwrite semantics (spec_md, frame_md, summary_md)`: the spec left render placement undefined while export overwrites the same dated file — execution-time lapses would rewrite the spec artifact on re-export unless `spec_md` deliberately excludes the ledger
  - seeds: `c19`
- `s11` — `challenge pass / unstated-assumptions lens: the adjudication surface`: decision c15 says adjudicate in bulk but names no move — confirm and reject take c\* and h\* ids only today; the deviate precedent is confirm and reject flags on the verb itself
  - seeds: `c18`
- `s12` — challenge pass / data-flow lens: deviate.py `_validate_refs` vs frame-side refs: the deviate affects field validates id-shaped refs against plan tasks, coverage targets, and the live source frame — a frame-side lapse cannot validate tN refs before a plan exists, so the free-text-ref language in decision c14 is imprecise as written
  - seeds: `c22`
- `s13` — `challenge pass / reversibility lens: deviate append-only vs scope --amend`: two correction idioms coexist: deviate corrects by append (no amend move), scope amends in place (no trail) — the lapse ledger must pick append-only or the written-late-is-written-flattering rationale collapses
  - seeds: `c20`
- `s14` — `challenge pass / concurrency lens: single-writer CLI + worktree fan-out`: clean — only the main agent at the repo root mutates .devague state (boundary c6), no locking exists today; residual risk confined to two operators sharing one checkout, which no current flow does

## Decisions

- the ledger attaches to the Frame as a new list of lapse records — the `scope_entries` pattern: reachable from `devague new` through execution, rendered but never gating; entries may free-text-ref plan tasks (tN) the way the deviate affects field does; no new store, no new engine
- filing is friction-free: the agent files a lapse immediately at the moment of the transition; llm-origin entries land proposed and never block anything; the human adjudicates in bulk at summarize-delivery time, and only approved entries are citable as confidence evidence in the Delivery Claims table
- the verb is `lapse` (noun and verb, like park and deviate); record ids are `lN`; the degrade and ledger names were rejected for collisions with the fail-open error-handling idiom and the delivery-ledger vocabulary

## Hard questions

- where does the ledger attach: the existing delivery store (zero new engine, but keyed 1:1 by plan slug — unreachable before a plan exists, `resolve_plan` fails closed with `no plan selected`), frame state, plan state, or a frame-keyed fourth store? the issue evidence arose at execution time, but its codes can arise during think and challenge too (resolved: frame-level list, like `scope_entries`: reachable from devague new through execution; entries may free-text-ref plan tasks the way the deviate affects field does; no new store)
- what is the verb named? `ledger` collides semantically with the established delivery-ledger vocabulary across contested.py, `delivery_store.py`, and deviate.py; `degrade` collides with the fail-open error-handling idiom in 8 files; `lapse` and `erode` are unused; the record id prefix must avoid c, h, q, v, s, t, r, and d (resolved: the verb is lapse; record ids are lN)
- does filing require human approval before recording, as deviate mandates (a user-origin record IS the approval, deviate/SKILL.md:97-100), or is the agent self-report recorded without approval as issue 97 proposes (the agent decides when it degraded; the CLI records it deterministically)? the load-bearing feature of the deviate template is exactly what the proposal drops (resolved: file free, adjudicate later: llm-origin entries land proposed and never block; the human adjudicates in bulk at summarize-delivery time; only approved entries are citable as confidence evidence)
- how does the spec distinguish covered from reachable for each code (embodiment#18: a code nobody ever files reads as a category nobody ever hit) — does each shipped code need a named producer moment in a skill, or a dogfood report before the vocabulary freezes?

## Open parks

- [follow_up] embodiment offers to dogfood a prototype and report back real entry counts and which degradation codes turned out dead — the closing offer in issue 97
- [follow_up] whether id-shaped lapse refs later deserve a contested-style join into plan and summary renders — deferred until dogfood shows refs are actually filed
