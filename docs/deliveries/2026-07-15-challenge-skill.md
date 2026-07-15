# Delivery Summary — challenge skill

plan: `challenge-skill` · run: `complete` · date: `2026-07-15`
baseline: `devague summary skeleton`

## Intent

Ship devague's seventh origin skill, `/challenge` — a risk-scaled blind-spot
discovery pass between `/think` and `/spec-to-plan` (issue #73) — by executing
the converged `challenge-skill` plan through `/assign-to-workforce`: four
tasks over three waves, one agent per task in an isolated git worktree,
TDD-gated merges, no new CLI engine (#20).

> devague gains a seventh origin skill, /challenge — a risk-scaled blind-spot
> discovery pass that pressure-tests the converged frame between /think and
> /spec-to-plan through structured lenses, routes every finding back through
> the existing deterministic moves, and records examined surfaces plus
> residual uncertainty instead of ever claiming there are no unknown unknowns

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — Author .claude/skills/challenge/SKILL.md — the seventh origin skill,
  method-only shape
- `t2` — learn teaches challenge: devague/cli/_commands/learn.py +
  tests/test_cli_learn.py in lockstep
- `t3` — Seven-leg docs sweep: README.md, CLAUDE.md, docs/skills.md,
  docs/skill-sources.md
- `t4` — Version bump to 0.19.0 + CHANGELOG entry; full gate green

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `.claude/skills/challenge/SKILL.md` (290 lines, sole file — method-only shape, `type: command`), all 5 acceptance criteria check-verified; commit `8ddd6b3`, merged `cca3d1b` |
| `t2` | delivered | one new `OPERATOR_SKILLS` entry + six→seven wording in `devague/cli/_commands/learn.py`, mirrored in `tests/test_cli_learn.py` (failing-first TDD: 8 failed → 616 passed); no new subparser/module/store; commit `a46bb33`, merged `b420372` |
| `t3` | delivered | seven-leg sweep of README.md, CLAUDE.md, docs/skills.md, docs/skill-sources.md — six-leg grep returns no hits, challenge third everywhere, shipped description quoted verbatim; commit `170dee2`, merged `735697d` |
| `t4` | delivered | `pyproject.toml` → 0.19.0 (+ `uv.lock`), Keep-a-Changelog 0.19.0 entry citing #73, and (per `d1`) the 0.19.0 CLAUDE.md Status paragraph; commit `d8758e0`, merged `fa49c23` |

## Mid-work Decisions

- `d1` — t4 additionally prepends a 0.19.0 release paragraph to CLAUDE.md's
  Status section (newest-first, repo convention) — the confirmed t4 acceptance
  criteria name only pyproject.toml and CHANGELOG.md; every prior release
  (0.15.0, 0.17.0, 0.18.0) also added a CLAUDE.md Status paragraph — omitting
  it would leave the Status section stale at 0.18.0 after this ships
  (recorded via `/deviate`, human-approved before t4 was spawned).
- t3 updated the standing "six-leg flow" sentence *inside* the historical
  0.18.0 Status paragraph to "seven-leg" — no deviation record covers this;
  t3's confirmed acceptance criterion 1 ("grepping the four files for six-leg
  wording returns no hits") required it, and the two purely historical
  "sixth" mentions in the same paragraph were left untouched.
- t3 kept README's "CLI-driving pair" framing (think / spec-to-plan) instead
  of grouping `/challenge` with the scripted skills, since challenge ships
  method-only with no wrapper script — a fidelity choice, captured here
  directly.
- The final PR was opened with `gh pr create` directly instead of the `cicd`
  skill's `agex pr open` wrapper, which failed transiently and treated
  pre-existing untracked working files as fatal; the `- devague (Claude)`
  signature was appended manually per convention.
- t1 attributes the spec's decision quotes as c17/c18/c19 (ids from the plan
  brief's mapping) even though the exported spec lists decisions unlabeled —
  flagged by the task agent, accepted as-is.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t4` (`d1`) | the confirmed t4 acceptance criteria name only pyproject.toml and CHANGELOG.md; every prior release (0.15.0, 0.17.0, 0.18.0) also added a CLAUDE.md Status paragraph — omitting it would leave the Status section stale at 0.18.0 after this ships | acceptable |

No other task drifted: t1, t2, and t3 delivered exactly against their
confirmed acceptance criteria (task-by-task accounting above).

## Evidence

- tests: `uv run pytest -n auto` — pass, **616 passed** (run after every wave
  merge: post-t2, post-t1, post-t3, post-t4)
- tests (TDD proof, t2): `tests/test_cli_learn.py` — 8 failed on
  tests-first run, green after implementation
- lint: `uv run flake8 --config=.flake8 devague/ tests/` — exit 0;
  `uv run black --check devague/ tests/` — clean;
  `uv run isort --check --profile black devague/ tests/` — exit 0;
  `markdownlint-cli2` on every changed markdown file — 0 errors
- version: `uv run devague --version` — `devague 0.19.0`
- commits: `a19819f..fa49c23` on `feat/challenge-skill` (spec `51f8490`,
  plan `2baa17c`, tasks `8ddd6b3` / `a46bb33` / `170dee2` / `d8758e0`,
  deviation ledger `f114634`)
- PRs / issues: PR #76 · issue #73
- deviation ledger: `.devague/deliveries/challenge-skill.json` (`d1`,
  approved, acceptable)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| `/challenge` ships as the seventh origin skill in the method-only shape (SKILL.md only, `type: command`, no new CLI verb) | high | file `.claude/skills/challenge/SKILL.md` · commit `8ddd6b3` · PR #76 |
| the skill's hard rules forbid a "no unknown unknowns" conclusion and require examined-surfaces + residual-uncertainty records on a clean pass | high | commit `8ddd6b3` (grep-verified against acceptance criteria 2/3) |
| `devague learn skills` teaches seven operator skills in seven-leg order, challenge third, method-only | high | commit `a46bb33` · `tests/test_cli_learn.py` in the 616-green suite |
| the CLI gained no new engine, verb, or store — the boundary (#20) held | high | t2 diff scope check (only `learn.py` + its tests under `devague/`) · commit `a46bb33` |
| all four doc surfaces name the seven-leg flow with challenge third | high | commit `170dee2` (six-leg grep: no hits) |
| 0.19.0 release prep is complete (version, changelog, Status paragraph) | high | commit `d8758e0` · `devague 0.19.0` |
| a `/challenge` pass following the shipped SKILL.md text end-to-end works on a real frame | unverified | the pass this run performed (scope entries s6–s8, parks v1–v2 on the `challenge-skill` frame) executed the specced method *before* the SKILL.md text existed; the first post-merge run per the shipped doc is follow-up evidence — not claimed done |

## Remaining Work / Follow-up

- Gate 3 — human review and merge of PR #76 (the final human gate; this
  artifact is its review map).
- Dogfood the shipped `/challenge` on the next real frame and watch the
  proportionality rule for over-/under-escalation (frame park `v2`,
  plan risk `r2`, and the `unverified` claim above — same follow-up).
- guildmaster re-vendors `/challenge` from
  `../devague/.claude/skills/challenge/` and re-broadcasts to the mesh on its
  own schedule (frame park `v1`, plan risk `r1`; the docs/skill-sources.md row
  documents the path).
