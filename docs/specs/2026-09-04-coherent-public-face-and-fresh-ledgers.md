# coherent public face and fresh ledgers

> devague's README now reads like agentculture.org/agents/devague — diagrams, real code examples, all eight skills in flow order — the eight skills tell one coherent story, and every ledger (claims, lapses, deviations, evidence, deltas) is CLI-managed and filed the moment it happens, so the record stays fresh
> instruction: Verify by reading README.md, the eight SKILL.md files and CLAUDE.md as one document: one diagram, eight legs everywhere, no six- or seven-leg text, no path or verb the CLI lacks

## Audience

- Humans meeting devague cold on GitHub or PyPI (a reader deciding whether to install it) first; operator agents driving the CLI second, via the skills and devague learn

## Before → After

- After: A newcomer reads README.md top to bottom and meets one eight-leg diagram, numbered moves with real captured output, the three human gates, and the ledgers the CLI keeps; the eight skills agree with each other and with the CLI; CLAUDE.md and docs describe the shipped surface with no statement the code contradicts
  - instruction: Read README.md, the eight SKILL.md files and CLAUDE.md as a first-time reader; list any leg, verb or path they disagree on

## Why it matters

- devague's method is only as credible as its own record: a README whose diagram contradicts its prose, two skills drawing a six-leg flow, and a CLAUDE.md that calls shipped verbs unimplemented undercut the anti-fabrication contract the tool exists to enforce
  - instruction: Cite README.md lines 10-12, deviate/SKILL.md lines 20-25 and CLAUDE.md lines 49-50 as the before state in the PR description

## Requirements

- README.md replaces its stale three-stage arrow (README.md lines 10-12: idea, spec, plan, build) with an eight-leg pipeline diagram as a mermaid fence, and adds a numbered move walkthrough (01 scope ... 08 summarize-delivery) modeled on the site page's pipeline stages and method sections
  - instruction: Diagram: a left-to-right mermaid flowchart with the eight legs and the three human gates as annotated nodes; keep it under 20 lines so GitHub renders it legibly
  - honesty: README.md contains exactly one mermaid fence naming all eight legs in flow order and a numbered walkthrough with one entry per leg; markdownlint-cli2 README.md exits 0
- README.md gains real, verified code examples: every command block is checked against the shipped 'devague --help' / 'devague plan --help' output, and one short verbatim terminal capture per engine (frame, plan, delivery ledger) shows actual output including the 'next:' stderr hint
  - instruction: Run each README command block in a throwaway frame under a scratch directory, paste stdout and the stderr next: line verbatim, and note the devague version the capture came from
  - honesty: Every fenced devague command in README.md is present in the shipped --help output at the version README names, and every captured output block was pasted from a real run in this repo, never typed by hand
  - honesty: Each captured output block in README.md names the devague version it was recorded at, so a reader can tell when a capture has aged past the installed release
- The deviate and summarize-delivery skills redraw their literal flow diagrams (deviate/SKILL.md lines 20-25, summarize-delivery/SKILL.md lines 22-27) as the eight-leg flow, and think/SKILL.md's after-export step (lines 275-277) cites .devague/frames/ and .devague/reviews/ instead of .devague/ and docs/reviews/ (closes issues 100 and 47)
  - instruction: Copy the eight-leg diagram already used in validate-delivery/SKILL.md lines 26-29 so all three literal diagrams are byte-identical
  - honesty: grep -r 'six-leg' .claude/skills returns nothing; the deviate and summarize-delivery diagrams list all eight legs; think/SKILL.md's after-export step names .devague/frames/ and .devague/reviews/; issues 100 and 47 can be closed from the PR
- Every skill that files a ledger record carries one explicit freshness rule in its hard rules: file the record at the moment the thing happens, never at closeout; today only challenge (line 178), deviate (lines 4-5, 44, 109) and summarize-delivery (lines 33, 308) say so, while scope, spec-to-plan, assign-to-workforce and validate-delivery do not
  - instruction: One sentence, same wording in all eight files, placed as the last hard rule so a diff across skills shows a single shared line
  - honesty: Each of the eight SKILL.md files carries the file-at-the-moment-it-happens rule inside its Hard rules section, worded identically, citing issue 97's 'written late is written flattering'
