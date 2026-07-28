# Delivery Summary — issue-backlog-sweep

plan: `issue-backlog-sweep` · run: `complete` · date: `2026-07-28`
baseline: `devague summary skeleton`

## Intent

Close devague's entire open issue backlog — fifteen issues — in one combined
release, executed as a single `/assign-to-workforce` fan-out of the
`issue-backlog-sweep` plan (19 tasks, 6 dependency waves, one agent per task
per wave in an isolated git worktree, TDD-gated merges). Three of the fifteen
were being worked around by hand in downstream repos: a permanent convergence
deadlock escaped only by editing frame JSON, a coverage gate that made a
milestone-scoped plan unexportable (worked around with a second renderer), and
unescaped export text failing consuming repos' markdownlint CI (worked around
by excluding the generated directory from lint). The release's own success
signal was that those three workarounds become deletable.

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — Escaping engine in render/`_md_safety.py`
- `t2` — Schema and load-order hardening in both stores
- `t3` — `spec_md` renderer sweep: parks, hard questions, dead seeds, escaping
- `t4` — Hard-question resolve move: interrogate --resolve
- `t5` — Reject cascade over attachments
- `t6` — Claim and scope-entry amend moves
- `t7` — scope --seeds accepts question ids
- `t8` — Live-target validation for cover and --covers
- `t9` — Per-target deferral: plan defer
- `t10` — Dependency validation at task creation
- `t11` — Multi-id transactional plan confirm/reject
- `t12` — Plan-risk amend
- `t13` — Summary scoped to confirmed tasks
- `t14` — Contested-by-deviation derivation: export, show, status
- `t15` — Durable gate-2 split artifact in assign-to-workforce
- `t16` — Scope skill fans out to smaller-tier subagents
- `t17` — learn/explain recipes cover every new surface
- `t18` — Docs sweep, changelog, version bump
- `t19` — End-to-end verification and issue closure map

## Actual Delivery

All 19 tasks delivered. Every merge passed the TDD gate (suite green before and
after); no merge was reverted.

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `md_safe_text()` in `devague/render/_md_safety.py` — pure, idempotent, code-span-aware. Commit `d655c2d` |
| `t2` | delivered | Both stores check `schema_version` before parsing; tolerant nested loads; `SCHEMA_VERSION`/`PLAN_SCHEMA_VERSION` → 4. Commit `4b97c57` |
| `t3` | delivered | `## Open parks` (all four kinds), resolved-question markers, rejected-parent exclusion, rejected-seed markers, escaping at every verbatim site. Commit `35932e4` |
| `t4` | delivered | `devague interrogate <cN> --resolve <qN> [--decision]`; gate skips rejected claims; `suggest_move` names the real move. Commit `615667c` |
| `t5` | delivered | `reject` cascades over honesty conditions and unresolved hard questions; `converge` stops warning about rejected assumptions. Commit `24b1837` |
| `t6` | delivered | `devague amend <cN> [--text] [--kind] [--reason]` + `scope --amend <sN>`; `Claim.revisions` trail. Commit `a7b5aa1` |
| `t7` | delivered | `scope --seeds` accepts hard-question (`q*`) ids; question seeds render in the scope section. Commit `6146c4d` |
| `t8` | delivered | `cover` / `--covers` validate against live-frame-derived targets. Commit `4b88608` |
| `t9` | delivered | `devague plan defer <target> --reason` / `--undo`; `## Deferred targets` in the export. Commit `22df59a` |
| `t10` | delivered | `--dep` / `depend --on` refuse self-deps and unknown ids at creation. Commit `95a5c2a` |
| `t11` | delivered | `plan confirm` / `plan reject` multi-id transactional; plan-group errors point at `plan explain`. Commit `a4aabfd` |
| `t12` | delivered | `plan risk --amend <rN> --text`. Commit `caf6b29` |
| `t13` | delivered | Summary scopes to confirmed tasks plus one rejected-count line. Commit `f439537` |
| `t14` | delivered | `devague/contested.py` — read-only derivation; markers in export, `show`, `status`; fails open. Commit `a7eda7a` |
| `t15` | delivered | `split-plan --write` → `docs/plans/<date>-<slug>-split.md` with a round-tripping owner/model block. Commit `7b654c6` |
| `t16` | delivered | `/scope` fans out to read-only subagents (sonnet default, 4-or-fewer inline / 5-or-more fan out). Commit `7059452` |
| `t17` | delivered | `learn` / `explain` / `PLAN_MOVES` teach all ten new surfaces; 24 grep tests. Commit `028f980` |
| `t18` | delivered | README, CLAUDE.md status entry, `docs/skills.md`, `docs/skill-sources.md`, `docs/spec-contract.md`, `docs/llm-guidance.md`, CHANGELOG, 0.20.1 → 0.21.0. Commit `f72fcf4` |
| `t19` | delivered | Adversarial end-to-end verification, three defect fixes, the closure map. Commit `95d8fed` |

