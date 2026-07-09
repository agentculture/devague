# Delivery Summary — summarize-delivery skill

plan: `summarize-delivery-skill` · run: `complete` · date: `2026-07-09`
baseline: `devague plan (summarize-delivery-skill)`

## Intent

This run set out to close the devague method's open end. The flow ran
`scope` → `think` → `spec-to-plan` → `assign-to-workforce` and then stopped:
nothing recorded what execution actually produced. Agents make mid-work
decisions, hit constraints, cut scope, and assert delivery claims that were
never in the plan, and none of it was captured. The run delivers the fifth
origin skill, **`summarize-delivery`** — the delivery-side closure leg that
turns an execution run into a committed accountability artifact — by executing
the converged plan `summarize-delivery-skill`: 5 tasks over 3 waves, fanned out
by `/assign-to-workforce` to a **mixed-backend workforce** and merged behind a
TDD gate.

This summary is the skill's second use and its first **self-application**: the
run that shipped `summarize-delivery` is reported by `summarize-delivery`.

## Planned Work

Quoted verbatim from `devague plan waves --json` (task id and summary, keyed by
id). The plan's waves are `[t1, t2, t3]` · `[t4]` · `[t5]`.

- `t1` — author .claude/skills/summarize-delivery/SKILL.md - the method-only
  skill with the eight-section delivery-summary template and the
  no-overclaiming hard rules
- `t2` — register summarize-delivery as the fifth origin skill in
  docs/skill-sources.md
- `t3` — update the flow docs: five-leg flow in CLAUDE.md, the
  assign-to-workforce handoff, and the README and docs/skills.md family mentions
- `t4` — dogfood: produce the first real delivery summary at docs/deliveries/
  for the sharper-end-to-end-method run (issue 53, PRs 53, 54, 58)
- `t5` — release hygiene: minor version bump with changelog, full test suite,
  and repo-wide markdown lint

## Actual Delivery

Every one of the 5 plan tasks is accounted for. Status breakdown:
**5 delivered, 0 partial, 0 dropped, 0 blocked.** Each merged behind the
`/assign-to-workforce` TDD gate (tests and tracked-markdown lint green before
*and* after every merge).

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `.claude/skills/summarize-delivery/SKILL.md` (379 lines): eight-section template, delivery-claim row contract, drift entry contract, hard rules, a partial-run worked example. Executed by **opus**. |
| `t2` | delivered | `docs/skill-sources.md` gains the fifth origin-skill row plus both prose enumerations and the vendoring-policy bullet. Executed by **colleague** (vLLM Qwen3.6-27B). |
| `t3` | delivered | Five-leg flow named in `CLAUDE.md`, `README.md`, `docs/skills.md`; new "after the final PR" handoff section in `.claude/skills/assign-to-workforce/SKILL.md`. Executed by **opus** after colleague failed twice — see Drift. |
| `t4` | delivered | `docs/deliveries/2026-07-09-sharper-end-to-end-method.md` — the first real delivery summary, covering the `#53` run: 14/14 tasks accounted for, 3 classified drift entries, 1 claim honestly marked `unverified`. Executed by **opus**. |
| `t5` | delivered | Version `0.16.0` → `0.17.0`, `CHANGELOG.md` `## [0.17.0]` entry, `uv.lock` self-pin. Executed by **opus** after colleague failed twice — see Drift. |

## Mid-work Decisions

Constraints discovered and choices made during execution that the plan did not
prescribe.

- **The workforce was made mixed-backend mid-gate.** The approved split plan
  assigned `t2`/`t3`/`t5` to a cheaper Claude model; the user amended it to the
  `colleague` CLI (a different backend — local vLLM Qwen3.6-27B) for the value
  of a genuinely independent mind. Accepted and applied.
- **`colleague work` exits `0` whether it succeeds or does nothing.** On failure
  it writes `status: incomplete`, `steps: 0`, `changed files: (none)` — and
  still returns exit code `0`. Its own prose summary is likewise not evidence.
  Detected only by parsing the `status:` line and reading the diff. The
  operator's TDD merge gate is what caught it.
- **Escalation policy adopted after repeated silent failure.** Two failures on a
  task were treated as sufficient evidence to reassign it to a stronger model
  rather than stall the wave. Applied to `t3` and `t5`.
