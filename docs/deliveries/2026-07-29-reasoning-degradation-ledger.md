# Delivery Summary — reasoning-degradation ledger

plan: `reasoning-degradation-ledger` · run: `complete` · date: `2026-07-29`
baseline: `devague summary skeleton`

## Intent

Ship issue [#97](https://github.com/agentculture/devague/issues/97) — a
deterministic move that records degradations of the *reasoning process*
(moments where an assumption was silently substituted for a check) as
first-class, append-only ledger entries filed when they happen. The
reasoning-side twin of `deviate`, filed friction-free and never gating
convergence. Six tasks across three dependency waves, fanned out by
`/assign-to-workforce` after the `/scope` → `/think` → `/challenge` →
`/spec-to-plan` legs converged and exported the spec and plan.

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — Lapse domain model on Frame: LapseRecord, lapse codes, schema v5
- `t2` — CLI verb lapse: file, list, adjudicate
- `t3` — Render the ledger: show and summary consume, spec stays untouched
- `t4` — Gate inertness pinned by tests
- `t5` — Skills sweep: producer, consumer, and the subagent boundary
- `t6` — Docs, contract, changelog, version

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `LapseRecord` + `LAPSE_CODES` + `LAPSE_STATUSES` and `Frame.lapses` / `add_lapse` / `find_lapse` / `set_lapse_status` in `devague/frame.py`; `SCHEMA_VERSION` 4→5; 31 new tests in `tests/test_frame_lapse.py`. Merged `4a47f74` |
| `t2` | delivered | `devague/cli/_commands/lapse.py` (file / `--list` / `--confirm` / `--reject`), registered in `cli/__init__.py`, `MOVES` row added in `learn.py`; 34 new tests in `tests/test_cli_lapse.py`. Merged `2bc7620` |
| `t3` | delivered | `_lapse_lines` in `render/frame_md.py`, `_lapse_evidence_lines` + `lapse_evidence` JSON in `render/summary_md.py`; `spec_md.py` unchanged by design, pinned by a byte-identity regression test; 17 new tests. Merged `0f67775` |
| `t4` | delivered | 20 gate-inertness tests across `tests/test_convergence.py` and `tests/test_plan_convergence.py`; zero production code, as the task specified. Merged `5259c33` |
| `t5` | delivered | `challenge` routing row + hard rule, `summarize-delivery` moves table + Delivery Claims step, `assign-to-workforce` worktree prohibition generalized, `docs/skills.md` enumerations swept. Merged `e95b7af` |
| `t6` | delivered | `docs/spec-contract.md` `LapseRecord` entity + Moves rows + schema v5, `README.md`, `CLAUDE.md`, `CHANGELOG.md`, version 0.21.0→0.22.0. Merged `b92f982` |

All six tasks delivered; none partial, dropped, or blocked.

## Mid-work Decisions

- `d1` — the `split-plan --write` path escapes verbatim task text before
  writing markdown — the committed gate-2 artifact failed the repo's own
  markdownlint: `cli/__init__.py` in `t2`'s instruction rendered as
  strong-emphasis (MD050 ×2, MD037 ×1). No plan task covers the split-plan
  script, and CI does not lint markdown, so nothing would have caught it
  before review. Approved by the gate-2 owner mid-run, recorded before the fix
  landed.
- The `/challenge` pass, run before `/spec-to-plan`, itself broke the spec
  export: a scope surface carrying its own code span was blind-wrapped in a
  second one (MD038). Fixed in `spec_md.py` / `frame_md.py` with three new
  tests, and folded into the baseline commit rather than a plan task — the
  breakage predated the plan, so no task could have covered it. No deviation
  record covers this; captured here directly.
- Three coverage targets (`h8`, `c13`, `h11`) were deliberately deferred at
  plan time, not dropped mid-run: all three measure the shipped verb in a real
  embodiment dogfood cycle and cannot be tested inside this PR. They render in
  the plan's `## Deferred targets` section with their reason.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t5` (`d1`) | the committed gate-2 artifact failed the repo's own markdownlint: `cli/__init__.py` in `t2`'s instruction rendered as strong-emphasis (MD050 ×2, MD037 ×1). No plan task covers the split-plan script, and CI does not lint markdown, so nothing would have caught it before review. Approved by the user mid-run. | acceptable |

No other task diverged from its confirmed contract. Two additions beyond the
letter of the acceptance criteria are noted rather than classified as drift,
because each stays inside its task's file scope and criteria: `t3` added a
`lapse_evidence` key to `summary_data()`'s JSON for parity with every other
section, and `t1` moved a second `SCHEMA_VERSION` pin in `tests/test_frame.py`
that the plan's instruction did not know existed.

## Evidence

- tests: full suite `uv run pytest -n auto -q` — **1071 passed**, 0 failed
  (970 before the run; +101)
- tests: `tests/test_frame_lapse.py`, `tests/test_cli_lapse.py` — 65 passed
- tests: `tests/test_convergence.py`, `tests/test_plan_convergence.py` — 67 passed
- lint: `uv run flake8 --config=.flake8 devague/ tests/` — clean
- lint: `uv run black --check devague/ tests/` — 101 files unchanged
- lint: `markdownlint-cli2 "README.md" "CHANGELOG.md" "CLAUDE.md" "docs/**/*.md"`
  — 0 errors
- version: `uv run devague --version` — `devague 0.22.0`
- commits: `e5047a4..8856938` (14 commits)
- issues: [#97](https://github.com/agentculture/devague/issues/97) (delivered),
  [#98](https://github.com/agentculture/devague/issues/98),
  [#99](https://github.com/agentculture/devague/issues/99),
  [#100](https://github.com/agentculture/devague/issues/100) (filed during the run)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| `devague lapse` files, lists, and adjudicates lapse records end to end | high | 34 tests in `tests/test_cli_lapse.py` · commit `2bc7620` · exercised for real on this run (`l1`, `l2` filed) |
| lapse codes validate fail-closed at filing but load tolerantly, so a retired code never bricks a frame | high | `tests/test_frame_lapse.py` file→retire→reload regression · commit `4a47f74` |
| the ledger never gates — no convergence blocker, warning, or parked item names a lapse in any status | high | 20 tests in `tests/test_convergence.py` + `tests/test_plan_convergence.py` · commit `5259c33` |
| the exported spec-md is byte-identical before and after filing lapses | high | byte-identity regression test in `tests/test_render_sharper.py` · commit `0f67775` |
| `SCHEMA_VERSION` 5 protects filed lapses from an older binary silently dropping them on save | high | reject-newer store test in `tests/test_frame_lapse.py` · commit `4a47f74` |
| the ledger surfaces as confidence evidence in `devague summary` | high | `_lapse_evidence_lines` · `tests/test_summary.py` · **this artifact's own skeleton rendered `l1`/`l2` as pending** |
| filing costs the operator under a minute (honesty condition `h8`) | unverified | deferred to the embodiment dogfood cycle — not claimed done |
| every shipped code has a reachable producer, not merely a definition (`c13`/`h11`) | unverified | deferred to the embodiment dogfood cycle — no code has been filed against four of the six |

Lapse ledger evidence: `l1` (`provenance-missing`) and `l2`
(`grader-unverified`) are **filed but still proposed** — pending the gate
owner's `devague lapse --confirm`/`--reject`, so neither is yet evidence and
neither caps a claim above. Both are self-reports about *this run's* reasoning:
`l1` records that the `/challenge` pass concluded markdown-safety was handled
after reading only the three CLI renderers, never `assign-to-workforce.sh`;
`l2` records that the per-task TDD merge gate ran pytest and flake8 and was
read as proving "the artifacts are clean" when it never ran markdownlint at
all. `d1` is the consequence both describe.

## Remaining Work / Follow-up

- **Adjudicate `l1` and `l2`** — `devague lapse --confirm l1 l2` (or reject).
  Until then they are pending, not evidence. This is the first real exercise of
  the adjudication path.
- [#98](https://github.com/agentculture/devague/issues/98) — `learn.py`'s
  `MOVES` dict is missing five verbs, so `devague explain deviate|summary|plan`
  all fail. Pre-existing; this run added only the `lapse` row deliberately, to
  keep the fix reviewable on its own (plan risk `r1`).
- [#99](https://github.com/agentculture/devague/issues/99) — the `d1` deviation
  filed as its own issue: `split-plan --write` wrote unescaped markdown because
  `safe_body` never ported `md_safe_text` despite a comment claiming exact
  parity. Fixed here; the issue proposes adding markdownlint to CI and
  addressing the duplicated-helper drift risk.
- [#100](https://github.com/agentculture/devague/issues/100) — `deviate` and
  `summarize-delivery` SKILL.md still draw the six-leg flow, omitting
  `/challenge`. Pre-existing since 0.19.0 and outbound to the whole mesh.
- **Deferred coverage targets `h8`, `c13`, `h11`** — the embodiment dogfood
  cycle. Issue #97 closes with embodiment offering to run it and report real
  entry counts and which codes turned out dead. `h11` commits to *removing* a
  dead code, not documenting it, so this is a real decision waiting on data
  (plan risk `r2`; parked items `v1`, `v2`).
- **Hard question `q4`** — how the spec distinguishes "covered" from
  "reachable" per code — remains open on the frame, non-blocking. Four of the
  six shipped codes have no filing yet, which is precisely the condition
  embodiment#18 warned about.
