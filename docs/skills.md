# Authoring devague's operator skills

This is the canonical guide for **authoring the devague operator skills**
in an agent runtime — what files they need, where they live, the entry-point
shape, and the contract between a skill and devague's state. It is the long-form
companion to `devague learn skills`, which surfaces a condensed, always-available
version of the same recipe. (`devague learn skills` teaches all **eight** skills
in flow order — three CLI-driving ones that ship a
`scripts/<name>.sh` resolver, and five method-only ones that are a `SKILL.md`
alone.)

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

### Shared conventions

Three pieces of text are shared across every skill's `SKILL.md`. This is
their single definition — each per-skill section below points here instead
of restating them, and every skill copies these verbatim rather than
reinventing its own wording.

**Hand-off section.** Each `SKILL.md`'s operating doc closes with a
`## Before and after this leg` section, using this two-line template:

```text
Previous leg: <skill name, or "nothing precedes">
Next leg: <skill name, or "nothing follows">
```

The terminal leg of the flow (currently `summarize-delivery`) writes
literally `nothing follows` for "Next leg"; the opening leg (currently
`scope`) writes literally `nothing precedes` for "Previous leg".

**Freshness rule.** Every skill's `## Hard rules (do not violate)` section
includes this sentence verbatim:

> File the record the moment the thing happens, never at closeout — written
> late is written flattering (issue 97).

**Flow diagram.** The eight-leg flow is defined once, here, as this fenced
block — the only diagram a skill may copy into its own `SKILL.md` (it
matches `validate-delivery/SKILL.md` lines 27-29 byte for byte):

