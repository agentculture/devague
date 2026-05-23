# devague — working-backwards spec engine

**Date:** 2026-05-23
**Status:** Approved (design)
**Design input:** [agentculture/devague#4](https://github.com/agentculture/devague/issues/4) ("Define Devague working-backwards flow") + its refinement comment.

## Context

The repo formerly known as `specifix` was renamed to **devague**
(`agentculture/specifix` → `agentculture/devague` on GitHub; one repo, the
onboarding scaffold from PR #3 carried over). devague is a *spec-creation tool —
the user's own alternative to the superpowers brainstorm→spec discipline, not a
wrapper around it.*

devague's method is **working backwards**: you start from the announcement
("pretend it shipped — what would you announce?"), build an **Announcement
Frame** by capturing classified claims, pressure-testing them with honesty
conditions and hard questions, parking unresolved uncertainty as first-class
"open vagueness," and only export a **buildable spec** once the frame
*converges*. Per the #4 refinement, this is a **state machine over claims,
honesty conditions, open vagueness, and convergence** driven by LLM-chosen
*moves* — not a linear wizard.

This document designs that as a buildable AgentCulture sibling.

## Goals / non-goals

**Goals**
- Turn a vague feature idea into a clear, bounded, buildable decision via the
  working-backwards flow.
- Make "no fabricated rigor" enforceable in code: LLM-proposed claims and
  honesty conditions stay `proposed` until the user confirms them.
- Gate spec export on convergence.
- Keep devague a clean sibling: deterministic, zero-runtime-dep CLI, fully unit-testable.

**Non-goals** (from #4)
- Do not start from implementation details.
- Do not position devague as *only* a spec generator (the frame is the first artifact).
- Do not hide uncertainty behind polished generated text.
- Do not require the user to fully understand the problem before starting.
- Do not reimplement superpowers; this is devague's own method.

## Architecture

**Deterministic CLI + resident agent.** Two responsibilities, cleanly split:

- **devague CLI** (deterministic, zero runtime deps): owns the Frame state,
  exposes the *moves* as verbs, mutates/renders state, and evaluates the
  convergence gate. No LLM calls inside the CLI → fully unit-testable.
- **Resident Claude agent** (the LLM): driven by `CLAUDE.md`, it decides the
  next move from the conversation, proposes claims and candidate honesty
  conditions, and always routes honesty conditions through user confirmation.
  This is the AgentCulture model — the CLI is the affordance, the agent is the brain.

Builds on the existing CLI chassis (`cli/__init__.py` dispatch, `_errors.py`,
`_output.py` strict stdout/stderr split + `--json`). Each move emits `--json`
so the agent can consume results programmatically.

### Domain model — the Frame

One Frame per change. **Source of truth: JSON** at `.devague/frames/<slug>.json`
(committed — the frame *is* a reviewable artifact).

```
Frame
  meta: { slug, title, status: drafting|converged|exported, created, updated }
  claims: [ Claim ]
  open_vagueness: [ Vagueness ]
  convergence: { last_evaluated, passed, missing: [ ... ] }   # cached result

Claim
  id            # stable short id, e.g. c1, c2
  kind          # announcement | audience | after_state | before_state
                # | why_it_matters | boundary | success_signal | open_question
  text
  origin        # user | llm
  status        # proposed | confirmed | rejected
  honesty_conditions: [ { id, text, status: proposed|confirmed } ]
  hard_questions:     [ { id, text, resolved: bool, blocking: bool } ]
  links: [ str ]      # PR/issue refs

Vagueness            # first-class open uncertainty
  id
  text
  kind          # unknown_nonblocking | unknown_blocking | out_of_scope | follow_up
  claim_id?     # optional link to a claim
```

Confirmation rules (the anti-fabrication core): a claim or honesty condition
created with `origin=llm` is born `proposed`; only an explicit user
`confirm`/`reject` transitions it. `origin=user` claims may be born `confirmed`.

### Moves → CLI verbs (deterministic, all support `--json`)

| Verb | Move | Effect |
|------|------|--------|
| `devague new "<announcement>"` | seed | Create a frame; capture the announcement as the first claim. The mandatory first move. |
| `devague capture --kind <kind> "<text>" [--origin user\|llm]` | capture | Record + classify a claim. |
| `devague interrogate <claim-id> [--honesty "…"] [--hard-question "…"] [--risk "…"] [--contradicts <id>]` | interrogate | Attach honesty conditions / hard questions / contradiction flags to a claim. llm-proposed honesty conditions land `proposed`. |
| `devague confirm <id>` / `devague reject <id>` | confirm | User-only status transitions for claims and honesty conditions. |
| `devague park "<text>" --kind <…> [--claim <id>]` | park | Move uncertainty into open vagueness. |
| `devague converge` | converge | Evaluate the gate; report pass, or the exact missing pieces. |
| `devague export [--format spec-md]` | export | Emit the buildable spec — **only if `converge` passes**; otherwise error listing gaps. |
| `devague show [--format frame-md]` / `devague list` | — | Render the current frame / list frames. |
| `devague learn` / `devague explain <move>` | — | Agent affordances, now real: `learn` teaches the working-backwards method + when to use each move; `explain` documents a verb. |

`--frame <slug>` selects a frame; otherwise the most-recently-touched frame is
the current one. The `whoami` stub retires.

### Convergence gate (`converge`)

Codifies #4's criteria; each failure names what's missing. A **spec-affecting
claim** is any claim whose `kind` is not `open_question` (i.e. it would appear in
the exported spec). A **major claim** is a confirmed spec-affecting claim.

- `announcement`, `audience`, `after_state` claims exist and are **confirmed**;
- `before_state` **or** `why_it_matters` exists;
- ≥1 `boundary` and ≥1 `success_signal` exist;
- no spec-affecting claim is still `proposed` (each is confirmed or rejected);
- every major claim has ≥1 **confirmed** honesty condition;
- no `unknown_blocking` vagueness remains;
- no open **blocking** hard question remains.

`export` refuses with a `DevagueError` (remediation = the gap list) until the gate passes.

### Output layer — pluggable renderers

Rendering and export go through a small **`Renderer` registry** (frame → text),
selected by `--format`, mirroring how `_commands` register. v1 ships two:

- `frame-md` — the **Announcement Frame** markdown (sections: Announcement,
  Audience, After-state experience, Why it matters, Before-state pain, Honesty
  conditions, Hard questions, Boundaries / non-goals, Success signals, Open
  vagueness). Used by `show`.
- `spec-md` — the **buildable spec** markdown derived from the converged frame,
  written to `docs/specs/<slug>.md`. Used by `export`.

Future modalities (NotebookLM content, an HTML site, guided user stories, …)
register as additional `Renderer`s behind the same `--format` seam — no engine
changes required. v1 implements only the two markdown renderers but builds the seam.

### Flow

`rough capture → pressure-test → convergence → spec`, emergent from moves rather
than imposed phases. The exported `spec-md` is a clean handoff that can feed an
implementation plan (e.g. the writing-plans discipline).

**First question (devague#4):** the announcement-first entry point is exactly

> What's the announcement?

with the supporting prompt

> Pretend this shipped successfully. What would you announce to users,
> teammates, or yourself?

**Canonical guided sequence.** The engine is move-driven (not a rigid wizard),
but #4's Definition of Done requires the guided stages be *documented* so users
and agents have a recommended arc. The ten stages map onto claim kinds and the
moves that advance each — `learn` teaches this sequence verbatim:

| # | Stage | Question | Advancing move |
|---|-------|----------|----------------|
| 1 | Announcement | what are we saying shipped? | `new` |
| 2 | Audience | who needs this? | `capture --kind audience` |
| 3 | After | what changed for them? | `capture --kind after_state` |
| 4 | Matter | why is it worth doing? | `capture --kind why_it_matters` |
| 5 | Before | what pain made this necessary? | `capture --kind before_state` |
| 6 | Honest | what must be true for it to be honest? | `interrogate --honesty` |
| 7 | FAQ | what hard questions remain? | `interrogate --hard-question` |
| 8 | Boundaries | what are we not promising? | `capture --kind boundary` |
| 9 | Success | how will we know? | `capture --kind success_signal` |
| 10 | Spec | what should be built? | `converge` → `export` |

The sequence is guidance, not a gate: the agent may revisit or reorder stages,
and convergence (not stage completion) is what unlocks `export`.

## Implementation phases

**Phase 0 — Rename `specifix` → `devague`** (do first, its own PR):
package dir `specifix/`→`devague/`; console script + `python -m devague`;
`SpecifixError`→`DevagueError`; `_SpecifixArgumentParser`→`_DevagueArgumentParser`;
`pyproject` name `devague` + `importlib.metadata.version("devague")`;
`culture.yaml` suffix `devague`; `sonar.projectKey=agentculture_devague`;
coverage source; CI lint/publish paths + TestPyPI notice; README / CLAUDE.md /
CHANGELOG / `docs/skill-sources.md`; tests. The `learn`/`explain` stubs survive
(bodies rewritten in Phase 2); `whoami` retires.
**PyPI:** stand up Trusted Publishing for a fresh `devague` distribution; leave
the published `specifix 0.1.0` as an orphan (no yank).

**Phase 1 — Frame domain model + storage**: `devague/frame.py` (dataclasses
for Frame/Claim/Vagueness, status transitions, JSON load/save, slug + id
allocation). Pure, no CLI. Unit-tested in isolation.

**Phase 2 — Moves as CLI verbs**: `new`, `capture`, `interrogate`,
`confirm`/`reject`, `park`, `show`, `list`, wired through the chassis with
`--json`; real `learn`/`explain` bodies teaching the method.

**Phase 3 — Convergence gate + spec export**: `converge` (gate logic +
gap reporting) and `export` (the `spec-md` renderer + the export-blocked-until-
converged guard), plus the `Renderer` registry and `frame-md` renderer.

## Testing

Deterministic throughout, mirroring the existing `tests/` layout:
- frame model: each status transition, confirm/reject rules, JSON round-trip, id/slug allocation;
- each move: state mutation + `--json` shape + error paths;
- convergence: a truth table over the gate criteria (each missing piece → named gap);
- export: blocked until converged; `spec-md` content derived from a converged fixture;
- renderer registry: format selection, unknown-format error.

Coverage stays above the existing `fail_under = 70`.

## Acceptance criteria

- Repo renamed end-to-end: `devague --version`, `python -m devague`, and the
  `devague` console script work; no `specifix` identifiers remain except the
  historical CHANGELOG entry and the `docs/skill-sources.md` divergence marker.
- `devague new` → `capture`/`interrogate`/`park`/`confirm` → `converge` →
  `export` produces `docs/specs/<slug>.md` from a frame that passes the gate,
  and `export` is refused (with the gap list) before convergence.
- LLM-origin claims/honesty conditions require explicit user confirmation.
- All moves support `--json`; `show` renders the Announcement Frame.
- Test suite green (pytest-xdist), coverage ≥ 70%; flake8 / markdownlint clean;
  `steward doctor` stays clean.

## Deferred

- Additional output modalities (NotebookLM, HTML site, user stories) — seam built, renderers later.
- Contradiction *detection* (the `--contradicts` flag records a link in v1; automated detection is later).
- Multi-frame ergonomics beyond `--frame` / current-frame.
- Mesh delegation (other agents asking devague to own a spec) — later.
- Claim-level parking: the `park` move records open vagueness, not a claim status.
  `Claim.status` has no `parked` value in v1; claim-parking is deferred.
