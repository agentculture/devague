# Build Plan — reasoning-degradation ledger

slug: `reasoning-degradation-ledger` · status: `exported` · from frame: `reasoning-degradation-ledger`

> devague gains a deterministic move that records degradations of the reasoning process — moments where an assumption was silently substituted for a check — as first-class append-only ledger entries filed when they happen: the reasoning-side twin of deviate, never gating convergence

## Tasks

### t1 — Lapse domain model on Frame: LapseRecord, lapse codes, schema v5

- instruction: mirror DeviationRecord (devague/delivery.py) for the record shape — id, code, what, `skipped_check`, refs, origin, status (proposed/approved/rejected); validate code in `add_lapse` (the filing path), NOT in `__post_init__`, so retired codes stay loadable — c21 deliberately refines the c2 chassis pattern here; statuses and origin still validate fail-closed in `__post_init__` (they never retire); the six issue-97 codes are the starting `LAPSE_CODES` tuple; bump `SCHEMA_VERSION` to 5 in frame.py and move the pin in tests/`test_frame_schema_v2.py`; new tests in tests/`test_frame_lapse.py`
- covers: c2, h2, c17, h12, c20, c21, h16
- acceptance:
  - Frame.lapses exists; `add_lapse` mints l1, l2, ... via the prefix-generic `_next`; llm origin lands proposed, user origin lands approved; `to_dict`/`from_dict` round-trip lapses verbatim
  - filing an unknown code raises ValueError, while `from_dict` loads a stored record carrying a retired code without error — pinned by a test that files, retires the code, and reloads
  - `SCHEMA_VERSION` == 5; a frame declaring 6 is refused fail-closed before parsing; a v4 frame without lapses loads clean and re-saves as v5
  - no amend or delete API exists for lapse records — the only post-filing mutation is `set_lapse_status`; refs are stored verbatim as free text, never validated

### t2 — CLI verb lapse: file, list, adjudicate

- instruction: clone the deviate.py argument surface minus --task and minus id-ref validation (refs stay free text); one new module devague/cli/`_commands`/lapse.py exposing register(), two lines in cli/`__init__.py` `_build_parser`; add the lapse row to the MOVES dict in learn.py; tests in tests/`test_cli_lapse.py`
- depends on: t1
- covers: c1, c12, c18, h15, h6
- acceptance:
  - `devague lapse "<what>" --code <code>` files against the current frame and echoes the minted id; `--origin llm` lands proposed; `--skipped "<check>"` and repeatable `--ref` are stored verbatim
  - `--list [--json]` renders every record with id, code, and status; `--confirm <lN>` / `--reject <lN>` transition only proposed records, refuse otherwise, and are mutually exclusive with recording
  - the argument surface has no amend or delete flag — pinned by a test over the parser
  - `devague explain lapse` succeeds and bare `devague learn` lists the move — the MOVES entry is test-pinned
  - recording is deterministic: no subprocess and no LLM call, mirroring the deviate determinism test

### t3 — Render the ledger: show and summary consume, spec stays untouched

- instruction: follow the `_mid_work_lines`/`_drift_lines` approved/pending/rejected discipline in `summary_md.py`; `frame_md.py` gets the new section; `spec_md.py` gets NO code change — only the byte-identity regression test; tests in tests/`test_summary.py` and tests/`test_render_sharper.py`
- depends on: t1
- covers: c4, h3, c10, c19, h14, h13
- acceptance:
  - devague show renders a Lapse ledger section (id, code, status, what) omitted entirely when empty
  - devague summary cites approved lapses as evidence for the Delivery Claims confidence column; proposed entries render visibly pending; rejected are omitted; zero entries keeps the existing empty-state line — all through `md_safe_text` and table-cell escaping
  - re-exporting the spec after filing lapses produces a byte-identical spec-md — pinned by a test that files a lapse and diffs `render_spec` output
  - a frame that fails to load degrades in summary exactly as today — no new failure mode

### t4 — Gate inertness pinned by tests

- instruction: pure test task, no production code: if a gate references lapses the production change is wrong, not the test; add to tests/`test_convergence.py` and tests/`test_plan_convergence.py`
- depends on: t1
- covers: h1
- acceptance:
  - converge output is byte-identical before and after filing lapses on an otherwise converged frame — proposed, approved, and rejected records all tried
  - neither gate ever names lapse records: frame and plan convergence blockers, warnings, and `parked_items` stay lapse-free in every status combination

### t5 — Skills sweep: producer, consumer, and the subagent boundary

- instruction: quote the shipped CLI surface exactly as t2 built it — no paraphrase; sweep .claude/skills/{challenge,summarize-delivery,assign-to-workforce}/SKILL.md plus docs/skills.md; the deviate skill needs no change beyond any enumeration that names all moves
- depends on: t2
- covers: c5, h4, c6, h5, c9, h7
- acceptance:
  - the challenge routing table gains a row routing an already-happened reasoning degradation to devague lapse, and the nothing-else hard rule names the move
  - the summarize-delivery read-only moves table and hard rule gain `lapse --list`, and the Delivery Claims method step reads the ledger to ground each confidence level
  - the assign-to-workforce worktree prohibition generalizes to every devague move, naming lapse explicitly: a task agent reports a degradation in its transcript, the main agent files it
  - no SKILL.md introduces a new gate or workflow owner: adjudication is named as `lapse --confirm` / `--reject` exercised by the existing gate owners; docs/skills.md enumerations match every table touched

### t6 — Docs, contract, changelog, version

- instruction: minor version bump (new feature) per the version-bump convention; keep the spec-contract Moves row shape identical to the deviate row
- depends on: t2
- covers: c7, c11, h9, h10
- acceptance:
  - docs/spec-contract.md gains the lapse entity (fields, statuses, id prefix l, the filing-time-closed load-time-tolerant code rule) plus a Moves contract row and a schema v5 line in Versioning
  - README.md names lapse in the flat-verb inventory and the agent-driving flow; CLAUDE.md status reflects the new surface
  - CHANGELOG entry and version bump land so the CI version-check passes
  - the CHANGELOG or README cites issue 97 and the embodiment corrections-record evidence — the before-state and its four grader failures are documented, not anecdotal

## Deferred targets

- `h8` (honesty): in the dogfood cycle no single filing costs the operator more than a minute — otherwise the cheap-enough-to-use-mid-flight premise is false — deferred: post-ship embodiment dogfood milestone (park v1): measurable only after a real cycle runs with the shipped verb
- `c13` (success_signal): in >= 1 dogfooded embodiment cycle, every degradation entry is filed mid-flight (0 reconstructed in the retrospective) and 0 codes ship without a named producer moment — codes with zero filings are dropped before the vocabulary freezes — deferred: post-ship embodiment dogfood milestone (park v1): measurable only after a real cycle runs with the shipped verb
- `h11` (honesty): a code with zero filings after the dogfood cycle is actually removed from the enum, not kept as documentation — covered is distinguished from reachable — deferred: post-ship embodiment dogfood milestone (park v1): the dead-code removal decision needs the dogfood filing counts

## Risks

- [follow_up] file the pre-existing learn.py explain gap (deviate, summary, plan absent from MOVES) as its own upstream issue before the PR merges — t2 adds only the lapse entry
- [follow_up] whether summarize-delivery should cap a delivery-claim confidence at low or unverified when an approved lapse names it — deferred to the embodiment dogfood report
