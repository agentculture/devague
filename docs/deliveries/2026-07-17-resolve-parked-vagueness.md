# Delivery Summary — resolve parked vagueness

plan: `resolve-parked-vagueness` · run: `partial` · date: `2026-07-17`
baseline: `devague summary skeleton`

## Intent

Ship the close-out for parked vagueness on both engines — `park --resolve`
(frames) and `plan risk --resolve` (plans) — closing issues #45, #55, #57,
and #60, by executing the ten-task converged plan via `/assign-to-workforce`:
nine build tasks fanned out to subagent worktrees across three waves with
TDD-gated merges, plus the release task. The run is `partial` only because
`t10`'s issue-close half is post-merge by definition and PR
[#81](https://github.com/agentculture/devague/pull/81) awaits the human gate.

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — Frame-side model: Vagueness resolution state + schema v3
- `t2` — Plan-side model: PlanRisk resolution state + plan schema v3
- `t3` — Frame gate: skip resolved vagueness, executable hint, parked_items
- `t4` — Plan gate: skip resolved risks, executable hint, parked_items
- `t5` — CLI: park --resolve VID --decision TEXT
- `t6` — CLI: plan risk --resolve RID --decision TEXT
- `t7` — Renderers: resolved items render with resolution; deliverables excludes them
- `t8` — Teaching + contract docs sweep: the close-out loop everywhere park is taught
- `t9` — E2E repro + quality gates: issue 57 lifecycle through the real CLI, both engines
- `t10` — Release + close-out: 0.20.0, CHANGELOG, PR, close the four issues

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `Vagueness.resolved`/`.resolution`, `Frame.resolve_vagueness`, `SCHEMA_VERSION` 3 — commit `367c2fe`, merged `c277e5b` |
| `t2` | delivered | `PlanRisk.resolved`/`.resolution`, `Plan.resolve_risk`, `PLAN_SCHEMA_VERSION` 3 — commit `625097f`, merged `691c545` |
| `t3` | delivered | frame gate + `parked_items` skip resolved; hint names `park --resolve` with the real id — commit `3f354ce`, merged `7ec6fbc` |
| `t4` | delivered | plan gate + `parked_items` skip resolved; hint names `plan risk --resolve` — commit `7f2dc74`, merged `6434e9f`, operator reconcile `1f80c3f` |
| `t5` | delivered | `park --resolve VID --decision TEXT [--claim CN]`, fail-closed refusals; adds `Vagueness.resolution_claim_id` — commit `62085ef`, merged `d1584b4` |
| `t6` | delivered | `plan risk --resolve RID --decision TEXT`, same refusal semantics — commit `f00fe51`, merged `f082f1f` |
| `t7` | delivered | frame_md/spec_md render resolution verbatim (`## Resolved vagueness` in specs); deliverables excludes resolved; new goldens — commit `0ad0c86`, merged `fd91dfc` |
| `t8` | delivered | `learn`, `docs/llm-guidance.md`, think skill, `docs/spec-contract.md` all teach the close-out; two learn tests — commit `c17a339`, merged `46aedb2` |
| `t9` | delivered | `tests/test_e2e_resolve.py`: issue-57 lifecycle e2e on both engines + markdownlint integration; quality gates all green — commit `93c7072`, merged `fb1ddbb` |
| `t10` | partial | 0.20.0 bump + CHANGELOG + PR #81 delivered (commit `abdc5d4`); the issue-close comments are post-merge and pending the human gate — `Closes` keywords in the PR body will auto-close #45/#55/#57/#60 on merge, comments naming the release still to be posted |

## Mid-work Decisions

No `/deviate` records exist for this plan (`devague deviate --list`: "no
deviations recorded yet") — no execution step departed from a confirmed task's
contract. Operator-level decisions inside the plan's latitude, captured
directly:

- `t5` storage seam: the plan required `--claim CN` to link the deciding claim
  but specified no storage; the operator granted a minimal
  `Vagueness.resolution_claim_id` field (additive, dataclass default — no
  extra schema bump) rather than overwriting the owning `claim_id` from park
  time. Validation landed in the model (`Frame.resolve_vagueness`), the same
  seam `add_scope_entry` uses.
- `t4` reconcile (commit `1f80c3f`): the delivered blocking-risk hint emitted a
  literal `RID` placeholder while the frame-side hint interpolated the real
  id; the operator harmonized the plan-side hint to interpolate `rN` before
  advancing the wave.
- `t5`/`t6` answered the frame's open hard question (already-resolved id →
  **refuse with a hint**, not no-op), the fail-closed choice the plan's
  instruction pre-pinned.
- Branch naming: a pre-existing `resolve-parked-vagueness` branch (commit
  `b5c9e7c`, an earlier session) holds a superseded flat-verb spec; this run
  shipped on `park-resolve` instead and left that branch untouched for the
  reviewer to delete.
- `t8` found `devague plan learn` already taught the resolve form (t6's commit
  covered `PLAN_MOVES`), so only the frame-side teaching needed edits.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t10` | the issue-close half is sequenced on the human PR gate (gate 3) — it cannot complete before merge; all pre-merge halves (bump, CHANGELOG, PR) are delivered | needs-follow-up |

No other task drifted: `t1`–`t9` delivered to their acceptance criteria as
confirmed (task-by-task accounting above).

## Evidence

- tests: `uv run pytest -n auto -q` — **689 passed** (baseline at plan start: 616), run after every wave merge and again at release
- coverage: `uv run pytest -n auto -q --cov=devague --cov-report=term` — **98.12%** (gate ≥ 95%)
- lint: `flake8` / `black` / `isort` / `bandit -r devague/` — clean (t9 report + release-commit run); `markdownlint-cli2` on all touched docs — 0 errors
- e2e: `tests/test_e2e_resolve.py::test_e2e_issue57_frame_park_resolve_lifecycle`, `::test_e2e_issue57_frame_export_passes_markdownlint`, `::test_e2e_issue57_plan_risk_resolve_lifecycle` — pass
- boundary: `git diff main...HEAD -- devague/` grep for subprocess/network/LLM usage — empty
- commits: `3e82751..abdc5d4` on branch `park-resolve` (9 task commits + 9 TDD-gated merge commits + 1 operator reconcile + release)
- PRs / issues: PR `#81` (SonarCloud quality gate passed; Qodo: 0 bugs, 0 rule violations, 0 requirement gaps); issues `#45` `#55` `#57` `#60`

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| a decided blocking park resolves through CLI moves alone — issue 57's exact repro converges and exports with zero `.devague` hand-edits | high | test `tests/test_e2e_resolve.py::test_e2e_issue57_frame_park_resolve_lifecycle` |
| the plan-side twin works end to end | high | test `tests/test_e2e_resolve.py::test_e2e_issue57_plan_risk_resolve_lifecycle` |
| resolved items stay on the record and render with their resolution; open-item listings exclude them | high | commit `0ad0c86` · goldens `tests/goldens/resolved_vagueness_{frame,spec}.md` |
| convergence hints now name executable moves on both engines | high | commits `3f354ce`, `7f2dc74`, `1f80c3f` · tests in `tests/test_convergence.py`, `tests/test_plan_convergence.py` |
| v2 artifacts load with defaults; newer artifacts fail closed on older binaries | high | round-trip/fail-closed tests in `tests/test_store.py`, `tests/test_plan_store.py`, `tests/test_frame.py`, `tests/test_plan.py` |
| every teaching surface teaches the close-out | high | commit `c17a339` · tests `tests/test_cli_learn.py` |
| issues #45/#55/#57/#60 are closed against the shipped release | unverified | pending gate 3 — PR `#81` carries the `Closes` keywords; comments naming the release follow the merge, not claimed done |

## Remaining Work / Follow-up

- `t10` second half — after the human merges PR `#81`: post the close-out
  comment on each of #45/#55/#57/#60 naming release 0.20.0 and the move that
  replaces its documented workaround (the `Closes` keywords auto-close them on
  merge). Owner: operator, post-merge.
- ~~Stale branch `resolve-parked-vagueness` (commit `b5c9e7c`, superseded
  flat-verb spec)~~ — done: the human approved deletion 2026-07-17; removed
  locally and on origin.
- Plan risk `r1` (follow_up, still open by design): downstream vendored copies
  of the think skill keep teaching the one-way park until guildmaster's next
  re-broadcast sync.
- Frame park `v1` (unknown_nonblocking, on the record): stale installed
  binaries downstream fail closed on v3 artifacts until upgraded — mitigated
  by the error's own upgrade hint.
