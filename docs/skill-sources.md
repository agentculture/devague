# Skill sources — vendored skill provenance

specifix vendors cross-sibling skills from `steward`, the AgentCulture skill
supplier. This follows the **cite, don't import** pattern: each skill is
copied into `.claude/skills/`, owned locally, and may diverge. Nothing
imports across repos at runtime.

This file is the upstream/downstream map. When upstream changes, re-sync
explicitly — these copies do not auto-update.

**Upstream provenance.** All six skills come from
[`agentculture/steward`](https://github.com/agentculture/steward), **MIT**-licensed
(the same license as specifix). They were vendored from the local steward checkout
at commit [`21414a9`](https://github.com/agentculture/steward/commit/21414a9)
(2026-05-22). The table records each skill's re-vendor path, the vendoring date,
and any local divergence; license (MIT) and upstream repo are shared across all
rows.

| Skill | Re-vendor from | Vendored | Runtime backing & notes |
|-------|----------------|----------|-------------------------|
| `cicd` | `steward` (`../steward/.claude/skills/cicd/`) | 2026-05-22 | **Runtime:** core PR-lifecycle verbs (`lint` / `open` / `read` / `reply` / `delta`) delegate to `agex pr` from `agentculture/agex-cli` — `agex` must be installed (`uv tool install agex-cli`). Steward keeps two extensions on top — `status` (SonarCloud gate + hotspots + unresolved-thread tally) and `await`. **Divergence:** local patch — `scripts/portability-lint.sh` drops GNU-only `xargs -r` in both grep pipelines (it fails on BSD/macOS; empties are already guarded) so the portability gate runs cross-platform; marked with `# specifix-divergence:`. Should be upstreamed to steward; drop on next re-vendor. SKILL.md body cites steward-specific constructs (e.g. `steward doctor`) as inherited upstream context, not specifix-actionable. Watch [agentculture/steward#34](https://github.com/agentculture/steward/issues/34): a known `pr-status.sh` `--repo` fix may need a local patch if `gh pr view` misbehaves. |
| `communicate` | `steward` (`../steward/.claude/skills/communicate/`) | 2026-05-22 | **Runtime:** GitHub issue-I/O verbs (`post-issue` / `post-comment` / `fetch-issues`) wrap `agtag` (>=0.1) — `agtag` must be installed. Signatures resolve from the local `culture.yaml` first-agent `suffix` (here: `specifix`), overridable via `agtag --as NICK`; mesh messages stay unsigned. **Divergence:** none — vendored verbatim. The `steward announce-skill-update` broadcast verb referenced in the body is steward-cli-only and not available to specifix. |
| `version-bump` | `steward` (`../steward/.claude/skills/version-bump/`) | 2026-05-22 | Pure Python (`scripts/bump.py`), no per-repo customization. **Divergence:** none — vendored verbatim. Watch [agentculture/steward#34](https://github.com/agentculture/steward/issues/34): a known insertion-point bug (`idx > 0` vs `idx != -1`) can mis-handle a `CHANGELOG.md` that starts directly with a `## [` entry; apply the documented local patch only if a bump fails. |
| `run-tests` | `steward` (`../steward/.claude/skills/run-tests/`) | 2026-05-22 | None — portable verbatim. Coverage source resolves from `[tool.coverage.run]` in `pyproject.toml`. |
| `sonarclaude` | `steward` (`../steward/.claude/skills/sonarclaude/`) | 2026-05-22 | None — portable verbatim. Project key resolves from `$SONAR_PROJECT` / `--project` (here: `agentculture_specifix`). |
| `doc-test-alignment` | `steward` (`../steward/.claude/skills/doc-test-alignment/`) | 2026-05-22 | **Stub upstream** — `scripts/check.sh` exits with a not-yet-implemented error today; the contract for what it will do lives in its `SKILL.md`. Vendored verbatim to carry the contract. |

## Vendoring policy

- **Cite, don't import.** Skills are copied, not symlinked or installed as
  a dependency.
- **Re-sync explicitly.** When upstream changes, re-vendor from
  `../steward/.claude/skills/<name>/`.
- **Diverge intentionally.** Record any divergence in the table above and
  in the downstream `SKILL.md` frontmatter `description`.
