# Delivery Summary — behavior validation and today spec

plan: `behavior-validation-and-today-spec` · run: `complete` · date: `2026-08-31`
baseline: `devague summary skeleton`

## Intent

Ship the behavioral-validation loop and the derived today spec (issue #107):
planted test obligations on frame claims and plan acceptance criteria, an
append-only evidence and behavioral-delta ledger in the delivery store, unmet-
obligation warnings in both convergence engines, staleness joins, the
`devague today` projection writing a committed `docs/current-spec.md`, the
Delivery Claims table populated from real evidence with lapse caps, the
`/validate-delivery` eighth leg, and the refreshed `learn` plus the
`learn review` gate-3 reviewer seam — executed as the 15-task, 6-wave
`behavior-validation-and-today-spec` plan by an assign-to-workforce fan-out
(one agent per task per wave, TDD-gated merges, four tasks escalated to opus
per the approved split plan).

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — Frame-side obligation model: Obligation records on claims with seam, behavior text, and source-text snapshot; SCHEMA_VERSION 5 to 6
- `t2` — Plan-side criterion obligations: obligations attach to task acceptance criteria; PLAN_SCHEMA_VERSION 4 to 5
- `t3` — Delivery-store evidence and delta records: EvidenceRecord and DeltaRecord, append-only with superseded flag; DELIVERY_SCHEMA_VERSION 1 to 2
- `t4` — The oblige CLI verbs: flat devague oblige for frame claims plus a plan-group verb for criterion obligations
- `t5` — The evidence CLI verb: file, list, confirm, reject evidence records with verbatim outcomes
- `t6` — The delta CLI verb: file behavioral deltas, supersede and retract as append-only events
- `t7` — Unmet-obligation warnings in both convergence engines, S1 and S2 pattern, never gating and never reading lapses
- `t8` — Staleness joins: deviations with un-updated evidence, and evidence for behavior no longer in the contract
- `t9` — The today-spec projection module: deterministic fail-open walk of all frames, plans, and deliveries into a behavior ledger view
- `t10` — The today renderer and verb: committed undated docs/current-spec.md, standalone-readable, with coverage boundary and evidence age
- `t11` — Delivery Claims populated from evidence: strength ladder as the confidence vocabulary, approved lapses as caps
- `t12` — The validate-delivery skill and the eight-leg flow renumbering sweep
- `t13` — devague learn refresh: teach obligations, evidence, deltas, the strength ladder, and the today spec
- `t14` — devague learn review: the reviewer seam — a self-contained gate-3 audit topic
- `t15` — End-to-end success-signal measurement on this repo's real state

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `Obligation` + `Frame.add_obligation` + `obligation_drift` in `devague/frame.py`; SCHEMA_VERSION 6; 24 tests |
| `t2` | delivered | `CriterionObligation` + `Plan.add_obligation` in `devague/plan.py`; PLAN_SCHEMA_VERSION 5; 20 tests (`plan_store.py` needed no change — its schema gate is generic) |
| `t3` | delivered | `EvidenceRecord`/`DeltaRecord`/`SupersessionEvent`/`RunReference` in `devague/delivery.py`; DELIVERY_SCHEMA_VERSION 2 with raw-dict check moved before parse; 50 tests |
| `t4` | delivered | `devague oblige` + `devague plan oblige`, drift markers in `show`/`plan show`, `criterion_obligation_drift` added to `plan.py`; 67 tests across four files |
| `t5` | delivered | `devague evidence` with run-reference shape validation and a no-subprocess pin; 36 tests |
| `t6` | delivered | `devague delta` with append-only supersede/retract; shared `cli/_refs.py` extracted from `deviate.py` (behavior pinned unchanged); 46 tests |
| `t7` | delivered | `_unmet_obligation_warnings` in both engines + `devague/obligation_evidence.py`; wired into `converge` and `status` on both engines; contested.py loaders made public with labels; 29 tests |
| `t8` | delivered | `devague/staleness.py` (stale deviations + orphaned evidence) rendered in `show`/`status`; 31 tests |
| `t9` | delivered | `devague/today.py` — lineage-based projection with conflict surfacing, fail-open walk, coverage span; 36 tests |
| `t10` | delivered | `devague/render/today_md.py` + `devague today` writing `docs/current-spec.md`; byte-identical-stores pin; 16 tests |
| `t11` | delivered | Delivery Claims populated from evidence in `summary_md.py` with `LAPSE_STRENGTH_CAPS`; staleness suffixes; 25 tests |
| `t12` | delivered | `.claude/skills/validate-delivery/SKILL.md` + eight-leg sweep of README/CLAUDE.md/docs (zero stale seven-leg mentions); command-table syntax fixed at reconcile (see Drift) |
| `t13` | delivered | `learn` gains behavioral-validation guidance, strength ladder, unmet-is-unmet operating rules; every-named-verb `--help` pin |
| `t14` | delivered | `devague learn review` (five-section gate-3 audit topic, twelve-command self-containment pins) + the eight-skill `learn skills` sweep |
| `t15` | delivered | `tests/test_end_to_end_validation.py` — warning count 1→0, one evidence-backed row, `today` byte-clean over this repo's real state, all measured from real subprocess stdout |

## Mid-work Decisions

No deviation records were filed (`devague deviate --list`: none) — no task
departed from its confirmed contract mid-run. Decisions not covered by any
record, captured directly:

- Wave 2 started before `t12` (docs-only, same wave 1) finished — no wave-2
  task depends on `t12` and its file footprint is disjoint; the dependency
  graph, not the wave boundary, was treated as the contract.
- `t7` wired the warnings into `status` as well as `converge` on both engines —
  leaving `status` silent would have made two views of the same gate disagree.
- `t11` touched `cli/_commands/summary.py` in addition to `summary_md.py` (the
  established edge-loading seam `status.py` uses; renderer stays pure).
- `t13` deliberately left the `learn skills` seven-name tuple to `t14` (same
  file territory); `t14` swept it to eight, including `plan learn`'s
  cross-reference.
- The operator fixed `t12`'s SKILL.md command table at reconcile after `t14`
  caught that it documented flags the real parsers do not accept.
- `t2` did not modify `plan_store.py` and `t1` did not modify `store.py` —
  both briefs allowed it, both stores' schema gates were already generic.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t12` | shipped a command table for `oblige`/`evidence`/`delta` written before those parsers existed, with flags that do not match them; caught by `t14`, fixed by the operator in the reconcile commit | acceptable |
| `t11` | tests were written after the implementation rather than failing-first, self-reported by the task agent as a process deviation from the TDD instruction | acceptable |

No other task diverged from its contract — backed by the task-by-task
accounting above and the zero deviation records.

## Evidence

- tests: `uv run pytest -n auto` — 1521 passed (from 1100 at baseline; +421)
- tests (behavioral, live run): `tests/test_obligation_warnings.py tests/test_today.py tests/test_today_md.py tests/test_today_cli.py tests/test_summary_delivery_claims.py tests/test_end_to_end_validation.py` — 109 passed at `3945fb7`
- lint: `flake8 --config=.flake8`, `black --check`, `isort --check --profile black` — clean; `markdownlint-cli2` — 0 errors on all touched docs
- commits: `a6fdd8e..c0a0392` (31 commits: 15 task merges + reconcile fixes + version bump)
- issues: #107 (motivating suggestion), #108 (filed mid-run: obligation-id ambiguity across frame/plan mints)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| Obligations plant at both legs and warn visibly-untested without gating | high | live run: `devague converge` emitted 3 warnings for `o1`–`o3` then stayed `converged ✓` · test `tests/test_obligation_warnings.py` |
| The evidence/delta ledger is append-only with adjudication and superseded flags as the only mutations | high | tests `tests/test_delivery_evidence.py`, `tests/test_cli_delta.py` (byte-for-byte no-edit pin) |
| `devague today` projects the behavior ledger read-only into `docs/current-spec.md` with an honest derived coverage boundary | high | live run over this repo's real state: 10 of 11 frames reported unledgered by name, zero behaviors projected while all deltas are proposed · test `tests/test_end_to_end_validation.py` |
| Delivery Claims render evidence strength capped by approved lapses | high | test `tests/test_summary_delivery_claims.py` · live run: placeholder retained while obligations are unadjudicated (nothing renders as delivered without approval) |
| The full loop closes: warning count 1→0 once approved evidence is filed | high | test `tests/test_end_to_end_validation.py` (counted from real subprocess stdout) |
| The live filings on this repo (`o1`–`o3`, `e1`–`e3`, `b1`–`b3`) validate the shipped behavior | unverified | pending human adjudication — llm-origin records are `proposed`; not claimed done |
| The reviewer seam teaches a correct and complete audit method | medium | `devague learn review` + twelve `--help` self-containment pins; capped below high by the pending `grader-unverified` lapse `l6` (t14's content tests share an author with the prose they check) |

Lapse ledger evidence: `l1`–`l6` all **pending approval (not yet evidence)** —
each is a task agent's self-report filed by the operator (`l1` t1 seam-as-free-
text, `l2` t3 approximate citations, `l3` t9 ledgered-frame semantics, `l4` t7
obligation-ref ambiguity → issue #108, `l5` t7 failing-evidence-discharges
ruling, `l6` t14 same-author content tests). None caps a claim above until
adjudicated; `l6` is treated as capping the reviewer-seam claim to `medium`
pre-emptively rather than flattering it.

## Remaining Work / Follow-up

- Human adjudication of the live filings: obligations `o1`–`o3`, evidence
  `e1`–`e3`, deltas `b1`–`b3` (`--confirm`/`--reject` on `oblige`/`evidence`/
  `delta`), and lapses `l1`–`l6` (`devague lapse --confirm/--reject`). After
  approval: re-run `converge` (warnings clear), `summary` (evidence-backed
  rows), `devague today` (behaviors project), and re-commit
  `docs/current-spec.md`.
- Issue #108 — disambiguate obligation refs across the frame and plan mints
  (qualified refs or disjoint id prefixes); until then the join under-warns.
- Plan risk `r2` (follow_up) — document the behavioral-test convention for
  consuming repos beyond the skill text.
- `l5`'s open ruling — whether an approved-but-failing evidence record should
  discharge the unmet-obligation warning (one-line predicate change if not).
- `docs/skills.md` does not yet mention the `learn review` topic (flagged by
  t14; outside its acceptance criteria).
