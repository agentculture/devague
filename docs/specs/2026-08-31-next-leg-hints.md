# next-leg hints

> Every devague command tells the agent how to progress - the next move in its leg and the hand-off to the next leg - via a hint the user can turn off or replace
> instruction: after implementation, run any verb (e.g. devague capture) and confirm a next-move hint appears on stderr; set the off switch and confirm it disappears

## Audience

- operators - the agent driving the CLI move by move - first; secondarily the humans reading the same terminal transcript
  - instruction: check the hint text is written as an instruction to the agent (imperative, names the exact next command or skill), not prose for humans

## Before → After

- After: after any devague command succeeds, one stderr hint names the next move within its leg or the hand-off to the next leg - unless the user turned hints off or replaced the text
  - instruction: capsys test: run a mutating verb, assert stderr contains exactly one hint-prefixed line and stdout is unchanged

## Why it matters

- an agent that stalls after a leg-ending verb drops the flow between legs; a per-command nudge keeps the eight-leg method self-driving without turning the CLI into a wizard
  - instruction: manual spot-check during gate-3 review: follow only the stderr hints end to end once

## Requirements

- hint emission hooks the single dispatch seam in devague/cli/`__init__.py` - `_dispatch`, after args.func succeeds - so every verb gains it in one place, with no per-module edits across the 24 command modules
  - instruction: grep devague/cli/`_commands` for the hint helper: zero call sites; implementation lives in devague/cli/`__init__.py` after rc = args.func(args)
  - honesty: the hint call site is `_dispatch` alone - no command module gains its own hint print
- hints ride stderr through the existing `emit_diagnostic` primitive in devague/cli/`_output.py` - never stdout, never inside a --json payload - preserving the stdout-results / stderr-diagnostics invariant
  - instruction: grep the hint implementation for `emit_result` usage; assert via a capsys test that stdout is unchanged for a representative verb with hints on
  - honesty: no hint ever prints to stdout in any mode, --json included
- the hint is overrideable: a user can disable hints entirely or replace the instruction text; absent an override, the defaults teach the eight-leg flow
  - instruction: set the off switch, run a verb, assert no hint; set replacement text, assert it prints verbatim
  - honesty: disabling hints requires no code change - a user-reachable switch (config or env) turns them off completely
- leg-ending verbs point across the leg boundary - export to /challenge or /spec-to-plan, plan export and plan waves to /assign-to-workforce, deviate to resuming the fan-out, evidence and delta filings toward summary and /summarize-delivery, today closing the loop - while within-leg verbs point at status as the in-leg next-move authority
  - instruction: review the hint table against the canonical order in learn.py; export, plan export, plan waves, deviate, evidence, delta, summary, today each cross a leg boundary
  - honesty: each leg-ending verb's default hint names the next leg's skill or verb, matching the eight-leg order devague learn teaches
- the eight SKILL.md hand-offs are reconciled to the same eight-leg order the hints teach: assign-to-workforce has no hand-off section at all, spec-to-plan and validate-delivery lack a dedicated After section, deviate's hand-off skips /validate-delivery, challenge's flow diagram omits validate-delivery, and summarize-delivery's provenance ordinal is stale
  - instruction: sweep the eight hand-off sections (add the missing ones, fix deviate and challenge), then markdownlint-cli2 the skill files
  - honesty: all eight SKILL.md files end with a hand-off consistent with the eight-leg order, assign-to-workforce included
- the progression hint uses a distinct stderr prefix (e.g. next:) - never hint:, which the error path already owns for remediation lines in `_output.py` `emit_error`
  - instruction: grep tests and `_output.py`: the two prefixes must never collide; a parser filtering hint: lines must not swallow progression hints
  - honesty: no stderr line ever starts with hint: unless it is an error remediation - progression hints grep cleanly by their own prefix
- config reading fails open: a missing, malformed, or unreadable pyproject.toml or env var never crashes a verb - hints just fall back to defaults (stdlib tomllib, parse errors swallowed to a diagnostic)
  - instruction: test: run a verb in a repo with a syntactically broken pyproject.toml - the verb succeeds and default hints print
  - honesty: a verb run against a syntactically broken pyproject.toml exits zero with default hints - verified by a dedicated test