```text
scope -> think -> challenge -> spec-to-plan -> assign-to-workforce ->
deviate -> validate-delivery -> summarize-delivery
```

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
table, and with `--write` also persists it as a durable gate-2 artifact); the
underlying `waves` call is still forwarded verbatim.

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
  proposed content. `assign-to-workforce` quotes a task's instruction and
  acceptance criteria verbatim into the per-subagent brief, straight from the
  `plan waves --json` payload (#53 t9/t13) — no operator paraphrasing.
- **Correct in place; never delete to make a gate go green.** `devague amend`
  (claim), `scope --amend` (finding), and `plan risk --amend` (risk text) fix
  wrong content without churning ids — so honesty conditions, hard questions,
  instructions, and inbound `--seeds` references stay pointed at something
  real (#84). Closing something out is a separate, evidence-bearing move:
  `park --resolve`, `interrogate <cN> --resolve <qN>`, `plan risk --resolve`,
  and `plan defer` each keep the item on the record with the decision that
  closed it.

## The operator skills

The **eight-leg flow**, with the two audiences each leg serves — **operators**
(the main agent driving the CLI move by move) and the **humans** who own the
three standing gates (the exported spec, the go/no-go on the implementation
split plan — including any mid-run deviation approved against it — and the
final PR review):

| Skill | Leg | What it drives |
|-------|-----|----------------|
| `scope` | idea → explored scope (the optional opening leg) | read-only exploration (inline, or fanned out to sonnet subagents at 5+ surfaces); findings land via existing `devague` moves, always run by the main agent |
| `think` | idea → spec (working backwards) | the flat `devague <move>` verbs |
| `challenge` | "a risk-scaled blind-spot discovery pass over a converged, exported frame BETWEEN /think and /spec-to-plan" | "pressure-test the spec through structured lenses, route every finding back through the existing deterministic moves as proposed-only content the human adjudicates" |
| `spec-to-plan` | spec → plan (working forwards) | the `devague plan <move>` group |
| `assign-to-workforce` | plan → parallel implementation | reads `devague plan waves` and `devague plan deliverables` (read-only); `split-plan --write` persists the gate-2 artifact |
| `deviate` | execution-time — an in-flight fan-out diverges from the confirmed plan | the `devague deviate` move (`--list [--json]`, `--confirm`/`--reject`), backed by the delivery store |
| `validate-delivery` | execution → evidence (the execution-to-evidence leg) — run the plan's behavioral tests agent-side once waves merge | `devague oblige` / `devague evidence` / `devague delta` (record-only; the CLI never runs a test); unmet is unmet |
| `summarize-delivery` | execution → accountability artifact (the delivery-side closure leg) | starts from `devague summary` / `devague deviate --list` / `devague lapse --list`; reads plan / git / PR / test evidence (read-only) |

### `scope` — idea → explored scope (method-only)

Survey the surfaces an idea touches **before** framing it: enumerate candidates,
explore each read-only, classify findings (in scope / out of scope / genuinely
unknown), then seed the `/think` frame with `boundary` / `non_goal` /
`assumption` claims that **cite what was explored**. Optional by size — small
ideas skip straight to `/think` (no wizard). From the sharper end-to-end method
spec ([devague#53](https://github.com/agentculture/devague/pull/53)).

**How the exploration step runs (new in 0.21.0, #79/#91).** The candidate
count decides the shape: **4 or fewer** surfaces are explored inline and
serially by the main agent, exactly as before — spinning up subagents to read
three files costs more than it saves. **5 or more** fan out one **read-only
exploration subagent per surface** (or per tight cluster of related surfaces),
defaulting every subagent to the smaller tier, **sonnet** — a default, not a
ceiling: escalate one subagent when that specific surface genuinely needs
synthesis, never the whole survey. The load-bearing rule of the fan-out is
that **subagents explore and report; they never run a `devague` move**. Each
returns a touched / not-touched / unknown verdict with the file, line, or
command output that grounds it, and the main agent alone runs every `capture`
/ `scope` / `question` / `park` call from that reported evidence — so
provenance and the anti-fabrication contract stay in one place instead of
being scattered across subagent transcripts the user never sees. The recorded
finding still cites the actual surface, never "a subagent explored this".

The skill ships no entry-point script of its own, but the CLI surface it
records into is live: `Frame.scope_entries` / `ScopeEntry` (`id`, `surface`,
`finding`, `seeds`) and the deterministic `devague scope` move that writes it
— `devague scope "<surface>" --finding "<text>" [--seeds <claim-id or
hard-question-id> ...]`, plus `scope --list [--json]` and, since 0.21.0,
`scope --amend <sN> --finding "<text>"` to correct a finding in place (#84).
`--seeds` accepts claim ids (`c*`) **and** claim-attached hard-question ids
(`q*`, #84) — the latter is the branch this skill's routing table sends a
"genuinely unknown, needs a user decision" finding down, whose provenance link
was previously unrecordable. An unknown seed id is refused with a hint.

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

- Source:
  [`.claude/skills/scope/`](https://github.com/agentculture/devague/blob/main/.claude/skills/scope/SKILL.md)
  (`SKILL.md` only).

### `think` — idea → buildable spec

Start from the announcement ("pretend it shipped — what would you announce?"),
build an Announcement Frame by capturing and classifying claims, pressure-test
them with honesty conditions and hard questions, park genuine unknowns as
first-class open vagueness, and `export` a spec only once the frame **converges**.
Since 0.21.0 the two moves that used to have no exit exist: `devague amend <cN>`
corrects a claim without losing its id (and its honesty conditions, hard
questions, `instruction`, and inbound scope seeds), and `devague interrogate
<cN> --resolve <qN> --decision "<text>"` closes out a blocking hard question —
before that, one blocking question deadlocked `converge` permanently
(#84, #48/#52).

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

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
If the pass notices its own reasoning degraded while sweeping — not a finding
about the spec, but the agent's own self-report — it files that the same
moment via `devague lapse --origin llm` instead (issue #97); adjudication is
`devague lapse --confirm`/`--reject`, exercised by the same human who already
owns the spec gate, not a new role. Mandatory but proportional — lightweight for ordinary work, rigorous when an
escalation signal (migrations, security-sensitive work, distributed state,
hardware, destructive or hard-to-reverse changes, concurrency hazards, any
data-loss surface) applies. Not a fourth standing gate: findings are
adjudicated inside the existing spec gate, mirroring how `/deviate` amends
gate 2 rather than adding one.

The skill ships no entry-point script of its own — it drives the same flat
`devague <move>` verbs `/think` already uses, so no new CLI surface,
subparser, or state model exists to resolve (#20). New in 0.19.0.

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

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

Since 0.21.0: `plan confirm` / `plan reject` take many ids in one transactional
call like the frame side, and argument errors inside the group point at
`devague plan explain <move>` (#86); `--dep` / `depend --on` refuse a
self-dependency or unknown id at creation rather than surfacing it later as a
`waves` cycle (#86); `cover` / `--covers` validate against targets re-derived
from the **live** frame, so a target the frame grew after seeding is coverable
straight away (#90); and `plan defer <target-id> --reason "<text>"` deliberately
excludes a target that belongs to a later milestone, which is what makes a
milestone-scoped plan converge honestly instead of being covered by a task that
merely names it (#85).

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

- Source:
  [`.claude/skills/spec-to-plan/`](https://github.com/agentculture/devague/blob/main/.claude/skills/spec-to-plan/SKILL.md)
  (`SKILL.md` + `scripts/spec-to-plan.sh`).

### `assign-to-workforce` — converged plan → parallel implementation

Reads `devague plan waves` (deterministic, read-only scheduling metadata) and
fans out independent tasks to **one agent per task per wave in isolated git
worktrees**, with **main-agent TDD-gated merges** (the task's tests pass before
*and* after the merge). Every worktree lives under one repo-owned root beside
the repo directory — `<parent-of-repo>/.worktrees.<repo-name>/agent-<task-id>`
— never a shared `../worktrees/` (which collides across repos and plans, since
task ids restart at `t1`, and reads as deletable scratch space to anyone else)
and never inside the repo (where `git add -A` sweeps checkouts into the PR and
`git clean -fdx` destroys live agent work). Exactly three human gates; the final PR uses the `cicd`
skill (`agex pr open`). Each subagent's brief quotes its task's fields verbatim
from the **`devague plan waves --json` payload** — the single source, whose
top-level `tasks` object carries each task's `summary`, `instruction`,
`acceptance_criteria`, and `covers`, so a brief needs no external context and
never an operator paraphrase (neither `plan show --json` nor the exported
plan-md is read alongside it). The `split-plan` subcommand
renders the implementation split plan as a four-column Wave / Task / Model /
Task summary table (real, editable model tokens; 72-character summary
truncation, #69) with has-instruction and acceptance-criteria-count markers,
and a trailing **End state** section quoting `devague plan deliverables`
verbatim (#70) — so gate 2's go/no-go sees what the plan actually produces, not
just its task map. Degrades gracefully to a one-line version hint on a
`devague` too old to have the `deliverables` verb.

**No devague move runs inside a task worktree — not just `devague plan`
(issue #97).** If a task agent notices its own reasoning degraded (a skipped
check, an assumption standing in for a real measurement, …), it reports that
in its transcript rather than filing it; the **main agent** files the record
after reconciling the worktree (`devague lapse "<what>" --code <code>
--origin llm`) the same way exploration subagents in `/scope` report rather
than run a `devague` move themselves (#79/#91). Adjudicating a filed lapse is
`devague lapse --confirm`/`--reject`, exercised by the same human who owns
gate 2/3 — no new role.

**The durable gate-2 artifact (`split-plan --write`, new in 0.21.0, #82).**
The exported spec (`docs/specs/*.md`) and the exported plan
(`docs/plans/*.md`) both persist; gate 2 previously survived only in
conversation. `--write` closes that gap by persisting the same content to
`docs/plans/<created-date>-<slug>-split.md` — beside the plan-md, using the
same date-prefix convention derived from the plan's own `created` timestamp,
so re-running updates that one file in place instead of spawning a dated
duplicate. The file carries the full per-wave/per-task content quoted verbatim
from `plan waves --json` (one `## Wave N` heading per wave, one
`### <task-id> — <summary>` per task), a `Task | Owner | Model` assignment
table that the script **reads back** before regenerating — so a human's edited
Owner/Model cell survives the next `--write`, matched by task id, rather than
resetting to the `sonnet` default — and the same End state section. It is an
**artifact-only** change: no plan-schema change, no new `devague` verb, and
`plan waves` / `show` / `deliverables` stay read-only exactly as before. Only
the assignment table is meant to be hand-edited; the wave/task sections above
it are fully regenerated every run. Present the file (or plain `split-plan`'s
stdout twin) at the go/no-go either way — `--write` keeps a committed record
of what was approved, it does not replace the live review.

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

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

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

- Source:
  [`.claude/skills/deviate/`](https://github.com/agentculture/devague/blob/main/.claude/skills/deviate/SKILL.md)
  (`SKILL.md` only).

### `validate-delivery` — execution-to-evidence leg: run the plan's behavioral tests

Runs *after* a plan's waves merge (via `/assign-to-workforce`, plus any
`/deviate` records) and *before* `/summarize-delivery` closes the loop: the
agent runs the confirmed plan's behavioral tests agent-side, then files what
it found as record-only devague entries — `devague oblige` (mark a claim's
behavioral obligation), `devague evidence` (obligation met by this test,
asserting this behavior, outcome pass or fail), and `devague delta` (a
behavioral added/amended/removed record with provenance back to the claim or
approved deviation and forward to its evidence). The CLI never runs a test
itself (issue #20); `llm`-origin filings land `proposed`, same
anti-fabrication contract as `deviate` and `lapse`. A failing or unchecked
outcome is filed and reported exactly as such — unmet is unmet, never
rounded up. Behavioral tests are identified either by a pytest marker (e.g.
`@pytest.mark.behavioral`) or a dedicated folder (e.g. `tests/behavioral/`
or `behavioral-tests/`) — both conventions are defined in the skill for
consuming repos to pick from. Motivating record: issue
[`agentculture/devague#97`](https://github.com/agentculture/devague/issues/97)
("Four graders failed in that cycle... Every one was found by reading data
afterwards; none by a test failing") and issue
[`agentculture/devague#107`](https://github.com/agentculture/devague/issues/107)
("Suggestion: behavioral validation and a derived current spec"). The exact
`oblige` / `evidence` / `delta` CLI surface ships in a parallel task; this
skill is written against those verb names with minimal command examples so
reconciliation stays cheap.

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

- Source:
  [`.claude/skills/validate-delivery/`](https://github.com/agentculture/devague/blob/main/.claude/skills/validate-delivery/SKILL.md)
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
memory. It also reads `devague lapse --list` (issue #97): an **approved**
reasoning-degradation lapse grounds a Delivery Claims confidence level
honestly instead of letting it default to `high`; a still-**proposed** one is
pending, not yet evidence; and adjudicating one (`devague lapse --confirm`/
`--reject`) is the same gate-owning human's job, never this skill's.

Its `SKILL.md` uses the shared hand-off section, freshness rule, and flow
diagram defined once in [Shared conventions](#shared-conventions) — it does
not restate them.

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