## Mid-work Decisions

- `d1` — run t17 (learn/explain recipes) after wave 5 instead of in wave 3 —
  the confirmed dependency graph under-specified it: three of the four surfaces
  its acceptance criterion names (`amend`, multi-id `plan confirm`/`reject`,
  `plan risk --amend`) do not exist until waves 4–5, so documenting them in
  wave 3 would have meant writing recipes for unshipped verbs.
- `d2` — run t18 (docs sweep, changelog, version bump) after t7, t12, and t17
  — same root cause: it must describe the shipped surface. Its confirmed deps
  were t15/t16/t17, and with t17 moved by `d1` plus three more verbs landing in
  waves 4–5, running it in wave 4 would have documented unshipped behavior.
- Both deviations changed execution order only; no plan state was mutated
  (deviate is the marking of the change). Both were taken under the operator's
  standing mid-run authorization and recorded before resuming.
- Not covered by any deviation record: a stale committed artifact
  (`docs/plans/2026-07-17-resolve-parked-vagueness.md`, exported by PR #81
  before the escaper existed) carried three MD037 errors. Rather than
  hand-editing it, it was re-exported through the new escaper — which both
  cleared the errors and demonstrated the #87 fix end to end on real
  pre-existing content. Commit `7ccf4ca`.
- Not covered by any deviation record: `.devague/deliveries/issue-backlog-sweep.json`
  was untracked, so the contested-marker derivation could not reproduce `d1`/`d2`
  for a fresh clone. Committed at `3404bd7` after t19 flagged it.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t17` (`d1`) | its acceptance criteria require documenting verbs that land in waves 4–5; the confirmed dep graph listed only t4 and t9 | acceptable |
| `t18` (`d2`) | must describe the shipped surface; deps under-specified for the same reason as `d1` | acceptable |

No task's *content* drifted from its confirmed contract — every task's
acceptance criteria were met as written. The drift is purely in execution
sequencing, and both entries are covered by approved records.

Three defects were found by t19's cross-task verification and fixed inside the
run rather than deferred, because each was small and in scope:

1. A **regression this release introduced**: `spec_md.py` composed
   `autolink_urls(md_safe_text(t))` while `plan_md.py`/`summary_md.py` composed
   the opposite order. Both corrupted an underscore-bearing URL — the spec order
   truncated it at the first underscore, silently pointing a committed
   artifact's link at the wrong address. Fixed by carving URLs out of
   `md_safe_text` the way code spans already were. This is the hazard filed
   speculatively as #94; it was real.
2. **#49 was only half closed** — a resolved hard question rendered
   `(resolved)` but dropped the recorded decision text, while the issue asked
   for "a pointer to the claim/decision that answered them". Now renders
   `(resolved: <decision>)`.
3. **`spec-to-plan/SKILL.md` was never swept** — it fell between t17 (CLI
   recipes) and t18 (whose criteria named four other docs). It still taught
   `plan reject` as single-id with a shell loop — *the exact workaround #86
   removed* — in a skill guildmaster re-broadcasts to the mesh.

## Evidence

- tests: `bash .claude/skills/run-tests/scripts/test.sh --ci` — **967 passed**, 0 failed
- coverage: **98.37 %** (gate: `fail_under = 95`)
- lint: `markdownlint-cli2 "**/*.md"` — 39 files, **0 errors**
- lint: `.claude/skills/**/*.md` force-linted — 19 files, **0 errors**
- lint: real-corpus export of the `issue-backlog-sweep` frame and plan — **0 errors**
- commits: `main..HEAD` — 42 commits, 71 files changed (+9405 / −417)
- version: `devague 0.21.0` (from 0.20.1)
- closure map: `docs/deliveries/2026-07-28-issue-backlog-sweep-closure-map.md`
- issues closed: #48, #49, #52, #79, #82, #83, #84, #85, #86, #87, #88, #90, #91, #92, #93, #94
- issues opened during the run: #94 (escaper composition — since fixed and closable), #95 (MD033 angle-bracket tokens — deferred)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| All fifteen backlog issues close, each with a named regression test | high | `docs/deliveries/2026-07-28-issue-backlog-sweep-closure-map.md` — verified against each issue's own acceptance criteria, and by running each reporter's repro against the built CLI |
| The convergence deadlock is gone; no frame JSON hand-editing is needed | high | test `tests/test_e2e_resolve.py::test_e2e_issue48_52_hard_question_block_resolve_converge_lifecycle`; both reporters' sequences re-run in scratch dirs |
| A milestone-scoped plan converges and exports with deferred targets | high | shell-cli's real 87-task plan converged and exported after `plan defer` on the 12 gaps + resolving risk `r13` — the artifact their `render_plan.py` was faking |
| Exported artifacts pass markdownlint on underscore-bearing identifiers | high | shell-cli's real spec: **8 errors → 1**, all seven MD037 cleared; survivor is unrelated MD033 (#95) |
| Rejected content no longer reaches the exported spec | high | test asserting the #83 repro's risk text is absent from exported markdown |
| An approved deviation marks the claims it contests, without rewriting the spec | high | `devague/contested.py` + `tests/test_contested.py`; verified against this repo's own `d1`/`d2` (task-only affects → correctly zero markers) |
| The escaper is presentational only — stored JSON and `--json` unchanged | high | byte-stability test over repeated export; frame JSON compared before/after |
| The gate-2 split decision now survives as a committed artifact | high | `docs/plans/2026-07-28-issue-backlog-sweep-split.md`; owner/model edit verified to survive regeneration |
| `/scope` exploration costs less by fanning out to smaller-tier subagents | medium | `.claude/skills/scope/SKILL.md` + `learn.py` `SCOPE_STAGE` pinned by `tests/test_teaching_surface_sweep.py`; the method change itself is not mechanically testable |
| The three downstream workarounds are deletable | medium | verified against the sibling repos' real state, not the issue text — see closure map; deletion happens in those repos, not here |

## Remaining Work / Follow-up

- **#95 (opened this run, deferred)** — angle-bracket tokens still render as
  inline HTML (MD033). Out of #87's stated criteria and not a regression;
  fixing it touches the shared escaper every renderer composes, which was too
  risky during final verification. It is the sole remaining lint error on
  shell-cli's real spec.
- **#94 (opened this run, fixed during it)** — the escaper-composition hazard
  turned out to be real and is fixed here; close it with this PR.
- **Downstream re-vendoring** — reachy-mini-cli, shell-cli, headspace-cli, and
  arm101-cli carry stale vendored skills and the three workarounds. They can
  re-vendor via guildmaster's re-broadcast after this merges and then delete
  the workarounds. Recorded as plan risk `r4` (`follow_up`).
- **The `qN` namespace collision** — claim-attached hard questions and the
  durable questions file both mint `qN` ids from independent counters, so
  `scope --seeds q1` could in principle link the wrong one. Documented as a
  hazard in `scope/SKILL.md` and `docs/spec-contract.md` this run; no data
  loss, but worth a real fix. Not yet filed.
- **#85's secondary ask, deliberately deferred** — warn at converge time when a
  task covers many targets with few acceptance criteria. Recorded as park `v3`
  on the frame; the issue's five formal acceptance criteria all pass without it.
- **`.devague/current_plan` tracking inconsistency** — it is tracked in git, but
  README lists it as uncommitted and `.gitignore` only ignores `.devague/current`.
  Pre-existing; flagged by t18, not fixed (it is a state change, not a docs one).
