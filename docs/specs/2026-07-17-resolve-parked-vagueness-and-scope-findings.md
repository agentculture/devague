# resolve parked vagueness and scope findings

> Parked vagueness and recorded scope findings in devague now have close-out moves: once the user decides an open unknown, a single move records the resolution, keeps the item in the frame as evidence, and stops it blocking convergence — and a stale scope finding can be amended in place. No more hand-editing .devague state JSON.
> instruction: Verify by running the #57 reproduction verbatim against the shipped build: park an `unknown_blocking`, decide it, resolve it, and confirm `converge` passes with no edit to `.devague` state.

## Audience

- devague operators (the main agent driving the CLI move by move) and the humans who own the spec gate — plus the three reporting repos that hit this hole in practice: colleague (#45, #55), devague itself (#57), and league-of-agents (#60).
  - instruction: Check the exported spec names both audiences; the four issues are the evidence trail, not a guess.

## Before → After

- Before: `park` is append-only (`Frame.add_vagueness`) and `v*` ids are unaddressable — `set_status` routes only `c*`/`h*`, and `confirm`/`reject` accept only those. A decided `unknown_blocking` therefore blocks `converge` forever; operators recover by hand-editing `.devague/frames/<slug>.json` (evidenced in league-of-agents commit 0c71282) or by replaying the frame — exactly the out-of-band state mutation the move-driven design exists to prevent.
  - instruction: Verify against `devague/frame.py` `set_status` (line 226) and the #57 reproduction; both confirm no `v*` path exists.
- Before: Scope entries carry the identical hole: `add_scope_entry` only appends and `scope` exposes no edit or remove, so an `s*` id is unaddressable by any move. A scope finding recorded with a typo — or with an unbackticked token that fails the repo's markdownlint on export — can only be corrected by hand-editing state JSON or replaying the whole frame.
  - instruction: Verify `devague scope --help` exposes only `--finding`/`--seeds`/`--list`, and that `add_scope_entry` appends unconditionally.
- After: A decided parked vagueness is closed out by a single deterministic move that records the resolution text, keeps the item in the frame as evidence rather than deleting it, and excludes it from the convergence gate — and `converge`'s hint names that actually-executable move.
  - instruction: Run the #57 reproduction end-to-end and confirm it converges with no edit to state JSON.
- After: A recorded scope finding can be corrected in place through a move: `scope --amend <sN> --finding "<text>"` replaces the finding text (and optionally its `--seeds`), so a stale or lint-breaking entry never forces a hand-edit or a frame replay.
  - instruction: Amend a scope entry, re-export, and confirm the corrected text lands with no state-JSON edit.

## Why it matters

- Hand-editing state JSON bypasses every state-transition rule, schema validation, and `--json` echo the CLI exists to enforce — the drift the method forbids. Four issues from three repos over five weeks (2026-06-03 to 2026-07-07) report the same hole, and `converge` actively recommends a move that cannot be executed.
  - instruction: Cite `convergence.py` line 188 as the mis-hint and the four issue numbers as the demand evidence.

## Requirements

- Resolving is a user-only transition, mirroring `confirm`: the `resolve` move takes no `--origin llm` path and the agent must never resolve a vagueness on the user's behalf.
  - instruction: Check the resolve parser exposes no `--origin` flag; assert in tests that resolution records origin user.
  - honesty: The `resolve` parser exposes no `--origin` flag, so an agent cannot mark a resolution as user-originated.
- A resolved vagueness stays in the frame with its resolution text — history, not deletion. This is the explicit contrast with the hand-edit evidenced in league-of-agents 0c71282, which had to DELETE v4 to unblock.
  - instruction: Assert the item is still present in `open_vagueness` after resolve, with resolution text intact.
  - honesty: `open_vagueness` still contains the item after resolve; nothing in the move deletes from the list.
- `converge` excludes a resolved vagueness from its blockers: `_missing_open_uncertainty` blocks only on an `unknown_blocking` that is NOT resolved, and `_parked_items` reports resolved items distinctly from still-open non-blocking ones.
  - instruction: Extend `devague/convergence.py` line 102 with the resolved predicate; test that a resolved `unknown_blocking` yields `ready_for_spec`.
  - honesty: A resolved unknown_blocking yields `ready_for_spec`; an unresolved one still blocks; a resolved item is not silently dropped from the frame's reported parked items.
- `converge`'s `suggest_move` hint for a blocking vagueness names the new executable move — replacing the current line 188 hint, whose two suggested moves cannot clear a `vN` and are the mis-hint all four issues cite.
  - instruction: Assert `suggest_move` for a blocking vagueness returns a `devague resolve` invocation.
  - honesty: The new hint text, pasted verbatim into a shell, executes successfully against the frame it was emitted for.
- Frames round-trip: save then load yields an identical frame, including resolved vagueness, its resolution text, its optional claim link, and any re-kind — and a schema-2 frame still loads under schema 3 with defaults.
  - instruction: Test round-trip on a resolved frame plus a schema-2 fixture; this is the #5 h15 contract.
  - honesty: A schema-2 frame fixture committed before this change still loads and round-trips under schema 3.
- Errors follow the existing output contract: an unknown `vN`, an unknown `--claim` id, and an already-resolved `vN` are each refused to stderr with a `hint:` line and a non-zero exit; results and `--json` go to stdout.
  - instruction: Mirror the refusal style of `scope --seeds` for the unknown-id cases.
  - honesty: Each refusal exits non-zero with a `hint:` on stderr and writes nothing to stdout.
- `show` and `status` surface resolved vagueness distinctly from open vagueness, so the evidence trail is readable without `--json` — and the exported spec-md renders a resolved item as resolved, with its resolution text.
  - instruction: Check `render/spec_md.py` and `render/frame_md.py`; markdownlint the exported spec.
  - honesty: An exported spec containing a resolved vagueness passes `markdownlint-cli2`.
- `scope --amend <sN> --finding "<text>" [--seeds <claim-id> ...]` replaces a recorded finding's text in place, refusing an unknown `sN` or an unknown seed id with a `hint:` on stderr. It mirrors the existing `scope` contract, adds no new store, and — like `resolve` — takes no `--origin` flag.
  - instruction: Amend an entry, assert the finding text is replaced and the id/surface are stable; assert unknown-id refusals exit non-zero.
  - honesty: Amending a scope entry then re-exporting yields the corrected text with no state-JSON edit and no frame replay.

## Honesty conditions

- The #57 reproduction runs verbatim and converges with zero edits to `.devague/frames/<slug>.json`; the operator never needs a text editor to unblock a decided unknown.
- This frame's own spec re-exports lint-clean using `scope --amend` alone — no replay, no hand-edit. The bug that forced this very frame's replay is gone.
- Each of the four issues (#45, #55, #57, #60) is answered by the shipped surface — #45's downgrade by `--kind`, #55/#57/#60's close-out by the bare form — and each can be closed citing this spec.
- No existing move can address a `v*` id today: verified against `set_status` (frame.py line 226), `confirm`, and `reject` — all route `c*`/`h*` only.
- No existing move can address an `s*` id today: `scope` exposes only `--finding`/`--seeds`/`--list`, and `add_scope_entry` appends unconditionally.
- A resolved unknown_blocking no longer appears in `converge`'s blockers, while a still-open one still does — the gate keeps meaning something.
- Amending a scope finding changes its text and nothing else: the `sN` id and surface are stable, and no other frame state moves.
- After this ships, no documented path to unblocking convergence requires editing state JSON — the `learn` operating rules' ban on hand-editing becomes honest rather than aspirational.
- This frame is itself evidence: it had to avoid parking any `unknown_blocking`, because doing so would trap it in the same unresolvable state the fix addresses — dogfooding the bug while speccing it.
- This frame is evidence twice over: its first export failed markdownlint on scope-entry text that no move could repair, forcing the replay recorded in c16 — the `s*` half of the bug, hit while speccing the `v*` half.
- The shipped surface adds exactly one flat verb plus one flag on an existing verb, and no LLM call inside the CLI; claim-text editing and frame-to-drafting reversion remain absent.
- `uv run pytest -n auto` passes with coverage >= 95%, and flake8 / black / isort / markdownlint all pass.

## Success signals

- All four issues (#45, #55, #57, #60) close against this release; the verbatim reproduction in #57 converges without touching state JSON; this frame's own spec re-exports lint-clean through `scope --amend` alone; test coverage stays >= 95% and all linters pass.
  - instruction: Run the #57 repro as an integration test; amend a scope entry and re-export; check coverage with `uv run pytest -n auto`.

## Scope / boundaries

- Not a general frame editor. In scope: resolving/re-kinding a `v*` and amending an `s*` finding — the two append-only surfaces with no close-out path. Out of scope: claim-text editing (the frame-side half of #60), deleting vagueness or scope entries, reverting a converged frame to drafting, and any LLM judgment on whether an unknown is genuinely resolved — resolving stays a user-only decision, mirroring `confirm`.
  - instruction: Check no new move accepts `--origin llm` for the resolve transition, and that no claim-text edit path ships.

## Non-goals

- The plan-side half of issue #60 (a task-text edit verb) is not in scope: `devague plan amend` shipped it in 0.18.0 (#68), covering summary and acceptance-criteria edits with a confirmed-task demotion. #60 is closed on that half by what already exists.
  - instruction: Confirm `devague/cli/_commands/plan.py` `cmd_plan_amend` covers the `plan edit <tN> --summary` ask in #60 before closing #60.

## Scope exploration

- `s1` — `devague/frame.py`: `Vagueness` is a 4-field dataclass (`id`/`text`/`kind`/`claim_id`) with no status or resolution field; `add_vagueness` only appends; `set_status` routes `c*`/`h*` only, so `v*` ids are unaddressable by any move. Deserialization is strict kwargs (`Vagueness(**v)`), so a new field means an older devague raises `TypeError` rather than a clean schema error.
- `s2` — `devague/convergence.py`: Only `kind == unknown_blocking` blocks (line 102); everything else is reported as tracked non-blocking via `_parked_items`. `suggest_move` line 188 emits a hint naming two moves that cannot clear a `vN` — the mis-hint all four issues cite.
- `s3` — `devague/cli/_commands/question.py`: The `question --resolve` loop cited as precedent by #55/#57 does NOT mutate frame state: it writes uncommitted markdown working state under `.devague/questions/`. Vagueness lives in committed frame JSON, so resolve is a frame mutation and a stronger contract than its cited precedent.
- `s4` — `devague/cli/_commands/plan.py`: `plan amend` (#68, 0.18.0) already ships summary + acceptance-criteria editing and flips a CONFIRMED task back to proposed. This closes the plan-side half of issue #60 before this frame starts.
- `s5` — `devague/store.py`: `SCHEMA_VERSION` is 2, and load fails closed when a persisted frame declares a newer one. Any new `Vagueness` field forces a decision on bumping to 3.
- `s6` — `devague/frame.py + devague/cli/_commands/scope.py`: Discovered by dogfooding THIS frame: `add_scope_entry` is append-only and `scope` exposes no edit or remove, so `s*` ids are unaddressable exactly like `v*`. This frame's own first export failed markdownlint on scope-entry text that no move could fix — the same trap, one surface over, hit within a single session of speccing it.

## Decisions

- The move is a new flat verb: `devague resolve <vN> "<resolution text>"` — a peer of `confirm`/`reject`/`park`, matching the language `converge` already uses in its hint, and the shape 2 of the 4 issues (#55, #60) proposed.
- One move, two situations: bare `resolve <vN> "<text>"` closes out an answered unknown (#55/#57/#60); `resolve <vN> "<text>" --kind <vagueness-kind>` additionally re-kinds it, so a downgraded dependency stops blocking yet stays tracked under its new kind (#45). Both paths mark the item resolved and record the resolution text.
- The decision-claim link is optional: `resolve <vN> "<text>" [--claim <cN>]`. Never required — forcing a claim to satisfy the gate would invite fabricating one, which the method forbids. An unknown claim id is refused with a hint (the `scope --seeds` precedent).
- `SCHEMA_VERSION` bumps 2 -> 3. `Vagueness` deserializes via strict kwargs, so without a bump an older devague hits a raw `TypeError` on the new field; with it, `store.load` refuses cleanly with an upgrade hint — the fail-closed contract from #5 (h15). New devague still reads schema-2 frames (missing keys take defaults).
- The spec widens beyond the four issues to cover scope entries (`s*`) alongside vagueness (`v*`): one release closes the whole unaddressable-id class rather than leaving an identical trap one surface over. Claim-text editing stays out, so the boundary against a general frame editor holds.
- This frame was replayed from its move history (rather than hand-edited) to fix lint-breaking scope text — the #57 recovery, and the only path that uses moves alone. Previously confirmed claim and honesty texts were reproduced verbatim so prior user confirmations stay honest; changed and new items went back to the user as proposed.

## Open / follow-up

- Whether `resolve` should be reversible (an un-resolve / re-open path). No reporter asked for it; the evidence is all one-directional. Deferring until someone hits it.
- Whether the frame-side claim-text edit ask in #60 (`devague edit <cN> --text`) gets its own follow-up issue, now that the plan-side half is closed by `plan amend` (#68) and this frame rules claim-text editing out of scope.
