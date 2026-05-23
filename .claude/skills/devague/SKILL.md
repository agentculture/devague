---
name: devague
description: >
  Operate the devague working-backwards spec tool: turn a vague feature idea
  into a buildable, pressure-tested spec by starting from the announcement
  ("pretend it shipped"), capturing and classifying claims, interrogating them
  with honesty conditions and hard questions, parking open vagueness as a
  first-class object, and exporting a spec only once the frame *converges*. Use
  when the user says "spec this", "work backwards", "turn this idea into a
  spec", "announcement frame", or "devague", or when a feature request is too
  vague to build yet. Authored and maintained in agentculture/devague (origin =
  devague); steward pulls this skill from here and broadcasts it to the
  AgentCulture mesh — it is NOT vendored from steward like the other skills here.
---

# devague — work an idea backwards into a buildable spec

`devague` turns a vague feature idea into a buildable spec by **working
backwards**: you start from the announcement you'd make if it had already
shipped, then build an **Announcement Frame** by capturing claims, pressure
-testing them, parking what's still genuinely unknown, and only exporting once
the frame converges.

The CLI is **deterministic and move-driven** — it is *not* a wizard. There is no
fixed sequence of prompts. **You (the agent) choose the next move; the CLI just
tracks state and tells you what's still missing.** Run `devague learn` for the
canonical ten-stage arc and `devague explain <move>` for any single move.

This skill is the operator: a portable wrapper plus one helper (`status`) that
reads the convergence gate and tells you the recommended next move.

## How to run

The entry point is `scripts/devague.sh`. Invoke it from the repository you are
speccing (frames persist under `.devague/` in the current directory):

```bash
bash .claude/skills/devague/scripts/devague.sh <move> [args...]
bash .claude/skills/devague/scripts/devague.sh status
```

It resolves the CLI portably — an installed `devague` on `PATH` (the normal
case), falling back to `uv run devague` when you are inside the devague checkout.
If neither resolves it prints an install hint (`uv tool install devague`). Every
move except `status` is forwarded verbatim, so you can equally call the CLI
directly (`devague <move> …`) when it is installed; the wrapper exists for
portable resolution and the `status` helper.

### Moves

| Move | What it does |
|------|--------------|
| `new "<announcement>"` | Start a frame from the announcement (the first move). Seeds an auto-confirmed `announcement` claim. |
| `capture --kind <kind> "<text>"` | Record + classify a claim. `--origin llm` lands it as `proposed`. |
| `interrogate <id> --honesty "…"` | Attach an honesty condition (what must be true). Also `--hard-question`, `--risk`, `--contradicts`, `--blocking`. |
| `confirm <id>` / `reject <id>` | Resolve a claim (`c*`) or honesty condition (`h*`). **User-only decision.** |
| `park "<text>" --kind <kind>` | Move uncertainty into first-class open vagueness instead of forcing an answer. |
| `converge` | Evaluate the gate; list remaining gaps. |
| `export` | Write the buildable spec to `docs/specs/` — only after `converge` passes. |
| `show` / `list` | Render a frame / list frames (`--json` for raw state). |
| `learn` / `explain <move>` | Teach the method / explain one move. |

Claim kinds: `announcement`, `audience`, `after_state`, `before_state`,
`why_it_matters`, `boundary`, `success_signal`, `open_question`. Vagueness kinds:
`unknown_nonblocking`, `unknown_blocking`, `out_of_scope`, `follow_up`.

### `status` — the next-move helper

`status` is a wrapper-only verb (the CLI has no `status`). It reads
`converge --json` + `list --json` and prints where the current frame stands, the
remaining gaps, and the recommended next move derived from the first gap:

```text
frame: my-feature    (1 frame total)
convergence: NOT passed — 2 gap(s):
  - missing a 'boundary' / non-goal claim
  - claim c2 has no confirmed honesty condition

recommended next move (first gap):
  devague capture --kind boundary "<text>"
```

Run it whenever you're unsure what to do next.

## Hard rules (do not violate)

These are the point of the method — convergence must mean something.

- **LLM proposals stay proposed.** A claim captured with `--origin llm`, and any
  honesty condition you (the agent) propose, lands as `proposed`. **Never
  `confirm` your own proposal.** Confirmation is a user-only decision — surface
  the proposal and let the user confirm or reject it. Proposed content must not
  silently become an authoritative requirement.
- **Honesty conditions route through the user.** Propose them freely with
  `interrogate --honesty`; the user owns whether they hold.
- **Converge, don't vibe.** `export` is gated on `converge` passing. Never claim
  the frame is ready on a hunch — run `converge` (or `status`) and resolve every
  listed gap. The gate requires confirmed `announcement` / `audience` /
  `after_state`, a `before_state` or `why_it_matters`, a `boundary`, a
  `success_signal`, a confirmed honesty condition on every spec-affecting claim,
  and no unresolved blocking vagueness or hard question.
- **Park real unknowns; don't paper over them.** If something is genuinely
  unknown, `park` it (blocking or non-blocking) rather than fabricating an
  answer. Blocking vagueness holds back convergence — by design.

## Output contract

Results go to **stdout**, diagnostics and errors to **stderr** — a strict split
you can rely on when parsing. Pass `--json` to any move for a structured payload
on the same stream. Exit code `0` on success, non-zero on user error (with a
`hint:` line). Frames live under `.devague/` in the current directory.

## Worked example

A short end-to-end session (the kind you'd run to spec a feature like
[devague#5](https://github.com/agentculture/devague/issues/5)):

```bash
d() { bash .claude/skills/devague/scripts/devague.sh "$@"; }

d new "Devague ships a documented spec contract"
d capture --kind audience "devague + the assisting LLM"
d capture --kind after_state "a vague idea becomes a buildable, pressure-tested spec"
d capture --kind why_it_matters "specs converge on evidence, not vibes"
d capture --kind boundary "not a full PRD generator; no fixed wizard"
d capture --kind success_signal "a frame exports only after the gate passes"

# Pressure-test a claim, then let the USER confirm the condition:
d interrogate c1 --honesty "the contract round-trips: save -> load -> identical frame"
# ...user reviews and runs: d confirm h1

# Park a genuine unknown instead of guessing:
d park "exact JSON schema versioning policy" --kind unknown_nonblocking

d status        # what's left + the next move
d converge      # gate; resolve any listed gaps
d export        # writes docs/specs/<slug>.md once converged
```

The exported spec-md is a buildable artifact; it can feed directly into
`superpowers:writing-plans` or a normal implementation PR.

## Provenance

This is a **first-party** skill — its origin is `agentculture/devague`, where the
devague agent maintains it alongside the tool it operates (dogfooding). It is the
*inverse* of the other skills under `.claude/skills/`, which devague vendors
**from** steward. When this skill is ready, steward pulls it **from** devague and
broadcasts it to the rest of the AgentCulture mesh. The `cite, don't import`
policy still holds: downstream repos copy it, they don't symlink or depend on it.
See `docs/skill-sources.md`.
