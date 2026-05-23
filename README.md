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

## Driving it from an agent

Inside AgentCulture, an assistant drives this CLI through two operator skills —
**`/think`** (idea→spec) and **`/spec-to-plan`** (spec→plan) — which add a
portable wrapper and a `status` next-move helper over the convergence gate. The
CLI is the deterministic affordance; the agent decides the next move. See
`CLAUDE.md` for that workflow and `docs/superpowers/specs/` for the design docs.
