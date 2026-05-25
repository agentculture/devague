# Skill sources — vendored skill provenance

devague vendors cross-sibling skills from `guildmaster`, the AgentCulture skill
supplier (the role moved from `steward` to `guildmaster` at the 2026-05-24
steward→guildmaster cutover; `steward` no longer broadcasts). This follows the
**cite, don't import** pattern: each skill is copied into `.claude/skills/`,
owned locally, and may diverge. Nothing imports across repos at runtime.

This file is the upstream/downstream map. When upstream changes, re-sync
explicitly — these copies do not auto-update.

**Upstream provenance.** All eight inbound skills come from
[`agentculture/guildmaster`](https://github.com/agentculture/guildmaster),
**MIT**-licensed (the same license as devague). The canonical kit (`cicd`,
`communicate`, `version-bump`, `run-tests`, `sonarclaude`, `doc-test-alignment`)
was first vendored from `steward` at commit
[`21414a9`](https://github.com/agentculture/steward/commit/21414a9) (2026-05-22)
and re-synced from the guildmaster checkout at commit
[`89591d5`](https://github.com/agentculture/guildmaster/commit/89591d5)
(2026-05-24, guildmaster 0.5.1); `agent-config` and `pypi-maintainer` were
vendored fresh from the same guildmaster checkout. The table records each skill's
re-vendor path, the vendoring date, and any local divergence; license (MIT) and
upstream repo are shared across all rows.

| Skill | Re-vendor from | Vendored | Runtime backing & notes |
|-------|----------------|----------|-------------------------|
| `cicd` | `guildmaster` (`../guildmaster/.claude/skills/cicd/`) | 2026-05-24 | **Runtime:** core PR-lifecycle verbs (`lint` / `open` / `read` / `reply` / `delta`) delegate to `agex pr` from `agentculture/agex-cli` — `agex` must be installed (`uv tool install agex-cli`). guildmaster keeps two extensions on top — `status` (SonarCloud gate + hotspots + unresolved-thread tally) and `await`. **Divergence:** local patch — `scripts/portability-lint.sh` drops GNU-only `xargs -r` in both grep pipelines (it fails on BSD/macOS; empties are already guarded) so the portability gate runs cross-platform; marked with `# devague-divergence:`. Should be upstreamed to guildmaster; drop on next re-vendor. SKILL.md body cites guildmaster-specific constructs as inherited upstream context, not devague-actionable. |
| `communicate` | `guildmaster` (`../guildmaster/.claude/skills/communicate/`) | 2026-05-24 | **Runtime:** GitHub issue-I/O verbs (`post-issue` / `post-comment` / `fetch-issues`) wrap `agtag` (>=0.1) — `agtag` must be installed. Signatures resolve from the local `culture.yaml` first-agent `suffix` (here: `devague`), overridable via `agtag --as NICK`; mesh messages stay unsigned. **Divergence:** none — vendored verbatim (now includes the new `scripts/templates/skill-new-brief.md`). The `teach` / `onboard` broadcast verbs referenced in the body are guildmaster-cli-only and not available to devague. |
| `version-bump` | `guildmaster` (`../guildmaster/.claude/skills/version-bump/`) | 2026-05-24 | Pure Python (`scripts/bump.py`), no per-repo customization. **Divergence:** none — vendored verbatim; content unchanged since steward `21414a9`. Watch the known insertion-point bug (`idx > 0` vs `idx != -1`) that can mis-handle a `CHANGELOG.md` starting directly with a `## [` entry (originally tracked at [steward#34](https://github.com/agentculture/steward/issues/34)); apply the documented local patch only if a bump fails. |
| `run-tests` | `guildmaster` (`../guildmaster/.claude/skills/run-tests/`) | 2026-05-24 | None — portable verbatim; content unchanged since steward `21414a9`. Coverage source resolves from `[tool.coverage.run]` in `pyproject.toml`. |
| `sonarclaude` | `guildmaster` (`../guildmaster/.claude/skills/sonarclaude/`) | 2026-05-24 | None — portable verbatim; content unchanged since steward `21414a9`. Project key resolves from `$SONAR_PROJECT` / `--project` (here: `agentculture_devague`). |
| `doc-test-alignment` | `guildmaster` (`../guildmaster/.claude/skills/doc-test-alignment/`) | 2026-05-24 | **Stub upstream** — `scripts/check.sh` exits with a not-yet-implemented error today; the contract for what it will do lives in its `SKILL.md`. Vendored verbatim; content unchanged since steward `21414a9`. |
| `agent-config` | `guildmaster` (`../guildmaster/.claude/skills/agent-config/`) | 2026-05-24 | **New (#38).** Read-only inventory view of a Culture agent's config (system-prompt file + `culture.yaml` + `.claude/skills` index); backs guildmaster's `guild show`. Ships `scripts/show.sh` + `data/backend-fingerprints.yaml`. **Divergence:** none — vendored verbatim (carries `type: command`). devague has no `guild` binary; vendored for standalone config inspection. |
| `pypi-maintainer` | `guildmaster` (`../guildmaster/.claude/skills/pypi-maintainer/`) | 2026-05-24 | **New (#38).** Switches a PyPI package install between the production index, TestPyPI, and a local editable checkout (`scripts/switch-source.sh`, delegates to `uv`). Strong fit — devague publishes to PyPI + TestPyPI via `.github/workflows/publish.yml`. **Divergence:** none — vendored verbatim; ships without a `type:` field (harmless on devague's `claude-code` backend). |

## Origin skills (outbound)

Not every skill here is inbound. The `think`, `spec-to-plan`, and
`assign-to-workforce` skills are **authored and maintained in this repo** —
devague is their origin/upstream, not a downstream consumer. The devague agent
dogfoods them to operate the devague CLI while improving the tool. The flow runs
the *opposite* direction of the table above: `guildmaster` re-vendors them from
here and re-broadcasts them to the mesh. (The skill names are `think` /
`spec-to-plan` / `assign-to-workforce`; the product/CLI they drive is `devague`.
`think` was renamed from `devague` in 0.4.0 — when guildmaster re-vendors, it must
relearn the new name.) Because devague is upstream, these are **not** re-vendored
back from guildmaster's re-broadcast copies — doing so would be circular (see the
issue #38 reply).

As of 0.13.0 (#38) all three carry `type: command` at the source, so guildmaster's
re-broadcast copies (which had to add it on vendor for the culture/agex backend)
match the source and need no patch.

| Skill | Origin | Downstream | Notes |
|-------|--------|------------|-------|
| `think` | **devague** (here: `.claude/skills/think/`) | `guildmaster`, then the AgentCulture mesh | Operator for the **idea→spec** leg of the deterministic devague CLI: portable resolution, driving the flat `devague <move>` verbs (`status` is now a first-class CLI verb, not embedded Python). Renamed from `devague` in 0.4.0. `guildmaster` re-vendors it from `../devague/.claude/skills/think/` and broadcasts it to the mesh. |
| `spec-to-plan` | **devague** (here: `.claude/skills/spec-to-plan/`) | `guildmaster`, then the AgentCulture mesh | Operator for the **spec→plan** leg (`devague plan ...`): portable resolution over the plan convergence gate. New in 0.4.0. Re-vendor from `../devague/.claude/skills/spec-to-plan/`. |
| `assign-to-workforce` | **devague** (here: `.claude/skills/assign-to-workforce/`) | `guildmaster`, then the AgentCulture mesh | Operator for the **implementation** leg (fan out `devague plan waves` to parallel agents in isolated git worktrees, with TDD-gated merges by the main agent). Three human gates only: spec / implementation split plan / final PR. The devague CLI remains non-orchestrating (#20) — this skill is the convention + helper, not new CLI behavior. New in 0.7.0. Re-vendor from `../devague/.claude/skills/assign-to-workforce/`. |

`cite, don't import` applies to both — downstream copies them, no
symlink/dependency. Written portable-first so they pass guildmaster's
`portability-lint.sh`.

## Vendoring policy

- **Cite, don't import.** Skills are copied, not symlinked or installed as
  a dependency.
- **Re-sync explicitly.** When upstream changes, re-vendor from
  `../guildmaster/.claude/skills/<name>/`.
- **Diverge intentionally.** Record any divergence in the table above and
  in the downstream `SKILL.md` frontmatter `description`.
- **Don't re-vendor devague-origin skills.** `think` / `spec-to-plan` /
  `assign-to-workforce` are authored here; pull fixes forward into this repo, not
  back from guildmaster's re-broadcast copies.
