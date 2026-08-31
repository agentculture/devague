# Delivery Summary — next-leg hints

plan: `next-leg-hints` · run: `complete` · date: `2026-08-31`
baseline: `devague plan (next-leg-hints)`

## Intent

> Every devague command tells the agent how to progress - the next move in
> its leg and the hand-off to the next leg - via a hint the user can turn
> off or replace

After: after any devague command succeeds, one stderr hint names the next
move within its leg or the hand-off to the next leg - unless the user turned
hints off or replaced the text

## Planned Work

- `t1` — Hint table and dispatch emission: new devague/cli/`_hints.py` with
  the verb-to-next-move table (flat verbs plus plan subverbs, status exempt,
  next: prefix), wired once into `_dispatch` on success
- `t2` — Override config: new devague/cli/`_hint_config.py` reading
  tool.devague from the CWD pyproject.toml plus the `DEVAGUE_HINTS` env var
  (env wins) - global on/off and per-verb replacement text, fail-open
- `t3` — Docs sweep: the global hint clause in docs/spec-contract.md, README,
  CLAUDE.md, and the learn/explain teaching surface
- `t4` — Eight SKILL.md hand-off reconciliation to the eight-leg order
- `t5` — Hint test suite: new tests/`test_cli_hints.py` plus the three
  permitted empty-stderr assertion updates

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | merged | `devague/cli/_hints.py` (153 lines): `hint_for()` classifies every leaf verb (flat, `plan:` subverbs) as exempt / leg-ending / within-leg; `emit_next_hint()` called exactly once from `_dispatch` on rc 0. Plus `tests/test_cli_hints.py` (56 tests) and, under approved `d1`, the three empty-stderr assertion updates. Under approved `d2`, the latent `split-plan --write` stderr-merge bug fix. |
| `t2` | merged | `devague/cli/_hint_config.py`: fail-open `tomllib` read of `[tool.devague]` in the CWD pyproject + `DEVAGUE_HINTS` env (off/0/false, env wins), per-verb replacement via `[tool.devague.hints]`; wired into the emission decision only — the default table untouched. `tests/test_hint_config.py` (44 tests). |
| `t3` | merged | One global hint clause in docs/spec-contract.md beside the stdout/stderr split statement; README + CLAUDE.md name the feature and overrides; `learn.py` MOVES teach the hint for the leg-ending verbs and the operating rules mention the contract. Under approved `d3`, `deviate` and `summary` gained their missing MOVES entries. |
| `t4` | merged | All eight SKILL.md hand-offs reconciled to the eight-leg order: think routes through /challenge; challenge's diagram includes validate-delivery; spec-to-plan and validate-delivery gained dedicated After sections; assign-to-workforce gained a hand-offs section naming /deviate and /validate-delivery; deviate routes through /validate-delivery; summarize-delivery's provenance ordinal clarified. |
| `t5` | merged | Gap analysis over t1/t2's tests, then: error-path assertions (zero `next:` on failure), the `hint:`-vs-`next:` prefix-disjointness assertions, the `@pytest.mark.behavioral` end-to-end walk that chooses every move by parsing the previous command's hint, and pytest marker registration in pyproject.toml. Verified the three d1 assertion sites rather than re-making them. |

## Mid-work Decisions

- `d1` (approved) — t1 absorbed t5's first line item: the three empty-stderr
  assertion updates were made in t1's commit because t1's hint wiring broke
  them immediately; t5 verified rather than re-made them.
- `d2` (approved) — t1 fixed an out-of-plan latent bug:
  `.claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh`'s
  `--write` path merged stderr into the JSON it parses; the new hint line
  would corrupt it. Now captures stderr separately.
- `d3` (approved) — t3 exceeded the docs sweep: `learn.py`'s MOVES had no
  `deviate` or `summary` entries at all (`devague explain deviate` failed
  with `unknown move`), so both were added with verbatim CLI syntax.
- `r1` (resolved) — multi-mode verbs: only a successful *filing* run of
  `deviate`/`evidence`/`delta` is leg-ending; `--list` and
  `--confirm`/`--reject` fall through to the within-leg `devague status`
  hint. Frame park `v1` resolved the same way.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|------------------------|-----------------|
| `t1` (`d1`) | the hint emission t1 ships makes the three assertions fail at t1 time; deferring the updates to t5 would leave wave-1 merges red, violating the TDD gate | `acceptable` |
| `t1` (`d2`) | latent pre-existing bug exposed by the feature itself; without the fix split-plan --write breaks on any hinting devague | `acceptable` |
| `t3` (`d3`) | acceptance criterion 2 requires devague explain to cover the override for the leg-ending verbs including deviate and summary; pre-existing coverage was absent, not merely stale | `acceptable` |

## Evidence

- tests: `uv run pytest -n auto -q` — `1629 passed` at `052af63` (after every
  wave's merge; also green after each individual merge: 1522 baseline → 1578
  (t1+t4) → 1622 (t2) → 1624 (t3) → 1629 (t5))
- behavioral: `uv run pytest -m behavioral -q` — `1 passed, 1628 deselected`
- lint: `black` / `isort --profile black` / `flake8 --config=.flake8` — clean
  on all touched Python; `markdownlint-cli2` — 0 errors on every touched
  markdown file
- commits: `ddfcfcd..052af63` (branch `feat/next-leg-hints`, five task
  branches merged `--no-ff` under `agent/next-leg-hints/*`)
- evidence ledger: `o1`-`o3` approved obligations; `e1`-`e4` approved
  execution-strength evidence (all pass, run-commit `052af63`); `b1`-`b3`
  approved behavioral deltas; projected into `docs/current-spec.md` via
  `devague today`

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| `c6` — the hint is overrideable: disable entirely or replace the text; defaults teach the eight-leg flow | `execution` | `e3`: `tests/test_hint_config.py` override + precedence tests (run 2026-09-01, commit `052af63`) |
| `c11` — after any command succeeds, one stderr hint names the next move or hand-off | `execution` | `e1`: the behavioral hint-following walk; `e2`: the every-verb exactly-once walk (run 2026-09-01, commit `052af63`) |
| `c13` — every verb except status hints; 0 of the pinned stdout/json tests changed; hints-off stderr is byte-identical | `execution` | `e4`: byte-identical strip-hint comparisons (run 2026-09-01, commit `052af63`) |

Lapse ledger evidence:

| Lapse | Code | What |
|-------|------|------|
| `l1` (approved) | `assumption-for-measurement` | t3 wrote the literal `next:` prefix into learn.py MOVES text assuming stdout rendering would not collide with the hint-free-stdout contract, instead of checking how `devague learn` renders MOVES; caught by the `tests/test_cli_hints.py` end-to-end failure, then reworded and re-verified by grep plus the full suite |

## Remaining Work / Follow-up

- guildmaster re-broadcast — the eight reconciled SKILL.md files (t4) are
  upstream here; guildmaster pulls and re-broadcasts them to the mesh on its
  own cycle. No action in this repo.
- t5's behavioral walk parses only the `suggest_move` text shapes a minimal
  frame emits; if `suggest_move` grows new blocker shapes the walk's parser
  needs extending (flagged by the t5 agent; by design, not an oversight).
