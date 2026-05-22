# devague Rename Implementation Plan (Phase 0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the internal package and identity `specifix` → `devague` so the renamed repo (`agentculture/devague`) is coherent end-to-end, before the working-backwards engine lands.

**Architecture:** Pure rename — no behavior change. The existing scaffold (CLI chassis + `learn`/`explain` stubs) keeps working; the existing test suite is the regression gate. `whoami` retires.

**Tech Stack:** Python ≥3.12, uv, hatchling, pytest.

**Design input:** `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md` (Phase 0).

---

## Notes for the executor

- A rename is all-or-nothing: imports break until every reference is updated, so the early steps will leave the tree un-runnable. Do **not** run tests until Step "verify". Commit once at the end of Task 1 and once after Task 2.
- The PyPI distribution becomes `devague` (new project). The already-published `specifix 0.1.0` is left as an orphan — do **not** yank it. Trusted-Publishing setup for `devague` is a manual maintainer step (see Task 2).
- Leave the historical `CHANGELOG.md [0.1.0]` entry and the `# specifix-divergence:` markers' *history* alone except where this plan says to rewrite them.

## File map

| File | Change |
|------|--------|
| `specifix/` (dir + all modules) | `git mv` → `devague/`; rewrite `specifix`→`devague`, `Specifix`→`Devague` inside |
| `specifix/cli/_commands/whoami.py` | delete (verb retires) |
| `pyproject.toml` | name, scripts, hatch packages, coverage source, isort first-party |
| `culture.yaml`, `sonar-project.properties` | suffix / projectKey / sources |
| `.github/workflows/{tests,publish,security-checks}.yml` | paths, `--cov`, TestPyPI notice |
| `tests/*.py` | imports + assertions; drop whoami tests |
| `README.md`, `CLAUDE.md` | prose + commands |
| `CHANGELOG.md` | new `[0.2.0]` entry (keep `[0.1.0]`) |
| `docs/skill-sources.md`, `.claude/skills/cicd/scripts/portability-lint.sh` | `specifix-divergence` → `devague-divergence` |

---

## Task 1: Rename the package and all references

**Files:** the whole tree (see map above).

- [ ] **Step 1: Move the package directory**

```bash
cd /home/spark/git/specifix   # local dir name is cosmetic; origin tracks agentculture/devague
git mv specifix devague
git rm devague/cli/_commands/whoami.py
```

- [ ] **Step 2: Rewrite identifiers inside the moved package and tests**

Replace `specifix` → `devague` and `Specifix` → `Devague` across the package and tests. The only class/parser names affected are `SpecifixError`→`DevagueError` and `_SpecifixArgumentParser`→`_DevagueArgumentParser`.

```bash
grep -rl -e specifix -e Specifix devague/ tests/ | xargs sed -i -e 's/Specifix/Devague/g' -e 's/specifix/devague/g'
```

- [ ] **Step 3: Drop the retired `whoami` registration**

Edit `devague/cli/__init__.py` `_build_parser()`: remove the `whoami` import and its `register(sub)` call, leaving only `learn` and `explain`.

```python
    from devague.cli._commands import explain as _explain_cmd
    from devague.cli._commands import learn as _learn_cmd

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
```

- [ ] **Step 4: Remove the whoami tests**

Edit `tests/test_cli_stubs.py`: delete `test_whoami_exits_zero_and_signals_greenfield` and `test_whoami_json` (the `learn`/`explain` tests stay).

- [ ] **Step 5: Update `pyproject.toml`**

Make these exact changes:

```toml
[project]
name = "devague"
version = "0.2.0"
description = "devague — turns a vague feature idea into a buildable spec by working backwards."
```

```toml
[project.scripts]
devague = "devague.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["devague"]
```

```toml
[tool.coverage.run]
source = ["devague"]
omit = ["devague/__pycache__/*"]
```

```toml
[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["devague"]
```

Also update `[project.urls]` `Homepage`/`Issues` to `https://github.com/agentculture/devague` and `[tool.bandit]` is unchanged.

- [ ] **Step 6: Update `devague/__init__.py` version lookup**

```python
try:
    __version__ = _v("devague")
except PackageNotFoundError:  # pragma: no cover  — editable install without metadata
    __version__ = "0.0.0+local"
```

