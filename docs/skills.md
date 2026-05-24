# Authoring devague's operator skills

This is the canonical guide for **authoring the three devague operator skills**
in an agent runtime — what files they need, where they live, the entry-point
shape, and the contract between a skill and devague's state. It is the long-form
companion to `devague learn skills`, which surfaces a condensed, always-available
version of the same recipe.

These three skills are devague's **outbound** skills — devague is their
origin/upstream (it dogfoods them to drive its own CLI), and steward re-vendors
them to the rest of the AgentCulture mesh under the `cite, don't import` policy.
See [`skill-sources.md`](skill-sources.md) for the provenance map. This guide is
about *creating* them in a runtime that doesn't have them yet.

## Consent — instructions for the assisting agent

devague **never writes skill files**; it stays a deterministic, non-orchestrating
CLI (#20). *You*, the agent, create the files — with the user in the loop:

- If the user explicitly asked you to set up or learn the operator skills,
  create them now using the recipe below.
- If you reached this by default (for example a bare `devague learn`), **ask the
  user for permission** before creating anything.
- **Never overwrite** an existing skill of the same name. If
  `<skills>/<name>/` already exists, stop and surface the conflict to the user
  instead of clobbering it.

## Minimum file structure

Each skill is one directory in your runtime's skills folder. For the Claude Code
backend that is `.claude/skills/<name>/`:

```text
<skills>/<name>/
├── SKILL.md                 # YAML frontmatter + the operating doc
└── scripts/
    └── <name>.sh            # portable CLI resolver (executable)
```

`SKILL.md` opens with YAML frontmatter:

```yaml
---
name: <name>
description: >
  One paragraph — what the skill does, when to use it (the trigger phrases),
  and that it is authored in agentculture/devague.
type: command
---
```

`type: command` is **required by the culture/agex backends** — a `SKILL.md`
without it is *silently skipped* by `backends/claude_code/probe.py`. It is
harmless on the `claude-code` backend, so always include it for portability.

The body of `SKILL.md` (after the frontmatter) is the operating doc: a short
intro, a "How to run" section, a moves/commands table, the hard rules, the
output contract, and a worked example. The three canonical skills are the
reference for this shape — copy from the sources linked below rather than
inventing structure.

## The entry-point script — portable CLI resolver

`scripts/<name>.sh` resolves the devague CLI portably and **forwards every move
verbatim**, so the CLI's own parser owns the surface and new devague moves work
without editing the script. The resolution order is:

1. an installed `devague` on `PATH` (the normal mesh case);
2. else `uv run devague` when inside a devague checkout (walk up to a
   `pyproject.toml` whose `name = "devague"`);
3. else print the hint `uv tool install devague` and exit non-zero.

The shape (copy the exact script from the per-skill source — don't hand-write it):

```bash
#!/usr/bin/env bash
set -euo pipefail

DEVAGUE=()
resolve_devague() {
    if command -v devague >/dev/null 2>&1; then
        DEVAGUE=(devague)            # installed tool — the normal mesh case
        return 0
    fi
    # Local-dev fallback: inside the devague checkout, run via uv.
    local dir="$PWD"
    while [ -n "$dir" ] && [ "$dir" != "/" ]; do
        if [ -f "$dir/pyproject.toml" ] \
            && grep -q '^name = "devague"' "$dir/pyproject.toml" 2>/dev/null; then
            command -v uv >/dev/null 2>&1 && { DEVAGUE=(uv run devague); return 0; }
            break
        fi
        dir=$(dirname "$dir")
    done
    echo "error: devague CLI not found." >&2
    echo "hint: install it with \`uv tool install devague\`." >&2
    return 1
}

resolve_devague
exec "${DEVAGUE[@]}" "$@"
```

`assign-to-workforce` adds one orchestration layer on top of this resolver (a
`split-plan` subcommand that renders `devague plan waves --json` as a human-facing
table); the underlying `waves` call is still forwarded verbatim.

## The skill ↔ devague contract

A skill drives the deterministic CLI and adds no business logic of its own:

- **Drive devague through its moves; never edit `.devague/` state by hand.** The
  CLI owns the frame/plan JSON under `.devague/`. A skill reads results from
  stdout (`--json` for structured payloads) and acts on them — it does not poke
  at the store directly.
- **LLM-proposed claims and honesty conditions stay `proposed`.** Confirmation is
  a user-only decision; the agent surfaces proposals and lets the user confirm or
  reject. This anti-fabrication contract is what makes convergence mean something
  (see [`llm-guidance.md`](llm-guidance.md)).
- **Three human gates only:** the exported spec, the implementation split plan
  (task map + per-task agent/model proposal + go/no-go), and the final PR.
  devague never orchestrates — it only *describes* the dependency graph via
  `devague plan waves` (#20). The fan-out, worktree management, and TDD-gated
  merges live in the `assign-to-workforce` skill and the operating agent, not in
  the CLI and not in a CI runner.

## The three operator skills

| Skill | Leg | What it drives |
|-------|-----|----------------|
| `think` | idea → spec (working backwards) | the flat `devague <move>` verbs |
| `spec-to-plan` | spec → plan (working forwards) | the `devague plan <move>` group |
| `assign-to-workforce` | plan → parallel implementation | reads `devague plan waves` (read-only) |

### `think` — idea → buildable spec

Start from the announcement ("pretend it shipped — what would you announce?"),
build an Announcement Frame by capturing and classifying claims, pressure-test
them with honesty conditions and hard questions, park genuine unknowns as
first-class open vagueness, and `export` a spec only once the frame **converges**.

- Source:
  [`.claude/skills/think/`](https://github.com/agentculture/devague/blob/main/.claude/skills/think/SKILL.md)
  (`SKILL.md` + `scripts/think.sh`).

### `spec-to-plan` — converged spec → buildable plan

Seed a plan from a **converged** frame (`devague plan new --frame <slug>`), add
tasks that cover every coverage target with acceptance criteria and an acyclic
dependency order, park unknowns as first-class risks, and `export` only once the
plan converges. Coaches small, file-disjoint, TDD-accepted tasks so the
downstream fan-out can run wide waves.

- Source:
  [`.claude/skills/spec-to-plan/`](https://github.com/agentculture/devague/blob/main/.claude/skills/spec-to-plan/SKILL.md)
  (`SKILL.md` + `scripts/spec-to-plan.sh`).

### `assign-to-workforce` — converged plan → parallel implementation

Reads `devague plan waves` (deterministic, read-only scheduling metadata) and
fans out independent tasks to **one agent per task per wave in isolated git
worktrees**, with **main-agent TDD-gated merges** (the task's tests pass before
*and* after the merge). Exactly three human gates; the final PR uses the `cicd`
skill (`agex pr open`).

- Source:
  [`.claude/skills/assign-to-workforce/`](https://github.com/agentculture/devague/blob/main/.claude/skills/assign-to-workforce/SKILL.md)
  (`SKILL.md` + `scripts/assign-to-workforce.sh`).

## See also

- `devague learn skills` / `devague learn skills:all` / `devague learn
  skills:<name>` — the condensed, always-available form of this guide, with the
  canonical source URLs for each skill (works for an agent operating an installed
  devague with no checkout).
- [`llm-guidance.md`](llm-guidance.md) — the portable operating contract every
  operator skill upholds.
- [`skill-sources.md`](skill-sources.md) — provenance and the `cite, don't
  import` vendoring policy.
