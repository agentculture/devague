# Build Plan — challenge skill

slug: `challenge-skill` · status: `exported` · from frame: `challenge-skill`

> devague gains a seventh origin skill, /challenge — a risk-scaled blind-spot discovery pass that pressure-tests the converged frame between /think and /spec-to-plan through structured lenses, routes every finding back through the existing deterministic moves, and records examined surfaces plus residual uncertainty instead of ever claiming there are no unknown unknowns

## Tasks

### t1 — Author .claude/skills/challenge/SKILL.md — the seventh origin skill, method-only shape

- instruction: Model the shape on .claude/skills/deviate/SKILL.md and .claude/skills/scope/SKILL.md (the method-only shape: SKILL.md only, no scripts/). Source of truth: docs/specs/2026-07-15-challenge-skill.md — quote decisions c17 (run after /think export, before plan new; findings reopen, reconverge, re-export the same dated file), c18 (resilience both-by-nature), c19 (escalation signal list) rather than re-deriving them. Flow position: seventh leg, third in order — scope, think, challenge, spec-to-plan, assign-to-workforce, deviate, summarize-delivery. Include the six output categories from issue 73 (known facts / assumptions / known unknowns / unexamined surfaces / residual surprise risk / resilience measures) mapped to their landing moves.
- covers: c1, h1, c2, h2, c7, h6, c12, h7, c13, h8, c14, h9, c15, h10, c16, h11
- acceptance:
  - .claude/skills/challenge/ contains exactly one file, SKILL.md; frontmatter carries name: challenge, type: command, and a description with trigger phrases naming devague as origin
  - the hard-rules section explicitly forbids concluding there are no unknown unknowns and requires recording examined lenses/surfaces plus residual uncertainty on a clean pass via `devague scope` entries and `park`
  - the body carries the proportionality rule with the named escalation signals (migrations, security-sensitive work, distributed state, hardware, destructive operations, hard-to-reverse changes, concurrency hazards, data-loss surfaces), the structured lenses, a findings-routing table using only existing moves (capture / interrogate / question / park / `devague scope` / `devague plan risk`), the after-/think-export timing with the reconverge-and-re-export loop, and resilience-placement coaching (spec-side when it changes what, plan-side when it changes how)
  - the intro states the before-state and surprise-cost rationale from issue 73 (nothing previously hunted omitted dimensions; discovery before planning is cheaper than a mid-run /deviate) and addresses both audiences — the operator and the gate-owning human
  - a worked example uses only real devague verbs (each appears in devague --help or devague plan --help); a Provenance section names devague as origin, seventh in the outbound family, guildmaster as re-broadcaster; markdownlint-cli2 on the file passes

### t2 — learn teaches challenge: devague/cli/_commands/learn.py + tests/test_cli_learn.py in lockstep

- instruction: Insert one OPERATOR_SKILLS entry for challenge in flow order (third, after think) with method_only semantics matching scope/deviate/summarize-delivery entries; update the six-to-seven wording at learn.py lines 212, 252, 280, 393, 412, 435. Mirror in tests/test_cli_learn.py lines 43-56 (tuple + METHOD_ONLY_NAMES) and the parametrized lists around lines 128-175. Write the failing tests first.
- covers: c3, h3, c5, h5
- acceptance:
  - `uv run devague learn skills:challenge` exits 0 and emits the challenge authoring recipe; `learn skills` and `learn skills:all` name seven operator skills in seven-leg order with challenge third, method-only (no script URL)
  - tests/test_cli_learn.py's origin-skill tuple, METHOD_ONLY_NAMES, and every parametrized skills:name case include challenge; `uv run pytest -n auto` passes
  - no stale six-skill or six-leg wording remains anywhere in devague/cli/_commands/learn.py
  - the diff adds no new argparse subparser, no new devague/ module, and no new store — the only devague/ code change is teaching content in learn.py

### t3 — Seven-leg docs sweep: README.md, CLAUDE.md, docs/skills.md, docs/skill-sources.md

- instruction: Depends on t1: quote the shipped .claude/skills/challenge/SKILL.md description into docs/skills.md and the skill-sources row instead of paraphrasing. README.md lines 82-94 and CLAUDE.md (Status paragraph + Project intent + ecosystem origin-skill list) move to seven legs. Keep CLAUDE.md's Status section style: newest release paragraph first.
- depends on: t1
- covers: c4, h4
- acceptance:
  - grepping the four files for six-leg / six leg / six operator wording returns no hits; all four name the seven-leg order with challenge third
  - docs/skills.md gains a challenge per-skill section and flow-table row whose description matches the shipped SKILL.md; docs/skill-sources.md gains the challenge outbound origin row and adds challenge to the do-not-re-vendor list
  - markdownlint-cli2 on the four files passes

### t4 — Version bump to 0.19.0 + CHANGELOG entry; full gate green

- instruction: Use the vendored version-bump skill (scripts/bump.py, minor). The package version single-sources from pyproject via importlib.metadata — no __init__.py edit needed. Changelog entry lists: Added (challenge skill, seventh leg), Changed (learn teaches seven skills; docs to seven-leg flow).
- depends on: t1, t2, t3
- acceptance:
  - pyproject.toml version is 0.19.0 and a Keep-a-Changelog 0.19.0 entry names the challenge skill, the learn/tests update, and the docs sweep, citing issue 73
  - on the final tree: uv run pytest -n auto, flake8, black --check, isort --check --profile black, and markdownlint-cli2 on changed markdown all pass

## Risks

- [follow_up] guildmaster re-vendors /challenge and re-broadcasts to the mesh on its own schedule — outside this repo's control; the skill-sources row documents the re-vendor path
- [unknown_nonblocking] proportionality calibration (lightweight vs rigorous) is only observable across future dogfooded runs; watch the first passes for over- or under-escalation
