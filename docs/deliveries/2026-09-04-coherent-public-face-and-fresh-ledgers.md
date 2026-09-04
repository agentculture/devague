# Delivery Summary — coherent public face and fresh ledgers

plan: `coherent-public-face-and-fresh-ledgers` · run: `complete` · date: `2026-09-04`
baseline: `devague summary skeleton`

## Intent

> devague's README now reads like agentculture.org/agents/devague — diagrams, real code examples, all eight skills in flow order — the eight skills tell one coherent story, and every ledger (claims, lapses, deviations, evidence, deltas) is CLI-managed and filed the moment it happens, so the record stays fresh

After: A newcomer reads README.md top to bottom and meets one eight-leg diagram, numbered moves with real captured output, the three human gates, and the ledgers the CLI keeps; the eight skills agree with each other and with the CLI; CLAUDE.md and docs describe the shipped surface with no statement the code contradicts

## Planned Work

- `t1` — Conventions source of truth in docs/skills.md: the shared hand-off section, the shared freshness rule, and the canonical eight-leg diagram block
- `t2` — CLAUDE.md: shrink the Status section to the current release plus a CHANGELOG pointer and remove the two false statements
- `t3` — docs/spec-contract.md: entity sections for Obligation, EvidenceRecord and DeltaRecord matching the shipped dataclasses
- `t4` — README.md rewrite: what / why it works / how to use / impact, with the eight-leg mermaid diagram, numbered walkthrough, agent-driven statement above the fold, verified captures and the artifact table
- `t5` — Skills cluster A (scope, think, challenge, spec-to-plan): fix think's after-export paths, add the shared hand-off section, freshness rule and next: hint mention
- `t6` — Skills cluster B (assign-to-workforce, deviate, validate-delivery, summarize-delivery): redraw the six-leg diagrams as eight legs, add the shared hand-off section, freshness rule, next: hint and devague today mentions
- `t7` — tests/`test_readme_commands.py`: pin README.md to the shipped CLI and to its own structural promises
- `t8` — Release hygiene: patch version bump and a CHANGELOG entry that quotes the before state verbatim
- `t9` — Verification sweep: boundaries untouched, no stale leg or verb text anywhere, lint and tests green, README answers the three reader questions

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | `docs/skills.md` gains `### Shared conventions` (hand-off heading + template, freshness sentence, canonical eight-leg block) and one pointer sentence per skill section — commit `6d349da`, merged `114a290` |
| `t2` | delivered | `CLAUDE.md` Status cut from 265 lines to one 0.24.0 paragraph plus a CHANGELOG pointer; both false statements gone; everything below Status byte-identical — commit `5350a54`, merged `c4bf2fe` |
| `t3` | delivered | `docs/spec-contract.md` gains Obligation, CriterionObligation, RunReference, EvidenceRecord, DeltaRecord, SupersessionEvent sections; field-diff script reported zero differences — commit `3a1d0f7`, merged `6119de5` |
| `t4` | delivered | `README.md` rewritten to the four sections with one mermaid diagram, eight-item walkthrough, three version-stamped captures, impact table (227 lines) — commit `204a92f`, merged `4d7023f`; then re-edited by the main agent under `d1` to 202 lines — commit `c5ae504` |
| `t5` | delivered | scope / think / challenge / spec-to-plan gain the hand-off section, freshness bullet and `next:` mention; think's after-export paths fixed (#47) — commit `112f28f`, merged `e4a36d6` |
| `t6` | delivered | assign-to-workforce / deviate / validate-delivery / summarize-delivery gain the same; deviate and summarize-delivery diagrams redrawn to eight legs (#100); `devague today` named in the two closing skills — commit `189bf33`, merged `dbf0ef6` |
| `t7` | delivered | `tests/test_readme_commands.py` (7 tests) pins README command lines to `devague.cli._build_parser` and its structure — commit `ee8e5a1`, merged `f223030` |
| `t8` | delivered | version 0.24.1, `uv.lock`, CHANGELOG entry quoting the three before-state lines — commit `b94b685`, merged `596a8e8`; two misattributed bullets corrected by the main agent — commit `952fe6a` (lapse `l2`) |
| `t9` | delivered | sweep ran every criterion; fixed a pre-existing MD038 in assign-to-workforce/SKILL.md — commit `fa5a21c`, merged `171589e`; its two criterion-1 failures were false positives of the criterion, not violations (lapse `l3`) |

## Mid-work Decisions

- `d1` — After t4's README lands and t7's pinning test merges, the main agent (not a workforce subagent) makes an additional editorial pass over README.md: validate it against the spec, make it welcoming, cut prose to light-or-none, keep it technical and clear; t7's test and t9's sweep must still pass afterwards — user request mid-run: the leading model owns the final README quality, beyond t4's acceptance criteria

- `d2` — Post-run README restructure by the main agent: install and agent setup move to the top, the verb-level walkthrough and the three console captures are removed, tests/test_readme_commands.py is re-pinned to the new section list; supersedes the shape t4 and t7 delivered — user direction after gate 3 opened: devague is installed with uv tool install / uvx and the agent learns the skills via devague learn skills; specific commands do not matter to the human reader
- CHANGELOG bullets from `t8` were corrected by the main agent after merge (think fix misdescribed; a CLAUDE.md quote misattributed to spec-contract.md) — no deviation record; recorded as lapse `l2` and fixed in `952fe6a`.
- `t9`'s first acceptance criterion produced two false failures (untracked files in `../org` dated July, and the `.devague/` frame and plan JSON the spec and plan commits intentionally added); resolved by measurement (`git -C ../org diff --stat` empty), not by editing the criterion — recorded as lapse `l3`.
- `t9` fixed a pre-existing MD038 lint error in assign-to-workforce/SKILL.md that the repo's `.claude/skills/**` lint ignore had hidden — within its instruction, no record needed.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|------------------------|-----------------|
| `t4` (`d1`) | user request mid-run: the leading model owns the final README quality, beyond t4's acceptance criteria | `acceptable` |
| `t4`, `t7` (`d2`) | user direction after gate 3 opened: devague is installed with uv tool install / uvx and the agent learns the skills via devague learn skills; specific commands do not matter to the human reader | `acceptable` |
| `t8` | CHANGELOG entry needed two factual corrections after merge (`l2`); the version bump and quotes were correct | `acceptable` |
| `t9` | criterion 1 as written flagged pre-existing untracked files and intended `.devague/` state as violations (`l3`); the honesty conditions h4 and h9 behind it hold | `acceptable` |

## Evidence

- tests: `tests/test_readme_commands.py` — pass (7 passed at 171589e; 5 passed at head after deviation d2 dropped the capture assertions)
- tests: `tests/test_spec_to_plan_skill.py tests/test_teaching_surface_sweep.py tests/test_cli_learn.py tests/test_summary.py` — pass (199 passed)
- tests: `uv run pytest -n auto -q` — pass (1651 passed; baseline before the run 1644)
- lint: `uv run flake8 --config=.flake8 devague/ tests/` — clean
- lint: `markdownlint-cli2 README.md CLAUDE.md CHANGELOG.md docs/*.md` — 0 errors
- lint: the eight SKILL.md files copied beside a config without the `.claude/skills/**` ignore — 0 errors
- grep: `six-leg|seven-leg|still unimplemented|ships separately|docs/reviews` across README, CLAUDE.md, docs, skills — 0 hits
- render: `readme_renderer` on README.md — one `pre lang=mermaid` block, list items intact (PyPI fallback)
- boundary: `git -C ../org diff --stat` and `--cached` — empty; `git -C ../guildmaster status --short` — empty
- commits: `4e66665..171589e` (spec, plan, split, nine task merges, two main-agent reconciliations)
- ledger: obligations `o1`–`o12`, evidence `e1`–`e12` (all pass, run commit `171589e`), deltas `b1` `b2`, deviations `d1` `d2`, lapses `l1`–`l3` — all approved
- note: `d2` removed the console captures after `e2`/`e1` were filed; `c3`'s capture half and `h14` no longer hold on the final README and are superseded by decision `c29`, not claimed
- PRs / issues: this branch's PR (opened after this artifact; closes #100 and #47)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| `c2` — README.md replaces its stale three-stage arrow (README.md lines 10-12: idea, spec, plan, build) with an eight-leg pipeline diagram as a mermaid fence, and adds a numbered move walkthrough (01 scope ... 08 summarize-delivery) modeled on the site page's pipeline stages and method sections | `execution` | `tests/test_readme_commands.py` (run 2026-09-04) |
| `c3` — README.md gains real, verified code examples: every command block is checked against the shipped 'devague --help' / 'devague plan --help' output, and one short verbatim terminal capture per engine (frame, plan, delivery ledger) shows actual output including the 'next:' stderr hint | `coverage` | `tests/test_readme_commands.py::test_every_readme_bash_devague_line_matches_the_shipped_cli` (run 2026-09-04; e13 replaces e2, whose test ref named a node that never existed — lapse l4) |
| `c4` — README.md does not copy the site page's leg count: agentculture.org/agents/devague still presents seven legs and seven operator skills (no validate-delivery, no lapse, no oblige/evidence/delta, no today); the README stays ahead and the site is updated separately in the org repo | `fidelity` | `git -C ../org diff --stat and diff --cached --stat` (run 2026-09-04) |
| `c6` — The deviate and summarize-delivery skills redraw their literal flow diagrams (deviate/SKILL.md lines 20-25, summarize-delivery/SKILL.md lines 22-27) as the eight-leg flow, and think/SKILL.md's after-export step (lines 275-277) cites .devague/frames/ and .devague/reviews/ instead of .devague/ and docs/reviews/ (closes issues 100 and 47) | `execution` | `grep -rn 'six-leg\|seven-leg\|docs/reviews' + md5sum of the three diagram blocks` (run 2026-09-04) |
| `c7` — Every skill that files a ledger record carries one explicit freshness rule in its hard rules: file the record at the moment the thing happens, never at closeout; today only challenge (line 178), deviate (lines 4-5, 44, 109) and summarize-delivery (lines 33, 308) say so, while scope, spec-to-plan, assign-to-workforce and validate-delivery do not | `execution` | `tr newline + grep across the eight SKILL.md` (run 2026-09-04) |
| `c8` — The eight skills share one hand-off convention: each SKILL.md states the leg before it and after it in a same-named section, mentions devague today where the leg produces or consumes it (validate-delivery, summarize-delivery), and mentions the 'next:' stderr hint as the CLI's own next-move signal (issue 40 item 14 flags spec-to-plan's missing hand-off section) | `execution` | `grep -l for the hand-off heading, 'next: ' and 'devague today'` (run 2026-09-04) |
| `c15` — CLAUDE.md's Status section shrinks to the current release plus a pointer to CHANGELOG.md, and its two false statements are removed (lines 49-50: 'the exact oblige / evidence / delta CLI surface ships separately'; lines 199-202: 'devague scope ... still unimplemented'); docs/spec-contract.md gains entity sections for Obligation, EvidenceRecord and DeltaRecord documenting the fields that exist today | `execution` | `awk over CLAUDE.md Status + grep -c of six entity headings in docs/spec-contract.md` (run 2026-09-04) |
| `c18` — Humans meeting devague cold on GitHub or PyPI (a reader deciding whether to install it) first; operator agents driving the CLI second, via the skills and devague learn | `execution` | `sed -n 1,12p README.md \| grep for ids, capture, interrogate, converge` (run 2026-09-04) |
| `c19` — A reader who has only the README can name the eight legs in order, the three human gates, and what devague never does (call an LLM, run a test, orchestrate); markdownlint-cli2 passes on every touched file; every command block in README matches the shipped --help output | `execution` | `markdownlint-cli2 on README.md CLAUDE.md CHANGELOG.md docs/*.md, and on the eight SKILL.md copied beside a config without the skills ignore` (run 2026-09-04) |
| `c23` — The numbered eight-leg walkthrough in README.md stands alone as the text fallback for the diagram: pyproject.toml line 6 makes README.md the PyPI long description, and a scratch probe with `readme_renderer` rendered a mermaid fence as a plain pre block (lang mermaid), so PyPI readers never see the diagram | `execution` | `uv run --with readme-renderer[md] python -m readme_renderer README.md` (run 2026-09-04) |
| `c24` — The full pytest suite stays green after the skill edits: tests/`test_spec_to_plan_skill.py` (t19) pins spec-to-plan's moves table to the live CLI, tests/`test_teaching_surface_sweep.py` section 9 pins learn output against scope/SKILL.md, tests/`test_cli_learn.py` pins the SKILL.md paths, and tests/`test_summary.py` pins the delivery summary's eight sections to summarize-delivery/SKILL.md order | `execution` | `uv run pytest -n auto -q` (run 2026-09-04) |
| `c25` — The PR bumps the version (patch, 0.24.x) and prepends a CHANGELOG.md entry: .github/workflows/tests.yml line 64 enforces the AgentCulture rule that every PR bumps the version, docs included | `coverage` | `uv run devague --version + grep -n in CHANGELOG.md` (run 2026-09-04) |

