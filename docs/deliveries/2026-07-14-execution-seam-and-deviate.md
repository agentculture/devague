# Delivery Summary — execution seam and deviate

plan: `execution-seam-and-deviate` · run: `complete` · date: `2026-07-14`
baseline: `devague summary skeleton`

## Intent

Ship devague 0.18.0 — the execution seam: a deliverables view that answers
"what do we have in the end?" at the go/no-go (#70), the four-column split-plan
table humans actually approve (#69), dependency-edge removal and task amending
without recreation cascades (#68), stdout-visible demotion (#67 hardening),
first-class human-approved deviation records connecting the plan to the
delivery summary (the new sixth leg), a render-only `devague summary` skeleton,
the `culture.yaml` backend revert (#66), and evidence-based closures of issues
62 and 67. Executed as 11 tasks over 4 dependency waves by an `/assign-to-workforce`
fan-out (one agent per task, isolated worktrees, TDD-gated merges).

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — plan-engine escape hatches and demotion visibility: `depend --remove`,
  new `amend` move, stdout flip echo
- `t2` — read-only `devague plan deliverables` view with `--json` and
  not-converged banner
- `t3` — delivery store and the `devague deviate` move
- `t4` — render-only `devague summary` verb with `--pr` PR-body mode
- `t5` — split-plan renders the four-column table with wave-listing markers
- `t6` — split-plan End state section quoting `plan deliverables`
- `t7` — new sixth origin skill `/deviate`
- `t8` — summarize-delivery consumes deviation records and the summary skeleton
- `t9` — culture.yaml backend reverts to claude with live agex verification
- `t10` — close issues 62 and 67 with cited evidence
- `t11` — release closure: version bump, changelog, docs, coverage and
  boundary audit

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `Plan.remove_dep` + `amend` move + stdout flip echo on all demoting moves; commit `d0b684f`, 24 tests in `tests/test_plan_escape_hatches.py` |
| `t2` | delivered | `devague plan deliverables [--json]`, `devague/render/deliverables_md.py`, `terminal_tasks` helper; commit `b12db1a`, 22 tests |
| `t3` | delivered | `devague/delivery.py`, `devague/delivery_store.py`, `devague deviate` verb; commit `6b06ec7`, 44 tests; dogfooded live in this very run (record `d1`) |
| `t4` | delivered | `devague summary [--pr] [--json]`, `devague/render/summary_md.py`; commit `1bcc8d0`, 30 tests; this artifact's baseline was rendered by it |
| `t5` | delivered | four-column `Wave / Task / Model / Task summary` table, real model tokens, 72-char truncation, wave-listing markers; commit `ba94f84` |
| `t6` | delivered | trailing End state section quoting `devague plan deliverables` verbatim, with graceful degradation hint on older devague; commit `436d323` |
| `t7` | delivered | `.claude/skills/deviate/SKILL.md` (sixth origin skill) + `docs/skill-sources.md` registration; commit `6934479` |
| `t8` | delivered | summarize-delivery starts from the `devague summary` skeleton, quotes approved deviations by `dN` id, three-tier baseline ladder; commit `003d0c6` |
| `t9` | delivered | `culture.yaml` declares `backend: claude` (commit `bee2158`); live verification passed — PR `#72` was opened via `agex pr open` with the reverted backend in place (criterion 2, risk `r1`) |
| `t10` | delivered | #67 closed with the 0.17.2 repro transcript; #62 closed citing 0.17.0/#63 and the dogfood artifact; both comments signed (operator task, no code) |
| `t11` | delivered | version 0.18.0, full CHANGELOG entry, six-leg-flow docs (`CLAUDE.md`, `README.md`, `docs/skills.md`), coverage + boundary audits; commit `8e729e3` |

## Mid-work Decisions

- `d1` — no PLAN_SCHEMA_VERSION bump shipped with `depend --remove` and
  `amend` (task `t1`, classification `acceptable`) — recorded during the run
  as llm-origin `proposed`, **approved by the user** at the final gate via
  `devague deviate --confirm d1`.
- `d2` — `devague learn skills` teaches authoring all six origin skills, not
  the original three (task `t11`, classification `acceptable`) — user-directed
  at the final PR gate (user origin, auto-approved); the recipe also stopped
  emitting script URLs for the three method-only skills, which would have
  been 404s.
- Mid-run, the human owner refined the split-plan Model-column contract
  ("should be the model, and if matters, harness — haiku, sonnet, opus, fable,
  colleague, codex"); forwarded verbatim to the `t5` agent and applied as a
  guidance line after the table, not a new column. Gate-2 owner amending the
  split in-flight; `t5`'s acceptance criteria were unchanged.
- `t3` made `--task` required when recording a deviation (the brief left it
  ambiguous) — symmetric with the missing-`--reason` refusal.
- `t2` extended "never refuses" to a regressed source frame: `deliverables`
  renders with the banner where `status`/`converge`/`export` raise; a
  missing/corrupt frame still raises.
- `t6` placed the End state section last (after the go/no-go block): the
  acceptance criterion "output ends with the End state section" overrode the
  brief's looser "before the go/no-go" wording — criteria are the contract.
- `t11` fixed two pre-existing stale doc statements the release made obviously
  wrong (plan-move lists missing `instruct`; the "Current gap: nothing
  consumes waves" paragraph) — invited by its instruction, noted for
  completeness.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t1` (`d1`, approved) | cutting an edge or amending criteria mutates existing list fields — no persisted shape change, so the frame assumption c14 (conditional on a plan-JSON shape change) did not apply; deviation records live in their own store per resolved q3 | acceptable |
| `t11` (`d2`, approved) | user directive at the final PR gate: the skill-authoring recipe still taught only think, spec-to-plan, and assign-to-workforce — an agent following it would rebuild a three-legged kit while the shipped flow has six legs | acceptable |
| `t9` | acceptance criterion 2 (live `agex pr open`) was sequenced after this artifact's first commit by design (risk `r1`); resolved in-run — PR `#72` opened via `agex pr open`, requiring a `git stash -u` workaround for an unrelated agex bug (filed upstream as devex issue 92) | acceptable |

No other task drifted: `t2`–`t8`, `t10`, `t11` delivered against their
acceptance criteria as confirmed.

## Evidence

- tests: `uv run pytest -n auto` — **614 passed** (final: all four waves +
  gate-3 review fixes + the d2 learn extension; 577 at wave close)
- coverage: `uv run pytest -n auto --cov=devague` — **98.02 %** (CI gate
  requires ≥ 95 %)
- lint: `uv run flake8 --config=.flake8 devague/ tests/` — clean;
  `markdownlint-cli2 "CHANGELOG.md" "README.md" "CLAUDE.md" "docs/skills.md"`
  — 0 errors
- boundary audit: grep for `subprocess|urllib|requests|httpx|socket|anthropic|
  openai` across `deliverables_md.py`, `summary_md.py`, `deviate.py`,
  `summary.py`, `delivery.py`, `delivery_store.py` — zero usages (one
  docstring stating the absence)
- commits: `40fa144..2bf6c33` (11 task commits + 11 merge commits on
  `spec/execution-seam-and-deviate`)
- issues: [#67](https://github.com/agentculture/devague/issues/67) closed
  (comment 4974139790), [#62](https://github.com/agentculture/devague/issues/62)
  closed (comment 4974140038)
- deviation store: `.devague/deliveries/execution-seam-and-deviate.json`
  (record `d1`, status `approved`)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| `devague plan deliverables` answers the end-state question read-only, never refusing (#70) | high | commit `b12db1a` · `tests/test_plan_deliverables.py` (22 tests, byte-identical-state proof) |
| split-plan renders the four-column table + End state section (#69, #70) | high | commits `ba94f84`, `436d323` · `tests/test_assign_to_workforce_script.py` (end-to-end script runs) |
| a dependency edge is removable and a task amendable without recreation (#68) | high | commit `d0b684f` · `tests/test_plan_escape_hatches.py` round-trip tests |
| every demoting move names the flip on stdout alone (#67 hardening) | high | commit `d0b684f` · stdout-only capture test |
| human-approved deviations are first-class, append-only records | high | commit `6b06ec7` · `tests/test_deviate.py` (44 tests) · live record `d1` produced during this run |
| `devague summary` renders the eight-section skeleton with no overclaim | high | commit `1bcc8d0` · `tests/test_summary.py` (30 tests) · this artifact's own baseline |
| the six-leg flow is documented end to end | high | commits `6934479`, `003d0c6`, `8e729e3` · files `.claude/skills/deviate/SKILL.md`, `docs/skill-sources.md`, `CLAUDE.md` |
| `devague learn skills` teaches authoring all six origin skills (method-only ones without fabricated script URLs) | high | commit `18af032` · `tests/test_cli_learn.py` |
| the cicd lane works with `backend: claude` from this repo | high | PR `#72` opened via `agex pr open` (signed, Qodo review posted) with `backend: claude` in `culture.yaml` |
| 0.18.0 publishes cleanly to PyPI | unverified | publish workflow runs post-merge — not claimed done |

## Remaining Work / Follow-up

- Issues #66, #68, #69, #70 close on PR merge (close-keywords in the PR body).
  Owner: human at gate 3.
- guildmaster re-broadcast: four origin skills changed here (`deviate` new;
  `assign-to-workforce`, `summarize-delivery` updated; `docs/skill-sources.md`
  registry) — guildmaster pulls from devague post-merge. Owner: guildmaster.
- Small follow-up found while dogfooding: the `devague summary` skeleton's
  `baseline:` line renders `devague plan (<slug>)` rather than the SKILL.md
  tier vocabulary (`devague summary skeleton`) — align the renderer's label
  with the skill's three-tier names. Candidate issue for 0.18.x.
- Upstream: devex issue 92 (`agex pr open` misreads gh's untracked-files
  warning as failure with a misleading network hint) — filed during this run;
  the `git stash -u` workaround stands until it lands. Owner: devex.
