# The Devague spec contract

The durable, reloadable artifact model that turns a vague idea into a
claim-based, pressure-tested, buildable spec — and the moves that operate on it.
This document is the **source of truth** for the entity model, the vocabulary,
the convergence verdict, and the per-move I/O contract (issue #5).

The CLI is deterministic and move-driven: the assisting LLM chooses moves, the
CLI tracks state. Every move accepts and emits JSON (`--json`), with a strict
`stdout` (results) / `stderr` (diagnostics) split, so an LLM can drive devague
without guessing internal state. All operations run fully offline against local
`.devague/` state.

For the portable, runtime-agnostic contract on *how* an assisting model should
operate Devague — the move-driven mental model and the anti-fabrication rules —
see [`llm-guidance.md`](llm-guidance.md) (also surfaced in `devague learn`).

## Versioning

Every frame carries an integer `schema_version` (currently `2`). It is written
on save and checked on load: a frame whose `schema_version` is newer than this
devague supports is rejected, fail-closed, with an actionable error. A 0.4.0
frame predates the field and loads as the current schema, so existing frames
keep working.

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
- `resolved` — boolean.
- `blocking` — boolean; a blocking, unresolved question holds back convergence.

### Vagueness

First-class open vagueness — parked uncertainty, not a markdown afterthought.

- `id` — `v1`, `v2`, …
- `text` — the unknown.
- `kind` — see Vagueness kinds.
- `claim_id` — optional owning claim.

### ScopeEntry

A recorded scope-exploration finding — the durable record of the optional
pre-frame leg (the `/scope` skill, #53). Lives on the frame as
`Frame.scope_entries` (v2, #53 t1).

- `id` — `s1`, `s2`, …
- `surface` — what was explored (a file, a subsystem, a doc — the operating
  agent's read-only survey, never devague's own code).
- `finding` — what was learned about that surface.
- `seeds` — claim ids this finding seeded (typically `boundary` / `non_goal` /
  `assumption` claims that cite what was actually explored); an unknown claim
  id is refused at construction, the same fail-closed rule as everywhere else.

The domain model (`Frame.add_scope_entry`) and its round-trip through
`schema_version` 2 already ship. The CLI move that records one —
`devague scope "<surface>" --finding "<text>" [--seeds <claim-id> ...]`, plus
`scope --list [--json]` to read them back — is planned in the #53 build plan
(task t3); it is not yet part of the Moves table below.

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

The CLI surface that sets instructions is planned, not yet shipped in this
increment:

- frame side: `capture --instruction "<text>"` (at creation) and
  `interrogate <c*|h*> --instruction "<text>"` (on an existing claim or honesty
  condition) — #53 task t4;
- plan side: `plan task --instruction "<text>"` (at creation) and a new
  `plan instruct <tN> --instruction "<text>"` move (on an existing task) — #53
  task t5.

`devague review` is meant to list each item's instruction alongside it once t4
lands, so the human review loop sees instructions the same way it sees
proposed claims and honesty conditions today.

## Convergence result

`converge` returns a structured verdict (not prose-only advice). The frame CLI
serializes it under `ready_for_spec`; the plan CLI under `ready_for_plan`.

- `ready_for_spec` (bool) — the gate: true when there are no blockers.
- `blockers` (list) — what holds convergence back.
- `warnings` (list) — surfaced but non-blocking (e.g. an unconfirmed assumption).
- `parked_items` (list) — tracked, non-blocking open vagueness.
- `required_next_moves` (list) — the recommended move per blocker.

A frame converges when there are confirmed `announcement` / `audience` /
`after_state` claims, a `before_state` or `why_it_matters`, a `boundary`, a
`success_signal`, a confirmed honesty condition on every spec-affecting claim,
and no unresolved blocking vagueness or blocking hard question. `export` is gated
on `ready_for_spec`.

### Structural sharpness warnings (soft rollout)

Two more deterministic warnings tighten the frame gate without changing what
blocks convergence — planned for `convergence.py` in #53 task t7:

- a confirmed spec-affecting claim carries no `instruction`;
- the frame has no measurable `success_signal` (a deterministic structural
  heuristic — never LLM judgment on the claim text).

The plan gate gains the symmetric warning in `plan_convergence.py` (#53 task
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
| `interrogate <cN> [--honesty/--hard-question/--risk/--contradicts]` | claim id + attachment | `{added: [...]}` | attaches a honesty condition / question (`llm` honesty → `proposed`) |
| `confirm <id>` / `reject <id>` | claim or honesty id | `{id, status}` | the **only** path to `confirmed` / `rejected` — user-only |
| `park "<text>" --kind K` | text, vagueness kind | `{id, kind}` | adds first-class open vagueness |
| `converge` | — | the convergence result | promotes/demotes frame `status` |
| `export [--format spec-md]` | — | `{path, format}` | writes the spec; requires `ready_for_spec` |
| `show` / `list` | — | frame dict / slug list | none |
| `learn` / `explain <move>` | — | method / move help | none |

**Validation errors** (all raise a clean `DevagueError`, exit code 1): unknown
claim kind / origin / status or vagueness kind (rejected at construction);
unknown claim or honesty id on `confirm`/`reject`; an invalid `--frame` slug; a
missing frame; a malformed or hand-edited frame file (including one whose
embedded slug doesn't match the requested slug, or whose `schema_version` is not
an integer); a frame whose `schema_version` is too new.

## Anti-fabrication guarantee

LLM-proposed claims and honesty conditions persist as `proposed` and require an
explicit user `confirm` before they affect convergence. Nothing auto-confirms,
`converge` never mutates a claim's status, and no fixed prompt sequence is
imposed — the CLI stays a move-driven state tracker.

The same guarantee extends to instructions once t4/t5 land: setting or
changing one on an already-confirmed item demotes it back to `proposed` (see
*Instructions* above) — content changes route through the user exactly like
new proposals.

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
see *Instructions* above), and PlanRisks. It reuses the same structured
convergence result, serialized under `ready_for_plan`. See
`docs/superpowers/specs/2026-05-23-devague-spec-to-plan-design.md`.

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

Plans carry the same persistence contract as frames. Every plan has an integer
`schema_version` (currently `2`, `PLAN_SCHEMA_VERSION`), written on save and
checked on load: `plan_store.load` **fails closed** with a clean `DevagueError`
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

> **v2 (#53 t2).** `PLAN_SCHEMA_VERSION` bumped to add `Task.instruction`. A v1
> plan predates it and loads with every task's `instruction` defaulted to `""`.
