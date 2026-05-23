# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

**Spec contract landed (#5).** The entity model is documented in
`docs/spec-contract.md` (the source of truth for kinds, the `(state × origin)`
vocabulary, the structured convergence result, and the per-move I/O contract).
Claim kinds now include `non_goal` / `requirement` / `assumption` / `decision`;
every frame carries a fail-closed `schema_version`; and `converge --json` emits
the structured `{ready_for_spec, blockers, warnings, parked_items,
required_next_moves}` (plans: `ready_for_plan`) — a hard break from the old
`{passed, missing}`.

**Spec→plan engine landed (v0.4.0).** Both deterministic engines now ship.
The **frame engine** (idea→spec) — Frame domain model, JSON store, convergence
gate, renderer registry, and the flat moves `new` / `capture` / `interrogate` /
`confirm` / `reject` / `park` / `converge` / `export` / `show` / `list` /
`learn` / `explain`. The **plan engine** (spec→plan) is its structural peer:
`devague/plan.py`, `plan_convergence.py`, `plan_store.py`, `render/plan_md.py`,
and the nested group `devague plan <move>` (`new` / `task` / `accept` / `depend`
/ `cover` / `confirm` / `reject` / `risk` / `converge` / `export` / `show` /
`list` / `learn` / `explain`). The two operator skills are `/think` (idea→spec,
renamed from `/devague`) and `/spec-to-plan` (spec→plan). Coverage ≥ 95 %; all
linters pass. Run `git ls-files` to see the real surface.

Real commands: `uv sync`; `uv run devague --version`; `python -m devague`;
`uv run pytest -n auto` (single test: `uv run pytest tests/<file>::<node> -v`);
`uv run flake8 --config=.flake8 devague/ tests/`; `uv run black devague/ tests/`;
`uv run isort --profile black devague/ tests/`; `markdownlint-cli2 "**/*.md"`.

## Working-backwards method

The agent drives the **deterministic** CLI — no LLM calls inside the CLI
itself. The workflow:

1. `devague new "<announcement>"` — the announcement-first entry point. The
   canonical first question is *"What's the announcement?"* ("Pretend this
   shipped successfully — what would you announce to users, teammates, or
   yourself?"). Creates a Frame seeded with the announcement claim
   (auto-confirmed, since it comes from the user). `devague learn` documents the
   full ten-stage guided sequence.
2. `devague capture --kind <kind> "<text>"` — add claims; LLM-proposed ones
   (`--origin llm`) land as `proposed` and require explicit user `confirm`.
3. `devague interrogate <claim-id>` — attach honesty conditions and hard
   questions; honesty conditions from the LLM are also `proposed`.
4. `devague confirm <id>` / `reject` / `park` — **all honesty conditions
   routed through the user**; the agent must not auto-confirm LLM proposals.
5. `devague converge` — evaluates the convergence gate; lists remaining gaps.
6. `devague export` — only succeeds after `converge` passes; writes a
   buildable spec-md to `docs/specs/`.

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
   add tasks; `--origin llm` lands `proposed` (user must `confirm`). Refine with
   `accept` / `depend` / `cover`.
3. `devague plan risk "<text>" --kind <kind>` — park a genuine unknown as a
   first-class plan risk instead of guessing.
4. `devague plan converge` — re-evaluates the gate **against the live frame**
   (catches frame drift); lists gaps. A plan converges when every target is
   covered by a confirmed task, every confirmed task has acceptance criteria, the
   dependency graph is acyclic, and no blocking risk remains.
5. `devague plan export` — only after `converge` passes; writes a buildable
   plan-md (topologically ordered) to `docs/plans/`.

Full design: `docs/superpowers/specs/2026-05-23-devague-spec-to-plan-design.md`.

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
Two operator skills cover the two legs: **`/think`** (idea→spec) and
**`/spec-to-plan`** (spec→plan); the product/CLI for both is **`devague`**.

This is a **state machine over claims, honesty conditions, open vagueness, and
convergence** driven by LLM-chosen moves — not a linear wizard. The CLI is
deterministic and fully unit-testable; the resident Claude agent decides the
next move. See `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`
for the full design.

devague is its own method — not a wrapper around `superpowers:brainstorming`
or `superpowers:writing-plans`, though the exported spec-md artifact can feed
directly into those workflows.

## Ecosystem context

devague belongs to the **AgentCulture** family (MIT, `Copyright (c) 2026
AgentCulture`); the GitHub remote is `origin/main` and lives under
`github.com/agentculture/devague`. Its closest structural analogs in this
workspace are the small Python CLI agents `agtag`, `appsec`, `seer-cli`, and
`steward` — when in doubt about how something *should* look here, read theirs.

`steward` is the source of truth for shared skills and the cross-repo way of
working in AgentCulture. Vendored skills are cited, not imported (cite-don't-import):
copy from `../steward/.claude/skills/<name>/` and track provenance in
`docs/skill-sources.md`.

## Stack expectations (when code lands)

The committed `.gitignore` is the standard Python template, and every sibling
agent is **uv**-based Python (`requires-python >=3.12`, hatchling build). Match
that unless the user asks otherwise. The established sibling shape is:

- A top-level package directory (`devague/`) with `__init__.py` and `__main__.py`
  (so `python -m devague` works).
- An argparse **CLI chassis** under `devague/cli/`: `__init__.py` with `main()`
  (exposed as the `devague` console script), plus `_errors.py` (a
  `DevagueError` + exit-code policy) and `_output.py` (strict stdout/stderr
  split, `--json` support).
- `devague/cli/_commands/` — one module per verb, each exposing `register()`.
  Frame verbs: `new`, `capture`, `interrogate`, `confirm`, `reject`, `park`,
  `converge`, `export`, `show`, `list`, `learn`, `explain`. The plan engine adds
  one module, `_commands/plan.py`, registering the nested `plan` subcommand group.
- Frame engine: `devague/frame.py`, `convergence.py`, `store.py`,
  `render/{spec_md,frame_md}.py`. Plan engine (its peer): `devague/plan.py`,
  `plan_convergence.py`, `plan_store.py`, `render/plan_md.py`, `cli/_plans.py`.
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
