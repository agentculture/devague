# challenge skill

> devague gains a seventh origin skill, /challenge — a risk-scaled blind-spot discovery pass that pressure-tests the converged frame between /think and /spec-to-plan through structured lenses, routes every finding back through the existing deterministic moves, and records examined surfaces plus residual uncertainty instead of ever claiming there are no unknown unknowns
> instruction: diff the shipped SKILL.md against this announcement claim by claim: risk-scaling rule present, position between /think and /spec-to-plan, findings routed through existing moves only, examined-surfaces record on a clean pass

## Audience

- operators — the main agent driving the deterministic CLI move by move — and the humans who own the spec and implementation-split-plan gates; downstream, the AgentCulture mesh once guildmaster re-broadcasts the skill
  - instruction: check the SKILL.md description names both audiences and docs/skill-sources.md routes challenge to guildmaster like the other six origin skills

## Before → After

- Before: a frame can converge on precisely stated claims while the original framing is still incomplete: open questions only capture uncertainty someone already noticed — nothing actively hunts omitted dimensions, hidden dependencies, or shared assumptions, and no record exists of which surfaces were ever examined (issue 73 problem statement)
- After: a converged frame no longer slides straight into planning untested: the operator runs a proportional challenge pass over structured lenses, every finding lands as a proposed claim, question, or park that the user adjudicates, the frame reconverges, and the exported spec carries examined-surfaces provenance and residual uncertainty
  - instruction: dogfood /challenge on a real frame and verify findings landed proposed-only, the frame reconverged, and the re-exported spec shows the examined surfaces

## Why it matters

- an articulated blind spot becomes a known unknown the method can manage; an unexamined one surfaces later as a mid-run /deviate or a production surprise — the pass raises the odds of discovery before planning and lowers the cost of the surprises that remain (issue 73)

## Requirements

- the new skill ships as .claude/skills/challenge/SKILL.md in the method-only shape — SKILL.md only, no scripts/ resolver, `type: command` frontmatter, a Provenance section naming devague as origin — matching the shipped deviate and summarize-delivery skills and the two-shape rule in docs/skills.md
  - honesty: listing .claude/skills/challenge/ shows exactly one file, SKILL.md, whose frontmatter carries `type: command` and whose Provenance section names devague as origin — no scripts/ directory
- devague/cli/_commands/learn.py OPERATOR_SKILLS gains a seventh entry for challenge and its six-skill / six-leg wording updates, so `devague learn skills` and `skills:challenge` teach the new skill; this is teaching-content in the existing learn verb, not a new engine
  - honesty: `devague learn skills:challenge` exits 0 and emits the challenge authoring recipe; `devague learn skills` output says seven operator skills in seven-leg order
- every surface naming the six-leg flow is updated to seven legs with challenge third: README.md (lines 82-94), CLAUDE.md (Status + Project intent), docs/skills.md (flow table + per-skill section), docs/skill-sources.md (origin-skills table + dont-re-vendor list)
  - honesty: grepping README.md, CLAUDE.md, docs/skills.md, and docs/skill-sources.md for six-leg wording returns no hits, and all four surfaces name challenge as the third leg
- when the pass finds nothing, it records which lenses and surfaces were examined and what residual uncertainty remains — it never claims there are no unknown unknowns (issue 73 success criteria; anti-fabrication contract in docs/llm-guidance.md)
  - honesty: the SKILL.md hard-rules section contains an explicit rule forbidding a no-unknown-unknowns conclusion, with the required fallback of recording examined lenses/surfaces plus residual uncertainty

## Honesty conditions

- the shipped SKILL.md actually is what the announcement claims: risk-scaled (an explicit proportionality rule), positioned between /think and /spec-to-plan in every flow doc, findings routed only through existing deterministic moves, and a no-unknown-unknowns-claim rule
- the PR diff registers no new argparse subparser, adds no new devague/ module or store, and the only devague/ code change is teaching content in cli/_commands/learn.py
- the SKILL.md description and body address the operator (move-by-move CLI driving) and the gate-owning human (confirmation of findings) as distinct readers, matching the other six origin skills
- issue 73's problem statement is accurately reflected: before this change no devague surface actively searched for omitted dimensions or recorded examined surfaces at spec time
- the skill's intro states the surprise-cost rationale — discovery before planning is cheaper than /deviate mid-run or a production surprise — rather than promising to eliminate unknown unknowns
- a dogfooded /challenge run on a real converged frame produces only proposed findings, triggers reconvergence, and the re-exported spec renders the examined surfaces — verified before the skill is called done
- the success-signal counts are checkable from state alone: frame JSON plus session transcript show every finding's lens/surface trace and zero llm-origin items confirmed without a user confirm move

## Success signals

- every challenge pass leaves at least 1 durable record — proposed findings routed through existing moves, or examined-surfaces entries with residual uncertainty on a clean pass; 0 passes conclude with a bare no-issues-found, and 0 LLM-origin findings reach confirmed status without an explicit user confirm
  - instruction: review a dogfooded pass: each finding traceable to a lens and surface; grep the frame JSON for llm-origin claims that are confirmed without a user confirm in the session log

