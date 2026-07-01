---
name: scope
description: >
  Explore the scope of a vague idea BEFORE framing it into a spec (the
  idea→scope leg; the optional opening move ahead of /think). Survey the
  surfaces the idea touches — code, docs, skills, CI, sibling repos — and seed
  the coming Announcement Frame with boundary, non-goal, and assumption claims
  that cite what was actually explored (provenance, not generic disclaimers).
  Use when the user says "explore scope", "scope this idea", "what does this
  touch", "map the scope", "scope exploration", or when an idea touches an
  existing codebase and speccing it cold would mean guessing its boundaries.
  Hand off to the sibling /think skill to build the frame. Authored and
  maintained in agentculture/devague (origin = devague); guildmaster pulls this
  skill from here and broadcasts it to the AgentCulture mesh — it is NOT
  vendored from guildmaster like the inbound skills here.
type: command
---

# scope — explore what an idea touches before you frame it

The skill is named **`scope`**; it is the **opening leg** of the devague method
— run it *before* the sibling **`/think`** skill frames an idea into a spec.
Where `/think` converges on *what* to build, `/scope` grounds *where the idea
lives*: which surfaces it touches, which it must not, and what is genuinely
unknown — so the frame starts from explored territory instead of guesses.

This comes from the sharper end-to-end method spec (devague#53): scope grounded
up front means convergence measures real coverage instead of vibes. The
exploration itself is **agent-side work** — the devague CLI stays deterministic
and never explores anything (#20).

## When to use — and when to skip

Use `/scope` when the idea touches an existing codebase or ecosystem: a feature
in a real repo, a process change across skills, anything where boundaries are
discoverable rather than invented.

**Skip it freely for small ideas.** Scope exploration is *not* a mandatory
first stage — the move-driven adaptive arc stays intact, and an idea that fits
in one announcement can go straight to `/think`. (This is a recorded non-goal
of the method: no wizard.)

## The method

1. **Enumerate candidate surfaces.** List what the idea *might* touch: source
   packages, CLI verbs, renderers, schemas, tests, docs, skills, CI workflows,
   sibling repos. `git ls-files` and the repo's `CLAUDE.md` are the usual map.
2. **Explore each surface read-only.** Read enough of each candidate to decide:
   touched, not touched, or unknown. Exploration never mutates anything —
   no edits, no state changes, no CLI moves yet.
3. **Classify every finding.** Each explored surface yields one of:
   - **in scope** — the idea changes it → becomes a `requirement` or
     `assumption` claim in the frame;
   - **out of scope** — the idea must not change it → becomes a `boundary` or
     `non_goal` claim;
   - **genuinely unknown** — can't tell without a decision → becomes a `park`
     (open vagueness) or a `question` (pending user decision).
4. **Seed the frame with provenance.** When `/think` starts, capture the
   findings as claims whose text **cites the surface explored** — "the CLI
   stays deterministic per issue 20; scope exploration is agent-side"
   beats "we won't overreach". Provenance, not generic disclaimers: a reviewer
   should be able to trace every boundary claim back to something you read.

## How findings land (the shipped surface)

There is no `devague scope` CLI verb yet — findings land through the existing
`devague` moves (this skill invokes the CLI directly and stays self-contained;
if `devague` isn't on your PATH: `uv tool install devague`):

| Finding | Move |
|---------|------|
| in scope (the idea changes this) | `capture --kind requirement` / `--kind assumption` (with `--origin llm` if you proposed it) |
| out of scope (must not change) | `capture --kind boundary` / `--kind non_goal` |
| genuinely unknown, needs a user decision | `question "<text>"` (later `question --resolve <qid> --decision "<text>"`) |
| genuinely unknown, not decidable now | `park "<text>" --kind unknown_blocking\|unknown_nonblocking` |

A deterministic **`devague scope` move** — recording explored surfaces and
findings as first-class frame state with provenance links — is **planned, not
shipped**: it is task t3 of the committed sharper-end-to-end-method plan
(`docs/plans/2026-07-01-devague-ships-a-sharper-end-to-end-method-a-guided.md`,
devague#53). Do not run `devague scope` until it exists; this skill documents
the surface as built.

## Hard rules (do not violate)

- **Exploration is read-only.** Surveying scope never edits files, never
  mutates frame state, never runs a mutating CLI move.
- **Provenance in every seeded claim.** A scope-derived claim cites what was
  explored. If you didn't read it, don't claim it.
- **LLM proposals stay proposed.** Findings you capture with `--origin llm`
  land `proposed`; the user confirms. Same anti-fabrication contract as
  `/think`.
- **Don't become a wizard.** Scope exploration is optional-by-size and
  adaptive. Never block a small idea on a survey it doesn't need.

## Worked example

Scoping "devague exports should carry per-item instructions" against the
devague repo itself:

```bash
# 1–2. enumerate + explore (read-only)
git ls-files devague/ | head -30       # the CLI package map
# read: devague/frame.py (claim model), devague/render/spec_md.py (renderer),
#       docs/spec-contract.md (schema contract), .claude/skills/think/SKILL.md

# 3–4. hand off to /think and seed with provenance
devague new "devague exports carry per-item instructions" --title "per-item instructions"
devague capture --origin llm --kind requirement "claims gain an optional instruction field — devague/frame.py claim model + docs/spec-contract.md schema both need a bump"
devague capture --origin llm --kind boundary "render/spec_md.py renders instructions verbatim; absent instructions render nothing — the renderer never fabricates filler"
devague capture --origin llm --kind non_goal "no LLM calls land inside the CLI (issue 20) — instruction text is authored by the operator/user, never generated in-CLI"
devague question "do instructions attach to frame claims, plan tasks, or both?"
```

Every claim above names the file or issue that was actually read — that is the
provenance bar.

## After scoping — hand off to /think

Scope exploration produces no artifact of its own (until the planned CLI move
lands, the findings *are* the seeded claims). When the survey is done, start
the frame with `/think` and capture the findings as the frame's opening claims.
The user confirms LLM-proposed ones there, as always.

## Provenance

This is a **first-party** skill — its origin is `agentculture/devague`, the
*fourth* in the outbound family after `/think`, `/spec-to-plan`, and
`/assign-to-workforce`, covering the pre-frame exploration leg. guildmaster
pulls it from here and broadcasts it to the AgentCulture mesh. The
`cite, don't import` policy still holds: downstream repos copy it, they don't
symlink or depend on it. See `docs/skill-sources.md`.
