# Build Plan — execution seam and deviate

slug: `execution-seam-and-deviate` · status: `exported` · from frame: `execution-seam-and-deviate`

> devague closes the execution seam: a deliverables view answers what we have in the end at the go or no-go, the split plan renders the table humans actually approve, dependency edges can be removed without task recreation, and human-approved deviations become first-class records that connect the plan to the delivery summary

## Tasks

### t1 — plan-engine escape hatches and demotion visibility: `depend --remove`, new `amend` move, stdout flip echo

- instruction: OWNS: devague/plan.py, devague/cli/_commands/plan.py, tests/test_plan_escape_hatches.py (new). Add Plan.remove_dep and an amend transition (summary edit; acceptance-criteria replace/remove by index). CLI: `depend <tN> --on <tM> --remove` cuts one edge; new `amend <tN> [--summary "<text>"] [--accept-replace <n> "<text>"] [--accept-remove <n>]`. Any demoting change (instruct, amend, depend remove) on a confirmed task flips it to proposed AND appends the flip to the stdout result line, e.g. `t1: instruction set (confirmed -> proposed; re-confirm)`; keep the stderr note and the flipped field in `--json`. TDD: write the stdout-only capture test first.
- covers: c5, h5, c24, h15, c25, h16
- acceptance:
  - depend remove cuts exactly the named edge; the task keeps summary, acceptance criteria, covers, and instruction unchanged (round-trip test)
  - amend edits the summary and replaces or removes acceptance criteria by index without touching deps, covers, or instruction
  - each demoting move (`instruct`, `amend`, `depend --remove`) on a confirmed task flips it to proposed and names the flip in the stdout result line, asserted by a test that captures stdout alone
  - converge stops reporting a removed edge; `--json` payloads carry the flipped field

### t2 — read-only `devague plan deliverables` view with `--json` and not-converged banner

- instruction: OWNS: devague/render/deliverables_md.py (new), devague/cli/_commands/plan.py (registration only), devague/plan.py (terminal-task helper), tests/test_plan_deliverables.py (new). Terminal tasks = active tasks no other active task depends on. Render from the live source frame: confirmed announcement / after_state / success_signal verbatim; terminal tasks with acceptance criteria; surviving frame parked vagueness plus non-blocking plan risks. Banner line when the plan has not converged; `--json` mirrors with a converged flag. Reuse the _md_safety helpers.
- depends on: t1
- covers: c2, h2
- acceptance:
  - on a converged plan, prints the confirmed announcement, after_state, and success_signal claims verbatim, terminal tasks with their acceptance criteria, and surviving parked items
  - on an unconverged plan it renders with an explicit not-converged banner and converged false in `--json` — it never refuses
  - two consecutive renders leave .devague/ byte-identical (read-only proof)

### t3 — delivery store and the `devague deviate` move

- instruction: OWNS: devague/delivery.py (new), devague/delivery_store.py (new), devague/cli/_commands/deviate.py (new), devague/cli/__init__.py (registration), tests/test_deviate.py (new). Store mirrors plan_store incl. the 0.17.0 version-stamping fix. Record `dN`: plan item ref, reason, affects (repeatable), origin, status proposed/approved/rejected, optional classification acceptable/risky/needs-follow-up (feeds the drift entry contract). CLI: `devague deviate "<what>" --task <tN> --reason "<text>" [--affects <ref> ...] [--classification <kind>] [--origin llm]`; `--confirm <dN>` / `--reject <dN>` are user-only; `--list [--json]` reads back.
- covers: c7, h7, c12, h10
- acceptance:
  - a deviate record persists under `.devague/deliveries/<plan-slug>.json` with its own schema_version, fail-closed load, and upgrade-on-write
  - llm-origin deviations land proposed; only user confirm marks them approved; user-origin records auto-approve; a record without a reason is refused with a hint
  - the plan JSON is byte-identical before and after every deviate operation (test-asserted)

### t4 — render-only `devague summary` verb with `--pr` PR-body mode

- instruction: OWNS: devague/render/summary_md.py (new), devague/cli/_commands/summary.py (new), devague/cli/__init__.py (registration), tests/test_summary.py (new). Eight-section skeleton from state only: Intent quotes the frame announcement and after_state; Planned Work lists every task id and summary verbatim; Actual Delivery emits one row per task with `<fill: status>` and `<fill: what landed>` placeholders (backtick-safe); Mid-work Decisions and Drift From Plan pre-seed from approved deviation records by id; Evidence, Delivery Claims, Remaining Work stay placeholders; run status renders as the `<complete | partial | failed>` placeholder. `--pr` renders title, announcement, wave and task map, approved deviations, and a pointer to the docs/deliveries artifact. Reuse _md_safety.
- depends on: t3
- covers: c27, h17
- acceptance:
  - renders all eight sections: Intent and Planned Work pre-filled verbatim from frame and plan; Actual Delivery one row per task with explicit fill placeholders; drift and mid-work sections quote approved deviation ids
  - no placeholder ever renders as a completed claim; the run status stays a placeholder; two renders are byte-identical and state is untouched
  - `--pr` emits the condensed PR-body skeleton, asserted by a stdout-only test; output is markdownlint-safe

### t5 — split-plan renders the four-column table with wave-listing markers

- instruction: OWNS: .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh, tests/test_assign_to_workforce_script.py (new). Reshape the per-task table to exactly Wave, Task, Model, Task summary; model default sonnet (presentation only — the CLI stays model-agnostic per issue 20); truncate summaries past 72 chars with an ellipsis. Move the has-instruction marker and acceptance-criteria count into the wave-batch listing lines. Keep the go or no-go prompt and the fan-out steps.
- covers: c4, h4
- acceptance:
  - split-plan prints exactly one per-task table with header Wave, Task, Model, Task summary, rows ordered by wave then task id
  - the summary cell is the real task summary from the waves payload, truncated with an ellipsis when long — never a placeholder; the model cell defaults to sonnet per row
  - the wave listing shows has-instruction and acceptance-count markers; the go or no-go prompt stays; a pytest drives the script end to end against a fixture plan