## Honesty conditions

- every registered verb emits a default hint, and the off switch silences every one of them
- the full pre-existing test suite passes with edits confined to the three named empty-stderr assertions - no other existing test file changes
- every default hint is imperative and names one concrete command or skill - no vague guidance
- a successful move prints exactly one hint line on stderr - never more
- an agent can traverse scope to summarize-delivery in a sandbox repo guided only by the hints
- the byte-identical-stderr claim is verified by a test capturing stderr per verb, not by eyeball
- `SCHEMA_VERSION`, `PLAN_SCHEMA_VERSION`, and `DELIVERY_SCHEMA_VERSION` are unchanged from main on the feature branch

## Success signals

- every verb except status emits a default hint (status is exempt as the existing next-move authority); 0 of the 14 exact-stdout and 17 exact-json equality tests change; with hints disabled, stderr is byte-identical to pre-feature output for every verb
  - instruction: run the full suite unmodified before adding any new tests; diff stderr of each verb with hints disabled against the previous release

## Scope / boundaries

- existing pinned outputs stay intact: the 14 exact-stdout and 17 exact-json equality tests pass untouched because the hint never lands on stdout; the only permitted edits to existing tests are the three exact empty-stderr assertions (`test_plan_cli_instructions.py`:139, `test_summary.py`:674, `test_cli_moves.py`:558), updated to tolerate the hint line; docs/spec-contract.md gains one global hint clause, not per-move table rewrites
  - instruction: run uv run pytest -n auto before adding any new test file; any edit to an existing test falsifies this boundary
- the feature persists nothing: no frame, plan, or delivery store change, no `SCHEMA_VERSION` bump anywhere - hints are computed per invocation from the verb table plus config
  - instruction: diff the three store modules and frame.py/plan.py/delivery.py against main: zero changes

## Non-goals

- the CLI stays deterministic and non-orchestrating (issue 20) and the method stays no-wizard: a hint is one static instructional line on stderr - it never gates, never blocks, never reads cross-engine state to decide for the agent, and never replaces status as the gap-driven authority

## Assumptions

- a new static verb-to-next-move table drives the hints; `_status.py`'s `required_next_moves` machinery is convergence-blocker-driven (`suggest_move` per unmet gap) and cannot be reused as-is, though its next-move rendering is the pattern to imitate
- the hint table key derives from argparse dest command plus the plan group's subcommand dest - a bare args.command says only plan for every nested plan verb

## Scope exploration

- `s1` — `devague/cli/__init__.py (_dispatch)`: every verb funnels through `_dispatch` (rc = args.func(args), line 149); it currently never touches output on success - the natural single seam for a post-command hint
  - seeds: `c2`
- `s2` — `devague/cli/_output.py`: `emit_diagnostic` (line 42) is the stated stderr informational-line convention and is currently unused by any verb - ready-made for hints; a stdout hint would corrupt --json output
  - seeds: `c3`
- `s3` — `tests/ + docs/spec-contract.md`: spec-contract.md pins a strict per-move stdout/stderr contract (lines 12-13, 397-420); exact-equality assertions concentrate in strip-equality single-echo moves and --json dict comparisons - stderr placement avoids the sweep
  - seeds: `c4`
- `s4` — `devague/cli/_status.py + convergence engines`: `required_next_moves` is populated per unmet convergence blocker (convergence.py:301, `plan_convergence.py`:353), keyed off artifact gaps, not off which verb just ran - per-command hints need their own table
  - seeds: `c5`
- `s5` — `config surface (whole-package grep)`: no configuration mechanism exists in devague today - no env vars, no config module, no tool.devague table; store.py `ensure_ignored` (lines 59-76) gives a clean committed-vs-ignored pattern, and siblings agentirc/auntiepypi already use per-tool pyproject tables
  - seeds: `c6`, `q1` (question, resolved)
