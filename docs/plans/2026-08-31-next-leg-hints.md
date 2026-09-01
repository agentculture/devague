# Build Plan — next-leg hints

slug: `next-leg-hints` · status: `exported` · from frame: `next-leg-hints`

> Every devague command tells the agent how to progress - the next move in its leg and the hand-off to the next leg - via a hint the user can turn off or replace

## Tasks

### t1 — Hint table and dispatch emission: new devague/cli/`_hints.py` with the verb-to-next-move table (flat verbs plus plan subverbs, status exempt, next: prefix), wired once into `_dispatch` on success

- instruction: Build the table in a new devague/cli/`_hints.py`: a dict keyed by verb name (for the plan group, key on `plan:<subverb>` read from the plan subparser dest). Emit via `emit_diagnostic` from `_dispatch` in devague/cli/`__init__.py` after rc = args.func(args) returns success - one line, prefix next: (never hint:, the error path owns that). Exempt status and plan status. Default texts are imperative and name one concrete command or skill; leg-boundary map: export -> /challenge or /spec-to-plan; plan export and plan waves -> /assign-to-workforce; deviate -> resume the fan-out; evidence/delta -> devague summary and /summarize-delivery; today -> commit docs/current-spec.md. Do not read config here - t2 adds it; hardcode default-on.
- covers: c1, c2, h4, c3, c7, h6, c10, h8, c11, h9, c12, c17, h12, c20, h14
- acceptance:
  - a successful run of every registered verb except status prints exactly one stderr line starting with next: (parametrized test over the verb table)
  - grep of devague/cli/`_commands` finds zero hint call sites; the only emission point is devague/cli/`__init__.py`
  - leg-ending verbs (export, plan export, plan waves, deviate, evidence, delta, summary, today) hint the next leg per the eight-leg order; within-leg verbs hint devague status or devague plan status
  - stdout is byte-identical with hints on, --json included; no store module or `SCHEMA_VERSION` constant is touched

### t2 — Override config: new devague/cli/`_hint_config.py` reading tool.devague from the CWD pyproject.toml plus the `DEVAGUE_HINTS` env var (env wins) - global on/off and per-verb replacement text, fail-open

- instruction: Stdlib tomllib only; read the consuming repo's ./pyproject.toml (CWD), swallow every parse/read error - fail open to defaults, mirroring contested.py's load-safely convention. Wire the lookup into `_hints.py`'s emission decision. `DEVAGUE_HINTS` accepts off/0/false (case-insensitive) to disable; any other value is ignored rather than an error. Keep config unpersisted - nothing lands in .devague state.
- depends on: t1
- covers: c6, h2, c19, h13
- acceptance:
  - `DEVAGUE_HINTS`=off silences every hint; hints = false under the tool.devague table does the same; env beats pyproject when both are set
  - a per-verb key under tool.devague hints replaces that verb's text verbatim; unknown keys are ignored
  - a missing, unreadable, or syntactically broken pyproject.toml never changes the exit code - the verb succeeds with default hints (dedicated test)
  - with hints disabled, stderr for every verb is byte-identical to pre-feature output (captured-stderr test, not eyeball)

### t3 — Docs sweep: the global hint clause in docs/spec-contract.md, README, CLAUDE.md, and the learn/explain teaching surface

- instruction: Quote the final default hint texts from the merged `_hints.py` table verbatim - do not restate from memory. The spec-contract clause lives beside the existing stdout/stderr split statement (lines 12-13 area).
- depends on: t1
- covers: c12
- acceptance:
  - docs/spec-contract.md gains one global clause describing the next: stderr hint and its override - no per-move table rewrites
  - README.md and CLAUDE.md name the hint feature and the tool.devague / `DEVAGUE_HINTS` override; devague explain covers the override for at least the leg-ending verbs; devague learn mentions hints in its operating rules
  - markdownlint-cli2 passes on every touched markdown file

### t4 — Eight SKILL.md hand-off reconciliation to the eight-leg order

- instruction: Fix exactly the inconsistencies the challenge pass recorded (s7): missing hand-off in assign-to-workforce, deviate skipping validate-delivery, challenge's diagram at line 27, buried hand-off in spec-to-plan (line 253), step-7-only hand-off in validate-delivery, stale ordinal in summarize-delivery's Provenance. Keep hand-off wording consistent with the CLI hint texts t1 ships - same next leg for the same boundary.
- covers: c8, h7
- acceptance:
  - assign-to-workforce gains a hand-off section naming /deviate (mid-run) and /validate-delivery (post-merge); deviate's hand-off routes through /validate-delivery before /summarize-delivery; challenge's flow diagram includes validate-delivery
  - spec-to-plan and validate-delivery gain a dedicated After section; summarize-delivery's provenance ordinal is corrected; all eight files pass markdownlint-cli2

### t5 — Hint test suite: new tests/`test_cli_hints.py` plus the three permitted empty-stderr assertion updates

- instruction: Use capsys/capfd against main() directly, matching the existing test idiom. The byte-identical-off test captures stderr per verb with `DEVAGUE_HINTS`=off and compares against a no-hints baseline. Mark the end-to-end hint-following walk with the behavioral pytest marker - it is this plan's behavioral contract for /validate-delivery.
- depends on: t1, t2
- covers: c4, h5, h3, h1, c13, h11, h10, h15
- acceptance:
  - the full pre-existing suite passes with edits confined to `test_plan_cli_instructions.py`:139, `test_summary.py`:674, `test_cli_moves.py`:558 (each updated to tolerate one next: line)
  - tests assert: exactly one next: stderr line per successful verb, zero next: lines on failure and on status, stdout unchanged with hints on for a --json verb, and no stderr line starts with hint: outside error paths
  - a behavioral test (behavioral pytest marker) walks new -> capture -> interrogate -> confirm -> converge -> export in a tmp repo following only the emitted hints

## Risks

- [unknown_nonblocking] multi-mode verbs (deviate, evidence, delta: filing vs --list vs --confirm) may need per-mode hint text rather than one per-verb line - decide during t1 table design, from the park v1 the challenge pass left
