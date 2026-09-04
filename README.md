# devague

Devague is a CLI that helps you turn a vague idea into a spec, a plan, and
an accounted-for delivery. Your AI agent drives devague. You hold the three
gates.

## Install

```bash
uv tool install devague      # or: uvx devague / pipx install devague
devague --version
```

## Set up your agent

Tell your agent:

> Run `devague learn skills` and create the eight devague operator skills.

```bash
devague learn skills         # what the agent reads: file layout, frontmatter, the rules
```

- The recipe is printed by the CLI; the agent writes the skill files, with
  your consent, into its own skills folder (Claude Code: `.claude/skills/`).
- It never overwrites a skill that already exists.
- `devague learn` alone teaches the method; `devague learn review` teaches
  the final-PR review.

## Work with your agent

From here on you talk to the agent, one skill at a time, in this order:

```mermaid
flowchart LR
  S[1 scope] --> T[2 think] --> C[3 challenge]
  C --> G1{{Gate 1 — you approve the spec}}
  G1 --> P[4 spec-to-plan] --> G2{{Gate 2 — you approve the split plan}}
  G2 --> A[5 assign-to-workforce] --> D[6 deviate] --> V[7 validate-delivery]
  V --> Z[8 summarize-delivery] --> G3{{Gate 3 — you review the PR}}
```

1. **`/scope`** — the agent surveys what the idea touches and records each
   finding.
2. **`/think`** — the agent works backwards from the announcement into a
   spec; every proposal waits for your confirm; it exports once the frame
   converges.
3. **`/challenge`** — the agent hunts blind spots in the spec; findings come
   back to you as proposals.
4. **`/spec-to-plan`** — the agent turns the spec into tasks with acceptance
   criteria and a dependency order; you confirm the plan.
5. **`/assign-to-workforce`** — you approve the split; the agent fans tasks
   out to a workforce of agents, one worktree each, merges gated by tests.
6. **`/deviate`** — the run stops when it must leave the plan; you approve
   the departure; it is recorded.
7. **`/validate-delivery`** — the agent runs the behavioral tests and files
   evidence and deltas; failing stays failing.
8. **`/summarize-delivery`** — the agent writes the accountability artifact
   and opens the PR you review.

Three gates are yours: the spec, the split plan, the PR. Everything else is
the agent's, and all of it is written down.

## Why it works

- **Gates, not vibes.** A spec or plan exports only after it converges.
- **The agent never confirms itself.** Anything it proposes stays proposed
  until you confirm it.
- **Nothing is deleted to go green.** Unknowns are parked, questions are
  resolved, out-of-milestone targets are deferred, all on the record.
- **Ledgers are append-only and filed on the spot.** Deviations, evidence,
  behavior deltas and reasoning lapses are recorded the moment they happen.

What devague never does:

- **Call an LLM.** The CLI is deterministic and fully unit-tested.
- **Run a test.** Tests run agent-side; devague records the result.
- **Orchestrate agents.** It describes the dependency graph; the skill does
  the fan-out.

## What lands where

| Path | Written by | Git |
|------|-----------|-----|
| `.devague/frames/<slug>.json` | `/scope`, `/think`, `/challenge` | committed |
| `.devague/plans/<slug>.json` | `/spec-to-plan` | committed |
| `.devague/deliveries/<plan-slug>.json` | `/deviate`, `/validate-delivery` | committed |
| `.devague/reviews/`, `.devague/questions/` | review and decision working files | gitignored (devague adds the rule) |
| `docs/specs/<date>-<slug>.md` | `/think` export | committed — the spec |
| `docs/plans/<date>-<slug>.md` | `/spec-to-plan` export, `/assign-to-workforce` split | committed — the plan and split |
| `docs/deliveries/<date>-<slug>.md` | `/summarize-delivery` | committed — what actually shipped |
| `docs/current-spec.md` | `/summarize-delivery` (`devague today`) | committed — what the app does now |

See also:

- `docs/skills.md` — the eight skills in long form.
- `docs/spec-contract.md` — every record kind and move contract.
- `CLAUDE.md` — how this repo drives itself with devague.
