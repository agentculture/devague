# issue-backlog-sweep

> devague closes its fifteen-issue backlog: exports become lossless and lint-clean, rejected and contested content stops leaking into artifacts, plans gain live coverage targets with per-target deferral, claims and hard questions gain amend and resolve moves, the delivery summary scopes to confirmed work, gate 2 gains a durable split artifact, and scope exploration fans out to smaller-tier subagents

## Audience

- operator agents driving devague across AgentCulture repos — the field reporters behind these issues (headspace-cli, reachy-mini-cli, shell-cli, arm101-cli, agentfront) — plus the humans owning the spec, split-plan, and final-PR gates who read the exported artifacts

## Before → After

- Before: fifteen open issues document real field failures on 0.20.x: two permanent convergence deadlocks (blocking hard questions unresolvable, cover refusing what converge demands — both worked around by hand-editing state JSON), specs that silently drop parks and leak rejected content, exports that fail downstream CI lint, an 87-row delivery table for 19 real tasks, and a five-move id-churning path to fix one number in a claim
- After: all fifteen open issues (#48, #49, #52, #79, #82-#88, #90-#93) close on one release: exported artifacts are lossless, lint-clean, and honest about rejection and deviation; plans cover live targets, defer deliberately, and validate deps at creation; hard questions resolve and claims amend without id churn; the summary is confirmed-only; gate 2 leaves a durable artifact; scope fans out to smaller-tier subagents

## Requirements

- export renders every parked kind: `render/spec_md.py:110-118` `_follow_up` filters to `follow_up`/`out_of_scope` only, so an unresolved `unknown_nonblocking` park renders nowhere in the spec; all open parks must render grouped by kind, and the pinning test `tests/test_render.py:301-306` flips from asserting absence to asserting presence (#93, #49)
  - honesty: honest only if a converged frame carrying open parks of all four kinds exports a spec where every open park appears, labeled by kind — verified by flipping tests/`test_render.py`:301-306 from asserting absence to asserting presence
- hard questions render honestly: `render/spec_md.py:104-107` shows no resolved marker and iterates all claims regardless of status — resolved questions render as resolved (or are omitted) and questions on rejected claims never render (#49, #83)
  - honesty: honest only if a resolved hard question renders with a resolved marker (or is omitted by documented choice) and a hard question on a rejected claim never reaches the export — regression covering the #83 repro shape: capture, interrogate --risk, reject, converge, export
- a user move resolves claim-attached hard questions: nothing in the codebase sets `HardQuestion.resolved` (only vagueness `frame.py:243` and plan-risk `plan.py:187` resolves exist), `set_status` (`frame.py:264-273`) routes only c\*/h\* ids, so the gate at `convergence.py:111-116` blocks forever; `suggest_move` (`convergence.py:206-211`) must name the real move (#48, #52)
  - honesty: honest only if the block-resolve-converge sequence completes through CLI moves alone (no state-JSON hand-edit), `suggest_move` names the shipped move verbatim, and resolved state survives a save/load round-trip
- reject cascades over attachments: rejecting a claim cascades to (or refuses over) its honesty conditions and hard questions, reporting what it took; `_assumption_warnings` (`convergence.py:120-126`) and the blocking-question gate skip rejected claims; `devague review` stops listing orphaned conditions (#83)
  - honesty: honest only if rejecting a claim with attachments reports exactly what it cascaded over (or refuses with an actionable hint), post-reject converge emits zero warnings about the rejected claim, and review lists zero orphaned conditions
- markdown escaping lands at the single verbatim seam: `render/_md_safety.py` (today only `autolink_urls`/`heading_safe`) gains identifier-aware escaping — code-span wrapping for underscore and dunder tokens per the #87 comment, fixing MD037 and MD050 — applied at every verbatim site in `spec_md.py`, `plan_md.py`, and `summary_md.py` (#87)
  - honesty: honest only if a frame whose text contains `_read_file`, `__init__.py`, `*`, `[`, a backtick, and a leading `#` exports spec-md and plan-md passing markdownlint-cli2 default config — the integration test extends tests/`test_export_markdownlint_integration.py`
- an amend move preserves identity: claims (`--text`/`--kind`, keeping id, honesty conditions, instruction, and inbound seeds), scope entries (`scope --amend sN --finding`), and plan risks (`plan risk --amend rN --text`); amending a confirmed item flips it to proposed with an echoed flip, matching the `interrogate.py:58-68` and plan `_FLIP_SUFFIX` precedent (#84)
  - honesty: honest only if amending a confirmed claim keeps its id, honesty conditions, instruction, and inbound scope seeds, flips it to proposed with an echoed flip, and correcting one number costs exactly one move — with the same holding for scope --amend and plan risk --amend
- `scope --seeds` accepts question ids: `Frame.add_scope_entry` (`frame.py:252-254`) validates seeds via `find_claim` only, so `q*` is refused today — yet the /scope routing table sends needs-a-user-decision findings to `question`, so that branch must be seedable (#84)
  - honesty: honest only if scope --seeds accepts a valid `q*` id, still refuses an unknown `q*` id with the show hint, and the seeded question renders in the exported scope-exploration section
- `plan cover` and `plan task --covers` validate against live-derived targets: `_require_target` (`cli/_commands/plan.py:145-151`) reads the stored snapshot that only `converge`/`export` refresh (`plan.py:496,530`) while `plan status` re-derives without persisting — verified by live repro: `plan status` recommends `plan cover t1 --target c7` and that exact move refuses with unknown coverage target; after `plan converge` it succeeds (#90)
  - honesty: honest only if the verified repro inverts: after the frame grows a confirmed claim, plan status recommends cover for it AND that exact cover succeeds immediately, with no intervening plan converge required
- a per-target deferral move (for example `plan defer <id> --reason`): deferred targets stop blocking `_missing_coverage` (`plan_convergence.py:26-32`), render as a Deferred targets section in plan-md (no such section exists, `render/plan_md.py:78-102`), and `plan status` distinguishes deliberately-deferred from not-yet-covered; today an `out_of_scope` risk has zero gate effect (#85)
  - honesty: honest only if a plan with deferred targets converges and exports, the export names every deferred target with its reason in a Deferred targets section, and plan status reports deliberately-deferred distinctly from not-yet-covered — exercising the shell-cli shape of 90 covered plus 12 deferred
- `plan task --dep` validates at creation: `add_dep` (`plan.py:134-136`) is a bare append, so self-dependencies and dangling deps are accepted silently (pinned by `tests/test_cli_plan.py:87-96`, which flips); refuse self-reference and unknown ids with actionable hints (#86)
  - honesty: honest only if plan task --dep naming the about-to-be-assigned id or an unknown id refuses at creation with an actionable hint, and tests/`test_cli_plan.py`:87-96 is flipped rather than deleted
- `plan confirm` and `plan reject` go multi-id transactional: today single-id (`cli/_commands/plan.py:827-835`) versus the frame-side batched `nargs` surface (`confirm.py:90-97`, `reject.py:10-15`) (#86)
  - honesty: honest only if plan confirm and plan reject with N ids apply transactionally — all valid or none applied — matching the frame-side contract in behavior and error text
- `devague summary` scopes to confirmed tasks: `_planned_work_lines`, `_actual_delivery_lines`, and `summary_data` (`render/summary_md.py:119-143, 265-271`) iterate every task today; rejected tasks leave Planned Work and the Actual Delivery table, replaced by a one-line rejected-count note; `dependency_waves` already excludes rejected tasks (`plan.py:285`) so the --pr wave map is safe (#88)
  - honesty: honest only if a plan with N confirmed and M rejected tasks emits exactly N Actual Delivery rows and N Planned Work entries plus a single line counting the M rejected, and the --pr wave map stays rejected-free
- approved deviations surface against contested claims: an approved deviation carries `--affects` claim ids (`deviate.py:78-89`) but no export/show/status code touches the delivery store today (zero grep hits); derive the back-reference read-only via enumerate `plan_store.list_slugs()`, filter `plan.frame_slug`, load the delivery per plan slug (#92)
  - honesty: honest only if an approved deviation whose --affects names a confirmed claim yields a contested marker under that claim on re-export AND a contested line in show/status, all derived read-only across the plan-slug join with zero frame-state mutation
- split-plan writes a durable gate-2 artifact: `docs/plans/<created-date>-<slug>-split.md` beside the exported plan-md, overwrite-in-place on re-run; today the script has no write step at all (`assign-to-workforce.sh:262-283` — subcommands split-plan, waves, help only) (#82)
  - honesty: honest only if the written split artifact carries real per-task summaries, acceptance criteria, instructions, the owner/model annotation block, and the End state section; re-running overwrites the same dated path; the file lints clean
- the /scope skill fans exploration out to smaller-tier read-only subagents (sonnet default): method-only change to SKILL.md steps 1-2 (`scope/SKILL.md:43-50`, today serial first-person), sweeping `learn.py` `SCOPE_STAGE` (`learn.py:153-171`), `docs/skills.md:156-176`, and the `docs/skill-sources.md` version-stamp row (#79, #91)
  - honesty: honest only if scope SKILL.md, learn.py `SCOPE_STAGE`, docs/skills.md, and the skill-sources ledger all describe the same subagent fan-out with the same default tier — a doc-alignment check, not four diverging texts
- every new or changed CLI surface in the sweep — hard-question resolve, claim/scope/risk amend, `plan defer`, multi-id `plan confirm`/`reject`, live-target cover — is documented in the `learn` and `explain` recipes in the same release; issue #52 makes this an explicit acceptance criterion for the resolve move
  - honesty: honest only if devague learn and devague explain output name every new verb/flag shipped in the sweep, checked by tests that grep the recipe text for each surface
- the render-time escaper never alters text inside existing code spans: claim text already mixes prose and backticked tokens (this frame is itself the counter-evidence corpus), so identifier wrapping must skip spans that are already code and stay stable across repeated exports
  - honesty: honest only if exporting this very frame twice in a row is byte-stable and lints clean — the frame whose claims mix backticked and bare identifiers is the regression corpus
- export flags scope entries whose `--seeds` cite a rejected claim instead of rendering a dead reference — the fourth #84 acceptance criterion, which claim c7 (amend) does not cover on its own
  - honesty: honest only if an exported spec whose scope entry seeds a rejected claim renders a visible rejected marker (or resolves the reference) instead of a bare dead id
- the contested-by-deviation derivation fails open: a missing, corrupt, or newer-schema delivery store never breaks `export`, `show`, or `status` — the artifact renders without markers and a diagnostic goes to stderr
  - honesty: honest only if export, show, and status succeed on a frame whose delivery store is missing, truncated, or declares a newer schema — covered by tests for all three corruption shapes

## Honesty conditions

- honest only if one release genuinely closes every one of the fifteen listed issues — each closed with a pointer to the shipping test/section, none closed as wontfix-by-stealth or half-delivered
- honest only if the #92 implementation adds no mutation path to frame state — the contested derivation is a pure function over existing frame, plan, and delivery state, and no claim id or text changes on re-export
- honest only if frame and plan JSON on disk are byte-identical before and after an export, and show --json output is unchanged by the escaping change
- honest only if every fix maps back to at least one named field report and each reporter repro in the issue bodies is covered by a regression test — no fix ships that answers nobody
- honest only if the release closes all fifteen without regressing the existing gates: the full suite, coverage, and the markdownlint integration tests pass on the same commit that closes them
- honest only if each named failure reproduces on 0.20.1 before the fix — the two deadlocks, the park drop, the rejected-content leak, the MD037/MD050 failures, and the 87-row summary all have failing-first tests or recorded repros
- honest only if the signals are checked mechanically: issue closure count, markdownlint exit code, pytest exit code and coverage threshold, and the downstream-workaround deletability confirmed on the issues by the reporting repos

## Success signals

- all 15 issues closed by the release with a regression test each; exported spec-md, plan-md, and split artifacts produce 0 markdownlint-cli2 errors under the default config; the full pytest suite stays green with coverage >= 95%; the 3 downstream workarounds named in the issues (`render_plan.py` projection, docs/specs lint ignores, hand-edited frame JSON) become deletable

## Scope / boundaries

- the exported spec stays a point-in-time record: the #92 fix never mutates claims, churns ids, or makes specs editable — contested markers are a pure render-time derivation, honoring the maintainer ruling quoted in #92 that deviate is the marking of the change
- escaping is presentational only: frame and plan JSON keep raw unescaped text and `show --json` output is unchanged, per the #87 acceptance criteria

## Non-goals

- the CLI stays deterministic and non-orchestrating (issue #20): scope subagent fan-out lives in skill method text, never as a CLI verb; any per-task owner/model assignment for #82 is recorded as inert data — the Model column today is presentation-only (`assign-to-workforce.sh:156-159`, `DEFAULT_MODEL = "sonnet"`)
- origin skills are never re-vendored back from guildmaster: every skill change lands in this repo and updates the `docs/skills.md` narrative plus the `docs/skill-sources.md` ledger row (`docs/skill-sources.md:38-66`)

## Assumptions

- issue #82 first ask is already shipped and its symptom was a stale vendored copy: since 0.16.0 the script renders real task content from `plan waves --json` (`assign-to-workforce.sh:202`; the JSON carries summary, instruction, acceptance criteria, and covers per `cli/_commands/plan.py:569-584`), so the live gaps are only the durable artifact and owner/model recording
- schema bumps are needed and currently hazardous: `HardQuestion(**q)` and `Vagueness(**v)` raw unpacking (`frame.py:315,322`) plus the version gate running after `from_dict` (`store.py:136-147`) means any new persisted field crashes older binaries with a raw TypeError instead of the fail-closed IncompatibleSchemaError; resolve and amend fields need a frame schema bump with the load order fixed
- the deviation-to-claim join stays derived, not stored: `Delivery` has no frame slug (`delivery.py:57` keys by plan slug only) and Frame has no reverse plan index, so #92 rendering derives the contested set at render time instead of adding reverse-pointer state
- decision c25 (no plan schema change) is scoped to the #82 owner/model recording only — the #85 defer move requires persisting deferred-target state, which means a `PLAN_SCHEMA_VERSION` bump, and `plan_store.load` (line 54 vs 62) has the same late-version-gate hazard c18 records for frames, so the load-order fix must cover both stores

## Scope exploration

- `s1` — `devague/render/spec_md.py`: park-kind filter `_follow_up` (lines 110-118) renders only `follow_up`/`out_of_scope`; hard questions (104-107) render with no resolved marker and no parent-status filter; all verbatim text passes only through `autolink_urls`, never an escaper
  - seeds: `c2`, `c3`, `c6`
- `s2` — `devague/convergence.py`: blocking-question gate (111-116) and assumption warnings (120-126) iterate claims status-agnostically, so rejected claims still block and warn; `suggest_move` (206-211) advertises a resolve path no CLI move implements
  - seeds: `c4`, `c5`
- `s3` — `devague/frame.py`: `set_status` (264-273) routes only c\*/h\*; `HardQuestion.resolved` exists but nothing sets it; `add_scope_entry` (252-254) validates seeds via `find_claim` only; no amend machinery exists for claim text or scope entries; `HardQuestion(**q)`/`Vagueness(**v)` unpacking (315, 322) rejects unknown keys
  - seeds: `c4`, `c7`, `c8`, `c18`
- `s4` — `devague/store.py`: the schema-version gate (143-147) runs after `from_dict` (136), so a newer-schema frame with new nested fields dies with a raw TypeError before reaching the fail-closed IncompatibleSchemaError
  - seeds: `c18`
- `s5` — `devague/cli/_commands/plan.py`: `_require_target` (145-151) validates cover/--covers against the stored snapshot; `_live` (108-118) re-derives from the live frame for converge/export/status; converge and export persist the refreshed snapshot (496-502, 527-543) but status does not; `plan confirm`/`reject` are single-id (827-835); `plan task --dep` is never validated (220-232)
  - seeds: `c9`, `c11`, `c12`
- `s6` — `devague/plan_convergence.py`: `_missing_coverage` (26-32) iterates every target unconditionally — no deferral set exists and `out_of_scope` risks have zero gate effect; `_missing_dep_integrity` (100-121) is shared by converge and waves, so both catch cycles but only after creation
  - seeds: `c10`, `c11`
- `s7` — `live repro of issue 90 against the 0.20.1 tree`: scratchpad run: frame converges, plan seeded, frame grows c7/h7, `plan status` recommends `devague plan cover t1 --target c7`, that exact move refuses with unknown coverage target, and after a persisting `plan converge` the same cover succeeds — the escape hatch exists but is accidental and the recommended move is the refusing path
  - seeds: `c9`
- `s8` — `devague/render/plan_md.py and devague/render/summary_md.py`: no markdown escaping beyond `autolink_urls`/`heading_safe`; plan-md has no Deferred targets section (sections: title, announcement, Tasks, Risks at 78-102); summary Planned Work (119-129) and Actual Delivery (132-143) iterate every task with no status filter while `dependency_waves` (plan.py:285) already excludes rejected tasks
  - seeds: `c6`, `c10`, `c13`
- `s9` — `devague/delivery.py, devague/delivery_store.py, devague/cli/_commands/deviate.py`: DeviationRecord carries `affects` validated against plan task ids, target ids, and all frame claim/honesty ids (deviate.py:78-89); statuses are proposed/approved/rejected; the store is keyed by plan slug only — no frame slug on Delivery and no reverse index on Frame
  - seeds: `c14`, `c19`
- `s10` — `devague/cli/_commands/export.py, show.py, status.py`: zero references to the delivery store in any of the five frame-side view/export modules (grep confirmed) — no path exists today to mark a confirmed claim contested by an approved deviation
  - seeds: `c14`
- `s11` — `.claude/skills/assign-to-workforce/SKILL.md and scripts/assign-to-workforce.sh`: the split-plan table renders real task content since 0.16.0 (script line 202 reads summaries from the `plan waves --json` payload); the Model column is a presentation-only hardcoded sonnet default (156-159); no --write flag and no \*-split.md artifact exists anywhere in the repo (subcommands: split-plan, waves, help at 262-283)
  - seeds: `c15`, `c17`, `c20`
- `s12` — `.claude/skills/scope/SKILL.md`: steps 1-2 (lines 43-50) describe serial first-person exploration; no subagent, fan-out, or model-tier language anywhere in the skill, and no precedent in think or spec-to-plan — the only fan-out pattern in the kit is assign-to-workforce worktree orchestration, which is the wrong shape for read-only exploration
  - seeds: `c16`
- `s13` — `devague/cli/_commands/learn.py`: `SCOPE_STAGE` (153-171) and `ASSIGN_TO_WORKFORCE_GUIDANCE` (65-112) assert method text that goes stale if the skills change; skill bodies are linked by raw GitHub URL, not embedded, so only the capsule dicts need sweeping
  - seeds: `c15`, `c16`
- `s14` — `docs/skills.md and docs/skill-sources.md`: origin-skill ledger rows carry per-skill version stamps that must be updated on any skill change (skill-sources.md:38-66); docs/skills.md:255-256 already drifts from SKILL.md:138-140 on where task briefs quote from
  - seeds: `c23`
- `s15` — `tests/`: pinned tests that must flip: `test_render.py:301-306` (nonblocking park stays unlisted) and `test_cli_plan.py:87-96` (unknown dep accepted); `test_export_markdownlint_integration.py` runs real markdownlint-cli2 as the escaping guard; `test_summary.py:227` is the rejected-X-omitted template; `test_e2e_resolve.py` is the resolve-lifecycle template for hard questions
  - seeds: `c2`, `c6`, `c11`, `c13`
- `s16` — `challenge pass / adjacent-systems lens: learn.py + explain recipes`: four new CLI surfaces land in this sweep and none of the spec claims covered documenting them; #52 explicitly requires learn/explain updates for the resolve move
  - seeds: `c31`
- `s17` — `challenge pass / counter-evidence lens: render/_md_safety.py + this frame as corpus`: this frame mixes backticked and bare identifiers in the same claim texts — an escaper that wraps inside existing code spans would corrupt its own spec on the next export; idempotence across repeated exports is required
  - seeds: `c32`
- `s18` — `challenge pass / lifecycle lens: spec_md scope section + issue 84 acceptance criteria`: the amend claim c7 covers three amend surfaces but not the dead-seed-reference acceptance criterion; reject-then-recapture (which this session itself performed on h8) leaves scope seeds citing rejected ids
  - seeds: `c33`
- `s19` — `challenge pass / containment lens: delivery-store reads from export/show/status`: the contested-marker join adds the first delivery-store read on the frame side; a corrupt or newer-schema delivery file must degrade to markerless rendering, never a crashed export
  - seeds: `c34`
- `s20` — `challenge pass / migration lens: plan.py PLAN_SCHEMA_VERSION + plan_store.py load order`: probe confirmed `plan_store`.load parses via `from_dict` (line 54) before the version gate (line 62) — the same hazard c18 records for frames; defer state forces a plan schema bump, so the fix must cover both stores
  - seeds: `c35`, `c18`
- `s21` — `challenge pass / actors lens: qN id namespace across HardQuestion and the questions file`: probe confirmed both hard questions (frame.py:201) and durable questions assign qN ids independently — recorded as pending decision q4 (seeds not linkable: --seeds refuses q ids until c8 lands, which is itself finding evidence for c8)
- `s22` — `challenge pass / concurrency lens: worktree-copied .devague state during fan-out`: clean pass: each worktree owns a full checkout copy of .devague, conflicts surface at reconcile per the documented worktree-contention convention; residual risk only if two agents ever share one checkout — no new claim seeded
- `s23` — `challenge pass / reversibility lens: one-combined-release decision c26`: clean pass: a CLI release reverts by version rollback/yank; the schema bumps are fail-closed downgrade-safe once the load-order fix lands (c18/c35); no new claim seeded

## Decisions

- issue 92 ships on both surfaces: contested markers in re-exported specs plus a read-only contested-by-dN line in `devague show`/`status` (resolves q1)
- issue 82 owner/model assignment is artifact-only: recorded in the durable split artifact via an annotation block the assign-to-workforce skill reads and writes — no plan schema bump, no `plan assign` verb (resolves q2)
- the sweep ships as one combined release: single branch, single PR closing all fifteen issues, one version bump (resolves q3)
- the #48/#52 resolve move ships as `devague interrogate <cN> --resolve <qN>` with an optional `--decision` recording how it was answered — the claim id disambiguates the shared qN namespace (resolves q4)

## Open parks

- [unknown_nonblocking] issue 86 reports plan converge missed a self-cycle on 0.20.0 but the code shows evaluate includes `_missing_dep_integrity` — unverified which is true for the installed 0.20.0; creation-time validation fixes it either way
- [unknown_nonblocking] whether issue 85 secondary ask — warn when a task covers many targets with few acceptance criteria — ships in this sweep or as a later plan-convergence warning heuristic
- [unknown_nonblocking] behavior of live-target cover when the source frame has regressed below convergence: `_live` refuses in that state — whether cover falls back to the stored snapshot or refuses with the reconverge hint is an implementation-time decision
- [unknown_nonblocking] re-exporting any historical committed frame after the escaping change rewrites its dated spec file with code-span wrapping — expected and presentational-only, but the first re-export after upgrade produces a large diff reviewers should anticipate
- [follow_up] downstream repos carry stale vendored copies and workarounds to retire once fixes land: reachy-mini-cli split placeholder table and `render_plan.py` projection (issues 82/85), shell-cli markdownlint ignores for docs/specs (issue 87); notify via guildmaster re-broadcast