- The eight skills share one hand-off convention: each SKILL.md states the leg before it and after it in a same-named section, mentions devague today where the leg produces or consumes it (validate-delivery, summarize-delivery), and mentions the 'next:' stderr hint as the CLI's own next-move signal (issue 40 item 14 flags spec-to-plan's missing hand-off section)
  - instruction: Use one heading text for the hand-off section in all eight skills; for the terminal leg say explicitly that nothing follows
  - honesty: Each SKILL.md has a hand-off section naming the leg before it and the leg after it; validate-delivery and summarize-delivery name devague today and docs/current-spec.md; every skill names the next: stderr hint as the CLI's own next-move signal
- CLAUDE.md's Status section shrinks to the current release plus a pointer to CHANGELOG.md, and its two false statements are removed (lines 49-50: 'the exact oblige / evidence / delta CLI surface ships separately'; lines 199-202: 'devague scope ... still unimplemented'); docs/spec-contract.md gains entity sections for Obligation, EvidenceRecord and DeltaRecord documenting the fields that exist today
  - instruction: Diff the spec-contract field lists against the dataclass fields with a one-off script before committing; do not document fields the code lacks
  - honesty: CLAUDE.md's Status section is one paragraph about the current release plus a pointer to CHANGELOG.md; docs/spec-contract.md has entity sections for Obligation, EvidenceRecord and DeltaRecord whose field lists match the dataclasses in devague/frame.py and devague/delivery.py
- The numbered eight-leg walkthrough in README.md stands alone as the text fallback for the diagram: pyproject.toml line 6 makes README.md the PyPI long description, and a scratch probe with `readme_renderer` rendered a mermaid fence as a plain pre block (lang mermaid), so PyPI readers never see the diagram
  - instruction: Run uv run --with 'readme-renderer\[md\]' python -m `readme_renderer` README.md -o /tmp/x.html and check the flow is legible in the HTML without the diagram
  - honesty: `readme_renderer` output of README.md, viewed without the diagram, still shows the eight legs in order in the numbered walkthrough
- The full pytest suite stays green after the skill edits: tests/`test_spec_to_plan_skill.py` (t19) pins spec-to-plan's moves table to the live CLI, tests/`test_teaching_surface_sweep.py` section 9 pins learn output against scope/SKILL.md, tests/`test_cli_learn.py` pins the SKILL.md paths, and tests/`test_summary.py` pins the delivery summary's eight sections to summarize-delivery/SKILL.md order
  - instruction: uv run pytest -n auto after every skill edit; a docs-only PR is not exempt
  - honesty: uv run pytest -n auto exits 0 on the branch before the PR opens, with no test skipped or deleted to get there
- The PR bumps the version (patch, 0.24.x) and prepends a CHANGELOG.md entry: .github/workflows/tests.yml line 64 enforces the AgentCulture rule that every PR bumps the version, docs included
  - instruction: Use the version-bump skill before opening the PR
  - honesty: pyproject.toml version differs from main and CHANGELOG.md has a matching entry at the top
- docs/skills.md's per-skill sections (lines 167-401) are swept to describe the shared hand-off convention and the shared freshness rule, so the long-form companion to devague learn skills does not contradict the skills it documents
  - instruction: grep docs/skills.md for each skill's heading and add the two shared conventions once, in the section that describes the minimum file structure
  - honesty: docs/skills.md names the shared hand-off section and the shared freshness rule exactly once each, with the same wording the eight SKILL.md files use

## Honesty conditions

