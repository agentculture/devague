# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

**Scaffolded (greenfield product).** The AgentCulture sibling skeleton has
landed: the `specifix` package with the argparse CLI chassis, tests, CI, the
six vendored skills, and `culture.yaml`. The CLI verbs (`learn` / `explain` /
`whoami`) are **honest placeholder stubs** — the actual spec-creation product is
not implemented yet. Run `git ls-files` to see the real surface rather than
trusting a layout described here.

Real commands (verify against `pyproject.toml`): `uv sync`;
`uv run specifix --version`; `python -m specifix`; `uv run pytest -n auto`
(single test: `uv run pytest tests/<file>::<node> -v`);
`uv run flake8 --config=.flake8 specifix/ tests/`; `markdownlint-cli2 "**/*.md"`.

## Project intent

**specifix** — an AgentCulture agent that *owns spec creation for changes* (per
`README.md`). The expected niche is producing the design/spec artifact that
precedes implementation, in the spirit of the brainstorming → spec → plan
workflow the workspace already uses (`docs/superpowers/specs/`,
`docs/superpowers/plans/` in sibling repos).

Before designing a bespoke spec format or transport, check what already exists:
the `superpowers:brainstorming`, `superpowers:writing-plans`, and
`superpowers:writing-skills` skills already encode a spec/plan discipline, and
sibling agents (`steward`, `agtag`, `culture`, `daria`) provide agent-to-agent
plumbing. Clarify with the user where specifix sits relative to those rather than
duplicating them.

## Ecosystem context

specifix belongs to the **AgentCulture** family (MIT, `Copyright (c) 2026
AgentCulture`); the GitHub remote is `origin/main` and will live under
`github.com/agentculture/specifix`. Its closest structural analogs in this
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

- A top-level package directory (`specifix/`) with `__init__.py` and `__main__.py`
  (so `python -m specifix` works).
- An argparse **CLI chassis** under `specifix/cli/`: `__init__.py` with `main()`
  (exposed as the `specifix` console script), plus `_errors.py` (a
  `SpecifixError` + exit-code policy) and `_output.py` (strict stdout/stderr
  split, `--json` support).
- `specifix/cli/_commands/` — one module per verb, each exposing `register()`.
  New scaffolds typically start with placeholder `learn` / `explain` / `whoami`
  verbs that are honest stubs, not faked functionality.
- `pyproject.toml`, `CHANGELOG.md`, `tests/`, `docs/`, `culture.yaml`,
  `sonar-project.properties`, `uv.lock`.

Likely commands once scaffolded (verify against the real `pyproject.toml` before
relying on them): `uv sync`; `uv run specifix --version`; `uv run pytest -n auto`
(single test: `uv run pytest tests/<file>::<node> -v`); `uv run flake8 / black /
isort`; `bandit` + `pylint` in CI; `markdownlint-cli2 "**/*.md"`.

## Conventions worth preserving

- **Version bump per PR.** Sibling repos bump the version in `pyproject.toml`
  (CI's `version-check` blocks merge if it matches `main`) and prepend a
  `CHANGELOG.md` entry. Adopt the vendored `version-bump` skill once this repo
  grows a `pyproject.toml`.
- **PRs via the `cicd` skill / `agex pr`.** Sibling repos drive PRs through the
  steward-origin `cicd` skill (delegating to the `agex pr` CLI). Use it here once
  vendored rather than hand-rolling `gh pr` flows.
- **Signing online posts.** PR descriptions and issue/PR comments authored on the
  user's behalf are signed so it's clear they're AI-authored: `- specifix (Claude)`
  once a `culture.yaml` (with the repo nick) exists, otherwise `- Claude`. Inside
  the `cicd` flow, the scripts append the signature — don't sign the body manually
  there.

## Finishing a branch: default to a PR, never pause for the menu

When work on a branch is complete and tests pass, **proceed directly to pushing
the branch and opening a Pull Request** — do not present an interactive "what
would you like to do?" menu and wait for a choice. This overrides the
Superpowers `finishing-a-development-branch` skill, whose default is to stop and
ask the user to pick among *merge locally / create PR / keep as-is / discard*.
That pause breaks the flow. In specifix — and in every AgentCulture sibling —
the standing choice is **always "push and open a Pull Request,"** done via the
`cicd` skill (`agex pr open`). Merge-locally / keep-as-is / discard happen only
on explicit user request. (Standing rule carried by the `cicd` skill since
steward 0.18.0.)

## What not to invent

Do not fabricate commands, module layouts, or test invocations — here or in
conversation. Until real code exists, answer "how do I run X" with "X doesn't
exist yet — want me to scaffold it?" (modeled on `agtag`/`appsec`) rather than a
guessed command.
