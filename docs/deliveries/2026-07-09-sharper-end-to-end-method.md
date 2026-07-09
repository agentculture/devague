# Delivery Summary — devague ships a sharper end-to-end method

plan: `devague-ships-a-sharper-end-to-end-method-a-guided` · run: `complete` · date: `2026-07-09`
baseline: `devague plan (devague-ships-a-sharper-end-to-end-method-a-guided)`

## Intent

This run set out to deliver the **sharper end-to-end method** for devague
(issue [#53](https://github.com/agentculture/devague/issues/53)): a guided
scope-exploration stage before the announcement frame, per-item verbatim
instructions on every claim and task, sharper spec/plan/frame exports, a
tightened structural convergence gate, and a guided plan-to-fanout leg that
carries those instructions to the workforce. It executed the converged plan
`devague-ships-a-sharper-end-to-end-method-a-guided` — 14 tasks over 5
file-disjoint waves — read back read-only from `devague plan waves --json`.
This summary is itself the first real use of the `summarize-delivery` skill it
reports against being available (that skill shipped in a later run).

## Planned Work

Quoted verbatim from `devague plan waves --json` (task id and summary, keyed by
id). The plan's waves are `[t1, t2]` · `[t3, t4, t5, t6, t7, t8, t12]` ·
`[t9, t10, t11]` · `[t13]` · `[t14]`.

- `t1` — Frame schema: scope entries + per-item instruction fields (frame.py, store.py)
- `t2` — Plan schema: per-task instruction field (plan.py, plan_store.py)
- `t3` — New CLI move: devague scope (cli/_commands/scope.py + registration)
- `t4` — Instruction flags on frame moves: capture/interrogate --instruction (capture.py, interrogate.py)
- `t5` — Instruction flags on plan moves: plan task --instruction + `instruct <tN>` (cli/_commands/plan.py)
- `t6` — Sharper frame renderers: instruction blocks + scope provenance (render/spec_md.py, render/frame_md.py)
- `t7` — Frame gate tightening: deterministic structural sharpness checks (convergence.py)
- `t8` — Plan gate tightening: instruction warnings (plan_convergence.py)
- `t9` — Sharper plan renderer + enriched waves payload (render/plan_md.py, waves output)
- `t10` — Teaching surface: learn/explain/status know the scope stage (learn.py, explain.py, cli/_status.py)
- `t11` — Operator skills teach the new surface (/think and /spec-to-plan SKILL.md)
- `t12` — Docs: spec-contract, llm-guidance, skills.md cover scope entity + instruction fields
- `t13` — assign-to-workforce consumes the enriched waves payload as the subagent brief
- `t14` — Dogfooded end-to-end run + boundary audit

## Actual Delivery

Every one of the 14 plan tasks is accounted for. All 14 landed in a single
implementation increment — commit `92c60ca` (release 0.16.0, PR
[#58](https://github.com/agentculture/devague/pull/58)) — verified against the
live CLI and the present source/test files, not the commit message. Status
breakdown: **14 delivered, 0 partial, 0 dropped, 0 blocked.**

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | Frame schema v2: `ScopeEntry` state + per-item instruction fields on claims/honesty conditions; `frame.py` `SCHEMA_VERSION = 2` (fail-closed, empty defaults for v1 files). |
| `t2` | delivered | Plan schema v2: `Task.instruction`; `plan.py` `PLAN_SCHEMA_VERSION = 2`; round-trips verbatim through save/load. |
| `t3` | delivered | `devague scope` CLI move present live (`surface` arg, `--finding`, `--seeds <claim-id>` with unknown-id refusal, `--list`, `--json`). |
| `t4` | delivered | `capture --instruction` and `interrogate --instruction` present live; instruction stored verbatim; changing it re-flips a confirmed item to `proposed`. |
| `t5` | delivered | `plan task --instruction` flag and the new `plan instruct <tN>` verb both present live in the plan subcommand group. |
| `t6` | delivered | Sharper frame/spec renderers: `render/spec_md.py` + `render/frame_md.py` render instruction blocks + a scope-provenance section (golden-file tested). |
| `t7` | delivered | Frame gate tightening in `convergence.py`: deterministic structural sharpness warnings (soft rollout, warnings-only). |
| `t8` | delivered | Plan gate tightening in `plan_convergence.py`: instruction-less-confirmed-task warnings. |
| `t9` | delivered | Sharper plan renderer + enriched `waves --json`: top-level `tasks` object carrying `{summary, instruction, acceptance_criteria, covers}` per id (confirmed present in the live payload). |
| `t10` | delivered | `devague learn` presents the scope stage as optional-but-recommended; `explain scope` and `explain question` both work (exit 0). See Drift — the summary also named `cli/_status.py`, which was not made scope-aware; the binding acceptance criteria (learn + explain only) are met. |
| `t11` | delivered | `.claude/skills/think/SKILL.md` and `.claude/skills/spec-to-plan/SKILL.md` document the scope stage, `--instruction` flags, and the enriched waves payload. |
| `t12` | delivered | `docs/spec-contract.md`, `docs/llm-guidance.md`, `docs/skills.md` all cover the scope entity + instruction fields + schema bumps. |
| `t13` | delivered | `.claude/skills/assign-to-workforce/SKILL.md` quotes the task instruction + acceptance criteria verbatim from `waves --json`; the operator-paraphrase step is gone. |
| `t14` | delivered | Dogfooded `scope → frame → spec → plan → fanout` e2e test (`tests/test_e2e_sharper_method.py`) + boundary audit (`tests/test_boundary_audit.py`, no LLM imports / no process spawning in the package). |

## Mid-work Decisions

Constraints and choices surfaced during execution that were not spelled out in
the plan (drawn from the run's commits, the CHANGELOG, and this verification).

- The plan was executed as a **devague-orchestrated workforce fan-out** (5 waves,
  one agent per task, TDD-gated merges) — the dogfooded application of
  `/assign-to-workforce` on the plan itself.
- The structural sharpness gate (`t7`/`t8`) shipped as **warnings-only (soft
  rollout)** rather than a hard blocker, so existing frames/plans still converge
  while the new checks bed in.
- Schema evolution was handled **fail-closed**: both `SCHEMA_VERSION` and
  `PLAN_SCHEMA_VERSION` bumped `1 → 2`; v1 files load with empty defaults, newer
  versions refuse to load.
- A post-merge `refactor(interrogate)` extracted helpers to clear a SonarCloud
  cognitive-complexity finding (S3776) inside PR `#58` — a quality fix made
  during the run, not a planned task.

## Drift From Plan

Exhaustive relative to the plan. Tasks `t1`–`t9`, `t12`, and `t14` landed exactly
per their acceptance criteria and are not drift entries. The entries below are
the only divergences.

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| release cadence (whole plan) | The single 14-task plan shipped across **three** versions: `0.14.1` (PR `#53`, `67a3eca`) exported the spec+plan artifacts and state only — no CLI; `0.15.0` (PR `#54`, `51669f7`) carried the method into the operator skills ahead of the CLI; `0.16.0` (PR `#58`, `92c60ca`) implemented all of `t1`–`t14`. The plan reads as a single increment and did not prescribe a version cadence. Every task landed; each CHANGELOG entry scopes its version honestly. `0.14.1` is the plan's own creation (the baseline), not execution. | acceptable |
| `t11` / `t13` (skill-teaching) | The operator-skill method text partly shipped early in `0.15.0` (`/scope` added; think / spec-to-plan / assign-to-workforce SKILL.md updated) **before** the `devague scope` / `--instruction` CLI surface existed — a transient "skills describe a CLI that does not exist yet" state, explicitly flagged in the `0.15.0` CLAUDE.md status. Both tasks were finalized against the shipped CLI in `0.16.0`. | acceptable |
| `t10` (teaching surface) | The task **summary** names `cli/_status.py` as a file that would "know the scope stage," but `cli/_status.py` has **zero** scope references and the status next-move helper was not made scope-aware. The task's binding **acceptance criteria** require only that `learn` present the scope stage and that `explain scope` / `explain question` work — both are met. The `_status.py` mention was descriptive, not contractual; leaving an optional pre-frame leg out of the next-move helper is defensible. | acceptable |

## Evidence

Read-only checks run to substantiate the claims below. Every pointer is
resolvable: a commit that exists, a file present in the tree, a merged PR, or a
test node that ran.

- tests: `uv run pytest -n auto -q` — **418 passed** (2.12s).
- tests (sharper-method subset): `tests/test_cli_scope.py tests/test_cli_instructions.py tests/test_plan_cli_instructions.py tests/test_convergence_sharper.py tests/test_plan_convergence_sharper.py tests/test_render_sharper.py tests/test_plan_render_sharper.py tests/test_frame_schema_v2.py tests/test_plan_store.py tests/test_teaching_scope.py tests/test_e2e_sharper_method.py tests/test_boundary_audit.py` — **135 passed**.
- live CLI: `devague scope --help`, `devague capture --help`, `devague interrogate --help`, `devague plan task --help`, `devague plan --help` (shows the `instruct` verb), `devague explain scope`, `devague explain question` — all present / exit 0.
- enriched waves: `devague plan waves --plan devague-ships-a-sharper-end-to-end-method-a-guided --json` — top-level `tasks` object with per-id `{summary, instruction, acceptance_criteria, covers}` confirmed.
- schema: `devague/frame.py` `SCHEMA_VERSION = 2` (line 15); `devague/plan.py` `PLAN_SCHEMA_VERSION = 2` (line 30).
- commits: `67a3eca` (0.14.1, spec+plan artifacts) · `51669f7` (0.15.0, skills carry) · `92c60ca` (0.16.0, `t1`–`t14` implementation).
- PRs: `#53` (MERGED, merge commit `67a3eca`) · `#54` (MERGED, `51669f7`) · `#58` (MERGED, `92c60ca`).
- CHANGELOG: `0.16.0` attributes all of `t1`–`t14` to the workforce fan-out; `0.15.0` and `0.14.1` scope their partial/preparatory releases honestly.

## Delivery Claims

Each claim carries a confidence level and at least one resolvable evidence
pointer. Nothing is asserted as done without evidence.

| Claim | Confidence | Evidence |
|-------|------------|----------|
| The `devague scope` CLI move ships (surface/finding/`--seeds`/`--list`/`--json`) | high | file `devague/cli/_commands/scope.py` · test `tests/test_cli_scope.py` · live `devague scope --help` |
| Per-item instructions ship on frame moves (`capture`/`interrogate --instruction`) | high | files `devague/cli/_commands/capture.py`, `interrogate.py` · test `tests/test_cli_instructions.py` |
| Per-item instructions ship on plan moves (`plan task --instruction` + `plan instruct <tN>`) | high | file `devague/cli/_commands/plan.py` · test `tests/test_plan_cli_instructions.py` · live `devague plan --help` |
| Frame + plan schemas bumped to v2, fail-closed | high | `devague/frame.py:15` · `devague/plan.py:30` · test `tests/test_frame_schema_v2.py`, `tests/test_plan_store.py` |
| Sharper exports render instruction blocks + scope provenance | high | files `devague/render/spec_md.py`, `render/frame_md.py`, `render/plan_md.py` · goldens `tests/goldens/sharper_frame.md`, `sharper_spec.md`, `sharper_plan.md` · test `tests/test_render_sharper.py`, `tests/test_plan_render_sharper.py` |
| Structural sharpness gate lands as warnings-only | high | files `devague/convergence.py`, `plan_convergence.py` · test `tests/test_convergence_sharper.py`, `tests/test_plan_convergence_sharper.py` |
| Enriched `waves --json` carries a per-task subagent-brief payload | high | live `devague plan waves --json` (`tasks` object) · test `tests/test_plan_render_sharper.py` |
| Teaching surface knows the scope stage (`learn`, `explain`) | high | file `devague/cli/_commands/learn.py` · live `devague explain scope` / `devague explain question` (exit 0) · test `tests/test_teaching_scope.py` |
| The status next-move helper was made scope-aware | unverified | `cli/_status.py` has no scope reference — not claimed done (see Drift `t10`; not a binding acceptance criterion) |
| Operator skills + docs teach the shipped surface | high | files `.claude/skills/think/SKILL.md`, `spec-to-plan/SKILL.md`, `assign-to-workforce/SKILL.md`, `docs/spec-contract.md`, `docs/llm-guidance.md`, `docs/skills.md` |
| Dogfooded e2e + boundary audit committed as tests | high | files `tests/test_e2e_sharper_method.py`, `tests/test_boundary_audit.py` (both in the 418-pass run) |
| The full `t1`–`t14` plan shipped (all 14 tasks) | high | commit `92c60ca` · PR `#58` (MERGED) · CHANGELOG `0.16.0` · per-task verification above |

## Remaining Work / Follow-up

- Status next-move helper (`cli/_status.py`) scope-awareness — the `t10` summary
  named it but the acceptance criteria did not, and it was not implemented.
  Decide whether the optional pre-frame scope leg should surface in `devague
  status` output; if yes, it is unstarted follow-up. Owner: devague maintainer.
- No blocked, dropped, or partial tasks from this run carry over — all 14 plan
  tasks were delivered, so there is no incomplete plan work to re-run.
- Method maturity follow-up (from the plan's own framing, not this run): the
  structural sharpness gate ships warnings-only; hardening it into a blocking
  gate is a deliberate future step once the soft rollout has bedded in.