### t6 — split-plan End state section quoting `plan deliverables`

- instruction: OWNS: .claude/skills/assign-to-workforce/scripts/assign-to-workforce.sh (End state addition), .claude/skills/assign-to-workforce/SKILL.md. After the table, print an End state section produced by running `devague plan deliverables` and quoting its output verbatim — never composed freehand. Degrade gracefully on older devague versions (portable mesh script). Extend the t5 script test.
- depends on: t2, t5
- covers: c3, h3
- acceptance:
  - split-plan output ends with an End state section that is the verbatim output of `devague plan deliverables`
  - with an older devague lacking the verb, the section degrades to a one-line hint naming the minimum version instead of failing
  - SKILL.md tells the operator to present the deliverables view at the go or no-go

### t7 — new sixth origin skill `/deviate`

- instruction: OWNS: .claude/skills/deviate/SKILL.md (new), docs/skill-sources.md. Model the doc on scope and summarize-delivery at their birth: method-first, `type: command` frontmatter (the culture-backend gotcha), origin devague, guildmaster re-broadcasts. Method: when execution must diverge from the confirmed plan, STOP the run; present what, why, and what it affects (tasks, coverage targets, acceptance criteria); get explicit human approval; record via `devague deviate` (llm origin lands proposed, the user confirms); adjust the affected task briefs; resume. Deviations are never silently folded into drift after the fact.
- depends on: t3
- covers: c8, h8
- acceptance:
  - the skill file exists with type command frontmatter and the stop, approve, record, adjust, resume method
  - hard rules forbid recording an unapproved deviation and continuing past a refused approval
  - docs/skill-sources.md registers deviate as the sixth origin skill; markdownlint passes

### t8 — summarize-delivery consumes deviation records and the summary skeleton

- instruction: OWNS: .claude/skills/summarize-delivery/SKILL.md. Method step 1 becomes: start from the `devague summary` skeleton, falling back to hand-assembly from `plan show` / `plan waves --json` when the verb or store is absent — and say so in the baseline line. Drift and mid-work sections reference approved deviation records by `dN` id. Hard rules unchanged; the no-overclaim contract stays intact.
- depends on: t3, t4
- covers: c9, h9
- acceptance:
  - the baseline step starts from the `devague summary` skeleton and degrades loudly to hand-assembly when the verb or store is absent
  - Drift From Plan and Mid-work Decisions quote approved deviation record ids when a delivery store exists
  - the read-only moves table lists `devague summary` and `devague deviate --list`; markdownlint passes

### t9 — culture.yaml backend reverts to claude with live agex verification

- instruction: OWNS: culture.yaml. One-line change: backend claude-code becomes claude (the mesh standard). devex 0.30.0 maps claude onto claude-code (agex-cli issue 46, closed), so the cicd lane keeps working. Verification is live: the release PR opened via `agex pr open` IS the test — record the result in the PR body. Leave .claude/skills/cicd/scripts/workflow.sh alone: its claude-code default is agex-internal vocabulary.
- covers: c6, h6
- acceptance:
  - culture.yaml declares backend claude; no other file changes in this task
  - `agex pr open` succeeds live from this repo before the release PR merges, recorded in the PR body

### t10 — close issues 62 and 67 with cited evidence

- instruction: No repo files. Use gh issue comment + close (or the communicate skill). Sign as - devague (Claude). The 67 comment should paste the actual stdout/stderr split from the repro so the already-fixed claim is checkable.
- covers: c17, h13
- acceptance:
  - issue 67 is closed with the 0.17.2 repro transcript (stderr note plus flipped true in `--json`, shipped 0.16.0 commit 92c60ca) and a pointer to the stdout-echo hardening in this release
  - issue 62 is closed citing 0.17.0 (#63) and docs/deliveries/2026-07-09-sharper-end-to-end-method.md; both comments signed per convention

### t11 — release closure: version bump, changelog, docs, coverage and boundary audit

- instruction: OWNS: pyproject.toml, CHANGELOG.md, CLAUDE.md, README.md, docs/skills.md. Bump minor via /version-bump; the CHANGELOG entry names: deliverables view, four-column split plan plus End state, depend remove plus amend plus stdout flip echo, deviate move plus skill plus delivery store, summary verb plus `--pr`, culture.yaml revert, and the two evidence-based closures. Docs name the six-leg flow scope, think, spec-to-plan, assign-to-workforce, deviate, summarize-delivery.
- depends on: t1, t2, t3, t4, t5, t6, t7, t8, t9, t10
- covers: c1, h1, c15, h11, c16, h12, c18, h14
- acceptance:
  - version bumped to 0.18.0 with a CHANGELOG entry naming every leg of the release
  - CLAUDE.md and README name the six-leg flow and the new verbs; the audience (operators driving the CLI, humans at the go or no-go and final-PR gates) is named
  - `uv run pytest -n auto` is green with coverage at or above 95 percent
  - the boundary audit finds no subprocess, network, or LLM call in the deliverables, deviate, or summary code paths

## Risks

- [unknown_nonblocking] the live agex pr verification can only run at PR-open time outside any task worktree — the release PR itself is the test vehicle (task t9)
- [unknown_nonblocking] the v1 deviate record shape beyond the specced fields (classification, timestamps) is fixed by instruction rather than spec — dogfooding may revise it in a follow-up (task t3)
