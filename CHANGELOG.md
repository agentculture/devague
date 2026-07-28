# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.21.0] - 2026-07-28

The fifteen-issue backlog sweep (the `issue-backlog-sweep` plan, tasks t1–t19)
— one devague-orchestrated workforce fan-out closing issues #48, #49, #52, #79, #82, #83, #84, #85, #86, #87, #88, #90, #91, #92, and #93.
Three of those were hard blockers downstream repos were already working around
by hand: hand-editing frame JSON (#48/#52), and writing a second plan renderer
(#85).

### Added

- **`devague interrogate <cN> --resolve <qN> [--decision "<text>"]`** — close
  out a claim's blocking hard question (#48, #52). Nothing in the codebase
  ever set `HardQuestion.resolved`, so a single blocking question deadlocked
  `converge` permanently and two downstream repos had to hand-edit
  `.devague/frames/*.json` to get past it. This is a USER decision, like
  `confirm` and `park --resolve`: the answer is recorded verbatim on the new
  `HardQuestion.resolution`, the question stays on the record with a
  `(resolved)` marker in the export, and the convergence hint now names the
  executable move instead of prose advice. A blocking question on a
  **rejected** claim also stops blocking — the claim was decided against, so
  the question is moot (#52's third fix).
- **`devague amend <cN> [--text "<text>"] [--kind K] [--reason "<why>"]`** —
  correct a claim without id churn (#84). Reject-and-recapture cost the claim
  its id, and with it every honesty condition, hard question, `instruction`,
  and inbound `scope --seeds` reference. `amend` keeps all of them, appends
  the superseded `(text, kind)` pair to a new `Claim.revisions` trail, and
  flips a confirmed claim back to `proposed` — the same re-confirm rule
  `interrogate --instruction` already applies. `origin` is never touched.
- **`devague scope --amend <sN> --finding "<text>"`** — replace a scope
  entry's finding in place, instead of recording a second entry that says
  "supersedes s18" and leaving the reader to notice the word (#84).
  Deliberately asymmetric with claim `amend`: a scope entry carries no
  status/origin to protect, so there is no revision trail.
- **`devague plan defer <target-id> --reason "<text>"` / `--undo`** — a
  deliberate, documented per-target exclusion from the coverage gate (#85). A
  milestone-scoped plan previously could not converge at all: every target
  derived from the frame had to be covered, so the gate rewarded tasks that
  merely *named* a target. A deferred target drops out of the gate, surfaces
  in `parked_items` labeled `deferred:`, and renders under a
  `## Deferred targets` section in the exported plan-md.
- **`devague plan risk --amend <rN> --text "<corrected>"`** — the plan half of
  #84: correct a stale risk's text in place.
- **Contested-by-deviation markers (`devague/contested.py`)** — a read-only
  derivation joining a frame's confirmed claims to approved deviations'
  `--affects` refs across the plan-slug boundary (#92). A re-exported spec
  renders a `contested by` marker naming the `dN` id under the claim, and
  `show` / `status` gain `contested:` lines (`--json` gains a `contested`
  key). The spec is **not** rewritten — it points forward to the ledger, per
  the issue's ruling that "deviate is the marking of the change". Fails open:
  a missing, corrupt, or newer-schema plan/delivery file degrades to "no
  markers from that source" plus a stderr diagnostic, never a crash.
- **`assign-to-workforce split-plan --write`** — persist the gate-2
  implementation split plan to `docs/plans/<created-date>-<slug>-split.md`
  (#82), beside the plan-md it describes. Unlike the exported spec and plan,
  gate 2 previously survived only in conversation. The file carries the full
  per-wave/per-task content quoted verbatim from `plan waves --json`, a
  `Task | Owner | Model` assignment table the script **reads back** so
  hand-edited cells survive regeneration, and the same End state section as
  plain `split-plan`. Artifact-only — no plan-schema change and no new
  `devague` verb.

### Changed

- **`devague reject <cN>` now cascades** onto the claim's still-live honesty
  conditions and unresolved hard questions, echoing
  `c21 -> rejected (also rejected: h3, q1)`; `--json` gains a `cascaded` key
  (#83). Rejected content was reaching the exported spec and staying in the
  `devague review` pool as if it still awaited a decision. `converge` also
  stops warning about a **rejected** assumption — that decision is already
  made, and the warning offered no useful next move.
- **`devague plan confirm` / `plan reject` take multiple ids in one
  transactional call**, matching the frame side (#86); argument errors raised
  inside the `plan` group now point at `devague plan explain <move>` instead
  of the generic `--help`.
- **`plan task --dep` and `plan depend --on` validate at creation** — a
  self-dependency and an unknown task id are both refused up front (#86),
  instead of surfacing much later as a `waves` cycle or dangling-dep error.
- **`plan cover` and `plan task --covers` validate against targets re-derived
  from the LIVE frame** (#90). The stored target snapshot was frozen at
  seeding while `converge` / `status` / `export` re-derived from the live
  frame, so `status` could recommend covering a target that `cover` then
  refused as unknown — and a frame that legitimately grew a claim mid-run
  could never converge again. The stored snapshot is still checked first (no
  I/O in the common case) and is refreshed and persisted on a live hit.
- **Verbatim text is markdown-escaped at render time** (#87):
  `devague/render/_md_safety.py` gains `md_safe_text()`, composed at every
  verbatim site in `spec_md.py`, `plan_md.py`, and `summary_md.py`.
  Underscore- and dunder-bearing identifiers wrap in code spans rather than
  backslash-escaping — one move that fixes both MD037 and MD050 — other
  markdown control characters escape, text already inside a code span passes
  through byte-for-byte, and the transform is idempotent. Presentational
  only: the store JSON and every `--json` payload are unchanged.
- **`devague summary` scopes Planned Work and Actual Delivery to CONFIRMED
  tasks** (#88), plus one line recording how many tasks were rejected during
  planning. A plan with 19 confirmed and 68 rejected tasks emitted 87 rows,
  which made the delivery artifact unusable. A `proposed` task is excluded
  too — it is still under adjudication, and folding it into either list would
  report an open decision as a closed one.
- **Frame and plan `schema_version` bump 3 → 4** — `HardQuestion.resolution`,
  `Claim.revisions`, and `CoverageTarget.deferred` / `.deferred_reason`. Both
  stores now check the declared version against the **raw** dict *before*
  constructing the domain object, so a genuinely newer file fails closed with
  the upgrade hint instead of an opaque `TypeError` from a nested dataclass,
  and nested `HardQuestion` / `Vagueness` loading tolerates unknown keys. A v3
  file loads with every new field defaulted.
- **The `scope` skill fans read-only exploration out to subagents** (#79,
  #91): **4 or fewer** candidate surfaces are explored inline and serially;
  **5 or more** fan out one read-only subagent per surface (or tight cluster),
  defaulting every subagent to the smaller tier, **sonnet** — a default, not a
  ceiling. Subagents explore and report; they never run a `devague` move. The
  main agent runs every `capture` / `scope` / `question` / `park` call itself,
  from the subagents' reported evidence, so provenance and the
  anti-fabrication contract stay in one place.
- **`devague scope --seeds` accepts claim-attached hard-question ids (`q*`)**
  as well as claim ids (#84's "smaller, related gap") — the branch the
  `/scope` routing table sends a "genuinely unknown, needs a user decision"
  finding down, whose provenance link was previously unrecordable. A question
  seed renders as `(question)`, or `(question, resolved)` once answered.
- Teaching surfaces swept in lockstep with the moves: `devague learn` /
  `learn skills`, `devague explain` / `plan explain`, `README.md`,
  `CLAUDE.md`, `docs/spec-contract.md`, `docs/llm-guidance.md`,
  `docs/skills.md`, `docs/skill-sources.md`, and the `think` / `scope` /
  `assign-to-workforce` skills.

### Fixed

- **Export fidelity** (#93, #49, #83). All four park kinds now render under
  `## Open parks`; the old filter surfaced only `follow_up` / `out_of_scope`
  and silently dropped every open `unknown_nonblocking` item — exactly the
  kind that legitimately coexists with a converged frame, so the artifact
  claimed more certainty than the frame held. A resolved hard question now
  carries a `(resolved)` marker instead of rendering as an open `(blocking)`
  one. Hard questions attached to a rejected claim are dropped entirely. And
  a scope-entry seed citing a rejected claim renders a `(rejected)` marker
  instead of a bare dead reference.

## [0.20.1] - 2026-07-20

### Changed

- **Fan-out worktrees now live in one repo-owned root:
  `<parent-of-repo>/.worktrees.<repo-name>/agent-<task-id>`.** The
  `assign-to-workforce` skill, `CLAUDE.md`, `docs/skills.md`, the `split-plan`
  fan-out instructions, and `devague learn` all teach the same mandatory path
  and resolve it at runtime instead of hardcoding it. Two paths that were
  previously in use are now explicitly forbidden: a shared `../worktrees/` (in
  a multi-repo parent it belongs to nobody, so it reads as deletable scratch
  space, and task ids restarting at `t1` in every repo and every plan make
  concurrent fan-outs collide on the same directory) and any in-repo path such
  as `.claude/worktrees/` (where `git add -A` sweeps agent checkouts into the
  PR and `git clean -fdx` destroys live work). Cleanup removes only the
  worktrees a run created — never the root itself, which a concurrent fan-out
  may be using. `docs/assign-to-workforce-worked-example.md` keeps its
  historical commands and gains a note pointing at the current convention.

## [0.20.0] - 2026-07-17

### Added

- **`devague park --resolve <vN> --decision "<text>" [--claim <cN>]`** — the
  close-out for parked vagueness (#45, #55, #57, #60). A decided blocking park
  now resolves through a CLI move: the item stays on the record with its
  resolution text (and optionally the deciding claim via a new
  `resolution_claim_id`), drops out of the convergence gate, and renders under
  a `## Resolved vagueness` section in exported specs. A bare `--resolve`
  without `--decision` is refused (evidence-bearing close-out); unknown and
  already-resolved ids are refused fail-closed.
- **`devague plan risk --resolve <rN> --decision "<text>"`** — the plan-side
  twin: a resolved blocking risk stops blocking `plan converge`, stays on the
  record, and drops out of open-item listings (`plan deliverables`,
  `parked_items`).

### Changed

- Frame `SCHEMA_VERSION` and `PLAN_SCHEMA_VERSION` bump 2 → 3 (the new
  `Vagueness.resolved`/`.resolution`/`.resolution_claim_id` and
  `PlanRisk.resolved`/`.resolution` fields); older binaries fail closed on v3
  artifacts with the existing upgrade hint, and v2 artifacts load with
  defaults.
- The blocking-vagueness and blocking-risk convergence hints now name the
  executable resolve move (previously they recommended "re-park it as
  non-blocking", which only ever appended a second item — #45's acceptance
  bar).
- Teaching surfaces (`devague learn`, `docs/llm-guidance.md`, the `/think`
  skill, `docs/spec-contract.md`) teach the resolve close-out wherever park
  is taught.

## [0.19.1] - 2026-07-15

### Fixed

- assign-to-workforce split-plan: `truncate()` no longer overshoots `MAX_SUMMARY_LEN` by the 3-char ellipsis — the rendered Task summary cell now stays within the 72-char cap (ellipsis included), so the table width control means what the constant says (#77).

## [0.19.0] - 2026-07-15

### Added

- **New seventh origin skill `/challenge`** (`.claude/skills/challenge/SKILL.md`) —
  method-only: no script, no new CLI verb. A risk-scaled blind-spot discovery
  pass between `/think` and `/spec-to-plan` that pressure-tests a converged,
  exported frame; findings route back through existing deterministic moves as
  proposed-only content for the human to adjudicate, and a clean pass records
  the examined surfaces plus residual uncertainty instead of claiming there
  are no unknown unknowns (#73).

### Changed

- **`devague learn skills` now teaches seven operator skills** in seven-leg
  flow order (`learn.py` and its tests updated in lockstep); README.md,
  CLAUDE.md, `docs/skills.md`, and `docs/skill-sources.md` moved from the
  six-leg to the seven-leg flow (#73).

## [0.18.1] - 2026-07-15

### Fixed

- skills: point the three wrapper scripts (`think.sh` / `spec-to-plan.sh` / `assign-to-workforce.sh`) and the `test_think_skill` docstring at **guildmaster**, the current mesh supplier, instead of the pre-cutover `steward` (matches every `SKILL.md` and the 2026-05-24 steward→guildmaster cutover) (#74).
- skills: reword the `think` / `spec-to-plan` / `assign-to-workforce` / `deviate` descriptions to say they are not vendored like the **inbound** skills (matching `scope` / `summarize-delivery`), since the other origin skills are also not vendored from guildmaster (#74).
- skills: refresh `scope`'s Provenance so its authoring-order ordinal reads correctly against its role as the **opening leg**, and add the missing never-re-vendored-back upstream clause (#74).

## [0.18.0] - 2026-07-15

The execution seam and deviate — devague#53's follow-on plan
(execution-seam-and-deviate, tasks t1–t11), implemented by a
devague-orchestrated workforce fan-out. Adds a sixth origin skill and closes
the loop between the confirmed plan and what the workforce actually produces
and does mid-run.

### Added

- **`devague plan deliverables [--json]`** — a read-only "end state" view over
  a plan: the confirmed announcement / after-state / success-signal claims
  verbatim from the plan's live source frame, every terminal task (an active
  task no other active task depends on) with its acceptance criteria, and the
  surviving open items (parked/pending). Never refuses — shows a
  not-converged banner instead of gating — because previewing the end state is
  exactly what's useful before convergence (#70, esd t2).
- **`devague deviate`** — first-class, append-only deviation records in a new
  delivery store, `.devague/deliveries/<plan-slug>.json`
  (`DELIVERY_SCHEMA_VERSION` 1, fail-closed load, upgrade-on-write like the
  frame/plan stores). `--origin llm` lands `proposed`; only the user
  `--confirm`/`--reject`s a proposed record — the same anti-fabrication rule as
  claims and tasks. `devague deviate --list [--json]` reads records back by
  `dN` id (esd t3).
- **New sixth origin skill `/deviate`** (`.claude/skills/deviate/SKILL.md`) —
  the execution-time leg: stop an in-flight `/assign-to-workforce` run the
  moment execution must diverge from the confirmed plan, get explicit human
  approval, and record the divergence via `devague deviate` before resuming —
  never fold a deviation silently into drift after the fact. Registered in
  `docs/skill-sources.md` alongside the other five origin skills (esd t7).
- **`devague summary [--pr] [--json]`** — a render-only, eight-section
  delivery-summary skeleton assembled from state alone (the plan, its live
  source frame, and the delivery/deviation store) — no fabricated content,
  no-overclaim placeholders throughout. `--pr` swaps in a condensed
  PR-body-shaped skeleton for pasting straight into a pull request description
  (esd t4).
- **`assign-to-workforce` split-plan renders a four-column table** — Wave |
  Task | Model | Task summary — with real, editable model tokens (e.g.
  `haiku`, `sonnet`) in the Model column and 72-character task-summary
  truncation for a scannable table, plus has-instruction and
  acceptance-criteria-count markers on the wave listing so the human sees at a
  glance which tasks carry working instructions (#69, esd t5).
- **`assign-to-workforce` split-plan gains a trailing End state section** that
  quotes `devague plan deliverables` verbatim — so the human go/no-go decision
  sees what the plan actually produces, not just its task map — degrading
  gracefully to a one-line version hint on a `devague` too old to have the verb
  (#70, esd t6).
- **`summarize-delivery` consumes deviation records and the summary
  skeleton** — the delivery-side closure leg now starts from
  `devague summary`'s skeleton and quotes every approved deviation by its `dN`
  id as recorded ground truth for Drift From Plan and Mid-work Decisions,
  instead of reconstructing execution-time drift from memory (esd t8).

### Changed

- **`devague plan depend <tN> --on <tM> --remove`** removes exactly one
  dependency edge; a new **`devague plan amend`** move edits a task's summary
  and/or replaces or removes acceptance criteria by index (#68, esd t1).
  Amending or demoting a CONFIRMED task (`amend`, `depend --remove`, and the
  existing `instruct`) flips it back to `proposed` for re-confirmation, and
  every demoting move now echoes that flip to stdout so the operator doesn't
  miss it silently (#67 hardening, esd t1). No `PLAN_SCHEMA_VERSION` bump was
  needed — edge removal and amendment mutate existing fields rather than
  adding new ones; recorded as deviation `d1` in this release's own delivery
  store.
- `culture.yaml` reverts the `backend` field to `claude`, the mesh standard,
  now that the upstream `agex-cli#46` blocker is closed (#66, esd t9).
- Docs (`CLAUDE.md`, `README.md`, `docs/skills.md`) now name the **six-leg
  flow** — `scope` → `think` → `spec-to-plan` → `assign-to-workforce` →
  `deviate` → `summarize-delivery` — and the audience each leg serves:
  operators (the main agent driving the CLI) and the humans who own the
  go/no-go and final-PR gates.
- `devague learn skills` now teaches authoring all six origin skills,
  marking scope/deviate/summarize-delivery method-only.

### Fixed

- Issues **#62** and **#67** closed with cited evidence (no code change in
  either case — evidence posted directly on the tracking issues).

## [0.17.2] - 2026-07-07

### Changed

- Changed the project license from MIT to Apache-2.0, added a retained MIT notice for vendored inbound skills, and updated package metadata and documentation references accordingly.

## [0.17.1] - 2026-07-10

### Fixed

- **`devague export` / `devague plan export` now emit markdownlint-safe markdown (#64).** Both renderers interpolate free-form claim/task/honesty prose straight into headings, blockquotes, and bullets, which tripped markdownlint's MD026 (no-trailing-punctuation) whenever a heading came from a sentence (the announcement, a task summary) and MD034 (no-bare-urls) whenever prose carried a bare `http(s)://` URL. Downstream repos (league-of-agents-platform) were hand-fixing every export before committing it. New shared helper `devague/render/_md_safety.py`: `heading_safe()` strips trailing punctuation from the `#`/`###` line only (blockquote/body copy keeps the sentence verbatim); `autolink_urls()` wraps a bare URL in `<...>` unless it is already inside `<>`, already the destination of a `[text](url)` link, or inside a code span. Both rules are pinned empirically against markdownlint-cli2 v0.21.0 (markdownlint v0.40.0). Rendering only — Frame/Plan JSON keeps the original text verbatim. New `tests/test_md_safety.py` (unit), hostile-input cases added to `tests/test_render.py` / `tests/test_render_plan.py`, and `tests/test_export_markdownlint_integration.py` (drives the real CLI end to end and shells out to `markdownlint-cli2`, skipping cleanly when it is not on PATH). Closes #64.

## [0.17.0] - 2026-07-09

Skills release plus one correctness fix. No new CLI verbs and no new CLI docs;
the only code change is a data-loss fix in the frame/plan stores (see *Fixed*).

### Added

- **New fifth origin skill `summarize-delivery`** — the delivery-side closure
  leg that runs after `/assign-to-workforce`. It turns an execution run into a
  committed accountability artifact: planned vs actual delivery, mid-work
  decisions, plan drift, evidence-backed delivery claims with confidence
  levels, and remaining work. Method-only in v1 — `SKILL.md` plus an
  eight-section template; no entry-point script and no new CLI verb. Runs on
  complete, partial, and failed runs; never overclaims (a delivery claim
  without evidence is marked `unverified`).
- **Registered as the fifth origin skill** in `docs/skill-sources.md`
  (alongside `scope` / `think` / `spec-to-plan` / `assign-to-workforce`) —
  authored here, re-broadcast by `guildmaster`, never re-vendored back.
- **First dogfood delivery artifact**:
  `docs/deliveries/2026-07-09-sharper-end-to-end-method.md` — the first real
  delivery summary, produced with the shipped template, covering the #53
  sharper-end-to-end-method run (all 14 plan tasks accounted for, three
  classified plan-drift entries, one delivery claim honestly marked
  `unverified`).

### Changed

- Flow docs now name the five-leg flow — `scope` → `think` → `spec-to-plan` →
  `assign-to-workforce` → `summarize-delivery` — in `CLAUDE.md`, `README.md`,
  and `docs/skills.md`, plus a new "after the final PR" handoff section in
  `.claude/skills/assign-to-workforce/SKILL.md` that points to
  `/summarize-delivery`.

### Fixed

- **`save()` now stamps the current `schema_version` (upgrade-on-write)** —
  `devague/store.py` and `devague/plan_store.py` re-emitted the
  `schema_version` loaded from disk instead of the one the running binary
  writes. A frame created under schema v1 and later mutated by a v2 binary was
  saved still labelled v1 while carrying v2-only payload (`scope_entries`,
  per-item `instruction`). An older binary then passed the fail-closed load gate
  (`schema_version > SCHEMA_VERSION`), loaded the file, silently dropped the
  unknown fields, and rewrote it — data loss. Both stores now stamp the current
  version on write, so an older binary correctly *refuses* the file instead.
  Found by Qodo on PR #63; regression tests added for both stores.

## [0.16.0] - 2026-07-07

### Added

- **The sharper end-to-end method ships** — the full #53 build plan (t1–t14),
  implemented by a devague-orchestrated workforce fan-out (5 waves, one agent
  per task, TDD-gated merges):
  - **`devague scope` move** records explored surfaces as first-class
    `ScopeEntry` state (`s1`… id, surface, finding, `--seeds` claim links with
    unknown-id refusal); `scope --list [--json]` reads them back (t1/t3).
  - **Per-item instructions**: optional verbatim `instruction` text on claims,
    honesty conditions (`capture --instruction`,
    `interrogate <c*|h*> --instruction`) and plan tasks
    (`plan task --instruction`, new `plan instruct <tN>` move). Adding or
    changing an instruction on a confirmed item flips it back to `proposed`
    for re-confirmation (t2/t4/t5).
  - **Sharper exports**: spec-md/frame-md render instruction blocks verbatim
    plus a scope-provenance section; plan-md renders per-task instruction
    bullets; absent instructions render nothing (golden-file tested) (t6/t9).
  - **Enriched `waves --json`**: adds a top-level `tasks` object —
    `{summary, instruction, acceptance_criteria, covers}` per task id — a
    self-contained subagent brief; existing keys unchanged (t9).
  - **Structural sharpness warnings** (soft rollout, warnings-only):
    instruction-less confirmed spec-affecting claims, non-measurable
    success signals (deterministic predicate, documented false-positive
    story), and instruction-less confirmed plan tasks (t7/t8).
  - **Teaching + skills**: `learn` presents the optional scope stage;
    `explain scope` / `explain question` work; /think, /spec-to-plan, /scope
    and /assign-to-workforce SKILL.md teach the shipped surface —
    assign-to-workforce briefs now come verbatim from `waves --json`
    (t10/t11/t13).
  - **Dogfooded e2e + boundary audit** committed as tests: a real idea (the
    unpark move, #57) runs scope → frame → spec → plan → fanout brief on the
    shipped surface; the audit pins no LLM imports and no process spawning in
    the package (#20) (t14).

### Changed

- Frame `SCHEMA_VERSION` and `PLAN_SCHEMA_VERSION` both bumped 1 → 2
  (fail-closed on newer; v1 files load with empty defaults).
- `docs/spec-contract.md`, `docs/llm-guidance.md`, `docs/skills.md` document
  the scope entity, instruction fields, schema bumps, and gate rules (t12).

## [0.15.0] - 2026-07-02

### Added

- New fourth origin skill `scope` (idea→scope): guided pre-frame scope exploration — survey the surfaces an idea touches read-only, classify findings, seed the /think frame with provenance-citing boundary/non-goal/assumption claims. Method-only until the `devague scope` CLI move lands (#53 plan t3).

### Changed

- `think` skill: scope-first pointer to /scope, export hygiene (always pass `new --title`; backtick angle-bracket tokens; no retitle/edit move exists), and the question→resolve→decision-claim loop.
- `spec-to-plan` skill: acceptance-criteria-as-instruction-contract coaching, plan-export text hygiene, and the single-task-id `confirm` note (frame confirm is multi-id; parity is a #53 follow-up).
- `assign-to-workforce` skill: task briefs must quote summary/acceptance criteria/covered targets verbatim from plan state — no operator paraphrasing (spec #53 honesty condition h5).
- docs/skills.md + docs/skill-sources.md + CLAUDE.md: the origin-skill family is now four; `devague learn skills` still teaches the three CLI-driving skills until #53 t10/t11 land.

## [0.14.1] - 2026-07-02

### Added

- Exported **spec and plan artifacts** for the upcoming "sharper end-to-end
  method" increment (docs/specs + docs/plans 2026-07-01, plus the frame/plan
  state JSON as the evidence trail; produced by a dogfooded /think and
  /spec-to-plan run). **Documentation and state only — no CLI changes ship in
  this release.** The `devague scope` move, per-item instructions, sharper
  exports + structural gate, and guided plan-to-fanout leg described there are
  *planned* work, tracked by the committed plan (14 tasks over 5 file-disjoint
  waves) and not yet implemented.

## [0.14.0] - 2026-06-23

### Added

- **Vendored the `remember` + `recall` memory skills from eidetic-cli**
  (cite-don't-import) — the write/read halves of eidetic's shared
  `~/.eidetic/memory` surface, so this agent (Claude and its colleague backend)
  can persist facts across sessions and recall them later, sharing one store.
  `remember` drives `eidetic remember` (idempotent upsert of one JSON record or
  an NDJSON batch on stdin, dedup by id + content hash); `recall` drives
  `eidetic recall` with four search modes — exact / approximate / keyword /
  hybrid — each hit carrying text, full provenance metadata, a relevance score,
  and a freshness signal. The `.sh` wrappers are byte-verbatim from eidetic-cli
  (their first-party origin); each `SKILL.md` is localized only in the
  illustrative `--scope <nick>` examples (Provenance keeps "First-party to
  eidetic-cli"). Both default to this agent's PRIVATE scope, reading the suffix
  from `culture.yaml`. Runtime dep: the `eidetic` CLI on PATH (else a local
  eidetic-cli checkout with `uv`). Propagated by rollout-cli's `eidetic-memory`
  recipe.

## [0.13.0] - 2026-05-25

### Added

- Vendored two new skills from guildmaster (#38): `agent-config` (read-only Culture agent-config inventory backing guildmaster's `guild show`) and `pypi-maintainer` (switch a PyPI install between the production index, TestPyPI, and a local editable checkout). `pypi-maintainer` is a strong fit — devague publishes to PyPI + TestPyPI via `.github/workflows/publish.yml`.

### Changed

- Skills supplier repointed `steward` -> `guildmaster` after the 2026-05-24 steward->guildmaster cutover (#38). Re-synced `cicd` and `communicate` from guildmaster (`communicate` gains `scripts/templates/skill-new-brief.md`); `doc-test-alignment` / `run-tests` / `sonarclaude` / `version-bump` are content-unchanged with provenance updated in `docs/skill-sources.md` and `CLAUDE.md`.
- devague's three origin skills (`think` / `spec-to-plan` / `assign-to-workforce`) now declare `type: command` at the source — the field guildmaster had to add on re-broadcast (required by culture/agex backends) and that `docs/skills.md` already specified — and their provenance prose repoints to guildmaster. They are deliberately NOT re-vendored back from guildmaster's re-broadcast copies: devague is their upstream.

### Fixed

- Preserved devague's intentional `cicd/scripts/portability-lint.sh` divergence (drops GNU-only `xargs -r`, which fails on BSD/macOS) across the guildmaster re-sync, instead of reintroducing the portability regression from the upstream copy.

## [0.12.0] - 2026-05-24

### Added

- `devague learn` now teaches skill authoring (#34): an optional topic arg —
  `devague learn skills` (and `skills:all` / `skills:NAME`) — emits a
  self-contained recipe for authoring the three operator skills (think /
  spec-to-plan / assign-to-workforce) in any runtime, framed as consent-gated,
  no-clobber instructions the agent follows. The CLI never writes skill files
  (#20); the agent does, with user consent. Bare `devague learn` appends the
  condensed authoring section.
- `docs/skills.md`: new canonical authoring guide (file layout, frontmatter incl.
  the `type:` gotcha for culture backends, the portable resolver pattern, the
  skill-to-devague contract, and the three human gates), referenced from
  `docs/llm-guidance.md` and `devague plan learn`.

## [0.11.1] - 2026-05-24

### Changed

- Trio skill-script header comments (`think.sh`, `spec-to-plan.sh`) no longer claim the wrapper *adds* a `status` subcommand — since 0.11.0 it is forwarded verbatim like every other move (devague#32, steward PR #58 review).

### Fixed

- `assign-to-workforce.sh` now installs its `mktemp` cleanup `EXIT` trap on the line immediately after creating the temp file, capturing the prior trap beforehand so the subshell-forking capture no longer sits inside the untracked-file window (devague#32).

## [0.11.0] - 2026-05-24

### Added

- `devague status` and `devague plan status` — first-class, read-only CLI verbs that compose `list` + `converge` and report the convergence verdict, remaining gaps, and the recommended next move (`--json` too). Internalised from the `think` / `spec-to-plan` skill wrappers (#30); they never mutate state and the plan verb re-checks the live source frame for drift. Shared renderer in `devague/cli/_status.py`.

### Changed

- The `think` / `spec-to-plan` skill wrappers are now thin: `status` is forwarded verbatim like every other move instead of being a wrapper-only verb implemented in embedded Python. This removed their `mktemp` temp-file and stdout-ordering hazards entirely (#30, Qodo via steward).

### Fixed

- `assign-to-workforce.sh` no longer leaks its `mktemp` temp file if interrupted by a signal — cleanup is now registered with an `EXIT` trap (#30). Its split-plan orchestration presentation deliberately stays out of the deterministic CLI (#20).

## [0.10.0] - 2026-05-24

### Added

- Subagent-driven implementation via the new **assign-to-workforce** skill (#13). Fans out a converged plan's `devague plan waves` to one agent per task per wave in isolated git worktrees, with main-agent **TDD-gated merges** (the task's tests pass before AND after merge); the human gates the spec, the implementation split plan, and the final PR. devague's CLI stays deterministic and non-orchestrating (#20) — it only *describes* the graph. Ships a portable `assign-to-workforce.sh` helper and is recorded as a first-party skill.
- `devague plan converge` now emits deterministic, **non-blocking warnings** for parallel/TDD fitness (#13): flags confirmed tasks with no acceptance criteria and over-serialized dependency graphs, without ever changing `ready_for_plan`/`blockers`.
- `devague learn` documents how to invoke assign-to-workforce (#13).

### Changed

- `/spec-to-plan` now coaches small, file-disjoint, TDD-accepted (parallelizable) tasks, and `CLAUDE.md` documents the assign-to-workforce convention and its three human gates (#13).

## [0.9.1] - 2026-05-23

### Added

- Spec + plan for subagent-driven implementation (#13). Drove `devague` /think then /spec-to-plan to produce a converged spec (`docs/specs/2026-05-23-devague-turns-a-converged-plan-into-parallel-simpl.md`) and a buildable, parallelizable plan (`docs/plans/...`) for the **assign-to-workforce** convention: a cited skill that fans out `devague plan waves` to one subagent per task per wave in isolated git worktrees, with main-agent TDD-gated per-task merges (no human per task) and exactly three human gates — the spec, the implementation split plan (tasks map + per-task subagent/model assignment + go/no-go), and the final PR. Planning artifacts only (no code yet); the CLI stays deterministic and non-orchestrating (#20).

## [0.9.0] - 2026-05-23

### Added

- **Plan dependency waves (#20).** New `devague plan waves [--json]` move emits the plan's task dependency graph as deterministic, machine-readable scheduling metadata (`{plan, waves}` — ordered batches of task ids where wave 0 has no unsatisfied dependency and each later wave depends only on earlier ones). Read-only and convergence-agnostic, so it works on an in-progress plan. Rejected tasks are excluded; a cycle or a dependency on a missing/rejected task is refused by reusing the plan-convergence dependency blockers (`dependency_blockers`). This is the small deterministic primitive behind #13: Devague *describes* the parallelizable graph; it does not spawn subagents, manage worktrees, mark tasks done, or pick a backend.
- **Dated export filenames (#12).** `devague export` and `devague plan export` now prefix the written file with the frame/plan creation date — `docs/specs/<YYYY-MM-DD>-<slug>.md` and `docs/plans/<YYYY-MM-DD>-<slug>.md`. The date comes from the object's `created` timestamp (not today), so re-exporting an unchanged artifact overwrites the same file rather than spawning a dated duplicate. Existing exported docs were renamed to match.

## [0.8.0] - 2026-05-23

### Added

- **Portable LLM guidance contract (#19).** New `docs/llm-guidance.md` — a runtime-agnostic operating contract for any assisting model driving Devague (not just Claude Code): the move-driven mental model, the (state × origin) vocabulary, the anti-fabrication hard rules, adaptive-not-scripted ordering, good/bad operator examples, and the forward (plan) leg. Distilled from the `/think` and `/spec-to-plan` skill contracts; it complements, and does not replace, an agent runtime's own main instruction file (`AGENTS.md`, `CLAUDE.md`, a system prompt).
- `devague learn` (text and `--json`) now always surfaces the operating rules: a `devague is NOT` framing (not a wizard / questionnaire / PRD generator), the anti-fabrication rules, and a pointer to `docs/llm-guidance.md`. JSON gains `not_a`, `operating_rules`, `guidance_doc` (a portable canonical URL — `docs/` is not shipped in the wheel), and `guidance_doc_repo_path` keys.

## [0.7.0] - 2026-05-23

### Added

- **Plan persistence hardening (#18).** Plans now carry an integer `schema_version` (`PLAN_SCHEMA_VERSION = 1`), written on save and checked on load — the plan-engine peer of the frame `schema_version` contract (#5). `plan_store.load` fails closed with a clean `DevagueError` (exit 1 + upgrade hint) when a plan declares a newer unsupported schema; pre-0.7.0 plans without the key load silently as the current schema.
- Loaded-object validation for plans: `Task.origin` / `Task.status` and `PlanRisk.kind` are now validated at construction (via `__post_init__`), so a hand-edited or corrupted plan file surfaces an actionable "malformed plan" `DevagueError` instead of a traceback. (Task/dep/cover *id* cross-references are deliberately not validated at load — coverage and acyclic-dependency checks already run against the live frame in `plan converge`.)

### Changed

- `devague/cli/_plans.py` `resolve_plan` now distinguishes an invalid `--plan` slug, a newer-schema plan, a missing plan, and a malformed plan file — each with its own remediation hint (mirroring the frame `resolve`).

### Fixed

- **Persistence integrity, both engines (PR #25 review).** `store.load` / `plan_store.load` now reject a file whose embedded `slug` disagrees with the requested slug (previously a tampered file could redirect a later `save` onto a different frame/plan). And `schema_version` is now parsed strictly via the shared `frame.parse_schema_version` — a non-integer value (`1.9`, `true`, `"1"`, `null`) is rejected instead of being silently coerced by `int()` (which truncated `1.9`→`1` and accepted `True`→`1`). Both guards were applied symmetrically to the frame engine to keep the persistence twins aligned.

## [0.6.1] - 2026-05-23

### Fixed

- `spec_md` now surfaces `requirement` **claim text** — the last remaining item of #21. Requirements render in a `## Requirements` section with their confirmed honesty conditions nested beneath each claim; honesty conditions on non-requirement claims move to a separate `## Honesty conditions` section (previously every honesty condition was dumped into one flat "Requirements / honesty conditions" list and the requirement claim text never rendered). Re-exported the committed specs to match. Closes #21.

## [0.6.0] - 2026-05-23

### Added

- **Human Review Loop (#17).** Makes the user-only confirmation step ergonomic at scale, preserving the anti-fabrication guarantee.
  - `devague review` (+ `--json`) lists every proposed (unconfirmed) claim and honesty condition with ids — un-gated by convergence and without mutating state — and persists a non-authoritative artifact to `.devague/reviews/<slug>.md`.
  - `confirm` / `reject` now accept multiple ids in one transactional call (any unknown id ⇒ nothing changes).
  - `confirm --from-review <file>` applies a reviewed decision set: each item is emitted with a `pending` marker the human edits to `confirm`/`reject`; `pending` lines are never auto-confirmed (round-trippable artifact).
  - `devague question` records / lists / resolves pending user decisions as durable working state in `.devague/questions/<slug>.md`.
  - devague manages `.gitignore` so `.devague/reviews/` and `.devague/questions/` stay uncommitted working state by default.

### Changed

- `confirm --json` now emits `{confirmed, rejected}` (lists) instead of `{id, status}`, reflecting the multi-id, transactional batch.

## [0.5.1] - 2026-05-23

### Added

- Spec + plan for the 0.6.0 Human Review Loop milestone (#17, folding in #11 and #14), produced by dogfooding `/think` then `/spec-to-plan` on devague itself. `docs/specs/devague-0-6-0-ships-the-human-review-loop-devague.md` (converged frame: 13 confirmed claims, 13 confirmed honesty conditions) and `docs/plans/devague-0-6-0-ships-the-human-review-loop-devague.md` (7 topologically ordered tasks covering all 26 targets, one parked non-blocking risk).
- Recorded design decisions in the frame: batch confirm/reject is transactional (abort-all on any invalid id); `confirm --from-review` is in scope for 0.6.0; devague manages `.gitignore` for `.devague/reviews/` and `.devague/questions/`; a CLI move (not a hand-written skill artifact) owns the pending-questions file.

### Fixed

- Renderers were lossy since the #5/#16 contract: `spec_md` rendered "Non-goals" from `boundary` claims only and never emitted `non_goal` / `decision`; `frame_md`'s sections omitted `non_goal` / `requirement` / `assumption` / `decision`. Both now render every claim kind — `spec_md` gains Scope / boundaries, Non-goals, Assumptions, Decisions, and Open questions sections; `frame_md` covers all twelve kinds. Re-exported this spec so the committed md matches the authoritative frame. Closes #21 (also flagged by Qodo on PR #22).

## [0.5.0] - 2026-05-23

### Added

- Spec contract (#5): claim kinds non_goal / requirement / assumption / decision, each with a documented convergence-gate role (requirement is spec-affecting; non_goal/decision are descriptive; an unconfirmed assumption is a warning, not a blocker).
- Every frame carries a fail-closed schema_version: written on save, validated on load (a newer/unknown version is rejected with an actionable error); existing 0.4.0 frames still load.
- docs/spec-contract.md — the documented source of truth for the entity model, the (state x origin) vocabulary, the structured convergence result, and the per-move input/output/transition/validation-error contract — plus a test-verified worked example at docs/examples/contract-example.json.
- Contract test suite: claim provenance, honesty-condition confirmation, parking vagueness, structured convergence failure, lossless round-trip, schema versioning, and an offline-operation guarantee (no networking imports; a full session runs with sockets stubbed).

### Changed

- BREAKING: converge --json now emits the structured result {ready_for_spec, blockers, warnings, parked_items, required_next_moves} (plans: ready_for_plan) instead of {passed, missing}. The /think and /spec-to-plan status helpers were updated in the same change; required_next_moves is now derived by the CLI. capture --json now includes origin.
- Frame loading raises distinct, actionable DevagueErrors (newer schema -> upgrade; malformed/hand-edited frame -> fix hint) instead of a generic 'invalid slug'.

## [0.4.1] - 2026-05-23

### Added

- docs/specs and docs/plans artifacts for issue #5 (Define the spec contract): a converged Announcement Frame spec and its buildable 11-task plan, generated by dogfooding /think + /spec-to-plan.

### Changed

- /think skill (SKILL.md): document the commit-then-/spec-to-plan close-out after a reviewed export (no "what next?" pause).

### Fixed

- `render/spec_md.py` + `render/plan_md.py`: exported markdown now satisfies the repo's own markdownlint config (blank line after every heading and before every list, MD022/MD032). Disabled MD036 for the renderers' italic metadata subtitle. Caught by dogfooding — `devague export` output was failing CI's markdown lint on `docs/specs` / `docs/plans`.

## [0.4.0] - 2026-05-23

### Added

- **Spec→plan engine** — a deterministic structural peer of the working-backwards frame engine that turns a converged spec into a buildable plan. New modules: `devague/plan.py` (Plan / Task / PlanRisk / CoverageTarget domain), `plan_convergence.py` (coverage + acceptance + acyclic-dependency + blocking-risk gate, reusing `ConvergenceResult`), `plan_store.py` (`.devague/plans/`), and `render/plan_md.py` (topologically-ordered buildable plan).
- Nested `devague plan` CLI group (`new` / `task` / `accept` / `depend` / `cover` / `confirm` / `reject` / `risk` / `converge` / `export` / `show` / `list` / `learn` / `explain`), all with `--json`. `plan new` requires a converged source frame; `converge`/`export` re-evaluate against the **live** frame and refuse on frame drift (deleted or regressed).
- New first-party **`/spec-to-plan`** skill (`.claude/skills/spec-to-plan/`): a portable wrapper (`scripts/spec-to-plan.sh`) forwarding to `devague plan` plus a `status` next-move helper over the plan gate.

### Changed

- **Renamed the `devague` skill to `think`** (`.claude/skills/think/`, `scripts/think.sh`) — clearer idea→spec framing and to pair with the new `/spec-to-plan` sibling. The product/CLI/repo name stays `devague`; only the skill identity changed. `docs/skill-sources.md` and downstream steward re-vendoring must relearn the new name. ("devague" remains a trigger keyword on `/think`.)

## [0.3.3] - 2026-05-23

### Added

- First-party `devague` skill (`.claude/skills/devague/`): a portable wrapper (`scripts/devague.sh`) that operates the working-backwards CLI, forwards every move, and adds a `status` next-move helper over the convergence gate; plus `tests/test_devague_skill.py` and an outbound-origin note in `docs/skill-sources.md`. Origin = devague; steward pulls it from here and broadcasts to the AgentCulture mesh.

## [0.3.2] - 2026-05-23

### Security

- `store.validate_slug()` now guards every slug-derived path (`--frame`,
  `.devague/current`, and a persisted `frame.slug`) against path traversal and
  absolute paths via a strict allowlist, closing an arbitrary file read/write
  through `load()` / `save()` / `export`.

### Fixed

- `devague new` no longer silently overwrites an existing frame when two titles
  slugify to the same value: `store.unique_slug()` allocates `<slug>-2`,
  `<slug>-3`, … and the chosen slug is surfaced in the output.

### Changed

- `devague new` and `devague learn` now use issue #4's exact entry point —
  first question *"What's the announcement?"* with the "users, teammates, or
  yourself" supporting prompt.
- Documented the canonical ten-stage guided sequence (Announcement → Spec) in
  the design doc and `devague learn` (also exposed via `learn --json`), while
  keeping the engine move-driven rather than a rigid wizard.
- Raised the coverage gate from 70 % to 95 %.
- Cleared four SonarCloud maintainability findings on the new code: collapsed
  the redundant `return 0` paths in `show` / `list` (S3516) and reduced the
  cognitive complexity of `render_frame` and `convergence.evaluate` below the
  threshold by extracting focused helpers (S3776). Behavior unchanged.

## [0.3.1] - 2026-05-23

### Fixed

- `converge` now demotes a `converged` frame back to `drafting` when a new
  blocking item is added and the gate re-runs (was stuck at `converged`).
- Removed the unreachable `parked` value from `CLAIM_STATUSES` and
  `Claim.status`; the `park` move records open vagueness, not a claim status.
  Updated convergence message wording, spec, and plan to match.
- `export --format` is now constrained to `choices=("spec-md",)`, preventing
  `--format frame-md` from silently writing the Announcement Frame as a spec.

## [0.3.0] - 2026-05-23

### Added

- The working-backwards engine: a deterministic Frame state machine
  (`devague/frame.py`, `store.py`, `convergence.py`) and the moves
  `new` / `capture` / `interrogate` / `confirm` / `reject` / `park` /
  `converge` / `export` / `show` / `list`, plus a pluggable renderer
  registry (`frame-md`, `spec-md`). `export` is gated on convergence;
  LLM-proposed claims and honesty conditions require user confirmation.
- Real `learn` / `explain` bodies teaching the method and the moves.

## [0.2.0] - 2026-05-23

### Changed

- Renamed the package and CLI `specifix` → `devague` (PyPI distribution
  `devague`; the orphaned `specifix 0.1.0` is left as-is). Console script,
  `python -m`, `culture.yaml` suffix, SonarCloud key, and docs all updated.

### Removed

- The placeholder `whoami` verb (the `learn` / `explain` affordances remain).

## [0.1.0] - 2026-05-22

### Added

- AgentCulture sibling scaffold: the `specifix` package (hatchling,
  Python >=3.12, zero runtime deps) with the afi-cli CLI chassis —
  structured errors, a strict stdout/stderr split, and `--json` support.
- Placeholder agent-first verbs `learn` / `explain` / `whoami` — honest
  "not yet implemented; specifix is greenfield" stubs.
- CI workflows: `tests.yml` (pytest + coverage + flake8 + SonarCloud +
  version-check), `security-checks.yml` (bandit + pylint), `publish.yml`
  (TestPyPI on PR, PyPI on main, via OIDC Trusted Publishing).
- `culture.yaml` declaring the `specifix` agent nick (`backend: claude`).
- Vendored skills from steward: `cicd`, `communicate`, `version-bump`,
  `run-tests`, `sonarclaude`, `doc-test-alignment`. Provenance tracked in
  `docs/skill-sources.md`.
- Repo-local lint configs: `.flake8`, `.markdownlint-cli2.yaml`,
  `.pre-commit-config.yaml`; `sonar-project.properties`; the
  `.claude/skills.local.yaml.example` per-machine config template.

Resolves #2.