- Every command block in README.md is checked against uv run devague --help / devague plan --help at the shipped version, and no diagram or skill draws a leg or verb the CLI does not have
- No file under the org repo (site-astro) is modified by this work; the site's seven-leg state is recorded as parked follow-up v1 and, if the user wants, an issue on agentculture/org
- No file outside this repo is modified; docs/skill-sources.md changes only if a provenance note needs a new date
- README.md's first screen, everything before the Install heading, uses no claim ids, move names or devague jargon that has not been introduced yet
- A reviewer given only README.md answers three questions correctly: the eight legs in order, the three gates, and the three things devague never does; markdownlint-cli2 exits 0 on every touched markdown file; a script diffs each README command block against --help output with 0 misses
- A first-time reader's walk through README.md, the eight SKILL.md files and CLAUDE.md finds zero disagreements on leg count, verb names or paths, checked by grep for 'six-leg', 'seven-leg', 'still unimplemented' and 'ships separately' returning nothing
- The PR description quotes the before state verbatim (README.md lines 10-12, deviate/SKILL.md lines 20-25, CLAUDE.md lines 49-50) so the credibility gap being closed is on record, not asserted

## Success signals

- A reader who has only the README can name the eight legs in order, the three human gates, and what devague never does (call an LLM, run a test, orchestrate); markdownlint-cli2 passes on every touched file; every command block in README matches the shipped --help output

## Scope / boundaries

- README.md does not copy the site page's leg count: agentculture.org/agents/devague still presents seven legs and seven operator skills (no validate-delivery, no lapse, no oblige/evidence/delta, no today); the README stays ahead and the site is updated separately in the org repo
  - instruction: git -C ~/git/org status --short must be empty after this work
- The eight origin skills are edited only in this repo (devague is their upstream per docs/skill-sources.md); guildmaster re-broadcasts them from here, and the agentculture.org page lives in the org repo, so neither is touched by this work beyond a follow-up issue
  - instruction: git status in this repo shows changes only under README.md, CLAUDE.md, docs/ and .claude/skills/; nothing under ../guildmaster

## Assumptions

- GitHub renders mermaid fences in README.md, and the repo's .markdownlint-cli2.yaml (config default true, MD013 off, no MD040 override) accepts a mermaid fence as a valid fenced-code language, so diagrams add no lint exception

## Scope exploration

- `s1` — `README.md lines 1-30 and 107-144`: the only diagram is a three-stage ASCII arrow that predates scope, challenge, deviate, validate-delivery and summarize-delivery; the prose below it already names all eight legs, so the diagram contradicts its own file
  - seeds: `c2`
- `s2` — `org repo site-astro/src/data/devague.ts (agentculture.org/agents/devague content model)`: the page's structure is: fast facts, the pipeline (seven named stages plus an animated SVG flow), the method (numbered moves), the human gate, the operator skills (one card per leg), real captures, what's next; README has no diagram, no numbered walkthrough and no explicit 'what devague never does' line
  - seeds: `c2`
- `s3` — `README.md sections Two engines / Human Review Loop, checked against uv run devague --help and devague plan --help (0.24.0)`: every verb the README names exists; there is no example that shows real output, and nothing mentions the 'next:' stderr hint that 0.24.0 prints after every non-exempt move
  - seeds: `c3`
- `s4` — `org repo site-astro/src/pages/agents/devague.astro header comment and site-astro/src/data/devague.ts (grep validate-delivery: 0 hits)`: the live page is a seven-leg presentation; it lacks validate-delivery, lapse, oblige/evidence/delta and today, so it is a structural model for the README, not a content source
  - seeds: `c4`
- `s5` — `.markdownlint-cli2.yaml and grep for mermaid/svg/png across README.md and docs/*.md`: zero diagrams exist anywhere in the repo's markdown today; the lint config does not block a mermaid fence
  - seeds: `c5`
- `s6` — `.claude/skills/deviate/SKILL.md lines 20-25 and summarize-delivery/SKILL.md lines 22-27`: both still draw 'scope -> think -> spec-to-plan -> assign-to-workforce -> deviate -> summarize-delivery' and summarize-delivery calls it the six-leg flow at the top while stating eight legs at lines 456-458; issue 100 is live on this checkout
  - seeds: `c6`