- [ ] **Step 7: Update `culture.yaml` and `sonar-project.properties`**

`culture.yaml`:

```yaml
agents:
- suffix: devague
  backend: claude
```

`sonar-project.properties`:

```properties
sonar.projectKey=agentculture_devague
sonar.organization=agentculture
sonar.sources=devague
sonar.tests=tests
```

- [ ] **Step 8: Update CI workflows**

In `.github/workflows/tests.yml`: `uv run flake8 --config=.flake8 devague/ tests/` and `--cov=devague`.
In `.github/workflows/security-checks.yml`: `bandit -r devague/` and `pylint devague/`.
In `.github/workflows/publish.yml`: path filters `"devague/**"` (both triggers) and the TestPyPI notice `... unsafe-best-match devague==${DEV_VERSION}`.

```bash
sed -i 's/specifix/devague/g' .github/workflows/tests.yml .github/workflows/security-checks.yml .github/workflows/publish.yml
```

- [ ] **Step 9: Update prose + the divergence markers**

```bash
sed -i 's/specifix/devague/g' README.md
sed -i 's/specifix-divergence/devague-divergence/g' .claude/skills/cicd/scripts/portability-lint.sh docs/skill-sources.md
```

Then hand-edit `CLAUDE.md`: replace `specifix`→`devague` throughout, update the **Project intent** section to describe devague's working-backwards method (don't leave the old "owns spec creation" framing stale), and keep the branch-finishing + signing sections (signature is now `- devague (Claude)`).

- [ ] **Step 10: Prepend a CHANGELOG entry** (keep `[0.1.0]`)

```markdown
## [0.2.0] - 2026-05-23

### Changed

- Renamed the package and CLI `specifix` → `devague` (PyPI distribution
  `devague`; the orphaned `specifix 0.1.0` is left as-is). Console script,
  `python -m`, `culture.yaml` suffix, SonarCloud key, and docs all updated.

### Removed

- The placeholder `whoami` verb (the `learn` / `explain` affordances remain).
```

- [ ] **Step 11: verify** — sync, then the full gate

```bash
uv sync
uv run python -m devague --version          # -> devague 0.2.0
uv run devague --version                     # -> devague 0.2.0
uv run devague learn                         # greenfield stub line
uv run pytest -n auto -q                     # all green
uv run flake8 --config=.flake8 devague/ tests/
markdownlint-cli2 "**/*.md"
git grep -i specifix -- . ':!CHANGELOG.md' ':!docs/superpowers/specs/*' ':!docs/superpowers/plans/2026-05-22-*' ':!uv.lock'   # expect: no matches
```

Expected: version prints `devague 0.2.0`; pytest green; flake8 + markdownlint clean; the `git grep` returns nothing (the excluded files are the historical changelog, the original onboarding spec/plan, and the lockfile which `uv sync` already rewrote).

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "Rename specifix -> devague (package, CLI, config, docs); retire whoami"
```

---

## Task 2: PyPI Trusted Publishing for `devague` (maintainer step)

**Files:** none (external configuration).

- [ ] **Step 1: Register the distribution**

On PyPI and TestPyPI, create a **pending publisher** for project `devague` pointing at `agentculture/devague`, workflow `publish.yml`, environments `pypi` / `testpypi` (mirrors how `specifix` was set up). Leave `specifix 0.1.0` published and untouched.

- [ ] **Step 2: Confirm via CI**

After the rename PR opens, the `publish.yml` `test-publish` job should succeed (publishes `devague-0.2.0.devN` to TestPyPI). If it fails with "project name incorrectly specified", the pending-publisher project name doesn't match `devague` — fix the registration.

---

## Self-review

- **Spec coverage:** Implements Phase 0 of the design (rename + PyPI). ✓
- **Placeholders:** none — every step has exact commands/edits. ✓
- **Consistency:** `DevagueError` / `_DevagueArgumentParser` / dist `devague` / `agentculture_devague` used consistently; matches what the engine plan imports. ✓

## Execution boundary

This plan is one PR. Open it via the `cicd` skill once Task 1 Step 11 is green; the engine plan (`2026-05-23-devague-working-backwards-engine.md`) builds on top after this merges.