## Scope / boundaries

- no new CLI engine, verb, or state model — challenge findings route through the existing deterministic moves only: capture / interrogate / question / park on the frame, `devague scope` for examined surfaces, `devague plan risk` for residual risk; the CLI stays deterministic and non-orchestrating per issue 20 and the issue 73 stated preference

## Non-goals

- challenge is not a fourth standing human gate — the three gates (exported spec, implementation split plan, final PR) stay; challenge output lands as proposed claims and questions the user confirms inside the existing spec gate, mirroring how /deviate amends gate 2 rather than adding one

## Assumptions

- examined-surfaces records reuse the existing `devague scope` move (surface + finding + optional seeds) — Frame.scope_entries already persists them and the exported spec-md already renders a Scope exploration section (issue 53 t3/t6), so residual-uncertainty provenance survives into the buildable spec with no new state
- residual risk that survives into planning lands via `devague plan risk --kind` — RISK_KINDS equals the vagueness kinds (unknown_nonblocking / unknown_blocking / out_of_scope / follow_up) in devague/plan.py, which already distinguishes blocking from nonblocking residual uncertainty

## Scope exploration

- `s1` — `.claude/skills/deviate/SKILL.md + .claude/skills/summarize-delivery/ + docs/skills.md file-structure rules`: the method-only origin-skill shape is established: SKILL.md only, type: command frontmatter required for culture/agex backends, Provenance section naming devague as origin; deviate (0.18.0) and summarize-delivery (0.17.0) both shipped this way
  - seeds: `c2`
- `s2` — `devague/cli/_commands/learn.py (OPERATOR_SKILLS at line 280, six-skill wording at lines 393/412/435)`: learn skills now teaches all six operator skills from a data tuple; adding challenge is one tuple entry plus wording — teaching content, not a new engine
  - seeds: `c3`
- `s3` — `README.md:82-94, CLAUDE.md Status/Project-intent, docs/skills.md flow table, docs/skill-sources.md origin table`: four doc surfaces name the six-leg flow and the origin-skill family explicitly; all four must move to seven legs together or the docs drift
  - seeds: `c4`
- `s4` — `docs/spec-contract.md vocabulary + devague/plan.py RISK_KINDS + .claude/skills/scope/SKILL.md findings table`: the existing move vocabulary already covers every challenge output: findings as capture kinds (requirement/assumption/boundary/non_goal/decision), pressure-tests as interrogate, pending decisions as question, open vagueness as park, examined surfaces as devague scope entries, residual plan risk as plan risk with the four vagueness kinds — no gap forcing a new CLI verb
  - seeds: `c5`, `c8`, `c9`
- `s5` — `issue 73 (integration options, success criteria) + CLAUDE.md three-human-gates section`: issue author prefers a distinct mandatory-but-proportional operator pass with no new CLI engine; success criteria require findings to reconverge the authoritative frame and forbid claiming zero unknown unknowns — and the three-gate structure stays untouched
  - seeds: `c6`, `c7`, `c10`, `c11`
- `s6` — `challenge pass / hidden-dependency lens: tests/test_cli_learn.py lines 43-56`: the learn tests hardcode the origin-skill tuple, METHOD_ONLY_NAMES, and parametrized skills:name cases — they must move to seven skills in lockstep with learn.py or CI fails; lands as acceptance criteria on the learn-content plan task under c3
  - seeds: `c3`
- `s7` — `challenge pass / adjacent-systems lens: .claude/skills.local.yaml.example, culture.yaml, .github/workflows`: clean pass — none of these carry a skill-count dependency; no change needed
- `s8` — `challenge pass / failure-mode + reversibility lenses over the spec itself`: no CLI behavior change means no version-skew failure mode for installed devague binaries (learn.py text is the only code delta); change is docs+skill additive, fully reversible by revert; concurrency and data-loss lenses not applicable to a docs-only delivery

## Decisions

- integration option 1 from issue 73, per the issue author: a distinct operator skill /challenge, run as a mandatory but proportional pass — lightweight for ordinary work, rigorous for high-risk work — with no new CLI engine until the workflow proves it needs one
- challenge is the seventh documented leg, positioned third: scope, think, challenge, spec-to-plan, assign-to-workforce, deviate, summarize-delivery — per the issue 73 proposal flow and the user's request driving this frame
- the challenge pass runs after /think exports: challenge the converged, exported frame before `devague plan new`; findings reopen the frame, reconverge, and re-export the same dated spec file — /think stays self-contained (resolves q1)
- resilience measures land in both spec and plan by nature: spec-side as requirement/boundary claims when they change what to build, plan-side as plan risks or tasks when they change how to build it — the skill coaches which is which (resolves q2)
- the named escalation signals that deepen the pass from lightweight to rigorous: migrations, security-sensitive work, distributed state, hardware, destructive operations, other hard-to-reverse changes, concurrency hazards, and any surface that can lose user data (resolves q3)

## Open / follow-up

- guildmaster re-vendors /challenge and re-broadcasts it to the mesh on its own schedule — outside this repo's control; the skill-sources row documents the re-vendor path so downstream picks it up on the next sync