Confidence tokens above are the evidence ledger's strength values. Three approved lapses cap what they touch: `l1` (a hand-edited capture, caught and restored) bears on `c3`; `l2` on the CHANGELOG half of `c25`; `l3` on the boundary check behind `c4`. None was found by reading data afterwards — each was filed the moment it was reported.

Lapse ledger evidence:

| Lapse | Code | What |
|-------|------|------|
| `l1` | `provenance-missing` | t4 README agent shortened a captured 'devague plan task' line (dropped --instruction and two --covers flags) while claiming captures were verbatim; caught before commit, exact recorded line restored and a byte-identity differ added |
| `l2` | `provenance-missing` | t8 CHANGELOG entry misdescribed think's fix (said 'route through /challenge'; the fix was the .devague/frames and .devague/reviews paths, #47) and attributed the 'ships separately' sentence to docs/spec-contract.md when git show main proves it was in CLAUDE.md |
| `l3` | `grader-unverified` | t9's first acceptance criterion, which I authored, graded 'git status --short empty' in ../org and a path allow-list without .devague/; both conflated pre-existing untracked files and intended frame/plan state with violations, so the grader reported two false failures |

## Remaining Work / Follow-up

- agentculture.org/agents/devague still presents seven legs (park `v1`) — file an issue on the `org` repo to bring the page to eight legs with validate-delivery, lapse, evidence/delta and today; owner: the user.
- guildmaster skill-update brief (park `v3`, risk `r2`) — after this PR merges, send the `communicate` skill's `skill-update-brief.md` so mesh consumers re-vendor the eight skills; owner: devague agent.
- README captures embed 0.24.x output (risk `r1`) — refresh when a release changes any captured line; the version comment on each capture makes staleness visible.
- `.claude/skills/**` is ignored by the repo's markdownlint config, so skill files lint only by hand (found by `t6`, fixed by `t9`) — consider a CI step that lints them with the ignore lifted; owner: follow-up issue.
- Obligation id prefix `o` collides between frame and plan (#108) — documented in spec-contract.md as a known ambiguity, not fixed here.
- After merge: close #100 and #47; then `/summarize-delivery`'s park `v2` (mermaid syntax parity with the site pipeline) stays open until the README is ever republished there.
