# devague

**`devague` is a command-line tool** that turns a vague feature idea into a
buildable **spec**, then that spec into a buildable **plan** — by working
backwards, then forwards. It is a small, deterministic Python CLI (no LLM calls
inside it, fully unit-tested) — not an agent, service, or daemon. You install it
and run `devague` from the repository you are speccing; state is plain JSON under
`.devague/`.

```text
vague idea ──▶ buildable spec ──▶ buildable plan ──▶ build
```

## Install

```bash
uv tool install devague      # or: pipx install devague / pip install devague
devague --version
```

## Two engines, one CLI

- **Frame engine** (idea→spec) — start from the announcement ("pretend it
  shipped"), capture and pressure-test claims, park open vagueness, and `export`
  a spec only once the frame *converges*. Flat verbs: `devague new` /
  `capture` / `interrogate` / `confirm` / `converge` / `export` / …
- **Plan engine** (spec→plan) — seed a plan from a converged frame, cover every
  target with tasks that carry acceptance criteria and an acyclic dependency
  order, and `export` a plan only once it *converges*. Nested group:
  `devague plan new` / `task` / `cover` / `converge` / `export` / …

Run `devague learn` (or `devague plan learn`) to learn the method, and `devague
explain <move>` for any single move.

## Human Review Loop

LLM-proposed claims and honesty conditions stay `proposed` until **you**
confirm them — that anti-fabrication rule is the point of the method. The review
loop makes that human step ergonomic at scale:

```bash
devague review                 # list every proposed (unconfirmed) item, with ids
devague review --json          # same, structured
devague confirm c2 h1 h3       # confirm many ids in one transactional call
devague reject c4 c5           # reject many ids in one call
devague confirm --from-review .devague/reviews/<slug>.md   # apply an edited review file
```

`review` is **not** gated on convergence and never mutates state. It writes a
durable, explicitly non-authoritative artifact you can review out of band, then
apply: each item is emitted with a `pending` marker — change it to `confirm` or
`reject` and feed the file back with `confirm --from-review`. `pending` lines are
never auto-confirmed; a batch is transactional (one bad id ⇒ nothing changes).

Open questions / pending decisions live as durable working state too:

```bash
devague question "should batch confirm be transactional?"   # record a pending decision
devague question --list                                     # review them
devague question --resolve q1 --decision "yes, transactional"
```

Applying a resolved decision into the frame stays an explicit move (e.g.
`devague capture --kind decision "…"` then `devague confirm`).

### `.devague/` — what's committed vs working state

| Path | Committed? |
|------|-----------|
| `.devague/frames/`, `.devague/plans/` | yes — the converged frame/plan state |
| `.devague/reviews/<slug>.md` | no — local review working state |
| `.devague/questions/<slug>.md` | no — local pending-decision working state |
| `.devague/current`, `.devague/current_plan` | no — local pointers |

devague keeps `reviews/` and `questions/` out of git for you (it manages
`.gitignore`). Promote one into `docs/` only if you intentionally want it
committed.

## Driving it from an agent

Inside AgentCulture, an assistant drives this CLI through two operator skills —
**`/think`** (idea→spec) and **`/spec-to-plan`** (spec→plan) — which add a
portable wrapper and a `status` next-move helper over the convergence gate. The
CLI is the deterministic affordance; the agent decides the next move. See
`CLAUDE.md` for that workflow and `docs/superpowers/specs/` for the design docs.
