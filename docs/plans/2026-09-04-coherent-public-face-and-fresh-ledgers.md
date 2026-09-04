# Build Plan — coherent public face and fresh ledgers

slug: `coherent-public-face-and-fresh-ledgers` · status: `exported` · from frame: `coherent-public-face-and-fresh-ledgers`

> devague's README now reads like agentculture.org/agents/devague — diagrams, real code examples, all eight skills in flow order — the eight skills tell one coherent story, and every ledger (claims, lapses, deviations, evidence, deltas) is CLI-managed and filed the moment it happens, so the record stays fresh

## Tasks

### t1 — Conventions source of truth in docs/skills.md: the shared hand-off section, the shared freshness rule, and the canonical eight-leg diagram block

- instruction: Touch only docs/skills.md. Read the eight SKILL.md files first so the diagram text matches validate-delivery/SKILL.md lines 26-29 byte for byte. Do not edit any SKILL.md here; t4 and t5 copy from this file.
- covers: c26, h18
- acceptance:
  - docs/skills.md's 'Minimum file structure' section defines, once each: (a) the hand-off section heading '## Before and after this leg' and its two-line template (previous leg, next leg; the terminal leg says 'nothing follows'), (b) the freshness rule sentence, verbatim, to be copied into every skill's Hard rules: 'File the record the moment the thing happens, never at closeout — written late is written flattering (issue 97).', and (c) a fenced text block with the eight legs 'scope -> think -> challenge -> spec-to-plan -> assign-to-workforce -> deviate -> validate-delivery -> summarize-delivery' marked as the only diagram skills may copy
  - Each of the eight per-skill sections (lines 167-401 today) gains one sentence pointing at the shared conventions rather than restating them
  - markdownlint-cli2 docs/skills.md exits 0

### t2 — CLAUDE.md: shrink the Status section to the current release plus a CHANGELOG pointer and remove the two false statements

- instruction: Touch only CLAUDE.md. History lives in CHANGELOG.md; do not move paragraphs there, delete them. Keep the eight-leg flow sentence and the ledger-never-gates rule somewhere below Status if deleting a paragraph would lose them (check 'Working-backwards method' and 'Project intent' already carry both).
- covers: c15, h8
- acceptance:
  - CLAUDE.md's '## Status' section is one paragraph describing 0.24.0 (next-leg hints) followed by one line pointing at CHANGELOG.md for history; the twelve older release paragraphs are deleted
  - grep -n 'ships separately' CLAUDE.md and grep -n 'still unimplemented' CLAUDE.md both return nothing
  - Every section after Status is byte-identical to before, except the 'Stack expectations' bullet that already lists the CLI verbs
  - markdownlint-cli2 CLAUDE.md exits 0

### t3 — docs/spec-contract.md: entity sections for Obligation, EvidenceRecord and DeltaRecord matching the shipped dataclasses

- instruction: Touch only docs/spec-contract.md. Mirror the LapseRecord section's shape (purpose, fields table, status vocabulary, which CLI verb files it, append-only note). Cite the filing verbs oblige / evidence / delta and the id prefixes o, e, b; note the o-prefix collision between frame and plan obligations (issue 108) as a known ambiguity, not a fix.
- covers: c15, h8
- acceptance:
  - docs/spec-contract.md has a section for each of Obligation (devague/frame.py) and CriterionObligation (devague/plan.py), EvidenceRecord with RunReference, DeltaRecord and SupersessionEvent (devague/delivery.py), each listing exactly the dataclass's fields with one line per field, in the style of the existing LapseRecord section
  - A one-off scratch script that reads dataclasses.fields() for each class and diffs against the documented field names reports zero differences; paste its output into the PR description
  - No field is documented that the code lacks (no timestamp fields: decision c17)
  - markdownlint-cli2 docs/spec-contract.md exits 0

### t4 — README.md rewrite: what / why it works / how to use / impact, with the eight-leg mermaid diagram, numbered walkthrough, agent-driven statement above the fold, verified captures and the artifact table

