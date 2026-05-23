# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.3] - 2026-05-23

### Added

- First-party `devague` skill (`.claude/skills/devague/`): a portable wrapper (`scripts/devague.sh`) that operates the working-backwards CLI, forwards every move, and adds a `status` next-move helper over the convergence gate; plus `tests/test_devague_skill.py` and an outbound-origin note in `docs/skill-sources.md`. Origin = devague; steward pulls it from here and broadcasts to the AgentCulture mesh.

## [0.3.2] - 2026-05-23

### Security

- `store.validate_slug()` now guards every slug-derived path (`--frame`,
  `.devague/current`, and a persisted `frame.slug`) against path traversal and
  absolute paths via a strict allowlist, closing an arbitrary file read/write
  through `load()` / `save()` / `export`.

### Fixed

- `devague new` no longer silently overwrites an existing frame when two titles
  slugify to the same value: `store.unique_slug()` allocates `<slug>-2`,
  `<slug>-3`, … and the chosen slug is surfaced in the output.

### Changed

- `devague new` and `devague learn` now use issue #4's exact entry point —
  first question *"What's the announcement?"* with the "users, teammates, or
  yourself" supporting prompt.
- Documented the canonical ten-stage guided sequence (Announcement → Spec) in
  the design doc and `devague learn` (also exposed via `learn --json`), while
  keeping the engine move-driven rather than a rigid wizard.
- Raised the coverage gate from 70 % to 95 %.
- Cleared four SonarCloud maintainability findings on the new code: collapsed
  the redundant `return 0` paths in `show` / `list` (S3516) and reduced the
  cognitive complexity of `render_frame` and `convergence.evaluate` below the
  threshold by extracting focused helpers (S3776). Behavior unchanged.

## [0.3.1] - 2026-05-23

### Fixed

- `converge` now demotes a `converged` frame back to `drafting` when a new
  blocking item is added and the gate re-runs (was stuck at `converged`).
- Removed the unreachable `parked` value from `CLAIM_STATUSES` and
  `Claim.status`; the `park` move records open vagueness, not a claim status.
  Updated convergence message wording, spec, and plan to match.
- `export --format` is now constrained to `choices=("spec-md",)`, preventing
  `--format frame-md` from silently writing the Announcement Frame as a spec.

## [0.3.0] - 2026-05-23

### Added

- The working-backwards engine: a deterministic Frame state machine
  (`devague/frame.py`, `store.py`, `convergence.py`) and the moves
  `new` / `capture` / `interrogate` / `confirm` / `reject` / `park` /
  `converge` / `export` / `show` / `list`, plus a pluggable renderer
  registry (`frame-md`, `spec-md`). `export` is gated on convergence;
  LLM-proposed claims and honesty conditions require user confirmation.
- Real `learn` / `explain` bodies teaching the method and the moves.

## [0.2.0] - 2026-05-23

### Changed

- Renamed the package and CLI `specifix` → `devague` (PyPI distribution
  `devague`; the orphaned `specifix 0.1.0` is left as-is). Console script,
  `python -m`, `culture.yaml` suffix, SonarCloud key, and docs all updated.

### Removed

- The placeholder `whoami` verb (the `learn` / `explain` affordances remain).

## [0.1.0] - 2026-05-22

### Added

- AgentCulture sibling scaffold: the `specifix` package (hatchling,
  Python >=3.12, zero runtime deps) with the afi-cli CLI chassis —
  structured errors, a strict stdout/stderr split, and `--json` support.
- Placeholder agent-first verbs `learn` / `explain` / `whoami` — honest
  "not yet implemented; specifix is greenfield" stubs.
- CI workflows: `tests.yml` (pytest + coverage + flake8 + SonarCloud +
  version-check), `security-checks.yml` (bandit + pylint), `publish.yml`
  (TestPyPI on PR, PyPI on main, via OIDC Trusted Publishing).
- `culture.yaml` declaring the `specifix` agent nick (`backend: claude`).
- Vendored skills from steward: `cicd`, `communicate`, `version-bump`,
  `run-tests`, `sonarclaude`, `doc-test-alignment`. Provenance tracked in
  `docs/skill-sources.md`.
- Repo-local lint configs: `.flake8`, `.markdownlint-cli2.yaml`,
  `.pre-commit-config.yaml`; `sonar-project.properties`; the
  `.claude/skills.local.yaml.example` per-machine config template.

Resolves #2.
