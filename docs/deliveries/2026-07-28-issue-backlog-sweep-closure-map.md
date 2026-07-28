# Issue closure map — issue-backlog-sweep (0.21.0)

Verification artifact for the fifteen-issue sweep. Each issue below was checked
against **its own stated acceptance criteria**, not the plan's paraphrase of
them, and — where the issue carried concrete repro steps — by running the
reporter's own sequence against the built CLI in a scratch directory rather
than by reading the tests.

Path rationale: `docs/deliveries/` is where this repo's delivery-side artifacts
live, under the same `<created-date>-<slug>` convention as the plan and spec
exports. The `-closure-map` suffix keeps it distinct from the
`devague summary`-derived delivery summary the `/summarize-delivery` leg writes
to `docs/deliveries/2026-07-28-issue-backlog-sweep.md`, mirroring how the gate-2
split artifact sits beside the plan export as `…-split.md`.

## Suite and lint evidence

| Check | Result |
| --- | --- |
| `bash .claude/skills/run-tests/scripts/test.sh --ci` | **967 passed**, 0 failed |
| Coverage (gate: `fail_under = 95`) | **98.37 %** |
| `markdownlint-cli2 "**/*.md"` | 39 files, **0 errors** |
| `.claude/skills/**/*.md` (force-linted; the bulk glob ignores them) | 19 files, **0 errors** |
| Real-corpus export lint (`issue-backlog-sweep` frame + plan) | **0 errors** |

## Closure map

| # | Issue | Verdict | Regression test(s) |
| --- | --- | --- | --- |
| 48 | Hard questions can never be resolved; `converge` wedged | closed | `tests/test_e2e_resolve.py::test_e2e_issue48_52_hard_question_block_resolve_converge_lifecycle` |
| 49 | `export` lossy: resolved questions read as open; `unknown_nonblocking` parks dropped | closed | `tests/test_render.py::test_spec_md_resolved_hard_question_renders_with_resolved_marker`, `::test_spec_md_resolved_hard_question_renders_its_decision_text`, `::test_spec_md_open_nonblocking_park_renders_labeled_by_kind` |
| 52 | Same deadlock as #48, with a five-point AC list | closed | `tests/test_e2e_resolve.py::test_e2e_issue48_52_hard_question_block_resolve_converge_lifecycle`, `::test_e2e_issue52_rejected_claim_unresolved_blocking_question_no_longer_blocks` |
| 79 | `/scope` should use subagents for exploration | closed (method-only) | `tests/test_teaching_surface_sweep.py::test_learn_documents_scope_fan_out_threshold` |
| 82 | `split-plan`: real task map + durable gate-2 artifact | closed | `tests/test_assign_to_workforce_script.py::test_split_plan_write_creates_durable_artifact_with_real_content`, `::test_split_plan_write_rerun_overwrites_in_place_and_preserves_edit`, `::test_split_plan_write_artifact_passes_markdownlint` |
| 83 | Rejecting a claim orphans attachments; rejected content reaches the spec | closed | `tests/test_cli_converge_export.py::test_export_never_leaks_a_rejected_claims_risk_text_issue_83`, `tests/test_convergence.py::test_rejected_assumption_does_not_warn` |
| 84 | No `amend` move; correcting a claim costs its id and breaks provenance | closed | `tests/test_cli_moves.py::test_amend_one_move_fixes_a_number_and_keeps_id_and_attachments`, `tests/test_e2e_resolve.py::test_e2e_issue84_plan_risk_amend_after_task_recreation_still_converges` |
| 85 | Milestone-scoped plans cannot converge | closed (secondary ask deferred, see below) | `tests/test_plan_convergence.py::test_shell_cli_shape_90_covered_12_deferred_converges` |
| 86 | Self-dependency accepted at creation; `plan reject` single-id | closed | `tests/test_cli_plan.py::test_task_dep_self_cycle_errors`, `::test_task_dep_unknown_id_errors`, `::test_depend_self_cycle_errors` |
| 87 | `export` renders claim text unescaped → MD037 / MD050 | closed | `tests/test_md_safety.py` (48 cases), `tests/test_export_markdownlint_integration.py::test_mixed_identifier_export_passes_markdownlint_cli2`, `::test_real_issue_backlog_sweep_frame_exports_lint_clean` |
| 88 | `devague summary` renders rejected tasks as planned work | closed | `tests/test_summary.py::test_mixed_status_plan_scopes_planned_work_and_actual_delivery_to_confirmed`, `::test_actual_delivery_has_one_row_per_confirmed_task_with_fill_placeholders` |
| 90 | `plan cover` refuses targets `plan converge` demands | closed | `tests/test_cli_plan.py::test_status_recommends_cover_and_cover_succeeds_without_reconverge` |
| 91 | Use a smaller tier (sonnet) for scope subagents | closed (method-only) | `tests/test_teaching_surface_sweep.py::test_learn_documents_scope_fan_out_threshold`, `::test_learn_json_scope_stage_includes_fan_out_key` |
| 92 | Exported spec never shows a deviation contested a confirmed claim | closed | `tests/test_contested.py::test_export_show_status_render_contested_marker_end_to_end`, `::test_export_show_status_fail_open_on_corrupt_delivery_store` |
| 93 | `export` drops `unknown_nonblocking` parks | closed | `tests/test_render.py::test_spec_md_open_nonblocking_park_renders_labeled_by_kind`, `tests/test_export_markdownlint_integration.py::test_mixed_identifier_export_lists_both_open_park_kinds` |