- `s7` — `.claude/skills/think/SKILL.md lines 85 and 274-278`: line 85 correctly documents .devague/reviews/ but the after-export step tells the agent to commit .devague/slug.json and docs/reviews/, neither of which the CLI writes; issue 47 is live on this checkout
  - seeds: `c6`
- `s8` — `all eight .claude/skills/*/SKILL.md, grepped for 'the moment' / 'immediately' / timing language`: timing guidance exists in three skills and is absent in five; assign-to-workforce lines 320-328 route a subagent's lapse to the main agent for later filing rather than immediate filing
  - seeds: `c7`
- `s9` — `all eight SKILL.md files, grepped for 'devague today' and 'next:'`: no skill mentions devague today although it is a shipped verb whose output docs/current-spec.md the delivery legs produce; no skill mentions the next: hint line (they document only the error-path hint: line from cli/`_output.py` line 39)
  - seeds: `c8`
- `s10` — `devague/frame.py lines 130-140 (ClaimRevision docstring) and devague/staleness.py lines 24-34`: no individual record carries a timestamp by design ('no other Frame entity does either'); only Frame/Plan/Delivery carry created/updated stamped on save (store.py 123-125, `plan_store.py` 42-44, `delivery_store.py` 44-46); staleness orders records by numeric id suffix as an approximation of chronology
  - seeds: `c9` (rejected)
- `s11` — `devague/cli/_commands/ (no ledger.py) and the --list flags on lapse.py, deviate.py, evidence.py, delta.py, oblige.py, scope.py`: the delivery store has no standalone show verb; each family is read only through its own --list, and nothing lists frame, plan and delivery records together
  - seeds: `c10` (rejected)
- `s12` — `devague/staleness.py docstring lines 1-16 and find_staleness (line 248), devague/contested.py, devague/frame.py obligation_drift (line 284)`: the shipped joins are deviation-vs-evidence, evidence-vs-obligation/delta, claim-vs-deviation and claim-text-vs-snapshot; nothing joins a confirmed claim against a later approved delta, the natural third direction the staleness docstring leaves open
  - seeds: `c11` (rejected)
- `s13` — `devague/cli/_commands/learn.py line 249 ('Plant obligations early') and devague/cli/_hints.py lines 79-107`: the only file-it-now rule in the tool is about obligations; the hint tables nudge the next leg and the human adjudication, never prompt filing
  - seeds: `c12` (rejected)
- `s14` — `CLAUDE.md sections The Reasoning Degradation Ledger and The boundary: devague stays deterministic (issue 20)`: the repo's standing rule is that ledgers never gate and the CLI never runs an LLM or orchestrates; a freshness feature must inherit both
  - seeds: `c13` (rejected)
- `s15` — `devague/frame.py lines 130-140 and the SCHEMA_VERSION checks in store.py / plan_store.py`: the codebase's pattern for additive fields is a `default_factory` that lets older frames load unchanged; a backfill would fabricate history
  - seeds: `c14` (rejected)
- `s16` — `CLAUDE.md lines 5-269 (Status, 13 reverse-chronological release paragraphs) and lines 49-51, 199-202; docs/spec-contract.md entity sections`: Status is a 265-line changelog duplicating CHANGELOG.md and contains two statements the code contradicts; spec-contract.md documents lapses and deviations but not obligations, evidence or deltas as record kinds
  - seeds: `c15`
- `s17` — `docs/skill-sources.md and CLAUDE.md Ecosystem context`: origin skills are never re-vendored back from guildmaster; the site page source is site-astro in the org repo
  - seeds: `c16`
- `s18` — `challenge pass / adjacent-systems lens: pyproject.toml readme field + readme_renderer probe in scratch`: PyPI's renderer emits a plain code block tagged mermaid (`pre lang=mermaid`) for a mermaid fence, no diagram; GitHub renders it; README must read well both ways
  - seeds: `c23`
- `s19` — `challenge pass / hidden-dependencies lens: tests/ grep for README and SKILL.md`: four test modules read or pin skill text; restructuring sections in spec-to-plan or summarize-delivery can fail them; the new hand-off section must be additive
  - seeds: `c24`
