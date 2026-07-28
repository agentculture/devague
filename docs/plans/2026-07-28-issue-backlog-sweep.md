# Build Plan — issue-backlog-sweep

slug: `issue-backlog-sweep` · status: `exported` · from frame: `issue-backlog-sweep`

> devague closes its fifteen-issue backlog: exports become lossless and lint-clean, rejected and contested content stops leaking into artifacts, plans gain live coverage targets with per-target deferral, claims and hard questions gain amend and resolve moves, the delivery summary scopes to confirmed work, gate 2 gains a durable split artifact, and scope exploration fans out to smaller-tier subagents

## Tasks

### t1 — Escaping engine in render/_md_safety.py

- instruction: Add a pure escape function in devague/render/_md_safety.py only — no renderer call sites here (they land in t3/t9/t13). Wrap underscore/dunder identifiers in code spans per the #87 comment preference; escape remaining markdown control characters; skip text already inside code spans; make double application a no-op.
- covers: c32, h25
- acceptance:
  - unit tests in tests/test_md_safety.py cover `_read_file`, `__init__.py`, `*`, `[`, backtick, and leading `#` inputs, plus already-backticked text passing through unchanged and idempotence on double application

### t2 — Schema and load-order hardening in both stores

- instruction: Fix store.py and plan_store.py to check schema_version BEFORE parsing via from_dict (today store.py:136-147 and plan_store.py:54-62 parse first); make HardQuestion/Vagueness loading tolerant of unknown keys like Claim already is (frame.py:315,322); bump frame SCHEMA_VERSION for the new hard-question resolution field and PLAN_SCHEMA_VERSION for defer state.
- acceptance:
  - a frame or plan JSON declaring a newer schema_version fails with the fail-closed IncompatibleSchemaError message, never a raw TypeError, covered by tests for both stores; existing v3 frames and plans load unchanged

### t3 — spec_md renderer sweep: parks, hard questions, dead seeds, escaping

