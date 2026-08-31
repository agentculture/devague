# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

**The validate-delivery skill lands — seventh in flow order, eighth origin
skill (issue #97, #107).** New skill **`/validate-delivery`**
(`.claude/skills/validate-delivery/SKILL.md`) — the execution-to-evidence leg
between `/assign-to-workforce`'s (and `/deviate`'s) fan-out and
`/summarize-delivery`'s closeout. Method-only, same shape as `/deviate`: the
agent runs the plan's behavioral tests agent-side after waves merge, then
files what it found via record-only devague moves — `devague oblige` (mark a
claim's behavioral obligation), `devague evidence` (obligation met by this
test, asserting this behavior, outcome pass or fail), and `devague delta`
(a behavioral added/amended/removed record with provenance back to the claim
or approved deviation and forward to its evidence). The CLI never runs a
test itself (issue #20); `llm`-origin filings land `proposed` for human
adjudication, same anti-fabrication contract as `deviate` and `lapse`. A
failing or unchecked outcome is filed and reported exactly as such — unmet
is unmet, never rounded up — feeding `devague summary`'s Delivery Claims
table, where evidence strength (coverage/fidelity/execution/sensitivity) is
the confidence vocabulary and approved lapses still cap it. Motivating
record, cited verbatim from issue `agentculture/devague#97`: "Four graders
failed in that cycle... Every one was found by reading data afterwards; none
by a test failing." The design traces to issue `agentculture/devague#107`,
"Suggestion: behavioral validation and a derived current spec," which
proposed behavior as the primary contract, four evidence types, the
strength ladder, and the current spec as a projection of a behavior ledger.
The behavioral-test convention for consuming repos is either a pytest
marker (e.g. `@pytest.mark.behavioral`) or a dedicated folder (e.g.
`tests/behavioral/` or `behavioral-tests/`) — both defined in the skill. The
exact `oblige` / `evidence` / `delta` CLI surface ships separately; this
leg's docs are written against those verb names with minimal command
examples so reconciliation stays cheap. `README.md`, this file,
`docs/skills.md`, `docs/skill-sources.md`, and `docs/spec-contract.md` are
swept to the **eight-leg flow** — `scope` → `think` → `challenge` →
`spec-to-plan` → `assign-to-workforce` → `deviate` → `validate-delivery` →
`summarize-delivery`.

**The Reasoning Degradation Ledger lands (0.22.0, issue #97).** A new flat
verb, **`devague lapse "<what>" --code <code> [--skipped "<check>"] [--ref
REF ...] [--origin user|llm] [--json]`** (plus `--list [--json]` and
`--confirm <lN>` / `--reject <lN>`), files a reasoning-degradation lapse — a
moment an assumption was silently substituted for a check — as a
first-class, **append-only** ledger entry on the frame (`Frame.lapses` /
`LapseRecord`, `SCHEMA_VERSION` 4→5): six starting codes
(`assumption-for-measurement`, `grader-unverified`, `control-absent`,
`n-below-claim`, `instrument-changed-mid-series`, `provenance-missing`)
validated fail-closed at the *filing* path (`Frame.add_lapse`), deliberately
**not** in `__post_init__` — a code retired after a dogfood cycle must not
brick a frame that already filed it, unlike every other kind vocabulary in
this codebase, which validates (and therefore re-validates on load) in
`__post_init__`. Filing mirrors `deviate`: `llm`-origin lands `proposed`
(needs a human `--confirm`/`--reject`), `user`-origin auto-approves — but
adjudication is the *only* mutation a filed lapse ever gets; there is no
amend and no delete, a deliberate asymmetry with `scope --amend`, since an
editable lapse would re-enable the written-late-is-written-flattering
failure the ledger exists to prevent. The ledger **never gates**: no
convergence blocker, warning, or parked item on either engine ever names a
lapse, in any status (pinned by `tests/test_convergence.py` and
`tests/test_plan_convergence.py`). It renders in `devague show` (every
lapse, any status) and as confidence evidence in `devague summary`'s
Delivery Claims section (approved entries only; a proposed one renders as
visibly pending; a rejected one is omitted); the exported spec-md never
grows a lapse section at all, since `export` overwrites the same dated file
on every re-export and process history must not rewrite the
what-to-build artifact. The motivating evidence, cited verbatim from issue
`agentculture/devague#97`: the embodiment repo's 21-task, 7-wave
`/scope`→`/summarize-delivery` fan-out produced its most useful artifact — a
corrections record — reconstructed only at the end, from memory; four
graders failed in that cycle (three inside a single task), every one found
by reading data
afterwards and none by a test failing, and one nearly shipped a false
safety claim; at least one of those transitions was recoverable only
because raw data happened to be committed, not because anything guaranteed
it would be.

**The fifteen-issue backlog sweep (0.21.0, issues #48 #49 #52 #79 #82 #83 #84 #85 #86 #87 #88 #90 #91 #92 #93).**
One workforce fan-out (the
`issue-backlog-sweep` plan, t1–t19) closing fifteen issues, three of which
downstream repos were already working around by hand. New moves:
**`devague interrogate <cN> --resolve <qN> [--decision]`** — nothing ever set
`HardQuestion.resolved`, so one blocking question deadlocked `converge`
*permanently* and two repos hand-edited frame JSON to escape (#48/#52);
**`devague amend <cN> [--text] [--kind] [--reason]`** — correct a claim
keeping its id, honesty conditions, hard questions, `instruction`, and
inbound `scope --seeds` refs, recording the superseded pair on a new
`Claim.revisions` trail and flipping a confirmed claim back to `proposed`
(#84); **`devague scope --amend <sN> --finding`** (in-place finding
correction — no revision trail, a deliberate asymmetry); **`devague plan
defer <target-id> --reason` / `--undo`** — a documented per-target exclusion
from the coverage gate so a milestone-scoped plan can converge at all, with a
`## Deferred targets` section in the export (#85); and **`devague plan risk
--amend <rN> --text`** (#84). Sharpened: `reject <cN>` cascades onto its
honesty conditions and unresolved hard questions (`--json` gains `cascaded`),
and `converge` stops warning about *rejected* assumptions (#83); `plan
confirm` / `plan reject` are multi-id and transactional, and plan-group
argument errors point at `devague plan explain <move>` (#86); `plan task
--dep` / `plan depend --on` refuse self-deps and unknown ids at creation
(#86); `plan cover` / `plan task --covers` validate against targets re-derived
from the **live** frame, so a target the frame grew after seeding is coverable
immediately (#90); `devague summary` scopes Planned Work / Actual Delivery to
**confirmed** tasks plus one rejected-count line (#88). Export fidelity: all
four park kinds render under `## Open parks`, resolved hard questions carry a
`(resolved)` marker, hard questions on rejected claims are excluded, and a
scope seed citing a rejected claim renders `(rejected)` (#93, #49). New
`render/_md_safety.md_safe_text()` escapes every verbatim render site
(`spec_md` / `plan_md` / `summary_md`) — underscore/dunder identifiers wrap in
code spans, existing code spans pass through, idempotent, presentational only
(#87). New read-only `devague/contested.py` joins confirmed claims to approved
deviations' `--affects` across the plan-slug boundary: re-exported specs and
`show` / `status` mark a claim contested by `dN` — the spec is *not* rewritten,
it points forward to the ledger — and it fails open on a missing/corrupt/newer
store (#92). Both `SCHEMA_VERSION` and `PLAN_SCHEMA_VERSION` are now **4**, and
both stores check the declared version against the **raw** dict before parsing.
Skills: `/scope` fans read-only exploration out to subagents — 4 or fewer
surfaces inline, 5 or more fan out, defaulting to **sonnet**; subagents explore
and report, the main agent runs every move (#79/#91) — and
`assign-to-workforce` gains **`split-plan --write`**, a durable gate-2 artifact
at `docs/plans/<created-date>-<slug>-split.md` whose owner/model annotations
survive regeneration (#82).

**The challenge skill lands — the seventh leg (0.19.0, #73).** New seventh
origin skill **`/challenge`** (`.claude/skills/challenge/SKILL.md`) — a
risk-scaled blind-spot discovery pass that runs after `/think` exports and
before `devague plan new`, pressure-testing the converged, exported frame
through structured lenses. Method-only: no script, no new CLI verb, no new
engine (#20) — every finding routes back through the existing deterministic
moves (`capture`, `interrogate`, `park`, …) as proposed-only content for the
human to adjudicate, and a reopened frame reconverges and re-exports before
the plan leg proceeds. A clean pass records the examined surfaces and
residual uncertainty via existing moves (`devague scope` entries, `park`,
`plan risk`) — never a claim that there are no unknown unknowns.
`devague learn skills` now teaches all **seven** operator skills then extant,
in flow order; `README.md`, this file, `docs/skills.md`, and
`docs/skill-sources.md` are swept to the then-current flow — `scope` → `think` → `challenge` →
`spec-to-plan` → `assign-to-workforce` → `deviate` → `summarize-delivery`.

**The execution seam and deviate (0.18.0, #53 esd t1–t11).** The flow gains a
**sixth leg** — **`deviate`** — plus the read-only "end state" that closes the
loop between a confirmed plan and what the workforce actually produces mid-run.
New CLI surface: `devague plan deliverables [--json]` (a never-refusing preview
of the plan's confirmed announcement/after-state/success-signal claims,
terminal-task acceptance criteria, and surviving open items, #70);
`devague plan depend <tN> --on <tM> --remove` and a new `devague plan amend`
move (edit a task's summary and/or acceptance criteria by index, #68), both
joining `instruct` in flipping a CONFIRMED task back to `proposed` and now
echoing that flip to stdout on every demoting move (#67 hardening);
`devague deviate` (`--list [--json]`, `--confirm`/`--reject`) recording
first-class, append-only deviation records in a new delivery store,
`.devague/deliveries/<plan-slug>.json`; and `devague summary [--pr] [--json]`,
a render-only eight-section delivery-summary skeleton built from state alone.
New sixth origin skill **`/deviate`** — stop an in-flight
`/assign-to-workforce` run the moment execution must diverge from the
confirmed plan, get explicit human approval, and record it via
`devague deviate` before resuming; it uses the existing implementation-split-plan
gate (gate 2), not a new fourth gate. `assign-to-workforce`'s split-plan now
renders a four-column Wave/Task/Model/Task-summary table with real model
tokens and a trailing End state section quoting `devague plan deliverables`
verbatim (#69, #70); `summarize-delivery` now starts from the `devague summary`
skeleton and quotes approved deviations by `dN` id instead of reconstructing
drift from memory. `culture.yaml` reverts `backend` to `claude`, the mesh
standard, now that `agex-cli#46` is closed (#66). Docs (this file, `README.md`,
`docs/skills.md`) now name the then-current six-leg flow — `scope` → `think` →
`spec-to-plan` → `assign-to-workforce` → `deviate` →
`summarize-delivery` — and the two audiences it serves: operators (the main
agent driving the CLI) and the humans who own the go/no-go and final-PR
gates.

**Operator kit carries the sharper method + new `/scope` skill (0.15.0).** The
sharper end-to-end method spec+plan merged in #53 (0.14.1: docs + state only);
this release carries its *method-level* half into the operator skills. New
fourth origin skill **`scope`** (idea→scope, the optional pre-frame exploration
leg — method-only: no script, no CLI verb; findings land via existing moves with
provenance-citing claims). `think` gained scope-first guidance, export hygiene
(`new --title`, backtick angle-bracket tokens — no retitle/edit move exists),
and the `question`→resolve→`decision`-claim loop; `spec-to-plan` gained the
acceptance-criteria-as-instruction-contract coaching and the single-id `confirm`
note; `assign-to-workforce` now requires **verbatim** task briefs (no operator
paraphrasing). The CLI is unchanged — `devague scope`, per-item `--instruction`,
sharper renderers/gates are the #53 build plan (t1–t14), still unimplemented;
`devague learn skills` still teaches the three CLI-driving skills until t10/t11.

**Skills re-synced to guildmaster + two new skills (0.13.0, #38).** The vendored
canonical kit now sources from `guildmaster` (the supplier role moved from
`steward` at the 2026-05-24 cutover): `cicd` / `communicate` re-synced (the `cicd`
`portability-lint.sh` `xargs -r` divergence is preserved), the other four are
content-unchanged with the ledger repointed, and two new skills were vendored —
`agent-config` (read-only agent-config inventory) and `pypi-maintainer` (devague
publishes to PyPI/TestPyPI). devague's three **origin** skills (`think` /
`spec-to-plan` / `assign-to-workforce`) were **not** re-vendored back — devague is
their upstream — but each gained `type: command` at the source. Provenance:
`docs/skill-sources.md`.

**`learn` now teaches skill authoring (0.12.0, #34).** `devague learn` gained an
optional topic arg: `devague learn skills` (and `skills:all` / `skills:<name>`)
emits a self-contained recipe for authoring the three operator skills (`think` /
`spec-to-plan` / `assign-to-workforce`) in any runtime — file layout, frontmatter
(incl. the `type:` gotcha for culture backends), the portable resolver pattern,
the skill↔devague contract, and the consent + no-clobber rules. It is framed as
instructions the *agent* follows: the CLI never writes skill files (it stays
deterministic and non-orchestrating, #20); the agent creates them with user
consent. Bare `devague learn` appends the condensed authoring section. Canonical
long-form guide: `docs/skills.md`.

**`status` internalised into the CLI (0.11.0, #30).** The next-move helper that
used to live as embedded Python inside the `think` / `spec-to-plan` skill
wrappers is now a first-class, read-only CLI verb — `devague status` and
`devague plan status` (sharing `devague/cli/_status.py`). Both compose
`list` + `converge` and report the verdict, gaps, and recommended next move
(`--json` too); neither mutates state. This removed the wrappers' `mktemp` +
embedded-stdout hazards (Qodo via steward); the trio's remaining `mktemp` (in
`assign-to-workforce.sh`, whose orchestration presentation deliberately stays
out of the deterministic CLI) gained a cleanup trap.

**Human Review Loop landed (0.6.0, #17).** `devague review` (+ `--json`) lists
every proposed claim + honesty condition with ids — un-gated by convergence,
never mutating state — and writes a non-authoritative artifact to
`.devague/reviews/<slug>.md`. `confirm` / `reject` now take multiple ids in one
**transactional** call; `confirm --from-review <file>` applies an edited review
artifact (`pending` lines are never auto-confirmed). `devague question` records
pending decisions in `.devague/questions/<slug>.md`. devague manages
`.gitignore` so `reviews/` and `questions/` stay uncommitted working state.

**Spec contract landed (#5).** The entity model is documented in
`docs/spec-contract.md` (the source of truth for kinds, the `(state × origin)`
vocabulary, the structured convergence result, and the per-move I/O contract).
Claim kinds now include `non_goal` / `requirement` / `assumption` / `decision`;
every frame carries a fail-closed `schema_version`; and `converge --json` emits
the structured `{ready_for_spec, blockers, warnings, parked_items,
required_next_moves}` (plans: `ready_for_plan`) — a hard break from the old
`{passed, missing}`.

**Spec→plan engine landed (v0.4.0).** Both deterministic engines now ship.
The **frame engine** (idea→spec) — Frame domain model, JSON store, convergence
gate, renderer registry, and the flat moves `new` / `capture` / `interrogate` /
`confirm` / `reject` / `review` / `question` / `park` / `converge` / `export` /
`status` / `show` / `list` / `learn` / `explain`. The **plan engine** (spec→plan)
is its structural peer:
`devague/plan.py`, `plan_convergence.py`, `plan_store.py`, `render/plan_md.py`,
and the nested group `devague plan <move>` (`new` / `task` / `accept` / `depend`
/ `cover` / `confirm` / `reject` / `risk` / `converge` / `export` / `waves` /
`status` / `show` / `list` / `learn` / `explain`). The two operator skills are `/think` (idea→spec,
renamed from `/devague`) and `/spec-to-plan` (spec→plan). Coverage ≥ 95 %; all
linters pass. Run `git ls-files` to see the real surface.

Real commands: `uv sync`; `uv run devague --version`; `python -m devague`;
`uv run pytest -n auto` (single test: `uv run pytest tests/<file>::<node> -v`);
`uv run flake8 --config=.flake8 devague/ tests/`; `uv run black devague/ tests/`;
`uv run isort --profile black devague/ tests/`; `markdownlint-cli2 "**/*.md"`.

## Working-backwards method

The agent drives the **deterministic** CLI — no LLM calls inside the CLI
itself. The workflow:

1. `devague new "<announcement>"` — the announcement-first entry point. The
   canonical first question is *"What's the announcement?"* ("Pretend this
   shipped successfully — what would you announce to users, teammates, or
   yourself?"). Creates a Frame seeded with the announcement claim
   (auto-confirmed, since it comes from the user). `devague learn` documents the
   full ten-stage guided sequence plus the always-on **operating rules** (the
   anti-fabrication contract); the portable, agent-agnostic version of that
   contract lives in `docs/llm-guidance.md` (#19).
2. `devague capture --kind <kind> "<text>"` — add claims; LLM-proposed ones
   (`--origin llm`) land as `proposed` and require explicit user `confirm`.
   Correct a claim in place with `devague amend <cN> [--text] [--kind]
   [--reason]` (#84) — it keeps the id, so honesty conditions, hard questions,
   `instruction`, and inbound `scope --seeds` refs all stay pointed at
   something real; the superseded `(text, kind)` pair lands on
   `Claim.revisions` and a confirmed claim flips back to `proposed`.
3. `devague interrogate <claim-id>` — attach honesty conditions and hard
   questions; honesty conditions from the LLM are also `proposed`. A blocking
   hard question is closed out with `devague interrogate <cN> --resolve <qN>
   --decision "<text>"` (#48/#52) — a USER decision, the claim-level twin of
   `park --resolve`; without it a blocking question deadlocks `converge`
   forever.
4. `devague confirm <id>` / `reject` / `park` — **all honesty conditions
   routed through the user**; the agent must not auto-confirm LLM proposals.
   Rejecting a claim cascades onto its still-live honesty conditions and
   unresolved hard questions, echoing `(also rejected: h3, q1)` (#83).
5. `devague scope "<surface>" --finding "<text>" [--seeds <cN|qN> …]` — record
   pre-frame exploration as first-class provenance; `--seeds` takes claim ids
   *or* claim-attached hard-question ids (#84), and `scope --amend <sN>
   --finding` corrects a finding in place.
6. `devague converge` — evaluates the convergence gate; lists remaining gaps.
7. `devague export` — only succeeds after `converge` passes; writes a
   buildable spec-md to `docs/specs/`. Verbatim claim text is markdown-escaped
   at render time (`render/_md_safety.md_safe_text`, #87) — presentational
   only, the stored JSON is untouched. A confirmed claim named by an approved
   deviation's `--affects` renders a `contested by <dN>` marker (#92): the
   spec is never rewritten, it points forward to the deviation ledger.

Full design: `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`.

## Spec→plan method (the forward leg)

The **plan engine** is the structural peer of the frame engine — same chassis,
same anti-fabrication rules, no LLM inside the CLI. It is namespaced under the
`devague plan` subcommand group (the *skill* is `/spec-to-plan`; the CLI verb is
`plan` — they intentionally differ, mirroring how `/think` drives the flat
verbs). The workflow:

1. `devague plan new --frame <slug>` — seed a plan from a **converged** frame.
   Derives **coverage targets** (the frame's confirmed claims + honesty
   conditions). Refuses an unconverged frame; refuses to clobber an existing plan.
2. `devague plan task "<summary>" [--accept … --dep … --covers … --origin]` —
   add tasks; `--origin llm` lands `proposed` (user must `confirm` — and
   `plan confirm` / `plan reject` take many ids in one transactional call, #86).
   Refine with `accept` / `depend` (or `depend --remove` to cut an edge, #68) /
   `cover` / `instruct` / `amend` (edit a task's summary and/or replace/remove
   acceptance criteria by index, #68). Amending or demoting a CONFIRMED task
   flips it back to `proposed` and echoes that flip to stdout (#67). `--dep` /
   `depend --on` refuse a self-dependency or an unknown task id at creation
   (#86); `cover` / `--covers` validate against targets re-derived from the
   **live** frame, so a target the frame grew after seeding is coverable
   straight away (#90).
3. `devague plan risk "<text>" --kind <kind>` — park a genuine unknown as a
   first-class plan risk instead of guessing (`--resolve` closes one out;
   `--amend <rN> --text` corrects a stale one in place, #84).
4. `devague plan defer <target-id> --reason "<text>"` — deliberately exclude a
   coverage target from *this* plan's gate when it genuinely belongs to a later
   one (`--undo` reverses it, #85). A deferred target drops out of the gate,
   surfaces in `parked_items` labeled `deferred:`, and renders under
   `## Deferred targets` in the export. This is the honest alternative to
   faking coverage — never write a task that merely names a target.
5. `devague plan converge` — re-evaluates the gate **against the live frame**
   (catches frame drift); lists gaps. A plan converges when every target is
   covered by a confirmed task **or deliberately deferred**, every confirmed
   task has acceptance criteria, the dependency graph is acyclic, and no
   blocking risk remains.
6. `devague plan export` — only after `converge` passes; writes a buildable
   plan-md (topologically ordered) to `docs/plans/<created-date>-<slug>.md`.
7. `devague plan waves [--json]` — emit the plan's dependency graph as
   deterministic **scheduling metadata** (`{plan, waves}`): ordered batches of
   task ids that an external operator *could* fan out. Read-only,
   convergence-agnostic (works on an in-progress plan), and explicitly **not
   orchestration** — Devague describes the graph; it does not spawn subagents,
   manage worktrees, mark tasks done, or pick a backend (#20). A cyclic or
   dangling graph is refused via the plan-convergence dependency blockers.
8. `devague plan deliverables [--json]` — a read-only "end state" preview:
   the plan's confirmed announcement/after-state/success-signal claims
   verbatim from its live source frame, every terminal task (an active task no
   other active task depends on) with its acceptance criteria, and the
   surviving open items. Never refuses — shows a not-converged banner instead
   of gating, since previewing the end state is useful before convergence
   too (#70).

Both `devague export` and `devague plan export` prefix the written file with the
frame/plan creation date (`<YYYY-MM-DD>-<slug>.md`, #12), so re-exporting an
unchanged artifact overwrites the same file rather than spawning a duplicate.

Full design: `docs/superpowers/specs/2026-05-23-devague-spec-to-plan-design.md`.

## Subagent-driven implementation (assign-to-workforce)

**Converged plans execute in parallel via a cited `assign-to-workforce` skill**
that fans out independent tasks to subagents in isolated git worktrees, keeping
the devague CLI deterministic and non-orchestrating (#20).

### The three human gates

1. **Spec gate**: the exported frame/spec.
2. **Implementation split plan gate**: the plan tasks map, per-task subagent +
   model assignment, and the go/no-go decision on assigning the plan to the
   workforce. `split-plan --write` persists it as a durable artifact at
   `docs/plans/<created-date>-<slug>-split.md` (#82) — the peer of the
   exported spec and plan-md, which gate 2 previously lacked; hand-edited
   `Owner` / `Model` cells are read back and survive regeneration. A mid-run
   deviation (recorded via `devague deviate` and the cited `/deviate` skill)
   is **not** a fourth standing gate — it is the human owner of this gate
   approving an amendment to it in-flight.
3. **Final PR gate**: human code review of the merged result.

### Worktree contention safety

Each subagent runs in an isolated git worktree — one worktree per task per wave.
Same-file overlaps between tasks (which the dependency graph does not
guarantee to exclude) surface as merge conflicts at reconcile time, never as
live races. The main/operating agent reconciles each merge.

### Where worktrees live: `.worktrees.<repo-name>` (mandatory)

**Every worktree a fan-out creates goes under one repo-owned root beside the
repo directory** — `<parent-of-repo>/.worktrees.<repo-name>/agent-<task-id>`.
For this repo that is `../.worktrees.devague/`. Resolve it, never hardcode it:

```bash
repo_root=$(git rev-parse --show-toplevel)
wt_root="$(dirname "$repo_root")/.worktrees.$(basename "$repo_root")"
git worktree add "$wt_root/agent-<task-id>" -b agent/<task-id>
```

Two paths are **forbidden**, and each was in use here before this convention:

- **A shared `../worktrees/`** — in a multi-repo parent like `~/git/`, that
  directory belongs to nobody, so it reads as scratch space another agent or
  human may delete while your wave is live. Worse, task ids restart at `t1` in
  every repo and every plan, so `../worktrees/agent-t1` from two concurrent
  fan-outs is literally the same directory. The repo-named root makes
  ownership visible and collisions impossible.
- **Anything inside the repo** (`.worktrees/`, `.claude/worktrees/`) — N full
  checkouts inside the tree you are about to commit means `git add -A` sweeps
  them into the PR and `git clean -fdx` destroys live agent work.

Clean up with `git worktree remove "$wt_root/agent-<task-id>"` per merged task.
Never `rm -rf` the root itself and never touch another repo's root — a
concurrent fan-out may be running inside it.

### Main-agent TDD merge gate (no human per task)

The main agent gates each subagent's worktree merge with test-driven development:
the task's tests must pass **before** the merge (validate the subagent's work)
and **after** the merge (catch conflicts). No human is in the per-task loop.
Per-task acceptance is uncommitted working state, mirroring the Human Review Loop
(#17).

### The boundary: devague stays deterministic

The devague CLI never spawns subagents, manages worktrees, marks tasks done, or
picks a backend (#20). Orchestration lives in the cited `assign-to-workforce`
skill and this convention, not in new CLI and not in a CI/CD runner.

### Roles

- **Operator/main agent**: drives execution of waves and merges each subagent's
  worktree (gated by TDD); owns the implementation split plan.
- **Per-task subagents**: may be simpler or cheaper models; each builds a single
  task test-first within its worktree. The `/scope` leg uses the same idea
  read-only: 5 or more candidate surfaces fan out one exploration subagent per
  surface, defaulting to **sonnet** — and those subagents *never* run a
  `devague` move, so provenance stays with the main agent (#79/#91).
- **Human**: owns the three gates (spec, implementation split plan, final PR),
  including approving mid-run deviations against gate 2 via `/deviate`.

### What consumes the scheduling metadata

`devague plan waves [--json]` emits the scheduling metadata (`{plan, waves,
tasks}`); the `assign-to-workforce` skill's `split-plan` subcommand is the
consumer — it renders the implementation split plan (task map, per-task
agent/model proposal, go/no-go) and a trailing End state section quoting
`devague plan deliverables` verbatim (#70), optionally persists all of it plus
an owner/model annotation table to
`docs/plans/<created-date>-<slug>-split.md` with `--write` (#82), then
performs the fan-out itself. The same `waves --json` payload is the **single
source** for every per-task brief — no `plan show --json` or exported plan-md
needed alongside it. `devague deviate` and the cited `/deviate` skill are the consumer for
mid-run departures from that plan; `devague summary` and `/summarize-delivery`
are the consumer for what actually shipped once the run ends. Devague itself
never orchestrates any of this (#20) — its use across all four is shared via
`devague learn`.

## Project intent

**devague** — an AgentCulture agent that turns a vague feature idea into a
**buildable spec**, then that spec into a **buildable plan**, by working
backwards then forwards. The spec method: start from the announcement ("pretend
it shipped — what would you announce?"), build an **Announcement Frame** by
capturing and classifying claims, pressure-testing them with honesty conditions
and hard questions, parking unresolved uncertainty as first-class "open
vagueness," and only exporting a buildable spec once the frame *converges*. The
plan method: seed a plan from that converged frame and converge it on coverage,
acceptance criteria, and an acyclic dependency order before exporting a plan.
The operator skills cover the **eight legs** in flow order: **`/scope`**
(idea→explored scope, the optional opening leg), **`/think`** (idea→spec),
**`/challenge`** (a risk-scaled blind-spot discovery pass between /think and
/spec-to-plan, adjudicated inside the existing spec gate), **`/spec-to-plan`**
(spec→plan), **`/assign-to-workforce`** (plan→parallel implementation),
**`/deviate`** (the execution-time leg — stop an in-flight fan-out the moment
it must diverge from the confirmed plan, get explicit human approval, and
record the divergence before resuming), **`/validate-delivery`** (the
execution-to-evidence leg — run the plan's behavioral tests agent-side once
waves merge, and file evidence and behavioral deltas via the CLI; unmet is
unmet), and **`/summarize-delivery`**
(execution→a committed accountability artifact, the delivery-side closure
leg); the product/CLI they drive is **`devague`**. The skills are written for
two audiences: **operators** — the main agent driving the deterministic CLI
move by move — and the **humans** who own the go/no-go decision on the
implementation split plan (gate 2, including any deviation against it) and
the final PR review (gate 3).

This is a **state machine over claims, honesty conditions, open vagueness, and
convergence** driven by LLM-chosen moves — not a linear wizard. The CLI is
deterministic and fully unit-testable; the resident Claude agent decides the
next move. See `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`
for the full design.

devague is its own method — not a wrapper around `superpowers:brainstorming`
or `superpowers:writing-plans`, though the exported spec-md artifact can feed
directly into those workflows.

## Ecosystem context

devague belongs to the **AgentCulture** family (Apache-2.0, `Copyright 2026
AgentCulture`); the GitHub remote is `origin/main` and lives under
`github.com/agentculture/devague`. Its closest structural analogs in this
workspace are the small Python CLI agents `agtag`, `appsec`, `seer-cli`, and
`steward` — when in doubt about how something *should* look here, read theirs.

`guildmaster` is the source of truth for shared skills and the cross-repo way of
working in AgentCulture (the supplier role moved from `steward` at the 2026-05-24
steward→guildmaster cutover; `steward` is still a sibling but no longer
broadcasts). Vendored skills are cited, not imported (cite-don't-import): copy
from `../guildmaster/.claude/skills/<name>/` and track provenance in
`docs/skill-sources.md`. The exception is devague's own `scope` / `think` /
`challenge` / `spec-to-plan` / `assign-to-workforce` / `deviate` /
`validate-delivery` / `summarize-delivery` — devague is their origin, so
guildmaster re-broadcasts them *from* here; never re-vendor them back.

## Stack expectations (when code lands)

The committed `.gitignore` is the standard Python template, and every sibling
agent is **uv**-based Python (`requires-python >=3.12`, hatchling build). Match
that unless the user asks otherwise. The established sibling shape is:

- A top-level package directory (`devague/`) with `__init__.py` and `__main__.py`
  (so `python -m devague` works).
- An argparse **CLI chassis** under `devague/cli/`: `__init__.py` with `main()`
  (exposed as the `devague` console script), plus `_errors.py` (a
  `DevagueError` + exit-code policy) and `_output.py` (strict stdout/stderr
  split, `--json` support).
- `devague/cli/_commands/` — one module per verb, each exposing `register()`.
  Frame verbs: `new`, `capture`, `amend`, `interrogate`, `confirm`, `reject`,
  `review`, `question`, `park`, `scope`, `lapse` (`--list`, `--confirm`,
  `--reject`; the Reasoning Degradation Ledger, #97), `converge`, `export`,
  `status`, `show`, `list`, `learn`, `explain` (`status` shares
  `cli/_status.py` with the plan engine), plus two more flat verbs, `deviate`
  (`--list`, `--confirm`, `--reject`) and `summary` (`--pr`), backed by
  `devague/delivery.py` + `devague/delivery_store.py`. The plan engine adds
  one module, `_commands/plan.py`, registering the nested `plan` subcommand
  group — `new` / `task` / `instruct` / `accept` / `amend` / `depend` (plus
  `--remove`) / `cover` / `defer` / `confirm` / `reject` / `risk` / `converge`
  / `export` / `waves` / `deliverables` / `status` / `show` / `list` / `learn`
  / `explain`.
- Frame engine: `devague/frame.py`, `convergence.py`, `store.py`,
  `render/{spec_md,frame_md}.py`. Plan engine (its peer): `devague/plan.py`,
  `plan_convergence.py`, `plan_store.py`, `render/plan_md.py`, `cli/_plans.py`.
  Delivery peer: `devague/delivery.py`, `delivery_store.py`,
  `render/summary_md.py`. Cross-cutting: `devague/contested.py` (the read-only
  claim↔deviation join, #92) and `render/_md_safety.py` (render-time markdown
  escaping, #87) — both pure and read-only; neither ever mutates a store.
- `pyproject.toml`, `CHANGELOG.md`, `tests/`, `docs/`, `culture.yaml`,
  `sonar-project.properties`, `uv.lock`.

Commands (verify against the real `pyproject.toml`): `uv sync`;
`uv run devague --version`; `uv run pytest -n auto`
(single test: `uv run pytest tests/<file>::<node> -v`);
`uv run flake8 --config=.flake8 devague/ tests/`; `uv run black devague/ tests/`;
`uv run isort --profile black devague/ tests/`;
`bandit -r devague/`; `pylint devague/`; `markdownlint-cli2 "**/*.md"`.

## Conventions worth preserving

- **Version bump per PR.** Sibling repos bump the version in `pyproject.toml`
  (CI's `version-check` blocks merge if it matches `main`) and prepend a
  `CHANGELOG.md` entry. Adopt the vendored `version-bump` skill once this repo
  grows a `pyproject.toml`.
- **PRs via the `cicd` skill / `agex pr`.** Sibling repos drive PRs through the
  steward-origin `cicd` skill (delegating to the `agex pr` CLI). Use it here once
  vendored rather than hand-rolling `gh pr` flows.
- **Signing online posts.** PR descriptions and issue/PR comments authored on the
  user's behalf are signed so it's clear they're AI-authored: `- devague (Claude)`
  once a `culture.yaml` (with the repo nick) exists, otherwise `- Claude`. Inside
  the `cicd` flow, the scripts append the signature — don't sign the body manually
  there.

## Finishing a branch: default to a PR, never pause for the menu

When work on a branch is complete and tests pass, **proceed directly to pushing
the branch and opening a Pull Request** — do not present an interactive "what
would you like to do?" menu and wait for a choice. This overrides the
Superpowers `finishing-a-development-branch` skill, whose default is to stop and
ask the user to pick among *merge locally / create PR / keep as-is / discard*.
That pause breaks the flow. In devague — and in every AgentCulture sibling —
the standing choice is **always "push and open a Pull Request,"** done via the
`cicd` skill (`agex pr open`). Merge-locally / keep-as-is / discard happen only
on explicit user request. (Standing rule carried by the `cicd` skill since
steward 0.18.0.)

## What not to invent

Do not fabricate commands, module layouts, or test invocations — here or in
conversation. Until real code exists, answer "how do I run X" with "X doesn't
exist yet — want me to scaffold it?" (modeled on `agtag`/`appsec`) rather than a
guessed command.