- instruction: Touch only README.md. Copy the eight-leg diagram legs from docs/skills.md (t1) so wording matches. Produce the captures by running the commands in a scratch directory (git init, devague new ... export, devague plan new ... waves, devague deviate ... --list) with 'uv run devague' from this checkout and paste stdout plus the stderr next: line verbatim; do not type output by hand. Keep the existing Human Review Loop content but fold it under 'Why it works'. Do not mention timestamps or a ledger verb (rejected claims c9-c14). The site page is a structural model only; it still shows seven legs.
- depends on: t1
- covers: c1, c2, c3, h14, c18, h10, c19, c20, c23, h15, h2, h3
- acceptance:
  - README.md has exactly four H2 sections in this order: 'What devague does', 'Why it works', 'How to use it', 'Impact: what lands where'; no other H2 exists
  - The first paragraph, before any H2, says devague is built to be driven by an AI agent through eight skills and that humans own three gates; it uses no claim ids, move names or ledger jargon
  - Exactly one fenced mermaid block exists, a flowchart LR under 20 lines naming the eight legs in order plus the three human gates; the old three-stage text arrow is gone
  - A numbered list with exactly eight entries, one per leg in order, each one sentence naming the skill and the CLI verbs it drives, appears directly after the diagram so a PyPI reader gets the flow without it
  - Every fenced bash block's devague commands are real: each verb, subverb and flag exists in the shipped --help output at 0.24.x; three captured output blocks (frame, plan, delivery ledger) are pasted from real runs, each preceded by a comment line naming the devague version, and each shows the next: stderr line
  - The impact section is one table with a row per artifact path the CLI writes: .devague/frames, plans, deliveries, current, reviews, questions, docs/specs, docs/plans, docs/deliveries, docs/current-spec.md, each with the verb that writes it and whether it is committed or gitignored
  - A three-item 'what devague never does' list appears in the 'Why it works' section: call an LLM, run a test, orchestrate agents
  - markdownlint-cli2 README.md exits 0 and README.md is under 260 lines

### t5 — Skills cluster A (scope, think, challenge, spec-to-plan): fix think's after-export paths, add the shared hand-off section, freshness rule and next: hint mention

- instruction: Touch only the four SKILL.md files named. Additive edits only: do not move or rename existing sections (tests pin spec-to-plan's moves table and learn's scope text). Copy the hand-off template, freshness sentence and diagram from docs/skills.md verbatim; do not paraphrase.
- depends on: t1
- covers: c6, h5, c7, h6, c8, h7
- acceptance:
  - think/SKILL.md's after-export step cites .devague/frames/ and .devague/reviews/; grep 'docs/reviews' .claude/skills/think/SKILL.md returns nothing (issue 47)
  - Each of scope, think, challenge, spec-to-plan SKILL.md has a '## Before and after this leg' section with the two-line template from docs/skills.md, naming the correct previous and next skill
  - Each of the four files ends its Hard rules list with the freshness rule sentence from docs/skills.md, byte-identical
  - Each of the four files mentions, once, that the CLI prints a next: line on stderr after every successful move and that the operator follows it or runs devague status
  - uv run pytest tests/`test_teaching_surface_sweep.py` tests/`test_spec_to_plan_skill.py` tests/`test_cli_learn.py` -q passes; markdownlint-cli2 on the four files exits 0 (they are ignored by the repo config, so run it by explicit path)

### t6 — Skills cluster B (assign-to-workforce, deviate, validate-delivery, summarize-delivery): redraw the six-leg diagrams as eight legs, add the shared hand-off section, freshness rule, next: hint and devague today mentions

