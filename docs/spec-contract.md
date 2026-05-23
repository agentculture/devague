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

## Versioning

Every frame carries an integer `schema_version` (currently `1`). It is written
on save and checked on load: a frame whose `schema_version` is newer than this
devague supports is rejected, fail-closed, with an actionable error. A 0.4.0
frame predates the field and loads as the current schema, so existing frames
keep working.

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

### HonestyCondition

What must be true for a claim to be honest.

- `id` — `h1`, `h2`, …
- `text` — the condition.
- `status` — `proposed` | `confirmed` | `rejected`.

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
missing frame; a malformed or hand-edited frame file; a frame whose
`schema_version` is too new.

## Anti-fabrication guarantee

LLM-proposed claims and honesty conditions persist as `proposed` and require an
explicit user `confirm` before they affect convergence. Nothing auto-confirms,
`converge` never mutates a claim's status, and no fixed prompt sequence is
imposed — the CLI stays a move-driven state tracker.

## Worked example

`docs/examples/contract-example.json` is a real, converged frame exercising the
full vocabulary (including `requirement`, `non_goal`, `decision`, and an
unconfirmed `assumption` that surfaces as a warning), plus a parked `follow_up`.
`tests/test_contract.py::test_contract_example_round_trips_and_converges` proves
it round-trips losslessly and converges, so this document's model stays honest.

## The plan peer

The plan engine (`devague plan …`) is the structural peer: a Plan holds coverage
targets derived from a converged frame, Tasks (`origin`/`status` like claims,
plus `deps`, `covers`, `acceptance_criteria`), and PlanRisks. It reuses the same
structured convergence result, serialized under `ready_for_plan`. See
`docs/superpowers/specs/2026-05-23-devague-spec-to-plan-design.md`.
