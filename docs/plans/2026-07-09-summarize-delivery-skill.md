# Build Plan — summarize-delivery skill

slug: `summarize-delivery-skill` · status: `exported` · from frame: `summarize-delivery-skill`

> devague closes the loop: after assign-to-workforce executes a plan, the new summarize-delivery skill turns the run into an accountability artifact - planned versus actual delivery, mid-work decisions, plan drift, evidence-backed delivery claims, and remaining work

## Tasks

### t1 — author .claude/skills/summarize-delivery/SKILL.md - the method-only skill with the eight-section delivery-summary template and the no-overclaiming hard rules

- instruction: model the file on .claude/skills/scope/SKILL.md (method-only precedent: no scripts dir, type: command, provenance section naming devague as origin and guildmaster as re-broadcaster) with the hard-rules voice of think/SKILL.md; source every section and rule from docs/specs/2026-07-09-summarize-delivery-skill.md; the Planned Work section must quote plan task ids and summaries verbatim from devague plan waves --json, mirroring the verbatim-brief rule in assign-to-workforce
- covers: c1, c2, c3, c4, c6, c7, c8, c9, c10, c11, c13, c14, c15, c16, h3, h4, h5, h6, h7, h9, h10, h11, h12, h14
- acceptance:
  - SKILL.md exists at .claude/skills/summarize-delivery/SKILL.md with frontmatter name summarize-delivery, a trigger-phrase description, and type: command
  - the template carries all eight sections in order: Intent, Planned Work, Actual Delivery, Mid-work Decisions, Drift From Plan, Evidence, Delivery Claims, Remaining Work / Follow-up - and a worked example shows a partial or failed run with every section still writable
  - hard rules state: a claim without evidence is marked unverified (never done); partial and failed runs are valid inputs; verification is read-only (tests, lint, git log); no devague state mutation - the only devague moves documented are the read-only plan show, plan waves, scope --list, show, status
  - each delivery-claim template row carries claim, confidence (high, medium, low, or unverified), and evidence fields with resolvable pointers (commit SHA, file path, PR or issue number, test node id); each drift entry names the plan item, the reason, and exactly one of acceptable, risky, needs-follow-up
  - SKILL.md names the three readers (operator, final-PR human, later reader), documents the committed artifact path `docs/deliveries/<created-date>-<slug>.md`, and documents degrading to git and PR history when no devague plan state exists

### t2 — register summarize-delivery as the fifth origin skill in docs/skill-sources.md

- instruction: mirror the scope row added in 0.15.0 (same table columns); update both enumerations (scope, think, spec-to-plan, assign-to-workforce) to include summarize-delivery
- covers: c17, h15
- acceptance:
  - the origin-skills table gains a summarize-delivery row: origin devague, downstream guildmaster then the mesh, re-vendor path, method-only note, new-in version
  - the surrounding prose is updated: the origin-skills intro and the vendoring-policy bullet enumerate all five origin skills including summarize-delivery
  - markdownlint-cli2 passes on docs/skill-sources.md

### t3 — update the flow docs: five-leg flow in CLAUDE.md, the assign-to-workforce handoff, and the README and docs/skills.md family mentions

- instruction: grep -rn assign-to-workforce across CLAUDE.md README.md docs/ .claude/skills/ to find every family enumeration; verify the on-disk CLAUDE.md status narrative first - it may already reflect 0.16.0 (issue 53 t1-t14 shipped in PR 58) - and only touch flow wording, not the release narrative
- covers: c1
- acceptance:
  - CLAUDE.md project intent names the five-leg flow ending in summarize-delivery
  - .claude/skills/assign-to-workforce/SKILL.md gains an after-the-final-PR handoff section pointing to /summarize-delivery, mirroring how think hands off to /spec-to-plan
  - every other repo doc that enumerates the origin-skill family (README.md, docs/skills.md if they do) is updated consistently, and markdownlint-cli2 passes on every changed docs file

### t4 — dogfood: produce the first real delivery summary at docs/deliveries/ for the sharper-end-to-end-method run (issue 53, PRs 53, 54, 58)

- instruction: the planned-work baseline is docs/plans/2026-07-01-devague-ships-a-sharper-end-to-end-method-a-guided.md plus devague plan show --json and plan waves --json (read-only) for that plan; evidence sources: git log for commits 67a3eca (spec+plan, 0.14.1), 51669f7 (skills carry, 0.15.0), 92c60ca (t1-t14 implementation, 0.16.0), plus gh pr view 53 54 58; the 0.14.1 docs-only versus 0.16.0 implementation split is candidate drift material - verify before claiming
- depends on: t1
- covers: c2, c15, h1, h2, h6, h8, h9, h11, h12, h13
- acceptance:
  - docs/deliveries/2026-07-09-sharper-end-to-end-method.md exists, produced with the shipped template, all eight sections present
  - 100% of the 2026-07-01 plan tasks (t1-t14) are accounted for as delivered, partial, dropped, or blocked, keyed by task id
  - every delivery claim row carries a confidence level plus at least 1 resolvable evidence pointer (commit SHA, file path, PR number, test node) or an explicit unverified marker
  - at least one drift entry with its classification, or an explicit no-drift statement backed by the task-by-task accounting
  - git status shows .devague/ untouched by producing the artifact, and markdownlint-cli2 passes on the artifact

### t5 — release hygiene: minor version bump with changelog, full test suite, and repo-wide markdown lint

- instruction: use the vendored version-bump skill (scripts/bump.py minor); follow the 0.15.0 entry shape for a skills-only release - no CLI change means no new CLI docs
- depends on: t1, t2, t3, t4
- acceptance:
  - pyproject.toml version is bumped minor over main and CHANGELOG.md gains a Keep-a-Changelog entry naming the summarize-delivery skill, the skill-sources registration, the flow-doc updates, and the dogfood delivery artifact
  - uv run pytest -n auto passes and markdownlint-cli2 repo-wide passes

## Risks

- [unknown_nonblocking] the on-disk CLAUDE.md status narrative may lag the 0.16.0 (issue 53 t1-t14) implementation - t3 verifies on disk before editing and corrects only flow wording
- [out_of_scope] guildmaster re-vendoring cadence for the new origin skill is outside this repo - the mesh copy lands whenever guildmaster next pulls