- **A brief-length hypothesis was formed and then falsified.** `t2` (short
  brief) succeeded and `t3` (longer) failed, suggesting brief size was the
  cause. A deliberately trimmed `t5` brief then failed identically, so the
  hypothesis was wrong: the failure is nondeterministic tool-call formatting
  (the model emits `` `<tool_call>list_dir(...)` `` or
  `` `<read_file>{...}` `` as literal prose at step 0). Recorded because the
  first explanation was stated before it was tested.
- **The installed `devague` had to be upgraded before the run could start.**
  `assign-to-workforce`'s wrapper resolves an installed `devague` on `PATH`
  ahead of the checkout's `uv run devague`; the installed binary was `0.14.1`
  and refused the schema-v2 plan (`uses schema_version 2, but this devague
  supports up to 1`). Resolved with `uv tool install -U devague` → `0.17.0`
  published on PyPI.
- **Branch namespace changed to avoid clobbering unmerged work.** The
  `/assign-to-workforce` worked example prescribes `agent/<task-id>`, but task
  ids restart at `t1` for every plan, and unmerged `agent/t1`–`agent/t5` from
  the `#53` run already existed. This run used `agent/sd-<task-id>`. No
  pre-existing branch was reused or deleted.
- **"Repo-wide markdown lint" was scoped to tracked files.** The operator's
  local tree carries gitignored `.devague/reviews/` artifacts with a
  pre-existing `MD026` violation. `t5` then established that a clean worktree
  has no such directory, so the raw `markdownlint-cli2 "**/*.md"` passes there
  too — the caveat was about the operator's working tree, not the repo.
- **PR review re-opened the CLI.** The plan converged on a skills-only release.
  Qodo's review of PR `#63` surfaced a real data-loss bug — this run's *own*
  frame had been committed as `schema_version: 1` while carrying v2 payload,
  because `think.sh` had resolved the stale installed `devague` 0.14.1 at
  `devague new` time and `save()` re-emitted the loaded version thereafter. The
  operator chose to fix the stores rather than only relabel the artifact:
  relabeling would have left the defect armed for the next frame edited across
  a version boundary. Release scope grew; `CHANGELOG.md`, the PR body, and this
  artifact were corrected to say so.
- **The operator misread its own review tooling, twice.** A hand-rolled regex
  over Qodo's comment scraped only `<summary>` tags and reported "no bug
  findings"; both findings sit in the collapsed `<details>` bodies — the exact
  failure mode already recorded in the operator's notes. `agex pr read`
  surfaced them on the first call. The earlier "no bugs" statement was wrong
  and is retracted here rather than quietly dropped.

## Drift From Plan

Exhaustive relative to the plan. Tasks `t1`, `t2`, and `t4` landed exactly per
their acceptance criteria and are not drift entries. The entries below are the
only divergences; all are classified `acceptable` except where noted.

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t3` (execution) | The approved split plan assigned this task to `colleague`. It failed twice — `status: incomplete`, `steps: 0`, zero files changed, exit `0` both times (flight ids `e8251d046733`, `fdac321b7780`). Reassigned to **opus** by the operator without returning to the human. The task's contract, acceptance criteria, and brief were unchanged; only the executing model differs. | acceptable |
| `t5` (execution) | Same failure mode, twice (flight ids `8171f73f3a2e`, `2b43baffea88`), including once with a deliberately shortened brief. Reassigned to **opus**. Contract unchanged. | acceptable |
| `t5` (scope limit) | The task brief limited edits to `pyproject.toml` / `CHANGELOG.md` / `devague/__init__.py`. The executing agent also committed `uv.lock` — a single-line devague self-version pin (`0.16.0` → `0.17.0`) regenerated by `uv`. Committing it is correct release hygiene; leaving it stale would re-dirty the tree on the next `uv sync`. The agent flagged it rather than hiding it. | acceptable |
| whole plan (deliverables) | This artifact — `docs/deliveries/2026-07-09-summarize-delivery-skill.md` — was **not** a plan task. The plan's only delivery-summary task was `t4` (the `#53` run). The operator added a self-application of the skill as a sixth, unplanned deliverable. It is additive, changes no confirmed task, and is the strongest available evidence that the skill works. | acceptable |
| run procedure (branch names) | The `/assign-to-workforce` worked example prescribes `agent/<task-id>`; this run used `agent/sd-<task-id>` because plan-local task ids collide in the repo-global branch namespace. The skill's own example would have failed here. The deviation was forced, and the skill's worked example is now known-wrong. | needs-follow-up |
| whole plan (release scope) | The plan and its `t5` acceptance criteria assumed a **skills-only** release with the CLI unchanged. PR review (Qodo, `#63`) surfaced a real data-loss bug in `devague/store.py` and `devague/plan_store.py`: `save()` re-emitted the `schema_version` loaded from disk rather than the one the running binary writes, so this run's own frame was committed as v1 while carrying v2 payload. Fixed in-branch (upgrade-on-write + 2 regression tests, `833ab78`), which makes the release **skills + one correctness fix**. `CHANGELOG.md` and the PR body were corrected to say so. Scope grew after convergence; the alternative — shipping a known data-loss bug — was worse. | acceptable |