## Scope notes on partly-in-scope issues

Three issues bundled asks that were **not** all in this release's scope. Recording
them here so the closures are not read as broader than they are.

- **#82 ask 1** (inline real task content in `split-plan`) shipped in **0.16.0**;
  the downstream symptom in the report was a stale vendored copy of the skill.
  Only asks 2 (owner/model annotations) and 3 (durable artifact) were in scope,
  and both landed. Ask 2 was implemented as the artifact-side annotation table
  the issue offered as its second option — no `plan assign` verb, no plan schema
  change (recorded as decision `c25`).
- **#85 secondary ask** — "warn when a task covers many targets with few
  acceptance criteria" — was **deliberately deferred**, recorded as park `v3` on
  the frame. #85's five formal acceptance criteria are all met; this was the
  paragraph under *Secondary note on coverage semantics*, not one of them.
- **#84's** four ACs plus the `plan risk --amend` follow-up in the comment
  thread all landed. `plan amend` for tasks pre-existed (0.18.0).

## Downstream workarounds — deletability verdict

| Workaround | Location | Verdict |
| --- | --- | --- |
| Plan projection script | `shell-cli` `scripts/render_plan.py` | **Deletable** |
| markdownlint ignores for generated artifacts | `shell-cli` `.markdownlint-cli2.yaml` | **Deletable for its stated cause**; one unrelated pre-existing error remains |
| Hand-edited `.devague/frames/<slug>.json` (`resolved: true`) | `arm101-cli`, `agentfront` (a practice, not a file) | **Deletable** |

### 1. `shell-cli/scripts/render_plan.py` — deletable

The script's own docstring says it should be deleted once devague#85 lands. It
existed because `guarded-local-operations-plane` (19 confirmed / 68 rejected
tasks, 102 targets) could not export: 12 targets were deliberately uncovered.

Verified against that repo's **real** committed frame and plan, copied into a
scratch directory and driven with this branch's CLI:

- `plan converge` reproduced exactly the 12 gaps #85 named, plus blocking risk
  `r13` — which is *itself* the placeholder recording the #85 limitation.
- Applying `plan defer` to the 12 targets, then resolving `r13`, converged the
  plan and **exported it**, with a `## Deferred targets` section naming all 12
  and their reasons.

That is the artifact `render_plan.py` was written to fake. Note the script is in
**`shell-cli`**, not `reachy-mini-cli` — both #85's body and its follow-up
comment are signed `shell-cli (Claude)`.

### 2. `shell-cli` markdownlint ignores — deletable for the cause #87 named

The config ignores `docs/specs/**` and `docs/plans/**` (not `docs/handoff/**`,
which does not exist in that repo), citing devague#87 by number.

Before/after on that repo's real spec, same frame, same rule set:

| Renderer | MD037 | MD033 | Total |
| --- | --- | --- | --- |
| devague 0.20.x (the committed artifact) | 7 | 1 | **8** |
| devague 0.21.0 (this branch) | 0 | 1 | **1** |

Every MD037 error the ignore was created for is gone. The surviving error is
**MD033/no-inline-html**, from a claim instruction containing the literal
placeholder token `<colleague>` — angle brackets are *not* in #87's acceptance
criteria (which name `*`, backtick, `[`, `]`, and a leading `#`), and the error
predates this release. So the ignore is removable once that one token is
backticked in the source claim, or once the follow-up below lands. Recorded as a
follow-up, not fixed here, because it is outside #87's stated bar and touches
the shared escaper every renderer uses.

### 3. Hand-edited frame JSON — deletable

Both #48 and #52 report editing `.devague/frames/<slug>.json` by hand to set
`resolved: true` on a blocking hard question. `devague interrogate <cN>
--resolve <qN> [--decision "<text>"]` now does it as a first-class move,
verified by running the reporters' own sequences; `suggest_move` names that
exact move, the decision text survives a save/load round trip, and a rejected
claim's unresolved blocking question no longer blocks the gate. Separately, the
store now tolerates unknown keys on hard questions, honesty conditions, and
parked vagueness instead of raising `TypeError` from `HardQuestion(**q)` — the
specific hazard #48 flagged about hand-editing.
