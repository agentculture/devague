# specifix onboarding — AgentCulture sibling scaffold

**Date:** 2026-05-22
**Status:** Approved (design)
**Closes:** agentculture/specifix issue #2

## Problem

`specifix` is a brand-new AgentCulture sibling repo — the agent that *owns
spec creation for changes*. Today it contains only `CLAUDE.md`, `LICENSE`,
`README.md`, `.gitignore`, and `.claude/settings.local.json` — no package,
no build config, no CI, no `culture.yaml`, no vendored skills.

Issue #2 ("the works") is the onboarding contract: bring `specifix` up to the
full shared sibling shape (the 12 required artifacts from steward's
`docs/sibling-pattern.md`, the quality pipeline, and the inherited
conventions) so agents and humans can move between AgentCulture repos without
relearning the layout.

## Scope

**In scope:** the onboarding *infrastructure* only — make `specifix` a
"healthy sibling" per steward's `docs/sibling-pattern.md`.

**Out of scope:** the actual specifix spec-creation product. The `learn` /
`explain` / `whoami` CLI verbs ship as honest placeholder stubs; designing
what the agent *does* (and where it sits relative to the
`superpowers:brainstorming` / `writing-plans` / `writing-skills` skills and
sibling agents) is a separate later effort.

## Decisions

| Decision | Choice |
|----------|--------|
| Scope | Onboarding infrastructure only; agent product deferred. |
| CLI verbs | `learn` / `explain` / `whoami` as honest placeholder stubs — each prints one "not yet implemented; specifix is greenfield" line and exits 0, with a structured `--json` payload. |
| Scaffold model | Mirror the `appsec` sibling — the most recent greenfield sibling that resolved this exact onboarding. PyPI distribution `specifix`, import `specifix`, console script `specifix`. (Issue §1 suggested `specifix-cli`, but the bare `specifix` name matches the registered PyPI Trusted-Publishing project and what `appsec` actually shipped.) |
| Skills | Vendor all **six** canonical skills directly from `../steward` (not from appsec — avoids inheriting appsec's documented divergences): `cicd`, `communicate`, `version-bump`, `run-tests`, `sonarclaude`, `doc-test-alignment`. Vendored verbatim — no divergence to record. |
| PR strategy | One PR for everything: full scaffold + all six vendored skills + provenance ledger. One version bump (`0.1.0`). Closes issue #2. Pushed and opened directly per the branch-finishing default. |

## Architecture

The repo mirrors the established sibling skeleton:

- **Package + CLI chassis** (`specifix/`): `__init__.py` (`__version__` via
  `importlib.metadata.version("specifix")`), `__main__.py`
  (`python -m specifix`), and `cli/` with `__init__.py` (argparse dispatch,
  structured-error routing, `--json` hint), `_errors.py` (`SpecifixError` +
  exit-code policy), `_output.py` (strict stdout/stderr split), and
  `_commands/{learn,explain,whoami}.py` (placeholder stubs, each with a
  `register(sub)`).
- **Tests** (`tests/`): package smoke test, error/output unit tests, chassis
  tests (`--version`, no-args help, unknown-verb error, `python -m`), and
  per-verb stub tests (exit 0 + output + `--json`).
- **Toolchain + config**: `pyproject.toml` (hatchling, py≥3.12, zero runtime
  deps, dev group), `.flake8`, `.markdownlint-cli2.yaml`,
  `.pre-commit-config.yaml`, `sonar-project.properties`
  (`agentculture_specifix`), `CHANGELOG.md` (Keep-a-Changelog `[0.1.0]`),
  `culture.yaml` (`suffix: specifix`, `backend: claude`), `.gitignore`
  skills.local carve-out.
- **CI** (`.github/workflows/`): `tests.yml` (pytest + coverage + flake8 +
  SonarCloud + version-check), `security-checks.yml` (bandit + pylint),
  `publish.yml` (TestPyPI on PR, PyPI on main, OIDC Trusted Publishing).
- **Vendored skills** (`.claude/skills/`): the six skills + the committed
  `.claude/skills.local.yaml.example`; provenance in `docs/skill-sources.md`.

## Acceptance criteria

- `pyproject.toml` (hatchling, py≥3.12); `python -m specifix` and
  `specifix --version` both work.
- `specifix/cli/` chassis with `_errors.py`, `_output.py`,
  `_commands/{whoami,learn,explain}.py` as honest stubs; `--json` supported.
- `tests/` with a passing pytest-xdist suite; `tests.yml` + `publish.yml`
  (incl. `version-check`, which auto-passes on the initial PR — no
  `pyproject.toml` on `main` yet).
- `culture.yaml` declares `backend: claude` and the nick `specifix`;
  `CLAUDE.md` agrees (backend-consistency).
- All six skills vendored under `.claude/skills/` (matching `name:`
  frontmatter + `scripts/`); provenance in `docs/skill-sources.md`.
- `.claude/skills.local.yaml.example` committed; `.flake8` and
  `.markdownlint-cli2.yaml` repo-local.
- `CHANGELOG.md` started; version bumped to `0.1.0` on the onboarding PR.
- `steward doctor ../specifix` exits clean.

### Known not-green at merge (not blockers)

- `publish.yml` runs red until PyPI Trusted Publishing is configured for
  `specifix` (a manual maintainer step: register on PyPI/TestPyPI,
  configure the OIDC publisher, create the `pypi` / `testpypi` environments).
- The SonarCloud quality gate does not report until `agentculture_specifix`
  is registered on sonarcloud.io and the GitHub App is installed. The scan
  step is gated on `SONAR_TOKEN_PRESENT`, so CI won't break if absent.

## References

- `steward/docs/sibling-pattern.md` — the 12 required artifacts and the
  `steward doctor` invariants.
- `steward/docs/skill-sources.md` — canonical upstream for each skill.
- `appsec/` — the greenfield scaffold exemplar.
- agentculture/specifix issue #2.
