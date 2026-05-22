# specifix Onboarding Implementation Plan

**Goal:** Scaffold `specifix` into a healthy AgentCulture sibling — package,
CLI chassis with placeholder verbs, CI, lint configs, `culture.yaml`, and six
vendored skills — in a single PR that closes issue #2.

**Architecture:** Mirror the `appsec` greenfield sibling. A hatchling-built
`specifix` package exposes a `specifix` CLI: a real argparse chassis
(`specifix/cli/`) with structured errors, a strict stdout/stderr split, and
`--json` support, plus three honest placeholder verbs (`learn` / `explain` /
`whoami`). Six canonical skills are copied verbatim from the local `../steward`
checkout. CI runs pytest + coverage + flake8 + SonarCloud + a version-check,
with bandit/pylint in a separate workflow and PyPI publishing via OIDC.

**Tech stack:** Python ≥3.12, `uv`, hatchling, pytest + pytest-cov +
pytest-xdist, flake8/black/isort/bandit/pylint, GitHub Actions, SonarCloud.

## Build sequence

Single branch (`onboard-sibling-pattern`), single PR. Each step verified
before the next.

1. **Package + CLI chassis** — `specifix/__init__.py`, `__main__.py`,
   `cli/{__init__,_errors,_output}.py`, `cli/_commands/{learn,explain,whoami}.py`.
   Verify: `uv run python -m specifix --version` works; each verb exits 0.
2. **Tests** — `tests/test_{package,cli_errors,cli_output,cli_chassis,cli_stubs}.py`.
   Verify: `uv run pytest -n auto` green; coverage above `fail_under = 70`.
3. **Toolchain + config** — `pyproject.toml`, `.flake8`,
   `.markdownlint-cli2.yaml`, `.pre-commit-config.yaml`,
   `sonar-project.properties`, `CHANGELOG.md`, `culture.yaml`, `.gitignore`
   carve-out. Verify: `uv run flake8 --config=.flake8 specifix/ tests/` and
   `markdownlint-cli2 "**/*.md"` clean.
4. **CI workflows** — `tests.yml`, `security-checks.yml`, `publish.yml`.
5. **Vendor six skills** — `cp -R` from `../steward` (`cicd`, `communicate`,
   `version-bump`, `run-tests`, `sonarclaude`, `doc-test-alignment`),
   `chmod +x` script entry points, write `docs/skill-sources.md` and
   `.claude/skills.local.yaml.example`. Verify: each `SKILL.md` `name:`
   matches its directory.
6. **Docs + CLAUDE.md** — this plan + the design spec; refresh `CLAUDE.md`
   Status and add the branch-finishing default.
7. **Verify as a sibling** — `uv sync`, full test/lint suite, then
   `steward doctor ../specifix` from a steward checkout; fix anything flagged.
8. **Open the PR** — via the vendored `cicd` skill (`agex pr`) so the
   `- specifix (Claude)` signature is auto-applied. Body resolves #2. One
   version bump: `0.1.0`.

## Known not-green at merge (tracked, not blockers)

- `publish.yml` runs red until PyPI Trusted Publishing is configured for
  `specifix`.
- The SonarCloud quality gate does not report until `agentculture_specifix`
  is registered (scan step gated on `SONAR_TOKEN_PRESENT`).
- CLI verbs are placeholder stubs; the specifix spec-creation product is
  undefined and deferred to a later effort.
