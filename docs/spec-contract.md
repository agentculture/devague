# The Devague spec contract

The durable, reloadable artifact model that turns a vague idea into a
claim-based, pressure-tested, buildable spec — and the moves that operate on it.
This document is the **source of truth** for the entity model, the vocabulary,
the convergence verdict, and the per-move I/O contract (issue #5) — across all
three engines: the **Frame** (idea→spec), its structural peer the **Plan**
(spec→plan), and the Plan's execution-side companion, the **delivery ledger**
(`devague deviate` / `devague summary` — see *The delivery peer* below).

The CLI is deterministic and move-driven: the assisting LLM chooses moves, the
CLI tracks state. Every move accepts and emits JSON (`--json`), with a strict
`stdout` (results) / `stderr` (diagnostics) split, so an LLM can drive devague
without guessing internal state. All operations run fully offline against local
`.devague/` state.

For the portable, runtime-agnostic contract on *how* an assisting model should
operate Devague — the move-driven mental model and the anti-fabrication rules —
see [`llm-guidance.md`](llm-guidance.md) (also surfaced in `devague learn`).

## Versioning

Every frame carries an integer `schema_version` (currently `4`). It is written
on save and checked on load: a frame whose `schema_version` is newer than this
devague supports is rejected, fail-closed, with an actionable error. A 0.4.0
frame predates the field and loads as the current schema, so existing frames
keep working.

The check runs against the **raw** loaded dict, *before* the domain object is
constructed (issue-backlog-sweep t2). Constructing first would surface a
genuinely newer file as an opaque `TypeError` from a nested dataclass that
does not recognise a key yet, instead of the intended fail-closed
`IncompatibleSchemaError` with its upgrade hint. For the same reason, nested
`HardQuestion` / `Vagueness` loading is tolerant of unknown keys rather than
splatting the raw dict. The plan store carries the identical guard.

> **v4 (issue-backlog-sweep t4/t6).** Bumped to add `HardQuestion.resolution`
> (#48/#52) and `Claim.revisions` (#84) — see *HardQuestion* and *Claim* under
> Entities. A v3 frame predates both: it loads with `resolution` defaulted to
> `""` and `revisions` to `[]`, so no question loads as answered and no claim
> loads with a fabricated revision trail.
>
> **v3 (resolve-parked-vagueness t1).** Bumped to add `Vagueness.resolved`,
> `Vagueness.resolution`, and `Vagueness.resolution_claim_id` — see *Vagueness*
> under Entities. A v2 frame predates all three: it loads with `resolved`
> defaulted to `False`, `resolution` to `""`, and `resolution_claim_id` to
> `None` — every pre-existing parked item loads as still-open, never silently
> resolved.
>
> **v2 (#53 t1).** Bumped to add `Frame.scope_entries` and an `instruction`
> field on `Claim` and `HonestyCondition` — see *ScopeEntry* under Entities and
> the *Instructions* section below. A v1 frame predates both: it loads with no
> scope entries and every `instruction` defaulted to `""` (empty means "no
> instruction," never fabricated to fill the gap).
>
> **Migration note.** Before this contract, devague (0.4.0) shipped no committed
> contract document and `converge --json` emitted `{passed, missing}`. This
> contract supersedes that with the structured convergence result below; the old
> keys are gone (a deliberate hard break).

## Entities

### Frame

A feature-framing workspace.

- `slug` — filesystem-safe id (lowercase, digits, hyphens).
- `title` — the announcement headline.
- `schema_version` — integer; see Versioning.
- `status` — `drafting` | `converged` | `exported`.
- `created`, `updated` — ISO-8601 UTC timestamps, stamped on save.
- `claims` — list of Claim.
- `open_vagueness` — list of Vagueness.
- `scope_entries` — list of ScopeEntry (v2, #53 t1; see below).

### Claim

A discrete statement that may become part of the spec.

- `id` — `c1`, `c2`, …
- `kind` — see Claim kinds.
- `text` — the statement.
- `origin` — `user` | `llm` (who proposed it).
- `status` — `proposed` | `confirmed` | `rejected`.
- `honesty_conditions` — list of HonestyCondition.
- `hard_questions` — list of HardQuestion.
- `links` — related claim ids.
- `instruction` — optional verbatim text: how to verify or implement this
  claim; `""` means none (v2, #53 t1). See *Instructions* below.
- `revisions` — list of ClaimRevision: the `(text, kind)` pairs this claim has
  superseded, oldest first (v4, #84). Empty for a claim that has never been
  amended — the common case, and every claim predating the field. Written only
  by `Frame.amend_claim`.

### ClaimRevision

A superseded `(text, kind)` pair, recorded when a claim is amended (v4, #84).
Deliberately a *lightweight* evidence marker, not an audit log: it captures
only the two fields `amend` can change plus an optional operator-authored
reason, and carries no timestamp or actor (no other Frame entity does either).

- `text` — the claim text that was replaced.
- `kind` — the claim kind that was replaced.
- `reason` — optional operator note on why it was amended; `""` means none.

### HonestyCondition

What must be true for a claim to be honest.

- `id` — `h1`, `h2`, …
- `text` — the condition.
- `status` — `proposed` | `confirmed` | `rejected`.
- `instruction` — optional verbatim text: how to verify this condition holds;
  `""` means none (v2, #53 t1). See *Instructions* below.

### HardQuestion

An unresolved question against a claim.

- `id` — `q1`, `q2`, …
- `text` — the question.
- `resolved` — boolean; `False` until closed via `Frame.resolve_hard_question`
  (v4, issue-backlog-sweep t4). That is the **only** mutator — before it
  shipped, nothing in the codebase ever set this field, so a blocking question
  deadlocked `converge` permanently (#48/#52).
- `resolution` — the optional free-text answer recorded with `--decision`;
  `""` means none (v4). Unlike `park --resolve`'s required `--decision`, the
  note is optional here; the resolution *state* is what clears the gate.
- `blocking` — boolean; a blocking, unresolved question holds back convergence
  unless its parent claim has been `rejected` (a claim decided against makes
  its open questions moot — a pure status check, not a resolution, so a
  rejected claim's question can still be resolved later without erroring).

Two independent counters mint `qN` ids — claim-attached hard questions (here)
and the separate durable `.devague/questions/<slug>.md` artifact driven by
`devague question` — and both start at `q1`. `Frame.find_hard_question` and
`Frame.resolve_hard_question` only ever search claim-attached questions; the
claim id is what disambiguates which namespace is meant.

### Vagueness

First-class open vagueness — parked uncertainty, not a markdown afterthought.

- `id` — `v1`, `v2`, …
- `text` — the unknown.
- `kind` — see Vagueness kinds.
- `claim_id` — optional owning claim, set at park time.
- `resolved` — boolean; `False` until closed via `Frame.resolve_vagueness`
  (v3, resolve-parked-vagueness t1). The **only** mutator — `park`/`confirm`/
  `reject` never touch it (decision c11).
- `resolution` — the resolution text recorded with `--decision`; `""` means
  not yet resolved (v3). The item stays on record with its resolution for
  provenance instead of being deleted.
- `resolution_claim_id` — optional *deciding* claim id recorded at resolve
  time via `--claim` (v3); distinct from `claim_id`, the *owning* claim set
  at park time, which `resolve_vagueness` never overwrites.

### ScopeEntry

A recorded scope-exploration finding — the durable record of the optional
pre-frame leg (the `/scope` skill, #53). Lives on the frame as
`Frame.scope_entries` (v2, #53 t1).

- `id` — `s1`, `s2`, …
- `surface` — what was explored (a file, a subsystem, a doc — the operating
  agent's read-only survey, never devague's own code).
- `finding` — what was learned about that surface.
- `seeds` — the ids this finding seeded (typically `boundary` / `non_goal` /
  `assumption` claims that cite what was actually explored). A seed may be a
  **claim id** (`c*`) or a **claim-attached hard-question id** (`q*`, #84 —
  the branch the `/scope` routing table sends a "genuinely unknown, needs a
  user decision" finding down, whose provenance link was previously
  unrecordable). An id resolving to neither is refused at construction, the
  same fail-closed rule as everywhere else.

The domain model (`Frame.add_scope_entry`) and its round-trip through
`schema_version` 2 shipped in #53 task t1; the CLI move that records one —
`devague scope "<surface>" --finding "<text>" [--seeds <c*|q*> ...]`, plus
`scope --list [--json]` to read them back — shipped in #53 task t3. An unknown
seed id is refused with a hint and nothing is persisted.

`scope --amend <sN> --finding "<text>"` (#84) replaces an entry's `finding` in
place: same `id`, same `surface`, same `seeds`, nothing else changes. It is
deliberately asymmetric with `amend` on a claim — a scope entry carries no
`status`/`origin` to protect, so there is **no revision trail** here. The
alternative it replaces was recording a second entry saying "supersedes s18",
which left both the wrong finding and its correction in the exported spec.

A seed that cites a **rejected** claim renders with a `(rejected)` marker in
the exported spec rather than as a bare dead reference, and a `q*` seed
renders as `(question)` — or `(question, resolved)` once answered (#84).

## Vocabulary

### Claim kinds

`announcement`, `audience`, `after_state`, `before_state`, `why_it_matters`,
`boundary`, `success_signal`, `open_question`, `non_goal`, `requirement`,
`assumption`, `decision`.

Their gate roles:

- **Spec-affecting** (must be confirmed and carry a confirmed honesty condition
  to converge): `announcement`, `audience`, `after_state`, `before_state`,
  `why_it_matters`, `boundary`, `success_signal`, `requirement`.
- **Descriptive** (no honesty condition required, never blocking):
  `open_question`, `non_goal`, `decision`.
- **Soft**: an unconfirmed `assumption` is a convergence *warning*, never a
  blocker.

### Claim states and provenance

State and provenance are orthogonal: `status ∈ {proposed, confirmed, rejected}`
× `origin ∈ {user, llm}`. The issue's proposed names map onto this model — no
information is lost and no rename is needed:

| Issue name | This contract |
|---|---|
| `user_provided` | a user capture → `(status=confirmed, origin=user)` |
| `llm_proposed` | `(status=proposed, origin=llm)` |
| `user_confirmed` | `(status=confirmed)` after an explicit user `confirm` |
| `rejected` | `status=rejected` |
| `parked` | a Vagueness entry (not a claim status) |

### Vagueness kinds

`unknown_nonblocking`, `unknown_blocking`, `out_of_scope`, `follow_up`. The
issue's `unknown_non_blocking` is `unknown_nonblocking`; `intentionally_out_of_scope`
is `out_of_scope`. Only `unknown_blocking` holds back convergence.

## Instructions

`Claim`, `HonestyCondition`, and (on the plan side) `Task` each carry an
optional `instruction` field: verbatim operator/user-authored text on how to
verify or implement that item. The default is `""` — empty means "no
instruction," never fabricated or defaulted to prose. Instructions are meant to
flow end to end: captured on a claim or honesty condition, carried onto the
plan tasks that cover it, rendered verbatim in exports, and quoted verbatim
into a workforce subagent's brief — no operator paraphrasing at any hop (#53).

Setting or changing an instruction is content, not metadata: **adding or
changing the instruction on an already-`confirmed` claim, honesty condition, or
task flips its status back to `proposed`.** The user re-confirms it, exactly
like any other proposed content — this is deliberate, not a bug, and keeps the
anti-fabrication guarantee intact even for a field that arrives after the
initial confirm.

The CLI surface that sets instructions ships in this increment:

- frame side: `capture --instruction "<text>"` (at creation) and
  `interrogate <c*|h*> --instruction "<text>"` (on an existing claim or honesty
  condition) — #53 task t4;
- plan side: `plan task --instruction "<text>"` (at creation) and the
  `plan instruct <tN> "<text>"` move (on an existing task) — #53 task t5.

`devague review` lists each item's instruction alongside it (t4), so the human
review loop sees instructions the same way it sees proposed claims and honesty
conditions.

## Convergence result

`converge` returns a structured verdict (not prose-only advice). The frame CLI
serializes it under `ready_for_spec`; the plan CLI under `ready_for_plan`.

- `ready_for_spec` (bool) — the gate: true when there are no blockers.
- `blockers` (list) — what holds convergence back.
- `warnings` (list) — surfaced but non-blocking (e.g. a still-`proposed`
  assumption; a **rejected** assumption no longer warns — that decision is
  already made and neither confirming nor re-rejecting it is a useful next
  move, #83).
- `parked_items` (list) — tracked, non-blocking open vagueness (plus, on the
  plan side, deliberately deferred coverage targets, labeled `deferred:`).
- `required_next_moves` (list) — the recommended move per blocker. For a
  blocking hard question this now names the executable move —
  `devague interrogate <cN> --resolve <qN> --decision "<how it was decided>"`,
  flagged as a USER decision — rather than prose advice (#48/#52).

A frame converges when there are confirmed `announcement` / `audience` /
`after_state` claims, a `before_state` or `why_it_matters`, a `boundary`, a
`success_signal`, a confirmed honesty condition on every spec-affecting claim,
and no unresolved blocking vagueness or unresolved blocking hard question on a
non-rejected claim. `export` is gated on `ready_for_spec`.

### Structural sharpness warnings (soft rollout)

Two more deterministic warnings tighten the frame gate without changing what
blocks convergence — shipped in `convergence.py` by #53 task t7, each rule's
exact predicate and false-positive story documented in that module's docstring:

- a confirmed spec-affecting claim carries no `instruction`;
- the confirmed `success_signal` claims contain no measurability token
  (a numeral, `%`, or a comparator — a deterministic structural heuristic,
  never LLM judgment on the claim text).

The plan gate carries the symmetric warning in `plan_convergence.py` (#53 task
t8): a confirmed task carries no `instruction`.

All three land as **warnings only** in this increment: they surface in
`warnings[]` alongside the existing unconfirmed-`assumption` warning, but never
add a blocker, so frames and plans that already converge keep converging
unchanged. A later increment may decide whether any of them graduates to a
blocker.

## Moves

All moves take `--json` and `--frame <slug>` (default: the current frame).
Mutating moves persist immediately and echo the changed entity. On user error
the exit code is non-zero and `stderr` carries a `hint:` line.

| Move | Input | Output (JSON) | Transition |
|---|---|---|---|
| `new "<text>"` | announcement text | frame slug | creates a frame; seeds a confirmed `announcement` claim |
| `capture --kind K "<text>" [--origin]` | kind, text, origin | `{id, kind, origin, status}` | adds a claim (`llm` → `proposed`, else `confirmed`) |
| `amend <cN> [--text "<text>"] [--kind K] [--reason "<why>"]` | claim id, new text and/or kind, optional reason | `{id, kind, text, origin, status, flipped}` | corrects a claim **in place** — id, honesty conditions, hard questions, `instruction`, and inbound scope `seeds` all survive; appends the superseded pair to `revisions`; flips a **confirmed** claim to `proposed` (v4, #84). `origin` is never touched |
| `interrogate <cN> [--honesty/--hard-question/--risk/--contradicts]` | claim id + attachment | `{added: [...]}` | attaches a honesty condition / question (`llm` honesty → `proposed`) |
| `interrogate <cN> --resolve <qN> [--decision "<text>"]` | claim id, hard-question id, optional resolution note | `{claim, id, resolved, resolution}` | closes out that claim's hard question (v4, #48/#52) — the **only** path to `HardQuestion.resolved`; user-only, the claim-level twin of `park --resolve`; mutually exclusive with every add-flag above |
| `scope "<surface>" --finding "<text>" [--seeds <c*\|q*> …]` | surface, finding, optional seed ids | `{id, surface, finding, seeds}` | records a scope-exploration finding (v2, #53 t3); `--amend <sN> --finding "<text>"` replaces a finding in place (#84) |
| `confirm <id> [<id>…]` / `reject <id> [<id>…]` | claim or honesty ids | `{confirmed, rejected, cascaded}` | the **only** path to `confirmed` / `rejected` — user-only, transactional; rejecting a claim cascades onto its still-live honesty conditions and unresolved hard questions (`cascaded`, echoed as `(also rejected: h3, q1)`, #83) |
| `park "<text>" --kind K` | text, vagueness kind | `{id, kind}` | adds first-class open vagueness |
| `park --resolve VID --decision "<text>" [--claim CN]` | vagueness id, decision text, optional deciding claim id | `{id, resolved, resolution, resolution_claim_id}` | closes out a parked item (v3, resolve-parked-vagueness t5) — the **only** path to `Vagueness.resolved`; user-only, mirrors `question --resolve` |
| `converge` | — | the convergence result | promotes/demotes frame `status` |
| `export [--format spec-md]` | — | `{path, format}` | writes the spec; requires `ready_for_spec` |
| `show` / `list` | — | frame dict / slug list | none |
| `learn` / `explain <move>` | — | method / move help | none |

**Validation errors** (all raise a clean `DevagueError`, exit code 1): unknown
claim kind / origin / status or vagueness kind (rejected at construction);
unknown claim or honesty id on `confirm`/`reject`; `park --resolve` without
`--decision`; positional park text passed together with `--resolve`; an
unknown or already-resolved vagueness id on `park --resolve`; an unknown
`--claim` id on `park --resolve`; an unknown claim id on `amend`, or `amend`
with neither `--text` nor `--kind`, or an unknown `--kind`; an unknown claim
id, an unknown or wrong-claim hard-question id, or an already-resolved
question on `interrogate --resolve`, and `--resolve` combined with any
add-flag; an unknown `--seeds` id on `scope` (resolving to neither a claim nor
a claim-attached hard question); an unknown entry id or a missing `--finding`
on `scope --amend`; an invalid `--frame` slug; a missing frame;
a malformed or hand-edited frame file (including one whose embedded slug
doesn't match the requested slug, or whose `schema_version` is not an
integer); a frame whose `schema_version` is too new.

## Anti-fabrication guarantee

LLM-proposed claims and honesty conditions persist as `proposed` and require an
explicit user `confirm` before they affect convergence. Nothing auto-confirms,
`converge` never mutates a claim's status, and no fixed prompt sequence is
imposed — the CLI stays a move-driven state tracker.

The same guarantee extends to instructions (#53 t4/t5): setting or changing one
on an already-confirmed item demotes it back to `proposed` (see *Instructions*
above) — content changes route through the user exactly like new proposals. It
extends to `amend` the same way (#84): correcting a confirmed claim's text or
kind flips it back to `proposed` rather than editing an approved statement
under the user.

It also extends to deviation records (see *The delivery peer* below): an
`llm`-origin deviation lands `proposed` and requires an explicit user
`--confirm` / `--reject`; nothing auto-approves an LLM-authored deviation, and
`set_status` only ever accepts a transition **from** `proposed` — it never lets
`--confirm` or `--reject` silently overwrite an already-resolved record.

## Worked example

`docs/examples/contract-example.json` is a real, converged frame exercising the
full vocabulary (including `requirement`, `non_goal`, `decision`, and an
unconfirmed `assumption` that surfaces as a warning), plus a parked `follow_up`.
`tests/test_contract.py::test_contract_example_round_trips_and_converges` proves
it round-trips losslessly and converges, so this document's model stays honest.

## The plan peer

The plan engine (`devague plan …`) is the structural peer: a Plan holds coverage
targets derived from a converged frame, Tasks (`origin`/`status` like claims,
plus `deps`, `covers`, `acceptance_criteria`, and an optional `instruction` —
verbatim text on how to implement/verify the task, `""` means none, v2, #53 t2;
see *Instructions* above), and PlanRisks (`id`, `text`, `kind`, optional
`task_id`, plus `resolved` / `resolution` — the plan-side twin of
`Vagueness.resolved` / `.resolution`, field names pinned verbatim across both
models, v3, resolve-parked-vagueness t2). It reuses the same structured
convergence result, serialized under `ready_for_plan`. See
`docs/superpowers/specs/2026-05-23-devague-spec-to-plan-design.md`.

### CoverageTarget

One thing the plan must deliver, derived from the source frame at
`plan new` (every confirmed claim and confirmed honesty condition).

- `id` — the frame id it mirrors: a claim id (`c*`) or honesty id (`h*`).
- `kind` — a claim kind, or `"honesty"` for an honesty condition.
- `text` — the target text, copied from the frame.
- `deferred` — boolean; `False` unless `plan defer` deliberately excluded this
  target from *this* plan's gate (v4, #85). Written only by
  `Plan.defer_target` / `Plan.undefer_target`.
- `deferred_reason` — why it is out of scope for this plan; `""` when not
  deferred (v4). `plan defer` requires a reason — a deferral without one is
  refused, the same evidence-bearing rule as `park --resolve --decision`.

A deferred target drops out of the coverage blocker, surfaces in
`parked_items` labeled `deferred:` (so it is visible, never silently
dropped), and renders under a `## Deferred targets` section in the exported
plan-md. This is the honest alternative to a task that merely *names* a
target: before it existed, a milestone-scoped plan could not converge at all
unless it faked coverage of work belonging to a later plan.

The stored `targets` list is a **snapshot** taken at `plan new`, while
`converge` / `status` / `export` re-derive targets from the live frame. `cover`
and `task --covers` therefore check the snapshot first (the common, no-I/O
case) and fall back to the live frame, refreshing and persisting the snapshot
on a hit (#90) — otherwise `status` could recommend covering a target that
`cover` then refused as unknown, and a frame that legitimately grew a claim
mid-run could never converge again. If the source frame has itself regressed
below its own gate, the frame-drift error surfaces as-is rather than being
reworded into "unknown coverage target".

### Moves

All plan moves take `--json` and `--plan <slug>` (default: the current plan).
Mutating moves persist immediately and echo the changed entity; `converge` /
`export` / `status` additionally re-evaluate against the **live** source
frame, so a frame that regressed below its own convergence after the plan was
seeded surfaces as a clean error (frame drift) rather than a stale pass.

| Move | Input | Output (JSON) | Transition |
|---|---|---|---|
| `new --frame <slug> [--title]` | source frame slug, optional title | `{slug, frame, targets}` | creates a plan from a **converged** frame; derives coverage targets; refuses an unconverged frame or a plan that already exists |
| `task "<summary>" [--accept … --dep … --covers … --origin --instruction]` | summary, origin, optional acceptance/deps/covers/instruction | `{id, status, acceptance, deps, covers, instruction}` | adds a task (`llm` → `proposed`, else `confirmed`) |
| `instruct <tN> "<text>"` | task id, instruction text | `{id, instruction, status, flipped}` | sets/replaces the task's instruction; flips a **confirmed** task back to `proposed` (see *The re-confirm rule* below) |
| `accept <tN> "<text>"` | task id, criterion text | `{id, acceptance}` | appends an acceptance criterion; does not change `status` |
| `amend <tN> [--summary "<text>"] [--accept-replace <n> "<text>" …] [--accept-remove <n> …]` | task id, optional summary replacement, index-addressed acceptance-criterion edits | `{id, summary, acceptance_criteria, status, flipped}` | edits the summary and/or acceptance criteria in place; flips a **confirmed** task back to `proposed`; refuses outright on a **rejected** task |
| `depend <tN> --on <tM>` | dependent task id, dependency task id | `{id, deps}` | appends a dependency edge; does not change `status`; refuses a self-dependency or an unknown `<tM>` at creation (#86) |
| `depend <tN> --on <tM> --remove` | dependent task id, dependency task id | `{id, deps, status, flipped}` | cuts exactly that one edge; flips a **confirmed** task back to `proposed`; refuses if the task did not depend on `<tM>` |
| `cover <tN> --target <c*\|h*>` | task id, coverage target id | `{id, covers}` | marks a task as covering a coverage target; does not change `status`; the target is validated against the stored snapshot first, then the **live** frame (#90) |
| `defer <target-id> --reason "<text>"` | coverage target id, reason | `{id, deferred, reason}` | deliberately excludes a target from *this* plan's gate (v4, #85); `--reason` is required |
| `defer <target-id> --undo` | coverage target id | `{id, deferred}` | reverses a prior deferral, returning the target to the active gate; refuses a target that was never deferred |
| `confirm <tN> [<tN>…]` / `reject <tN> [<tN>…]` | one or more task ids | `{ids, status}` | the **only** path to `confirmed` / `rejected` — user-only and **transactional**: every id is validated first, so one bad id changes nothing (#86). Plan tasks have no attachments to cascade over, unlike the frame side |
| `risk "<text>" --kind K [--task <tN>]` | risk text, vagueness kind, optional task ref | `{id, kind, task}` | records a first-class PlanRisk |
| `risk --resolve RID --decision "<text>"` | risk id, decision text | `{id, resolved, resolution}` | closes out a plan risk (v3, resolve-parked-vagueness t6) — the **only** path to `PlanRisk.resolved`; user-only, mirrors `park --resolve` (no `--claim` analog — risks link tasks via `--task`, not a deciding claim) |
| `risk --amend RID --text "<corrected>"` | risk id, corrected text | `{id, kind, text, task, resolved, resolution}` | corrects a risk's text in place (#84) — the plan-side twin of the frame's `amend`; `kind`, `task_id`, and resolution state are untouched |
| `converge` | — | the convergence result (`ready_for_plan`) | promotes/demotes plan `status`; re-evaluates against the live source frame |
| `export [--format plan-md]` | — | `{path, format}` | writes the buildable plan; requires `ready_for_plan` |
| `waves [--json]` | — | `{plan, waves, tasks}` | none — read-only, convergence-agnostic (see below) |
| `deliverables [--json]` | — | `{plan, converged, announcement, after_state, success_signal, terminal_tasks, open_items}` | none — read-only, convergence-agnostic (see below) |
| `status` / `show` / `list` | — | status verdict / plan dict / slug list | none |
| `learn` / `explain <move>` | — | method / move help | none |

**Validation errors** (all raise a clean `DevagueError`, exit code 1): an
unknown task id on `instruct` / `accept` / `amend` / `depend` / `cover` /
`confirm` / `reject`; an unknown coverage target on `cover` or
`task --covers`; `amend` called against a **rejected** task, or with neither
`--summary` nor an acceptance edit, or with an out-of-range acceptance index;
`depend --remove` naming an edge the task does not have; a self-dependency or
an unknown dependency id on `task --dep` / `depend --on`; an unsound
dependency graph (a cycle, or a dependency on a missing/rejected task) on
`waves`; `new` against an unconverged frame or over an existing plan; a
source frame that has regressed below its own convergence on `converge` /
`export` / `status` (frame drift, also surfaced as-is by `cover` / `defer`
when the id is absent from the stored snapshot); `risk --resolve` without
`--decision`; positional risk text passed together with `--resolve`; an
unknown or already-resolved risk id on `risk --resolve`; an unknown risk id or
a missing `--text` on `risk --amend`; `defer` without `--reason`, an unknown
target id, an already-deferred target on `defer`, or a never-deferred target
on `defer --undo`; an invalid `--plan` / `--frame` slug; a missing plan; a
malformed or hand-edited plan file; a plan whose `schema_version` is too new.
An argument error raised inside the `plan` group points at
`devague plan explain <move>` rather than the generic `--help` (#86).

### The re-confirm rule

Three moves **demote** an already-`confirmed` task back to `proposed`:
`instruct` (changing the verbatim instruction — see *Instructions* above),
`amend` (editing the summary or acceptance criteria), and `depend --remove`
(cutting a dependency edge). Each is content, not metadata, so the same
anti-fabrication guarantee applies: the user re-confirms it exactly like any
other proposed content. `accept`, `depend` (adding an edge), `cover`, and
`task --covers` never flip status — they only add.

The flip is echoed on **stdout itself**, not only on `stderr` and in
`--json` (`flipped: true`) — e.g. `t1: instruction set (confirmed ->
proposed; re-confirm)` — because a harness reading only stdout must still see
the demotion (issue #67 hardening, #53-esd t1).

`plan waves` emits the plan's dependency graph as deterministic, machine-readable
scheduling metadata — `{plan, waves}`, where `waves` is an ordered list of task-id
batches (wave 0 has no unsatisfied dependency; each later wave depends only on
earlier ones). It is **read-only**, never mutates state, and is **not** gated on
convergence, so it works on an in-progress plan. Rejected tasks are excluded; a
cycle or a dependency on a missing/rejected task is refused by reusing the
plan-convergence dependency blockers. The boundary is deliberate (issue #20):
Devague *describes* the parallelizable graph; an external operator (Culture,
codexd, …) decides how — or whether — to execute it. Devague does not spawn
subagents, manage worktrees, mark tasks done, or choose a backend.

`plan deliverables` is the read-only "what do we have in the end?" view
(issue #70): the live source frame's confirmed `announcement` /
`after_state` / `success_signal` claims verbatim, the plan's **terminal
tasks** (active tasks no other active task depends on) with their acceptance
criteria, and surviving open items (the frame's non-blocking parked
vagueness plus the plan's non-blocking risks). Like `waves` it never mutates
state and is **not** gated on convergence — an unconverged plan still
renders, with an explicit not-converged banner (text) / `converged: false`
(JSON) instead of a refusal, because previewing the end state is exactly
what is useful *before* convergence, at the assign-to-workforce go/no-go
(issue #20: Devague describes state, it does not gate the human's decision).

Plans carry the same persistence contract as frames. Every plan has an integer
`schema_version` (currently `4`, `PLAN_SCHEMA_VERSION`), written on save and
checked on load — against the **raw** dict before the domain object is built,
the same hardening the frame store carries: `plan_store.load` **fails closed**
with a clean `DevagueError`
(exit code 1, upgrade hint) when a plan declares a `schema_version` newer than
this devague supports. A pre-0.7.0 plan with no `schema_version` key loads
silently as the current schema. Loaded `Task.origin` / `Task.status` and
`PlanRisk.kind` are validated at construction; an invalid value surfaces as a
"malformed plan" `DevagueError` rather than a traceback. (Task/dep/cover **id**
cross-references are deliberately *not* validated at load — coverage and acyclic
dependency checks already run against the live frame in `plan converge`.)

Both `load`s also reject a file whose embedded slug disagrees with the requested
slug (so a tampered file can't silently redirect a later `save`), and parse
`schema_version` strictly via the shared `frame.parse_schema_version` — a
non-integer value is rejected rather than coerced. These guards are symmetric
across the frame and plan persistence twins.

> **v4 (issue-backlog-sweep t9).** `PLAN_SCHEMA_VERSION` bumped to add
> `CoverageTarget.deferred` and `CoverageTarget.deferred_reason` (#85) — see
> *CoverageTarget* above. A v3 plan predates both: every target loads with
> `deferred` defaulted to `False` and `deferred_reason` to `""`, so nothing
> loads as silently out of scope.
>
> **v3 (resolve-parked-vagueness t2).** `PLAN_SCHEMA_VERSION` bumped to add
> `PlanRisk.resolved` and `PlanRisk.resolution` — the plan-side twin of the
> frame's v3 Vagueness bump. A v2 plan predates both: it loads with `resolved`
> defaulted to `False` and `resolution` to `""`, so every pre-existing risk
> loads as still-open.
>
> **v2 (#53 t2).** `PLAN_SCHEMA_VERSION` bumped to add `Task.instruction`. A v1
> plan predates it and loads with every task's `instruction` defaulted to `""`.

## The delivery peer

The delivery ledger (`devague deviate` / `devague summary`) is the plan's
**execution-side companion**, the smallest deterministic slice of a parked
delivery engine (#53-esd t3): where a Plan is the contract the user confirmed, a
Delivery records where execution actually diverged from it. It never touches
the plan itself — **the plan JSON stays byte-identical through every
`deviate` operation** (test-asserted) — and it has no independent identity of
its own: a delivery's key is its source plan's slug verbatim, so there is no
separate "current delivery" pointer; every move that reads or writes one
resolves the plan first.

### Delivery

- `plan_slug` — the source plan's slug, verbatim.
- `schema_version` — integer; see *Schema versioning* below.
- `created`, `updated` — ISO-8601 UTC timestamps, stamped on save.
- `deviations` — list of DeviationRecord.

### DeviationRecord

- `id` — `d1`, `d2`, …
- `what` — what deviated, verbatim.
- `task_ref` — the plan item this deviation relates to (e.g. `t3`); must
  resolve to a task id on the resolved plan — an unknown `--task` is refused.
- `reason` — required; a deviation without a reason is refused with a hint —
  never fabricated.
- `affects` — repeatable list of plan-item/coverage refs this deviation also
  touches; defaults to `[]`. An id-shaped ref (one that looks like a plan
  task id, a coverage-target id, or a source-frame claim/honesty-condition
  id) must resolve in plan tasks ∪ coverage targets ∪ the source frame's
  claim/honesty ids; a free-text ref that is not id-shaped is accepted as-is.
- `origin` — `user` | `llm` (who proposed it).
- `status` — `proposed` | `approved` | `rejected`; see *Status transitions*
  below.
- `classification` — optional, one of `acceptable` | `risky` |
  `needs-follow-up` (`CLASSIFICATIONS`); feeds the drift-entry contract the
  `summarize-delivery` skill consumes.

### Status transitions

A user-authored deviation (the default) **auto-approves**: it lands directly
as `approved`, since a user-authored record already carries the human
approval the ledger exists to capture. An `llm`-authored deviation
(`--origin llm`) lands `proposed` and requires explicit user resolution — the
same anti-fabrication rule as claims and tasks: nothing auto-confirms an LLM
proposal.

`--confirm <dN>` and `--reject <dN>` are the **only** way a `proposed` record
is resolved (user-only), and are mutually exclusive within a single `deviate`
invocation. Both moves — and `set_status` underneath them — only accept the
transition **from `proposed`** to `approved` or `rejected`: resolving a
record that is not currently `proposed` (already `approved`, already
`rejected`, or an auto-approved user record) is refused as a user error
rather than silently overwritten.

### Moves

| Move | Input | Output (JSON) | Transition |
|---|---|---|---|
| `deviate "<what>" --task <tN> --reason "<text>" [--affects <ref> …] [--classification K] [--origin]` | what, task ref, reason, affects, classification, origin | `{id, what, task, reason, affects, origin, status, classification}` | appends a DeviationRecord (`llm` → `proposed`, else auto-`approved`) |
| `deviate --confirm <dN>` / `deviate --reject <dN>` | deviation id | `{id, status}` | the only path to `approved` / `rejected` — user-only; mutually exclusive with each other; refused unless the record is currently `proposed` |
| `deviate --list [--plan]` / bare `deviate` | — | `{plan, deviations: […]}` | none (default action) |
| `summary [--pr] [--json]` | — | eight-section skeleton dict, or the condensed PR-body skeleton dict under `--pr` | none — read-only, never persists |

**Validation errors** (all raise a clean `DevagueError`, exit code 1): missing
`--reason`; missing `--task`; an unknown `--task` (not a task id on the
resolved plan); an id-shaped `--affects` ref that fails to resolve in plan
tasks ∪ coverage targets ∪ source-frame claim/honesty ids; an unknown
`classification` or `origin` (rejected at construction); an unknown deviation
id on `--confirm` / `--reject`; passing both `--confirm` and `--reject` in the
same invocation; `--confirm` / `--reject` against a deviation that is not
currently `proposed`; no plan selected; an invalid `--plan` slug; a malformed
or hand-edited delivery file (an embedded `plan_slug` that disagrees with the
requested slug, or a `schema_version` that is not an integer); a delivery
whose `schema_version` is too new.

### `summary`

`devague summary` renders the eight-section delivery-summary skeleton the
`summarize-delivery` skill starts from, pre-filled from state alone — the
plan, its live source frame, and the delivery store — and nothing else.
Section names and order are pinned to the template in
`.claude/skills/summarize-delivery/SKILL.md`: Intent, Planned Work, Actual
Delivery, Mid-work Decisions, Drift From Plan, Evidence, Delivery Claims,
Remaining Work / Follow-up. Only two of the eight are pre-filled from
delivery state beyond the plan's own task list — **Mid-work Decisions** and
**Drift From Plan** — and both quote only **`approved`** deviation records by
id; a `proposed` deviation is never rendered as if it were a decision — it
surfaces, if at all, as an explicit "pending approval" line, never folded
into an approved list. Everything else that cannot be mechanically derived
(run status, per-task delivery status, evidence, delivery claims, remaining
work) renders as an explicit backticked `` `<fill: …>` `` placeholder —
literal code spans, never inline HTML, so no placeholder is ever mistaken for
a completed claim. `--pr` swaps in a condensed PR-body skeleton — title,
announcement, the wave/task map, approved deviations, and a pointer to the
`docs/deliveries/<date>-<slug>.md` artifact this skeleton seeds. Both modes
are pure functions of `(Plan, Optional[Frame], Delivery)`: read-only, no I/O
beyond the initial loads, and deterministic — rendering twice yields
byte-identical output.

Planned Work and Actual Delivery are scoped to **confirmed** tasks (#88), plus
one line recording how many tasks were rejected during planning. A `rejected`
task is planning history, and a `proposed` task is still under adjudication —
folding either into an accountability artifact about what shipped would report
an open or reversed decision as a closed one. A plan with 19 confirmed and 68
rejected tasks emitted 87 rows before this.

## Render-time contracts

Two things happen only at render time. Neither touches the stored JSON, and
neither appears in any `--json` payload — a `--json` view mirrors the
underlying data verbatim, exactly as the stores hold it.

### Markdown safety (#87)

`devague/render/_md_safety.py` composes two passes over every field of
verbatim claim / task / instruction / deviation text, at every verbatim site
in `spec_md.py`, `plan_md.py`, and `summary_md.py`:

- `md_safe_text()` — underscore- and dunder-bearing identifiers are wrapped in
  code spans rather than backslash-escaped (fixing MD037 and MD050 in one
  move, since Markdown never parses inside a code span); the remaining
  markdown control characters (`*`, `[`, `]`, a stray backtick, a leading
  `#`) are backslash-escaped; text already inside a matched backtick pair is
  left byte-for-byte untouched. Pure and **idempotent**:
  `md_safe_text(md_safe_text(x)) == md_safe_text(x)`.
- `autolink_urls()` / `heading_safe()` — bare URLs are wrapped in `<…>`
  (MD034), and heading text additionally has MD026 trailing punctuation
  stripped.

The exported artifacts therefore pass `markdownlint-cli2` without the author
having to hand-escape claim text, and the frame/plan JSON round-trips
unchanged.

### Contested claims (#92)

`devague/contested.py` derives, read-only and at render time, the claims an
approved deviation has contested. A frame outlives the plans seeded from it
and carries no reverse pointer to them, so the join enumerates plan slugs,
keeps the plans whose `frame_slug` matches, loads each one's delivery ledger,
and matches every **approved** deviation's `--affects` refs back onto the
frame's **confirmed** claims.

- The exported spec renders a nested "⚠ contested by `dN`" bullet under the
  claim (with the deviation's `classification` and `reason`); `show` and
  `status` render `contested: <claim> by <deviation>` lines, and both gain a
  `contested` key under `--json`.
- **The spec is never rewritten.** Per the maintainer ruling on #92, the
  artifact points *forward* to the ledger rather than being edited to match
  execution — "deviate is the marking of the change".
- **Fails open.** This is the first time frame-side read paths reach across to
  the plan and delivery stores at all, so a plan file or delivery ledger that
  is missing, truncated, or declares a newer schema degrades to "no markers
  derived from that source" plus a human-readable diagnostic on stderr —
  never a crash and never a blocked `export` / `show` / `status`. A plan with
  no delivery ledger yet (the common case) is not a diagnostic at all.
- Nothing here mutates a claim, a plan, or a ledger, and no id is invented.

### Schema versioning

Deliveries carry the same persistence contract as frames and plans. Every
delivery has an integer `schema_version` (currently `1`,
`DELIVERY_SCHEMA_VERSION`), written on save and checked on load:
`delivery_store.load` **fails closed** with a clean `DevagueError` when a
delivery declares a `schema_version` newer than this devague supports. A
pre-field delivery loads silently as the current schema. `save()` always
stamps the schema version this binary actually writes (the 0.17.0
upgrade-on-write fix, applied here) rather than re-emitting a loaded/older
label, so a delivery loaded under an older label and then mutated with newer
fields is never rewritten under that stale label — the same guard that
protects frames and plans. `load` also rejects a file whose embedded
`plan_slug` disagrees with the requested slug (a tampered file can't
silently redirect a later `save`), symmetric with the frame/plan persistence
twins.

The delivery store lives at `.devague/deliveries/<plan-slug>.json` (the peer
of `.devague/plans/<slug>.json`). It is never written by any frame or plan
move, and no `deviate` / `summary` move ever writes to `.devague/frames/` or
`.devague/plans/` — the delivery store is the plan's execution-side
companion, not a mutation of it: **the plan JSON stays byte-identical through
every `deviate` operation.**