## Evidence

Read-only checks run to substantiate the claims below. Every pointer is
resolvable: a commit that exists, a file present in the tree, or a test run
that happened.

- tests: `uv run pytest -n auto -q` — **418 passed**, run before and after each
  of the five merges (the TDD gate).
- lint: `git ls-files '*.md' | grep -v '^docs/superpowers/' | grep -v
  '^.claude/skills/' | xargs markdownlint-cli2` — **23 files, 0 errors**.
- task commits: `a5ea5e0` (`t1`) · `ae22bbd` (`t2`) · `91dfc99` (`t3`) ·
  `e69bcea` (`t4`) · `39d102a` (`t5`).
- merge commits: `dc03e63` (`t1`) · `ea395d6` (`t2`) · `b138a48` (`t3`) ·
  `63665fe` (`t4`) · `b259ba6` (`t5`).
- provenance commits: `c41800b` (converged spec, `/think`) · `9166f73`
  (converged plan, `/spec-to-plan`).
- colleague failure artifacts: branches `colleague/e8251d046733-*`,
  `colleague/fdac321b7780-*` (`t3`), `colleague/8171f73f3a2e-*`,
  `colleague/2b43baffea88-*` (`t5`) — each with `status: incomplete`, zero
  changed files. Success artifact: `colleague/d2d145ec48bd-*` (`t2`),
  `status: ok`, 5 `edit_file` steps.
- version: `pyproject.toml` `version = "0.17.0"` (`main` is `0.16.0`).
- frame provenance: `devague scope --list` records 5 scope entries (`s1`–`s5`),
  each citing the surface explored and the claim ids it seeded.
- gate arithmetic: the plan's 30 coverage targets (`c*`/`h*`) are each covered
  by a confirmed task; `devague plan converge` reported `converged ✓`.

## Delivery Claims

Each claim carries a confidence level and at least one resolvable evidence
pointer. Nothing is asserted as done without evidence.

