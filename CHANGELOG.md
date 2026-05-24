# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.1] - 2026-05-24

### Changed

- Trio skill-script header comments (`think.sh`, `spec-to-plan.sh`) no longer claim the wrapper *adds* a `status` subcommand — since 0.11.0 it is forwarded verbatim like every other move (devague#32, steward PR #58 review).

### Fixed

- `assign-to-workforce.sh` now installs its `mktemp` cleanup `EXIT` trap on the line immediately after creating the temp file, capturing the prior trap beforehand so the subshell-forking capture no longer sits inside the untracked-file window (devague#32).

## [0.11.0] - 2026-05-24

### Added

- `devague status` and `devague plan status` — first-class, read-only CLI verbs that compose `list` + `converge` and report the convergence verdict, remaining gaps, and the recommended next move (`--json` too). Internalised from the `think` / `spec-to-plan` skill wrappers (#30); they never mutate state and the plan verb re-checks the live source frame for drift. Shared renderer in `devague/cli/_status.py`.

### Changed

- The `think` / `spec-to-plan` skill wrappers are now thin: `status` is forwarded verbatim like every other move instead of being a wrapper-only verb implemented in embedded Python. This removed their `mktemp` temp-file and stdout-ordering hazards entirely (#30, Qodo via steward).

### Fixed

- `assign-to-workforce.sh` no longer leaks its `mktemp` temp file if interrupted by a signal — cleanup is now registered with an `EXIT` trap (#30). Its split-plan orchestration presentation deliberately stays out of the deterministic CLI (#20).

## [0.10.0] - 2026-05-24

### Added

- Subagent-driven implementation via the new **assign-to-workforce** skill (#13). Fans out a converged plan's `devague plan waves` to one agent per task per wave in isolated git worktrees, with main-agent **TDD-gated merges** (the task's tests pass before AND after merge); the human gates the spec, the implementation split plan, and the final PR. devague's CLI stays deterministic and non-orchestrating (#20) — it only *describes* the graph. Ships a portable `assign-to-workforce.sh` helper and is recorded as a first-party skill.
- `devague plan converge` now emits deterministic, **non-blocking warnings** for parallel/TDD fitness (#13): flags confirmed tasks with no acceptance criteria and over-serialized dependency graphs, without ever changing `ready_for_plan`/`blockers`.
- `devague learn` documents how to invoke assign-to-workforce (#13).

### Changed

- `/spec-to-plan` now coaches small, file-disjoint, TDD-accepted (parallelizable) tasks, and `CLAUDE.md` documents the assign-to-workforce convention and its three human gates (#13).

## [0.9.1] - 2026-05-23

### Added

- Spec + plan for subagent-driven implementation (#13). Drove `devague` /think then /spec-to-plan to produce a converged spec (`docs/specs/2026-05-23-devague-turns-a-converged-plan-into-parallel-simpl.md`) and a buildable, parallelizable plan (`docs/plans/...`) for the **assign-to-workforce** convention: a cited skill that fans out `devague plan waves` to one subagent per task per wave in isolated git worktrees, with main-agent TDD-gated per-task merges (no human per task) and exactly three human gates — the spec, the implementation split plan (tasks map + per-task subagent/model assignment + go/no-go), and the final PR. Planning artifacts only (no code yet); the CLI stays deterministic and non-orchestrating (#20).

## [0.9.0] - 2026-05-23

### Added

- **Plan dependency waves (#20).** New `devague plan waves [--json]` move emits the plan's task dependency graph as deterministic, machine-readable scheduling metadata (`{plan, waves}` — ordered batches of task ids where wave 0 has no unsatisfied dependency and each later wave depends only on earlier ones). Read-only and convergence-agnostic, so it works on an in-progress plan. Rejected tasks are excluded; a cycle or a dependency on a missing/rejected task is refused by reusing the plan-convergence dependency blockers (`dependency_blockers`). This is the small deterministic primitive behind #13: Devague *describes* the parallelizable graph; it does not spawn subagents, manage worktrees, mark tasks done, or pick a backend.
- **Dated export filenames (#12).** `devague export` and `devague plan export` now prefix the written file with the frame/plan creation date — `docs/specs/<YYYY-MM-DD>-<slug>.md` and `docs/plans/<YYYY-MM-DD>-<slug>.md`. The date comes from the object's `created` timestamp (not today), so re-exporting an unchanged artifact overwrites the same file rather than spawning a dated duplicate. Existing exported docs were renamed to match.

## [0.8.0] - 2026-05-23

### Added

- **Portable LLM guidance contract (#19).** New `docs/llm-guidance.md` — a runtime-agnostic operating contract for any assisting model driving Devague (not just Claude Code): the move-driven mental model, the (state × origin) vocabulary, the anti-fabrication hard rules, adaptive-not-scripted ordering, good/bad operator examples, and the forward (plan) leg. Distilled from the `/think` and `/spec-to-plan` skill contracts; it complements, and does not replace, an agent runtime's own main instruction file (`AGENTS.md`, `CLAUDE.md`, a system prompt).
- `devague learn` (text and `--json`) now always surfaces the operating rules: a `devague is NOT` framing (not a wizard / questionnaire / PRD generator), the anti-fabrication rules, and a pointer to `docs/llm-guidance.md`. JSON gains `not_a`, `operating_rules`, `guidance_doc` (a portable canonical URL — `docs/` is not shipped in the wheel), and `guidance_doc_repo_path` keys.

## [0.7.0] - 2026-05-23

### Added

- **Plan persistence hardening (#18).** Plans now carry an integer `schema_version` (`PLAN_SCHEMA_VERSION = 1`), written on save and checked on load — the plan-engine peer of the frame `schema_version` contract (#5). `plan_store.load` fails closed with a clean `DevagueError` (exit 1 + upgrade hint) when a plan declares a newer unsupported schema; pre-0.7.0 plans without the key load silently as the current schema.
- Loaded-object validation for plans: `Task.origin` / `Task.status` and `PlanRisk.kind` are now validated at construction (via `__post_init__`), so a hand-edited or corrupted plan file surfaces an actionable "malformed plan" `DevagueError` instead of a traceback. (Task/dep/cover *id* cross-references are deliberately not validated at load — coverage and acyclic-dependency checks already run against the live frame in `plan converge`.)

### Changed

- `devague/cli/_plans.py` `resolve_plan` now distinguishes an invalid `--plan` slug, a newer-schema plan, a missing plan, and a malformed plan file — each with its own remediation hint (mirroring the frame `resolve`).

### Fixed

- **Persistence integrity, both engines (PR #25 review).** `store.load` / `plan_store.load` now reject a file whose embedded `slug` disagrees with the requested slug (previously a tampered file could redirect a later `save` onto a different frame/plan). And `schema_version` is now parsed strictly via the shared `frame.parse_schema_version` — a non-integer value (`1.9`, `true`, `"1"`, `null`) is rejected instead of being silently coerced by `int()` (which truncated `1.9`→`1` and accepted `True`→`1`). Both guards were applied symmetrically to the frame engine to keep the persistence twins aligned.

## [0.6.1] - 2026-05-23

### Fixed

- `spec_md` now surfaces `requirement` **claim text** — the last remaining item of #21. Requirements render in a `## Requirements` section with their confirmed honesty conditions nested beneath each claim; honesty conditions on non-requirement claims move to a separate `## Honesty conditions` section (previously every honesty condition was dumped into one flat "Requirements / honesty conditions" list and the requirement claim text never rendered). Re-exported the committed specs to match. Closes #21.

## [0.6.0] - 2026-05-23

### Added

- **Human Review Loop (#17).** Makes the user-only confirmation step ergonomic at scale, preserving the anti-fabrication guarantee.
  - `devague review` (+ `--json`) lists every proposed (unconfirmed) claim and honesty condition with ids — un-gated by convergence and without mutating state — and persists a non-authoritative artifact to `.devague/reviews/<slug>.md`.
  - `confirm` / `reject` now accept multiple ids in one transactional call (any unknown id ⇒ nothing changes).
  - `confirm --from-review <file>` applies a reviewed decision set: each item is emitted with a `pending` marker the human edits to `confirm`/`reject`; `pending` lines are never auto-confirmed (round-trippable artifact).
  - `devague question` records / lists / resolves pending user decisions as durable working state in `.devague/questions/<slug>.md`.
  - devague manages `.gitignore` so `.devague/reviews/` and `.devague/questions/` stay uncommitted working state by default.

### Changed

- `confirm --json` now emits `{confirmed, rejected}` (lists) instead of `{id, status}`, reflecting the multi-id, transactional batch.

## [0.5.1] - 2026-05-23

### Added

- Spec + plan for the 0.6.0 Human Review Loop milestone (#17, folding in #11 and #14), produced by dogfooding `/think` then `/spec-to-plan` on devague itself. `docs/specs/devague-0-6-0-ships-the-human-review-loop-devague.md` (converged frame: 13 confirmed claims, 13 confirmed honesty conditions) and `docs/plans/devague-0-6-0-ships-the-human-review-loop-devague.md` (7 topologically ordered tasks covering all 26 targets, one parked non-blocking risk).
- Recorded design decisions in the frame: batch confirm/reject is transactional (abort-all on any invalid id); `confirm --from-review` is in scope for 0.6.0; devague manages `.gitignore` for `.devague/reviews/` and `.devague/questions/`; a CLI move (not a hand-written skill artifact) owns the pending-questions file.

### Fixed

- Renderers were lossy since the #5/#16 contract: `spec_md` rendered "Non-goals" from `boundary` claims only and never emitted `non_goal` / `decision`; `frame_md`'s sections omitted `non_goal` / `requirement` / `assumption` / `decision`. Both now render every claim kind — `spec_md` gains Scope / boundaries, Non-goals, Assumptions, Decisions, and Open questions sections; `frame_md` covers all twelve kinds. Re-exported this spec so the committed md matches the authoritative frame. Closes #21 (also flagged by Qodo on PR #22).

## [0.5.0] - 2026-05-23

### Added

- Spec contract (#5): claim kinds non_goal / requirement / assumption / decision, each with a documented convergence-gate role (requirement is spec-affecting; non_goal/decision are descriptive; an unconfirmed assumption is a warning, not a blocker).
- Every frame carries a fail-closed schema_version: written on save, validated on load (a newer/unknown version is rejected with an actionable error); existing 0.4.0 frames still load.
- docs/spec-contract.md — the documented source of truth for the entity model, the (state x origin) vocabulary, the structured convergence result, and the per-move input/output/transition/validation-error contract — plus a test-verified worked example at docs/examples/contract-example.json.
- Contract test suite: claim provenance, honesty-condition confirmation, parking vagueness, structured convergence failure, lossless round-trip, schema versioning, and an offline-operation guarantee (no networking imports; a full session runs with sockets stubbed).

### Changed

- BREAKING: converge --json now emits the structured result {ready_for_spec, blockers, warnings, parked_items, required_next_moves} (plans: ready_for_plan) instead of {passed, missing}. The /think and /spec-to-plan status helpers were updated in the same change; required_next_moves is now derived by the CLI. capture --json now includes origin.
- Frame loading raises distinct, actionable DevagueErrors (newer schema -> upgrade; malformed/hand-edited frame -> fix hint) instead of a generic 'invalid slug'.

## [0.4.1] - 2026-05-23

### Added

- docs/specs and docs/plans artifacts for issue #5 (Define the spec contract): a converged Announcement Frame spec and its buildable 11-task plan, generated by dogfooding /think + /spec-to-plan.

### Changed

- /think skill (SKILL.md): document the commit-then-/spec-to-plan close-out after a reviewed export (no "what next?" pause).

### Fixed

- `render/spec_md.py` + `render/plan_md.py`: exported markdown now satisfies the repo's own markdownlint config (blank line after every heading and before every list, MD022/MD032). Disabled MD036 for the renderers' italic metadata subtitle. Caught by dogfooding — `devague export` output was failing CI's markdown lint on `docs/specs` / `docs/plans`.

## [0.4.0] - 2026-05-23

### Added

- **Spec→plan engine** — a deterministic structural peer of the working-backwards frame engine that turns a converged spec into a buildable plan. New modules: `devague/plan.py` (Plan / Task / PlanRisk / CoverageTarget domain), `plan_convergence.py` (coverage + acceptance + acyclic-dependency + blocking-risk gate, reusing `ConvergenceResult`), `plan_store.py` (`.devague/plans/`), and `render/plan_md.py` (topologically-ordered buildable plan).
- Nested `devague plan` CLI group (`new` / `task` / `accept` / `depend` / `cover` / `confirm` / `reject` / `risk` / `converge` / `export` / `show` / `list` / `learn` / `explain`), all with `--json`. `plan new` requires a converged source frame; `converge`/`export` re-evaluate against the **live** frame and refuse on frame drift (deleted or regressed).
- New first-party **`/spec-to-plan`** skill (`.claude/skills/spec-to-plan/`): a portable wrapper (`scripts/spec-to-plan.sh`) forwarding to `devague plan` plus a `status` next-move helper over the plan gate.

### Changed

- **Renamed the `devague` skill to `think`** (`.claude/skills/think/`, `scripts/think.sh`) — clearer idea→spec framing and to pair with the new `/spec-to-plan` sibling. The product/CLI/repo name stays `devague`; only the skill identity changed. `docs/skill-sources.md` and downstream steward re-vendoring must relearn the new name. ("devague" remains a trigger keyword on `/think`.)

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