- instruction: devague/render/spec_md.py: render all open park kinds grouped by kind (replace the `_follow_up` filter at 110-118); render hard questions with resolved markers and skip rejected parent claims (104-107); flag scope entries whose seeds cite a rejected claim; apply the t1 escaper at every verbatim site. Flip tests/test_render.py:301-306.
- depends on: t1
- covers: c2, c3, c6, c22, c33, h2, h3, h6, h18, h26
- acceptance:
  - a converged frame with open parks of all four kinds exports a spec listing each park labeled by kind
  - a resolved hard question renders with a resolved marker and a hard question on a rejected claim is absent from the export (the #83 repro shape: capture, interrogate --risk, reject, converge, export)
  - a scope entry seeding a rejected claim renders a visible rejected marker instead of a bare dead id
  - exporting the issue-backlog-sweep frame twice is byte-stable, lints clean under markdownlint-cli2 default config, and frame JSON on disk is byte-identical before and after; `show --json` output unchanged

### t4 — Hard-question resolve move: interrogate --resolve

- instruction: Per decision c36: `devague interrogate <cN> --resolve <qN> [--decision "<text>"]`. Add Frame.resolve_hard_question storing the optional decision text (schema field from t2); make the convergence gate (convergence.py:111-116) skip rejected claims; update suggest_move (206-211) to name the shipped move verbatim.
- depends on: t2
- covers: c4, h4
- acceptance:
  - the block-resolve-converge sequence completes through CLI moves alone, suggest_move output names the shipped move, resolved state and decision text survive a save/load round-trip, and a rejected claim with an unresolved blocking question no longer blocks converge

### t5 — Reject cascade over attachments

- instruction: Rejecting a claim cascades to its honesty conditions and hard questions, echoing what it took (`c21 -> rejected (also rejected: h3, q1)`); `_assumption_warnings` (convergence.py:120-126) skips rejected claims; `devague review` stops listing conditions whose parent claim is rejected.
- depends on: t4
- covers: c5, h5
- acceptance:
  - rejecting a claim with attachments reports exactly what cascaded; post-reject converge emits zero warnings about the rejected claim; review lists zero orphans; regression test asserts the risk text is absent from the exported markdown

### t6 — Claim and scope-entry amend moves

- instruction: New `devague amend <cN> --text/--kind` keeping id, honesty conditions, instruction, and inbound scope seeds; `devague scope --amend <sN> --finding`; amending a confirmed claim flips it to proposed with the echoed flip, matching the interrogate.py:58-68 precedent; origin never changes silently.
- depends on: t5
- covers: c7, h7
- acceptance:
  - amending a confirmed claim keeps its id and attachments and flips it to proposed with an echo; correcting one number costs exactly one move; scope --amend replaces a finding in place

### t7 — scope --seeds accepts question ids

- instruction: Frame.add_scope_entry (frame.py:252-254) accepts `q*` ids resolving against claim-attached hard questions; unknown `q*` still refused with the show hint; exported scope section renders question seeds.
- depends on: t6
- covers: c8, h23
- acceptance:
  - scope --seeds with a valid `q*` id records; an unknown `q*` id is refused with the hint; the seeded question renders in the exported scope-exploration section

### t8 — Live-target validation for cover and --covers

- instruction: Make `_require_target` (cli/_commands/plan.py:145-151) validate against live-frame-derived targets exactly as converge does via `_live` (108-118), persisting the refreshed snapshot on success; decide the regressed-frame fallback (frame park v4) here — either stored-snapshot fallback or refusal with the reconverge hint — and test the chosen behavior.
- covers: c9, h9
- acceptance:
  - the verified #90 repro inverts: after the frame grows a confirmed claim, `plan status` recommends cover for it AND that exact cover succeeds immediately with no intervening converge; a target unknown to both stored and live sets is still refused

### t9 — Per-target deferral: plan defer

- instruction: New `devague plan defer <target-id> --reason "<text>"` persisting deferral state (plan schema bump from t2); `_missing_coverage` (plan_convergence.py:26-32) excludes deferred targets; `plan status` reports deliberately-deferred distinctly; plan_md renders a Deferred targets section naming each with its reason, and applies the t1 escaper at its verbatim sites.
- depends on: t1, t2, t8
- covers: c10, h10, c6
- acceptance:
  - a plan with deferred targets converges and exports; the export names every deferred target with its reason; status distinguishes deferred from uncovered; the shell-cli shape (90 covered, 12 deferred) converges in a test
  - plan-md output passes markdownlint-cli2 with underscore-bearing task text (MD050 regression from the #87 comment)

### t10 — Dependency validation at task creation

- instruction: plan task `--dep` refuses the about-to-be-assigned id (self-cycle) and unknown task ids at creation with actionable hints; `depend <tN> --on <tM>` gets the same checks; flip tests/test_cli_plan.py:87-96 rather than deleting it.
- depends on: t9
- covers: c11, h11
- acceptance:
  - creating a task with `--dep` naming its own id or an unknown id fails with the actionable hint; the flipped test passes; existing valid graphs are unaffected

### t11 — Multi-id transactional plan confirm/reject

- instruction: plan confirm/reject accept N ids applied transactionally (all valid or none), matching the frame-side contract (confirm.py:27-50); argument errors inside the plan group point at `devague plan explain <move>`.
- depends on: t10
- covers: c12, h12
- acceptance:
  - plan reject with three ids where one is invalid applies none and says why; with all valid, applies all in one call; error hints inside the plan group name `plan explain`

### t12 — Plan-risk amend

- instruction: New `plan risk --amend <rN> --text "<corrected>"` editing risk text in place, preserving id, kind, task link, and resolution state — the #84 comment case where a referenced task id rotates.
- depends on: t11
- covers: c7
- acceptance:
  - amending a risk keeps its id, kind, and resolution state while replacing text; amending an unknown rid is refused with a hint

### t13 — Summary scoped to confirmed tasks

- instruction: summary_md.py: Planned Work and Actual Delivery (119-143) plus summary_data (265-271) iterate confirmed tasks only, with a single line counting rejected tasks; apply the t1 escaper at verbatim sites; `dependency_waves` already excludes rejected (plan.py:285) so --pr needs no change — pin that with a test.
- depends on: t1
- covers: c13, h13
- acceptance:
  - a plan with N confirmed and M rejected tasks emits exactly N Actual Delivery rows and N Planned Work entries plus one line counting the M rejected; the --pr wave map stays rejected-free; regression test covers a mixed-status plan

### t14 — Contested-by-deviation derivation: export, show, status

- instruction: Per decisions c24/c19: a pure read-only derivation joining frame claims to approved deviations via plan_store.list_slugs() filtered on frame_slug, then delivery_store per plan slug; re-exported specs render a contested marker under affected confirmed claims; show/status gain a contested line; missing/corrupt/newer-schema delivery stores degrade to markerless rendering with a stderr diagnostic — never a crash; zero frame-state mutation.
- depends on: t3
- covers: c14, c21, c34, h14, h17, h27
- acceptance:
  - an approved deviation whose --affects names a confirmed claim yields a contested marker on re-export and a contested line in show and status
  - export, show, and status succeed on a frame whose delivery store is missing, truncated, or declares a newer schema (three corruption-shape tests); frame JSON is byte-identical before and after

### t15 — Durable gate-2 split artifact in assign-to-workforce

- instruction: Per decision c25 (artifact-only): the skill script gains a write mode producing `docs/plans/<created-date>-<slug>-split.md` — real per-task summaries, acceptance criteria, instructions from `plan waves --json`, an owner/model annotation block the skill reads back on re-run, and the End state section; re-running overwrites the same dated path; SKILL.md documents the flow; no plan schema change, no new CLI verb.
- covers: c15, h15
- acceptance:
  - the written split artifact carries real task content, the annotation block, and End state; re-run overwrites in place; the file passes markdownlint-cli2

### t16 — Scope skill fans out to smaller-tier subagents

- instruction: scope/SKILL.md steps 1-2 gain a read-only subagent fan-out pattern with a smaller default tier (sonnet), scaled by surface count — small ideas still explore inline (no wizard); provenance and read-only rules unchanged.
- covers: c16, h16
- acceptance:
  - SKILL.md instructs subagent fan-out with a default smaller tier and keeps the read-only + provenance hard rules; the no-wizard escape for small ideas survives

### t17 — learn/explain recipes cover every new surface

- instruction: devague learn, learn skills (SCOPE_STAGE at learn.py:153-171, ASSIGN_TO_WORKFORCE_GUIDANCE at 65-112), and explain document: interrogate --resolve, amend, scope --amend, plan defer, plan risk --amend, multi-id plan confirm/reject, live cover, and the scope subagent fan-out.
- depends on: t4, t9
- covers: c31, h24
- acceptance:
  - tests grep learn/explain output for each new verb and flag; the #52 acceptance criterion (learn/explain document the resolve path) passes

### t18 — Docs sweep, changelog, version bump

- instruction: README.md, CLAUDE.md status entry, docs/skills.md, docs/skill-sources.md version-stamp rows (including the docs/skills.md:255-256 waves-json drift), CHANGELOG.md entry, minor version bump via /version-bump; sign nothing manually — cicd appends.
- depends on: t15, t16, t17
- acceptance:
  - all four docs describe the shipped behavior; version-check CI passes; markdownlint-cli2 clean on changed docs

### t19 — End-to-end verification and issue closure map

- instruction: Repro-first evidence: each of the fifteen issues has a named regression test; full suite green via run-tests with coverage at or above 95 percent; the markdownlint integration test exports the issue-backlog-sweep frame as corpus; produce the issue-to-test closure map for the PR body so each issue closes with a pointer.
- depends on: t7, t12, t13, t14, t18
- covers: c1, c27, c28, c29, c30, h1, h19, h20, h21, h22
- acceptance:
  - pytest -n auto green with coverage >= 95 percent; markdownlint integration green; a closure map lists all 15 issues each naming its regression test; the three downstream workarounds are named as deletable in the map

## Risks

- [unknown_nonblocking] task granularity across a 19-task combined release may shift once implementation starts; mid-run divergence routes through /deviate against gate 2
- [unknown_nonblocking] regressed-frame fallback for live cover (frame park v4) is decided inside t8 — either stored-snapshot fallback or refusal with the reconverge hint (task t8)
- [unknown_nonblocking] first re-export of historical committed specs after the escaper lands produces large presentational diffs (frame park v5) — reviewers should expect them
- [follow_up] downstream repos (reachy-mini-cli, shell-cli, headspace-cli) must re-vendor updated skills via the guildmaster re-broadcast after release and can then delete their workarounds