- `s20` — `challenge pass / lifecycle lens: .github/workflows/tests.yml version-check job`: CI blocks merge without a bump even for docs-only changes; the spec did not name it
  - seeds: `c25`
- `s21` — `challenge pass / unexamined-surfaces lens: docs/skills.md and docs/skill-sources.md`: docs/skills.md documents each skill's structure and was not named by any claim; devague learn skills output names no section headings (grep), so learn.py stays untouched under c17
  - seeds: `c26`
- `s22` — `challenge pass / unstated-assumptions lens: README captures vs releases`: captured output embeds the version and ids; it ages with every release and nothing regenerates it; seeded an honesty condition that each capture is version-stamped
- `s23` — `challenge pass / security, migration, concurrency, reversibility lenses: README.md, .claude/skills, CLAUDE.md, docs`: clean pass: text-only changes under git, revertible by git revert; no store, schema, or CLI surface touched under decision c17; residual risk is only downstream skill copies aging (parked)
- `s24` — `challenge pass / observability lens: CI tests.yml + markdownlint`: clean pass: lint and the doc-pinning tests are the only signals; markdownlint ignores .claude/skills/\*\* so skill files must be linted by hand

## Decisions

- This frame changes no devague CLI behavior: it refreshes README.md, the eight origin skills, CLAUDE.md and docs so a human reader can follow the method; the CLI-managed ledgers (lapse, deviate, oblige, evidence, delta) and the file-it-the-moment-it-happens rule are documented as existing behavior, not built
- README.md says plainly, above the fold, that devague is built to be driven by an AI agent through the eight skills; a human reads it to understand what the agent will do, where the three human gates sit, and what the CLI refuses to do on its own
  - instruction: The first paragraph of README.md names the agent as the operator and the human as the gate owner; no wording implies a human types the moves by hand
- README.md is organised around the four things a reader cares about, in this order: what devague is doing, why it works (the method and the gates), how to use it (install, the moves, the skills), and impact — what lands in .devague/ (frames, plans, deliveries) and in docs/ (specs, plans, deliveries, current-spec.md)
  - instruction: Four top-level sections in that order; the impact section is a table of every artifact path the CLI writes, with the verb that writes it and whether it is committed
- Scope is wider than the README the user asked for, deliberately, and for three different reasons: CLAUDE.md is covered because two of its statements are false against the code (lines 49-50 say the oblige/evidence/delta verbs ship separately; lines 199-202 say devague scope is still unimplemented), a verified staleness finding; docs/spec-contract.md is covered for completeness, not staleness (it documents lapses and deviations but not obligations, evidence or deltas), so a reader of the README's impact section can follow every ledger to its contract; docs/skills.md is covered only as a consequence of the skill edits (t5, t6): it is the single source the eight skills copy the shared hand-off section and freshness rule from, and it would contradict them otherwise. Nothing else outside README.md and the eight skills is touched
  - instruction: The PR description carries this paragraph under a heading 'Why more than the README'; a reviewer who wants README-only can drop t2 and t3 without breaking t4-t9

## Hard questions

- Should CLAUDE.md's Status section keep only the current release and point to CHANGELOG.md, or be removed in favour of the stable method sections alone? (resolved: CLAUDE.md Status keeps one paragraph for the current release plus a pointer to CHANGELOG.md; the twelve older release paragraphs and the two false statements go)

## Open parks

- [unknown_nonblocking] Whether GitHub's mermaid renderer and the AgentCulture site's markdown pipeline (if README is ever re-published there) agree on the same diagram syntax is unverified
- [unknown_nonblocking] Target length for README.md once captures and the walkthrough land is undecided; the site page runs long by design, a README may not
- [follow_up] The agentculture.org page (org repo, site-astro) still presents seven legs; bringing it to eight with validate-delivery, lapse, evidence/delta and today is a separate org-repo issue, not part of this frame
- [follow_up] After merge, guildmaster needs a skill-update brief (communicate skill template skill-update-brief.md) so mesh consumers re-vendor the eight skills; not part of this frame