- instruction: Touch only the four SKILL.md files named. Additive edits; never reorder summarize-delivery's eight summary sections. Copy template, sentence and diagram from docs/skills.md verbatim. In assign-to-workforce leave scripts/ untouched.
- depends on: t1
- covers: c6, h5, c7, h6, c8, h7
- acceptance:
  - deviate/SKILL.md and summarize-delivery/SKILL.md draw the eight-leg diagram byte-identical to validate-delivery/SKILL.md; grep -r 'six-leg' .claude/skills returns nothing (issue 100); deviate calls itself the sixth of eight legs
  - Each of the four files has a '## Before and after this leg' section from the docs/skills.md template; summarize-delivery's says nothing follows
  - Each of the four files ends its Hard rules list with the freshness rule sentence from docs/skills.md, byte-identical; assign-to-workforce's lapse guidance (lines 320-328 today) is reworded so the main agent files the lapse at the moment the subagent reports it, not at closeout
  - validate-delivery and summarize-delivery each mention devague today and docs/current-spec.md as the projection the delivery ledger feeds; each of the four mentions the next: stderr hint once
  - uv run pytest tests/`test_summary.py` -q passes (it pins the summary's eight sections to summarize-delivery/SKILL.md order); markdownlint-cli2 on the four files by explicit path exits 0

### t7 — tests/`test_readme_commands.py`: pin README.md to the shipped CLI and to its own structural promises

- instruction: Touch only tests/`test_readme_commands.py`. Follow tests/`test_spec_to_plan_skill.py`'s shape (`REPO_ROOT`, read the file, plain asserts with messages). Use the parser the CLI builds in devague/cli/`__init__.py`; if no factory is exposed, parse --help text via subprocess as a fallback and say so in a comment. Skip commands inside captured-output blocks (they are output, not input).
- depends on: t4
- covers: h11, h2, h3, h14, c24, h16
- acceptance:
  - A new tests/`test_readme_commands.py` parses every fenced bash block in README.md, extracts each line starting with devague, and asserts the verb, subverb and every --flag exist in the argparse parser (build it via devague.cli's parser factory, no subprocess); zero misses on the rewritten README
  - The same module asserts: exactly one mermaid fence; a numbered list of exactly eight legs in flow order directly after it; every captured output block is preceded by a comment naming a devague version; the four H2 sections in order
  - uv run pytest -n auto exits 0 with the new module included and no existing test changed

### t8 — Release hygiene: patch version bump and a CHANGELOG entry that quotes the before state verbatim

- instruction: Touch only pyproject.toml, devague/`__init__.py`, CHANGELOG.md and uv.lock. Use the version-bump skill (bash .claude/skills/version-bump/scripts/bump.py patch or its documented entry point). Take the before-state quotes from git show main:README.md, main:.claude/skills/deviate/SKILL.md and main:CLAUDE.md so they are the real old text. The PR description reuses this entry.
- depends on: t2, t3, t4, t5, t6
- covers: c25, h17, c21, h13
- acceptance:
  - pyproject.toml version is 0.24.1 and devague/`__init__.py` agrees; CHANGELOG.md has a top entry for 0.24.1 dated today
  - The CHANGELOG entry quotes, verbatim, the three before-state lines: README.md's old three-stage arrow, deviate/SKILL.md's old six-leg diagram, and CLAUDE.md's old 'ships separately' sentence; it names issues 100 and 47 as closed
  - uv run devague --version prints 0.24.1

### t9 — Verification sweep: boundaries untouched, no stale leg or verb text anywhere, lint and tests green, README answers the three reader questions

- instruction: Read-only except for fixing lint or grep hits it finds in files owned by earlier tasks (report each fix). Run every command in the acceptance criteria and paste the output into the task report verbatim. Do not modify the org or guildmaster checkouts.
- depends on: t7, t8
- covers: c4, h4, c16, h9, c20, h12, c1, h1, c19, c24, h16
- acceptance:
  - git -C ../org status --short and git -C ../guildmaster status --short are both empty; git status in this repo lists changes only under README.md, CLAUDE.md, CHANGELOG.md, pyproject.toml, uv.lock, devague/`__init__.py`, docs/, tests/ and .claude/skills/
  - grep -rn 'six-leg\|seven-leg\|still unimplemented\|ships separately' README.md CLAUDE.md docs/\*.md .claude/skills/\*/SKILL.md returns nothing
  - markdownlint-cli2 on README.md, CLAUDE.md, CHANGELOG.md, docs/\*.md and each of the eight SKILL.md files by explicit path exits 0; uv run pytest -n auto exits 0; uv run flake8 --config=.flake8 devague/ tests/ exits 0
  - The task report answers, from README.md alone, the eight legs in order, the three human gates, and the three things devague never does, quoting the README line that answers each

## Risks

- [unknown_nonblocking] Captured README output embeds devague 0.24.x ids and text; it will age with every release and nothing regenerates it. Mitigation is the version comment on each capture (h14); a refresh is a future chore, not this plan's (task t4)
- [follow_up] After merge, guildmaster needs a skill-update brief (communicate skill template skill-update-brief.md) so mesh consumers re-vendor the eight skills; outside this plan
