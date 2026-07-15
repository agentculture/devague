# Authoring devague's operator skills

This is the canonical guide for **authoring the devague operator skills**
in an agent runtime — what files they need, where they live, the entry-point
shape, and the contract between a skill and devague's state. It is the long-form
companion to `devague learn skills`, which surfaces a condensed, always-available
version of the same recipe. (`devague learn skills` currently teaches the three
CLI-driving skills; the recipe for the method-only `scope` skill joins it when
its `devague scope` CLI move lands — see the #53 build plan, tasks t3/t10/t11.)

These skills are devague's **outbound** skills — devague is their
origin/upstream (it dogfoods them to drive its own CLI), and guildmaster re-vendors
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
- **Instructions flow verbatim, never invented.** Claims, honesty conditions,
  and plan tasks may carry an optional `instruction` field — how to verify or
  implement that item (frame side: `capture --instruction` / `interrogate
  --instruction`, #53 t4; plan side: `plan task --instruction` / `plan instruct
  <tN>`, #53 t5). Setting or changing an instruction on an already-confirmed
  item flips it back to `proposed` — the user re-confirms, same as any other
  proposed content. `assign-to-workforce` is meant to quote a task's
  instruction and acceptance criteria verbatim into the per-subagent brief
  (#53 t9/t13) — no operator paraphrasing.

## The operator skills

The **seven-leg flow**, with the two audiences each leg serves — **operators**
(the main agent driving the CLI move by move) and the **humans** who own the
three standing gates (the exported spec, the go/no-go on the implementation
split plan — including any mid-run deviation approved against it — and the
final PR review):

| Skill | Leg | What it drives |
|-------|-----|----------------|
| `scope` | idea → explored scope (the optional opening leg) | read-only exploration; findings land via existing `devague` moves |
| `think` | idea → spec (working backwards) | the flat `devague <move>` verbs |
| `challenge` | "a risk-scaled blind-spot discovery pass over a converged, exported frame BETWEEN /think and /spec-to-plan" | "pressure-test the spec through structured lenses, route every finding back through the existing deterministic moves as proposed-only content the human adjudicates" |
| `spec-to-plan` | spec → plan (working forwards) | the `devague plan <move>` group |
| `assign-to-workforce` | plan → parallel implementation | reads `devague plan waves` and `devague plan deliverables` (read-only) |
| `deviate` | execution-time — an in-flight fan-out diverges from the confirmed plan | the `devague deviate` move (`--list [--json]`, `--confirm`/`--reject`), backed by the delivery store |
| `summarize-delivery` | execution → accountability artifact (the delivery-side closure leg) | starts from `devague summary` / `devague deviate --list`; reads plan / git / PR / test evidence (read-only) |

### `scope` — idea → explored scope (method-only)

Survey the surfaces an idea touches **before** framing it: enumerate candidates,
explore each read-only, classify findings (in scope / out of scope / genuinely
unknown), then seed the `/think` frame with `boundary` / `non_goal` /
`assumption` claims that **cite what was explored**. Optional by size — small
ideas skip straight to `/think` (no wizard). From the sharper end-to-end method
spec ([devague#53](https://github.com/agentculture/devague/pull/53)).

The skill ships no entry-point script of its own, but the CLI surface it
records into is live: `Frame.scope_entries` / `ScopeEntry` (`id`, `surface`,
`finding`, `seeds`) shipped in #53 task t1, and the deterministic
`devague scope` move that writes it (`devague scope "<surface>"
--finding "<text>" [--seeds <claim-id> ...]`, plus `scope --list [--json]`)
shipped in #53 task t3; this skill's `devague learn skills` authoring recipe
lands with tasks t10/t11.

- Source:
  [`.claude/skills/scope/`](https://github.com/agentculture/devague/blob/main/.claude/skills/scope/SKILL.md)
  (`SKILL.md` only).

### `think` — idea → buildable spec

Start from the announcement ("pretend it shipped — what would you announce?"),
build an Announcement Frame by capturing and classifying claims, pressure-test
them with honesty conditions and hard questions, park genuine unknowns as
first-class open vagueness, and `export` a spec only once the frame **converges**.

- Source:
  [`.claude/skills/think/`](https://github.com/agentculture/devague/blob/main/.claude/skills/think/SKILL.md)
  (`SKILL.md` + `scripts/think.sh`).

### `challenge` — risk-scaled blind-spot discovery pass (method-only)

Quoted verbatim from the shipped `SKILL.md` frontmatter `description` (not
paraphrased, per the doc-sweep instruction that shipped it):

> Run a risk-scaled blind-spot discovery pass over a converged, exported
> frame BETWEEN /think and /spec-to-plan (the seventh origin skill, third
> leg in flow order): pressure-test the spec through structured lenses,
> route every finding back through the existing deterministic moves as
> proposed-only content the human adjudicates, and on a clean pass record
> the examined lenses/surfaces and residual uncertainty — never a claim
> that there are no unknown unknowns. Use when the user says "challenge
> this spec", "blind-spot pass", "pressure-test the frame", "what are we
> missing", "unknown unknowns", or after /think exports and before
> `devague plan new`. Authored and maintained in agentculture/devague
> (origin = devague); guildmaster pulls this skill from here and broadcasts
> it to the AgentCulture mesh — it is NOT vendored from guildmaster like
> the inbound skills here.

Concretely: it sweeps structured lenses (adjacent systems, unstated
assumptions, overlooked actors/lifecycle stages/failure modes, security/
migration/concurrency/reversibility, missing observability/rollback, cheap
probes) against the exported spec, routes findings through the existing
deterministic moves (`capture` / `interrogate` / `question` / `park` /
`devague scope` / `devague plan risk`) as `--origin llm`-proposed content the
human adjudicates, then reconverges and re-exports the same dated spec file.
Mandatory but proportional — lightweight for ordinary work, rigorous when an
escalation signal (migrations, security-sensitive work, distributed state,
hardware, destructive or hard-to-reverse changes, concurrency hazards, any
data-loss surface) applies. Not a fourth standing gate: findings are
adjudicated inside the existing spec gate, mirroring how `/deviate` amends
gate 2 rather than adding one.

The skill ships no entry-point script of its own — it drives the same flat
`devague <move>` verbs `/think` already uses, so no new CLI surface,
subparser, or state model exists to resolve (#20). New in 0.19.0.

- Source:
  [`.claude/skills/challenge/`](https://github.com/agentculture/devague/blob/main/.claude/skills/challenge/SKILL.md)
  (`SKILL.md` only).

### `spec-to-plan` — converged spec → buildable plan

Seed a plan from a **converged** frame (`devague plan new --frame <slug>`), add
tasks that cover every coverage target with acceptance criteria and an acyclic
dependency order, park unknowns as first-class risks, and `export` only once the
plan converges. Coaches small, file-disjoint, TDD-accepted tasks so the
downstream fan-out can run wide waves. The per-task `instruction` field and the
`plan task --instruction` / `plan instruct <tN>` moves shipped in #53 t2/t5;
acceptance criteria remain the testable contract, instructions the working
guidance carried verbatim to the workforce.

- Source:
  [`.claude/skills/spec-to-plan/`](https://github.com/agentculture/devague/blob/main/.claude/skills/spec-to-plan/SKILL.md)
  (`SKILL.md` + `scripts/spec-to-plan.sh`).

### `assign-to-workforce` — converged plan → parallel implementation

Reads `devague plan waves` (deterministic, read-only scheduling metadata) and
fans out independent tasks to **one agent per task per wave in isolated git
worktrees**, with **main-agent TDD-gated merges** (the task's tests pass before
*and* after the merge). Exactly three human gates; the final PR uses the `cicd`
skill (`agex pr open`). Each subagent's brief quotes its task's fields verbatim
from `plan show --json` / the exported plan-md — including the per-task
`instruction` — never an operator paraphrase. The `split-plan` subcommand
renders the implementation split plan as a four-column Wave / Task / Model /
Task summary table (real, editable model tokens; 72-character summary
truncation, #69) with has-instruction and acceptance-criteria-count markers,
and a trailing **End state** section quoting `devague plan deliverables`
verbatim (#70) — so gate 2's go/no-go sees what the plan actually produces, not
just its task map. Degrades gracefully to a one-line version hint on a
`devague` too old to have the `deliverables` verb.

- Source:
  [`.claude/skills/assign-to-workforce/`](https://github.com/agentculture/devague/blob/main/.claude/skills/assign-to-workforce/SKILL.md)
  (`SKILL.md` + `scripts/assign-to-workforce.sh`).

### `deviate` — execution-time leg: an in-flight fan-out diverges from the plan

Runs *during* an `/assign-to-workforce` run, at the moment execution must
diverge from the confirmed plan: stop the run, present what/why/what-it-affects
to the human, get explicit approval, then record the divergence via the
deterministic `devague deviate` move before resuming. Not a fourth standing
gate — the human owner of gate 2 (the implementation split plan) amending it
mid-flight. `--origin llm` lands `proposed`; only the user
`--confirm`s/`--reject`s. Deviation records persist as a first-class,
append-only ledger in `.devague/deliveries/<plan-slug>.json` and are the
connective tissue `/summarize-delivery` quotes by `dN` id instead of
reconstructing drift from memory. New in 0.18.0.

- Source:
  [`.claude/skills/deviate/`](https://github.com/agentculture/devague/blob/main/.claude/skills/deviate/SKILL.md)
  (`SKILL.md` only).

### `summarize-delivery` — execution run → accountability artifact

The delivery-side closure leg: after `/assign-to-workforce` executes a plan —
complete, partial, or **failed** — record what actually shipped as a committed
accountability artifact at `docs/deliveries/<created-date>-<slug>.md`. It
separates planned work from actual delivery, captures mid-work decisions and
plan drift, and states every delivery claim with a confidence level and evidence
pointers — a claim without evidence is marked `unverified`, never asserted as
done. Method-only in v1 (a `SKILL.md` + an eight-section template; no
entry-point script and no new CLI verb — the deterministic CLI surface is
unchanged, #20). New in 0.17.0. As of 0.18.0 it starts from the
`devague summary` (optionally `--pr`) skeleton and quotes every approved
`/deviate` record by its `dN` id as recorded ground truth for Drift From Plan
and Mid-work Decisions, instead of reconstructing execution-time drift from
memory.

- Source:
  [`.claude/skills/summarize-delivery/`](https://github.com/agentculture/devague/blob/main/.claude/skills/summarize-delivery/SKILL.md)
  (`SKILL.md` + an eight-section delivery-summary template).

## See also

- `devague learn skills` / `devague learn skills:all` / `devague learn
  skills:<name>` — the condensed, always-available form of this guide, with the
  canonical source URLs for each skill (works for an agent operating an installed
  devague with no checkout).
- [`llm-guidance.md`](llm-guidance.md) — the portable operating contract every
  operator skill upholds.
- [`skill-sources.md`](skill-sources.md) — provenance and the `cite, don't
  import` vendoring policy.