| Claim | Confidence | Evidence |
|-------|------------|----------|
| The `summarize-delivery` skill ships, method-only (no script, no CLI verb) | high | file `.claude/skills/summarize-delivery/SKILL.md` · commit `a5ea5e0` · the directory contains no `scripts/` |
| Its template carries all eight sections in order, and a partial-run worked example | high | file `.claude/skills/summarize-delivery/SKILL.md` (template block lines 123–197, `## Intent` → `## Remaining Work / Follow-up`; partial-run worked example lines 305–356) |
| Delivery-claim rows require confidence + resolvable evidence; drift entries require exactly one classification | high | `SKILL.md` "the row contract" / "the entry contract" sections |
| It is registered as the fifth origin skill | high | file `docs/skill-sources.md` · commit `ae22bbd` |
| The five-leg flow is named across the flow docs, with a workforce handoff | high | files `CLAUDE.md`, `README.md`, `docs/skills.md`, `.claude/skills/assign-to-workforce/SKILL.md` · commit `91dfc99` |
| The first dogfood artifact accounts for 100 % of the `#53` plan's 14 tasks and marks one claim `unverified` | high | file `docs/deliveries/2026-07-09-sharper-end-to-end-method.md` · commit `e69bcea` · independently re-verified: `grep -ci scope devague/cli/_status.py` → `0` |
| The `#53` artifact's evidence pointers resolve | high | operator re-check: all cited files/tests exist; `frame.py:15` and `plan.py:30` read `SCHEMA_VERSION = 2`; PRs `#53`/`#54`/`#58` MERGED with merge commits `67a3eca`/`51669f7`/`92c60ca`; sharper-method subset = exactly **135 passed** |
| Release `0.17.0` with a Keep-a-Changelog entry naming all four deliverables | high | `pyproject.toml` · `CHANGELOG.md` `## [0.17.0]` · commit `39d102a` |
| The devague CLI gains no new verbs; its only code change is the schema-stamp fix | high | commits `a5ea5e0`..`39d102a` touch no file under `devague/`; `833ab78` touches only `store.py` / `plan_store.py` (no verb added) |
| The full suite passes and tracked markdown lints clean | high | `uv run pytest -n auto` → **420 passed** (418 + 2 regression tests) · markdownlint → 0 errors · `flake8` / `isort` clean |
| Producing *this* summary left `.devague/` unmutated | high | only read-only moves used (`plan waves --json`, `scope --list`); the sole `.devague/` change on this branch is `current_plan`, written earlier by `devague plan new` during the `/spec-to-plan` leg |
| `colleague work` returns exit `0` on silent failure | high | **6 of 7 attempts** (incl. 2 on the post-review schema fix): `status: incomplete`, `steps: 0`, `changed files: (none)`, exit `0` |
| A real data-loss bug (stale `schema_version` on save) is fixed, with tests that fail without the fix | high | commit `833ab78` · `tests/test_store.py::test_save_upgrades_stale_schema_version_on_write` and the `test_plan_store.py` peer — both verified to FAIL against the pre-fix source, then pass |
| Qodo finding 2 ("LLM tasks stored as confirmed") is a false positive | high | `devague/plan.py:109` — `status = "proposed" if origin == "llm" else "confirmed"`; the tasks were confirmed by the user at the review gate, and `confirm` leaves `origin` as immutable provenance |
| The final PR gate (human gate 3) has passed | unverified | PR `#63` is open and awaiting human review — not claimed |
| guildmaster will re-broadcast `summarize-delivery` to the AgentCulture mesh | unverified | outside this repo; no observation available here |
| The skill produces good summaries for runs it did not itself execute | low | one instance only (`t4`, the `#53` run) — a single successful application is weak evidence of generality |

## Remaining Work / Follow-up

- **Open the final PR (human gate 3).** The last remaining gate; the human
  reviews and merges. This artifact is the review map. Owner: operator, then
  the human.
- **Fix `/assign-to-workforce`'s worked example — branch namespace.** It
  prescribes `agent/<task-id>`, which collides across plans because task ids
  restart at `t1`. Recommend namespacing per plan (`agent/<plan-slug>-<task-id>`)
  and checking `git merge-base --is-ancestor` before reusing any branch. This
  run hit the collision immediately. Owner: devague maintainer.
- **Reap or merge the stale `agent/t1`–`agent/t5` branches** left unmerged by
  the `#53` run. They were deliberately not touched here. Owner: devague
  maintainer.
- **Report `colleague work`'s exit-code behavior upstream.** Exiting `0` on
  `status: incomplete` makes silent failure indistinguishable from success to
  any caller that checks `$?`. Owner: colleague maintainer.
- **Delivery engine remains parked** (frame vagueness `v1`, kind `follow_up`):
  a third structural peer with a delivery store, per-task accounting, and a
  deterministic no-overclaim gate. Deferred until dogfooding the method-only
  skill shows machine state is needed. One self-application is not yet that
  evidence.
- **Inherited from the `#53` run, unresolved:** whether
  `devague status` should surface the optional pre-frame scope leg
  (`cli/_status.py` has no scope reference). Recorded in
  `docs/deliveries/2026-07-09-sharper-end-to-end-method.md`; still a decision
  the maintainer owes. Owner: devague maintainer.
- **Confirmation provenance is not persisted.** Qodo's finding 2 was a false
  positive, but it gestures at something real: the stored state records a
  task's `origin` and its terminal `status`, not *who* confirmed it or *when*.
  A static reader cannot distinguish a user-confirmed item from an
  auto-confirmed one; only the CLI's behavior guarantees the gate. Consider
  recording confirmation provenance. Owner: devague maintainer.
- **The `think.sh` wrapper resolves a stale `PATH` binary ahead of the
  checkout**, which is how this run's frame was stamped v1 in the first place.
  The schema fix stops the silent data loss, but the wrapper still prefers an
  installed `devague` over the local `uv run devague`. Owner: devague
  maintainer.
- **No blocked, dropped, or partial tasks** carry over from this run — all 5
  plan tasks were delivered, so there is no incomplete plan work to re-run.