- `s6` — `devague/cli/_commands (verb-to-leg survey)`: no leg-ending verb prints any forward hint on success today: export.py:48, plan.py:976 and 1015, deviate.py:126, evidence.py:165, delta.py:162, summary.py:60, today.py:45 all end at a bare echo
  - seeds: `c7`
- `s7` — `.claude/skills (eight SKILL.md hand-offs)`: hand-off prose is inconsistent: challenge/SKILL.md:27 omits validate-delivery from its flow diagram, deviate/SKILL.md:157 hands directly to /summarize-delivery, assign-to-workforce/SKILL.md ends at Provenance with no next-leg pointer
  - seeds: `c8`
- `s8` — `issue 20 + method non-goals`: learn teaches position and role, never a you-just-ran-X-now-run-Y nudge; status is gap-driven; a static per-verb hint is additive, not duplicative - and must not become orchestration
  - seeds: `c9`
- `s9` — `challenge pass / failure-mode lens: devague/cli/_output.py error path`: `emit_error` already writes hint: prefixed remediation lines to stderr on failure (line 39); an identically prefixed progression hint would be indistinguishable to parsers
  - seeds: `c17`
- `s10` — `challenge pass / adjacent-systems lens: devague/cli/__init__.py argparse wiring`: sub = parser.`add_subparsers`(dest=command) at line 83; nested plan verbs need their own dest read at the dispatch seam or every plan move gets one generic hint
  - seeds: `c18`
- `s11` — `challenge pass / counter-evidence lens: tests stderr assertions`: the scope-leg survey checked stdout pinning only; a follow-up grep found 3 exact err-empty assertions and 184 readouterr().err sites - the byte-identical-stderr boundary c4 is falsifiable as stated
  - seeds: `q3` (question, resolved)
- `s12` — `challenge pass / operations lens: config read path`: devague runs inside consuming repos - the tool.devague table read is of the CWD pyproject, an arbitrary user file; fail-open mirrors contested.py's load-safely convention
  - seeds: `c19`
- `s13` — `challenge pass / migration lens: store schemas`: clean pass - hint state lives nowhere in .devague, so no schema bump and no upgrade path; residual risk none identified
  - seeds: `c20`
- `s14` — `challenge pass / reversibility + observability lenses: off switch, stderr visibility`: clean pass - the off switch is the rollback, the hint is itself the observability; no containment surface found beyond fail-open config

## Decisions

- override home: tool.devague table in pyproject.toml, with a `DEVAGUE_HINTS` env var fallback for non-Python projects and per-user override; precedence env over pyproject
- override granularity: one global on/off switch plus per-verb replacement text keyed by verb name
- hints print on stderr in --json mode too - stderr is JSON-agnostic by the output contract; machine-mode silence is just the off switch

## Hard questions

- three existing tests assert stderr == empty exactly (`test_plan_cli_instructions.py`:139, `test_summary.py`:674, `test_cli_moves.py`:558) - does c4's zero-test-edit boundary bend to allow amending those three, or do hints ship default-off in the test conftest? (resolved: amend c4: the three empty-stderr assertions may be updated to tolerate the hint line; hints stay default-on everywhere including CI)
- where does the override live - a committed .devague config file, a tool.devague table in pyproject.toml, or a `DEVAGUE_HINTS` env var - and is it committed team state or per-user gitignored state? (resolved: the override lives in a tool.devague table in pyproject.toml (committed, team-visible, sibling precedent); a `DEVAGUE_HINTS` env var is the fallback for non-Python projects and per-user override)
- override granularity: one global on/off plus a replacement template, or per-verb / per-leg replacement text? (resolved: global on/off plus per-verb replacement text - one switch kills all hints, individual verbs' text replaceable by key)
- is 100 percent of verbs literal - do read-only reporting verbs (status, show, list, learn, explain, converge) hint too, or would a hint after status (itself the next-move authority) be noise? (resolved: all verbs hint except status, which already renders the recommended next move)

## Open parks

- [unknown_nonblocking] whether multi-mode verbs (deviate, evidence, delta: filing vs --list vs --confirm) need per-mode hint text rather than one per-verb line - not decidable until the table is designed
