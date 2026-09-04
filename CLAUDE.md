# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

**Every verb gains a next-move stderr hint (next-leg-hints).** After each
successful, non-exempt move, the CLI now prints one line to stderr —
`next: <recommended move>` — naming what to run next (a leg-ending verb like
`export` or `summary` names the next skill/command; everything else falls
through to `devague status` / `devague plan status`). `status` and `plan
status` are exempt, since reporting the next move is already their whole
purpose. Emission is centralized in `devague/cli/_hints.py`, called exactly
once from dispatch — no command module emits it itself — so stdout (including
every `--json` payload) is untouched. The default per-verb text is
overrideable via `[tool.devague]` in `pyproject.toml` (`hints = false` turns
hints off globally; `[tool.devague.hints]` replaces one verb's text) or the
`DEVAGUE_HINTS` environment variable (`off` / `0` / `false`; the environment
wins over `pyproject.toml`). `devague explain <move>` documents the override
for the leg-ending verbs (`export`, `deviate`, `evidence`, `delta`, `summary`,
`today`), and `devague learn`'s operating rules mention it.

History lives in `CHANGELOG.md`.

## Working-backwards method

The agent drives the **deterministic** CLI — no LLM calls inside the CLI
itself. The workflow:

1. `devague new "<announcement>"` — the announcement-first entry point. The
   canonical first question is *"What's the announcement?"* ("Pretend this
   shipped successfully — what would you announce to users, teammates, or
   yourself?"). Creates a Frame seeded with the announcement claim
   (auto-confirmed, since it comes from the user). `devague learn` documents the
   full ten-stage guided sequence plus the always-on **operating rules** (the
   anti-fabrication contract); the portable, agent-agnostic version of that
   contract lives in `docs/llm-guidance.md` (#19).
2. `devague capture --kind <kind> "<text>"` — add claims; LLM-proposed ones
   (`--origin llm`) land as `proposed` and require explicit user `confirm`.
   Correct a claim in place with `devague amend <cN> [--text] [--kind]
   [--reason]` (#84) — it keeps the id, so honesty conditions, hard questions,
   `instruction`, and inbound `scope --seeds` refs all stay pointed at
   something real; the superseded `(text, kind)` pair lands on
   `Claim.revisions` and a confirmed claim flips back to `proposed`.
3. `devague interrogate <claim-id>` — attach honesty conditions and hard
   questions; honesty conditions from the LLM are also `proposed`. A blocking
   hard question is closed out with `devague interrogate <cN> --resolve <qN>
   --decision "<text>"` (#48/#52) — a USER decision, the claim-level twin of
   `park --resolve`; without it a blocking question deadlocks `converge`
   forever.
4. `devague confirm <id>` / `reject` / `park` — **all honesty conditions
   routed through the user**; the agent must not auto-confirm LLM proposals.
   Rejecting a claim cascades onto its still-live honesty conditions and
   unresolved hard questions, echoing `(also rejected: h3, q1)` (#83).
5. `devague scope "<surface>" --finding "<text>" [--seeds <cN|qN> …]` — record
   pre-frame exploration as first-class provenance; `--seeds` takes claim ids
   *or* claim-attached hard-question ids (#84), and `scope --amend <sN>
   --finding` corrects a finding in place.
6. `devague converge` — evaluates the convergence gate; lists remaining gaps.
7. `devague export` — only succeeds after `converge` passes; writes a
   buildable spec-md to `docs/specs/`. Verbatim claim text is markdown-escaped
   at render time (`render/_md_safety.md_safe_text`, #87) — presentational
   only, the stored JSON is untouched. A confirmed claim named by an approved
   deviation's `--affects` renders a `contested by <dN>` marker (#92): the
   spec is never rewritten, it points forward to the deviation ledger.

Full design: `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`.

## Spec→plan method (the forward leg)

The **plan engine** is the structural peer of the frame engine — same chassis,
same anti-fabrication rules, no LLM inside the CLI. It is namespaced under the
`devague plan` subcommand group (the *skill* is `/spec-to-plan`; the CLI verb is
`plan` — they intentionally differ, mirroring how `/think` drives the flat
verbs). The workflow:

1. `devague plan new --frame <slug>` — seed a plan from a **converged** frame.
   Derives **coverage targets** (the frame's confirmed claims + honesty
   conditions). Refuses an unconverged frame; refuses to clobber an existing plan.
2. `devague plan task "<summary>" [--accept … --dep … --covers … --origin]` —
   add tasks; `--origin llm` lands `proposed` (user must `confirm` — and
   `plan confirm` / `plan reject` take many ids in one transactional call, #86).
   Refine with `accept` / `depend` (or `depend --remove` to cut an edge, #68) /
   `cover` / `instruct` / `amend` (edit a task's summary and/or replace/remove
   acceptance criteria by index, #68). Amending or demoting a CONFIRMED task
   flips it back to `proposed` and echoes that flip to stdout (#67). `--dep` /
   `depend --on` refuse a self-dependency or an unknown task id at creation
   (#86); `cover` / `--covers` validate against targets re-derived from the
   **live** frame, so a target the frame grew after seeding is coverable
   straight away (#90).
3. `devague plan risk "<text>" --kind <kind>` — park a genuine unknown as a
   first-class plan risk instead of guessing (`--resolve` closes one out;
   `--amend <rN> --text` corrects a stale one in place, #84).
4. `devague plan defer <target-id> --reason "<text>"` — deliberately exclude a
   coverage target from *this* plan's gate when it genuinely belongs to a later
   one (`--undo` reverses it, #85). A deferred target drops out of the gate,
   surfaces in `parked_items` labeled `deferred:`, and renders under
   `## Deferred targets` in the export. This is the honest alternative to
   faking coverage — never write a task that merely names a target.
5. `devague plan converge` — re-evaluates the gate **against the live frame**
   (catches frame drift); lists gaps. A plan converges when every target is
   covered by a confirmed task **or deliberately deferred**, every confirmed
   task has acceptance criteria, the dependency graph is acyclic, and no
   blocking risk remains.
6. `devague plan export` — only after `converge` passes; writes a buildable
   plan-md (topologically ordered) to `docs/plans/<created-date>-<slug>.md`.
7. `devague plan waves [--json]` — emit the plan's dependency graph as
   deterministic **scheduling metadata** (`{plan, waves}`): ordered batches of
   task ids that an external operator *could* fan out. Read-only,
   convergence-agnostic (works on an in-progress plan), and explicitly **not
   orchestration** — Devague describes the graph; it does not spawn subagents,
   manage worktrees, mark tasks done, or pick a backend (#20). A cyclic or
   dangling graph is refused via the plan-convergence dependency blockers.
8. `devague plan deliverables [--json]` — a read-only "end state" preview:
   the plan's confirmed announcement/after-state/success-signal claims
   verbatim from its live source frame, every terminal task (an active task no
   other active task depends on) with its acceptance criteria, and the
   surviving open items. Never refuses — shows a not-converged banner instead
   of gating, since previewing the end state is useful before convergence
   too (#70).

Both `devague export` and `devague plan export` prefix the written file with the
frame/plan creation date (`<YYYY-MM-DD>-<slug>.md`, #12), so re-exporting an
unchanged artifact overwrites the same file rather than spawning a duplicate.

Full design: `docs/superpowers/specs/2026-05-23-devague-spec-to-plan-design.md`.

## Subagent-driven implementation (assign-to-workforce)

**Converged plans execute in parallel via a cited `assign-to-workforce` skill**
that fans out independent tasks to subagents in isolated git worktrees, keeping
the devague CLI deterministic and non-orchestrating (#20).

### The three human gates

1. **Spec gate**: the exported frame/spec.
2. **Implementation split plan gate**: the plan tasks map, per-task subagent +
   model assignment, and the go/no-go decision on assigning the plan to the
   workforce. `split-plan --write` persists it as a durable artifact at
   `docs/plans/<created-date>-<slug>-split.md` (#82) — the peer of the
   exported spec and plan-md, which gate 2 previously lacked; hand-edited
   `Owner` / `Model` cells are read back and survive regeneration. A mid-run
   deviation (recorded via `devague deviate` and the cited `/deviate` skill)
   is **not** a fourth standing gate — it is the human owner of this gate
   approving an amendment to it in-flight.
3. **Final PR gate**: human code review of the merged result.

### Worktree contention safety

Each subagent runs in an isolated git worktree — one worktree per task per wave.
Same-file overlaps between tasks (which the dependency graph does not
guarantee to exclude) surface as merge conflicts at reconcile time, never as
live races. The main/operating agent reconciles each merge.

### Where worktrees live: `.worktrees.<repo-name>` (mandatory)

**Every worktree a fan-out creates goes under one repo-owned root beside the
repo directory** — `<parent-of-repo>/.worktrees.<repo-name>/agent-<task-id>`.
For this repo that is `../.worktrees.devague/`. Resolve it, never hardcode it:

```bash
repo_root=$(git rev-parse --show-toplevel)
wt_root="$(dirname "$repo_root")/.worktrees.$(basename "$repo_root")"
git worktree add "$wt_root/agent-<task-id>" -b agent/<task-id>
```

Two paths are **forbidden**, and each was in use here before this convention:

- **A shared `../worktrees/`** — in a multi-repo parent like `~/git/`, that
  directory belongs to nobody, so it reads as scratch space another agent or
  human may delete while your wave is live. Worse, task ids restart at `t1` in
  every repo and every plan, so `../worktrees/agent-t1` from two concurrent
  fan-outs is literally the same directory. The repo-named root makes
  ownership visible and collisions impossible.
- **Anything inside the repo** (`.worktrees/`, `.claude/worktrees/`) — N full
  checkouts inside the tree you are about to commit means `git add -A` sweeps
  them into the PR and `git clean -fdx` destroys live agent work.

Clean up with `git worktree remove "$wt_root/agent-<task-id>"` per merged task.
Never `rm -rf` the root itself and never touch another repo's root — a
concurrent fan-out may be running inside it.

### Main-agent TDD merge gate (no human per task)

The main agent gates each subagent's worktree merge with test-driven development:
the task's tests must pass **before** the merge (validate the subagent's work)
and **after** the merge (catch conflicts). No human is in the per-task loop.
Per-task acceptance is uncommitted working state, mirroring the Human Review Loop
(#17).

### The boundary: devague stays deterministic

The devague CLI never spawns subagents, manages worktrees, marks tasks done, or
picks a backend (#20). Orchestration lives in the cited `assign-to-workforce`
skill and this convention, not in new CLI and not in a CI/CD runner.

### Roles

- **Operator/main agent**: drives execution of waves and merges each subagent's
  worktree (gated by TDD); owns the implementation split plan.
- **Per-task subagents**: may be simpler or cheaper models; each builds a single
  task test-first within its worktree. The `/scope` leg uses the same idea
  read-only: 5 or more candidate surfaces fan out one exploration subagent per
  surface, defaulting to **sonnet** — and those subagents *never* run a
  `devague` move, so provenance stays with the main agent (#79/#91).
- **Human**: owns the three gates (spec, implementation split plan, final PR),
  including approving mid-run deviations against gate 2 via `/deviate`.

### What consumes the scheduling metadata

`devague plan waves [--json]` emits the scheduling metadata (`{plan, waves,
tasks}`); the `assign-to-workforce` skill's `split-plan` subcommand is the
consumer — it renders the implementation split plan (task map, per-task
agent/model proposal, go/no-go) and a trailing End state section quoting
`devague plan deliverables` verbatim (#70), optionally persists all of it plus
an owner/model annotation table to
`docs/plans/<created-date>-<slug>-split.md` with `--write` (#82), then
performs the fan-out itself. The same `waves --json` payload is the **single
source** for every per-task brief — no `plan show --json` or exported plan-md
needed alongside it. `devague deviate` and the cited `/deviate` skill are the consumer for
mid-run departures from that plan; `devague summary` and `/summarize-delivery`
are the consumer for what actually shipped once the run ends. Devague itself
never orchestrates any of this (#20) — its use across all four is shared via
`devague learn`.

## Project intent

**devague** — an AgentCulture agent that turns a vague feature idea into a
**buildable spec**, then that spec into a **buildable plan**, by working
backwards then forwards. The spec method: start from the announcement ("pretend
it shipped — what would you announce?"), build an **Announcement Frame** by
capturing and classifying claims, pressure-testing them with honesty conditions
and hard questions, parking unresolved uncertainty as first-class "open
vagueness," and only exporting a buildable spec once the frame *converges*. The
plan method: seed a plan from that converged frame and converge it on coverage,
acceptance criteria, and an acyclic dependency order before exporting a plan.
The operator skills cover the **eight legs** in flow order: **`/scope`**
(idea→explored scope, the optional opening leg), **`/think`** (idea→spec),
**`/challenge`** (a risk-scaled blind-spot discovery pass between /think and
/spec-to-plan, adjudicated inside the existing spec gate), **`/spec-to-plan`**
(spec→plan), **`/assign-to-workforce`** (plan→parallel implementation),
**`/deviate`** (the execution-time leg — stop an in-flight fan-out the moment
it must diverge from the confirmed plan, get explicit human approval, and
record the divergence before resuming), **`/validate-delivery`** (the
execution-to-evidence leg — run the plan's behavioral tests agent-side once
waves merge, and file evidence and behavioral deltas via the CLI; unmet is
unmet), and **`/summarize-delivery`**
(execution→a committed accountability artifact, the delivery-side closure
leg); the product/CLI they drive is **`devague`**. The skills are written for
two audiences: **operators** — the main agent driving the deterministic CLI
move by move — and the **humans** who own the go/no-go decision on the
implementation split plan (gate 2, including any deviation against it) and
the final PR review (gate 3).

This is a **state machine over claims, honesty conditions, open vagueness, and
convergence** driven by LLM-chosen moves — not a linear wizard. The CLI is
deterministic and fully unit-testable; the resident Claude agent decides the
next move. See `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`
for the full design.

devague is its own method — not a wrapper around `superpowers:brainstorming`
or `superpowers:writing-plans`, though the exported spec-md artifact can feed
directly into those workflows.

## Ecosystem context

devague belongs to the **AgentCulture** family (Apache-2.0, `Copyright 2026
AgentCulture`); the GitHub remote is `origin/main` and lives under
`github.com/agentculture/devague`. Its closest structural analogs in this
workspace are the small Python CLI agents `agtag`, `appsec`, `seer-cli`, and
`steward` — when in doubt about how something *should* look here, read theirs.

`guildmaster` is the source of truth for shared skills and the cross-repo way of
working in AgentCulture (the supplier role moved from `steward` at the 2026-05-24
steward→guildmaster cutover; `steward` is still a sibling but no longer
broadcasts). Vendored skills are cited, not imported (cite-don't-import): copy
from `../guildmaster/.claude/skills/<name>/` and track provenance in
`docs/skill-sources.md`. The exception is devague's own `scope` / `think` /
`challenge` / `spec-to-plan` / `assign-to-workforce` / `deviate` /
`validate-delivery` / `summarize-delivery` — devague is their origin, so
guildmaster re-broadcasts them *from* here; never re-vendor them back.

## Stack expectations (when code lands)

The committed `.gitignore` is the standard Python template, and every sibling
agent is **uv**-based Python (`requires-python >=3.12`, hatchling build). Match
that unless the user asks otherwise. The established sibling shape is:

- A top-level package directory (`devague/`) with `__init__.py` and `__main__.py`
  (so `python -m devague` works).
- An argparse **CLI chassis** under `devague/cli/`: `__init__.py` with `main()`
  (exposed as the `devague` console script), plus `_errors.py` (a
  `DevagueError` + exit-code policy), `_output.py` (strict stdout/stderr
  split, `--json` support), and `_hints.py` + `_hint_config.py` (the
  per-verb `next: ...` stderr hint emitted once from dispatch, and its
  `[tool.devague]` / `DEVAGUE_HINTS` override, respectively).
- `devague/cli/_commands/` — one module per verb, each exposing `register()`.
  Frame verbs: `new`, `capture`, `amend`, `interrogate`, `confirm`, `reject`,
  `review`, `question`, `park`, `scope`, `lapse` (`--list`, `--confirm`,
  `--reject`; the Reasoning Degradation Ledger, #97), `converge`, `export`,
  `status`, `show`, `list`, `learn`, `explain` (`status` shares
  `cli/_status.py` with the plan engine), plus two more flat verbs, `deviate`
  (`--list`, `--confirm`, `--reject`) and `summary` (`--pr`), backed by
  `devague/delivery.py` + `devague/delivery_store.py`. The plan engine adds
  one module, `_commands/plan.py`, registering the nested `plan` subcommand
  group — `new` / `task` / `instruct` / `accept` / `amend` / `depend` (plus
  `--remove`) / `cover` / `defer` / `confirm` / `reject` / `risk` / `converge`
  / `export` / `waves` / `deliverables` / `status` / `show` / `list` / `learn`
  / `explain`.
- Frame engine: `devague/frame.py`, `convergence.py`, `store.py`,
  `render/{spec_md,frame_md}.py`. Plan engine (its peer): `devague/plan.py`,
  `plan_convergence.py`, `plan_store.py`, `render/plan_md.py`, `cli/_plans.py`.
  Delivery peer: `devague/delivery.py`, `delivery_store.py`,
  `render/summary_md.py`. Cross-cutting: `devague/contested.py` (the read-only
  claim↔deviation join, #92) and `render/_md_safety.py` (render-time markdown
  escaping, #87) — both pure and read-only; neither ever mutates a store.
- `pyproject.toml`, `CHANGELOG.md`, `tests/`, `docs/`, `culture.yaml`,
  `sonar-project.properties`, `uv.lock`.

Commands (verify against the real `pyproject.toml`): `uv sync`;
`uv run devague --version`; `uv run pytest -n auto`
(single test: `uv run pytest tests/<file>::<node> -v`);
`uv run flake8 --config=.flake8 devague/ tests/`; `uv run black devague/ tests/`;
`uv run isort --profile black devague/ tests/`;
`bandit -r devague/`; `pylint devague/`; `markdownlint-cli2 "**/*.md"`.

## Conventions worth preserving

- **Version bump per PR.** Sibling repos bump the version in `pyproject.toml`
  (CI's `version-check` blocks merge if it matches `main`) and prepend a
  `CHANGELOG.md` entry. Adopt the vendored `version-bump` skill once this repo
  grows a `pyproject.toml`.
- **PRs via the `cicd` skill / `agex pr`.** Sibling repos drive PRs through the
  steward-origin `cicd` skill (delegating to the `agex pr` CLI). Use it here once
  vendored rather than hand-rolling `gh pr` flows.
- **Signing online posts.** PR descriptions and issue/PR comments authored on the
  user's behalf are signed so it's clear they're AI-authored: `- devague (Claude)`
  once a `culture.yaml` (with the repo nick) exists, otherwise `- Claude`. Inside
  the `cicd` flow, the scripts append the signature — don't sign the body manually
  there.

## Finishing a branch: default to a PR, never pause for the menu

When work on a branch is complete and tests pass, **proceed directly to pushing
the branch and opening a Pull Request** — do not present an interactive "what
would you like to do?" menu and wait for a choice. This overrides the
Superpowers `finishing-a-development-branch` skill, whose default is to stop and
ask the user to pick among *merge locally / create PR / keep as-is / discard*.
That pause breaks the flow. In devague — and in every AgentCulture sibling —
the standing choice is **always "push and open a Pull Request,"** done via the
`cicd` skill (`agex pr open`). Merge-locally / keep-as-is / discard happen only
on explicit user request. (Standing rule carried by the `cicd` skill since
steward 0.18.0.)

## What not to invent

Do not fabricate commands, module layouts, or test invocations — here or in
conversation. Until real code exists, answer "how do I run X" with "X doesn't
exist yet — want me to scaffold it?" (modeled on `agtag`/`appsec`) rather than a
guessed command.
