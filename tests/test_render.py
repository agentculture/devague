from __future__ import annotations

import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, not shipped code
from pathlib import Path

import pytest

from devague import render
from devague.cli._errors import DevagueError
from devague.frame import Frame


def _frame() -> Frame:
    f = Frame(slug="s", title="My Feature")
    a = f.add_claim("announcement", "Shipped fast specs", origin="user")
    f.add_honesty(a, "must be honest", origin="user")
    f.add_claim("audience", "developers", origin="user")
    f.add_vagueness("scale unknown", "follow_up")
    return f


def test_formats_include_frame_and_spec() -> None:
    assert "frame-md" in render.formats()
    assert "spec-md" in render.formats()


def test_render_frame_md_has_sections() -> None:
    out = render.render(_frame(), "frame-md")
    assert "# Announcement Frame — My Feature" in out
    assert "## Announcement" in out
    assert "Shipped fast specs" in out
    assert "## Open vagueness" in out


def test_render_spec_md_has_title_and_audience() -> None:
    out = render.render(_frame(), "spec-md")
    assert out.startswith("# My Feature")
    assert "## Audience" in out
    assert "developers" in out


def assert_markdownlint_clean(md: str) -> None:
    """Rendered markdown must pass the repo's markdownlint config (``default: true``).

    Pins the renderer dogfooding fixes — ``devague export`` / ``show`` output must
    satisfy MD022 (blank below headings), MD032 (blank before lists), and MD036 (no
    wholly-emphasized line used as a pseudo-heading) without any rule exemption.
    """
    lines = md.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#"):
            below_blank = i + 1 >= len(lines) or lines[i + 1] == ""
            assert below_blank, f"heading not followed by blank: {line!r}"
        if line.startswith("- "):
            prev = lines[i - 1] if i > 0 else ""
            ok = prev == "" or prev.startswith(("- ", "  "))
            assert ok, f"list not preceded by blank/list: {line!r} (prev {prev!r})"
        stripped = line.strip()
        emph = bool(stripped) and stripped[0] in "_*" and stripped[-1] in "_*"
        if emph and not stripped.startswith(("#", "- ")):
            raise AssertionError(f"wholly-emphasized line (MD036): {line!r}")


# Back-compat alias for callers importing the older name.
assert_blanks_around_headings_and_lists = assert_markdownlint_clean


def test_spec_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render.render(_frame(), "spec-md"))


def test_frame_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render.render(_frame(), "frame-md"))


def test_spec_md_omits_empty_before_after_section() -> None:
    # _frame() has no before_state/after_state claims — the section must not appear.
    out = render.render(_frame(), "spec-md")
    assert "## Before → After" not in out


def _rich_frame() -> Frame:
    """A frame exercising the kinds added by the #5/#16 contract."""
    f = Frame(slug="r", title="Rich Feature")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    f.add_honesty(ann, "must be honest", origin="user")  # non-requirement honesty
    f.add_claim("boundary", "scope is X only", origin="user")
    f.add_claim("non_goal", "does not call an LLM", origin="user")
    f.add_claim("non_goal", "no external services", origin="user")
    f.add_claim("assumption", "frames fit in memory", origin="user")
    f.add_claim("decision", "batch is transactional", origin="user")
    req = f.add_claim("requirement", "review lists proposed items", origin="user")
    f.add_honesty(req, "review never mutates state", origin="user")
    return f


def test_spec_md_renders_non_goal_and_decision() -> None:
    # Regression for #21 / Qodo: spec-md must not silently drop non_goal + decision.
    out = render.render(_rich_frame(), "spec-md")
    assert "## Non-goals" in out
    assert "does not call an LLM" in out
    assert "no external services" in out
    assert "## Decisions" in out
    assert "batch is transactional" in out
    assert "## Assumptions" in out
    assert "frames fit in memory" in out
    # boundary keeps its own section, distinct from non-goals
    assert "## Scope / boundaries" in out
    assert "scope is X only" in out
    assert_markdownlint_clean(out)


def test_spec_md_renders_requirement_claim_text_with_nested_honesty() -> None:
    # #21 remaining item: requirement *claim* text must render, not only its honesty.
    out = render.render(_rich_frame(), "spec-md")
    assert "## Requirements" in out
    assert "- review lists proposed items" in out  # the requirement claim text
    assert "  - honesty: review never mutates state" in out  # nested under it
    # honesty on non-requirement claims still appears, in its own section
    assert "## Honesty conditions" in out
    assert "must be honest" in out  # the announcement's honesty (non-requirement)
    assert_markdownlint_clean(out)


def test_frame_md_renders_non_goal_and_decision() -> None:
    out = render.render(_rich_frame(), "frame-md")
    for needle in (
        "## Non-goals",
        "does not call an LLM",
        "## Decisions",
        "batch is transactional",
        "## Requirements",
        "## Assumptions",
    ):
        assert needle in out, needle
    assert_markdownlint_clean(out)


def test_review_md_banner_and_proposed_only() -> None:
    f = Frame(slug="rv", title="Review me")
    f.add_claim("announcement", "Shipped", origin="user")  # confirmed — excluded
    f.add_claim("audience", "devs", origin="llm")  # c2 proposed — included
    out = render.render(f, "review-md")
    assert "review-md" in render.formats()
    assert "nothing confirmed yet" in out.lower()
    assert "`c2`" in out and "devs" in out
    assert "Shipped" not in out  # confirmed items are not part of the review artifact
    assert_markdownlint_clean(out)


def test_review_md_empty_when_no_proposals() -> None:
    f = Frame(slug="rv2", title="All confirmed")
    f.add_claim("announcement", "Shipped", origin="user")  # confirmed
    out = render.render(f, "review-md")
    assert "nothing awaiting review" in out.lower()
    assert_markdownlint_clean(out)


def test_spec_md_omits_honesty_for_unconfirmed_claims() -> None:
    # #24 (Qodo): a proposed/rejected claim carrying a confirmed honesty must not
    # leave an orphan honesty bullet — spec-md renders confirmed claims only.
    f = Frame(slug="o", title="Orphan")
    f.add_claim("announcement", "Shipped", origin="user")  # confirmed
    proposed = f.add_claim("audience", "maybe devs", origin="llm")  # proposed
    f.add_honesty(proposed, "honesty whose parent is unconfirmed", origin="user")
    out = render.render(f, "spec-md")
    assert "honesty whose parent is unconfirmed" not in out
    assert "maybe devs" not in out  # the proposed claim text is omitted too


def test_unknown_format_raises() -> None:
    with pytest.raises(DevagueError):
        render.render(_frame(), "nope")


# ── #64: markdownlint-safe rendering (MD026 trailing-punctuation headings, ────
# MD034 bare URLs) ─────────────────────────────────────────────────────────────


def _hostile_frame() -> Frame:
    """A frame whose announcement ends in '.' and whose claims/honesty carry a
    bare URL — the exact shape league-of-agents-platform hit in #64.
    """
    f = Frame(slug="hostile", title="League of Agents is live at https://league-of-agents.ai.")
    ann = f.add_claim(
        "announcement",
        "League of Agents is live at https://league-of-agents.ai.",
        origin="user",
    )
    f.add_honesty(ann, "check http://status.example.com for uptime.", origin="user")
    f.add_claim("audience", "players who visit https://league-of-agents.ai", origin="user")
    f.add_vagueness("follow up at https://example.com/todo", "follow_up")
    return f


def test_spec_md_title_heading_strips_trailing_period() -> None:
    out = render.render(_hostile_frame(), "spec-md")
    assert out.startswith("# League of Agents is live at <https://league-of-agents.ai>\n")
    assert not out.split("\n", 1)[0].rstrip().endswith(".")


def test_spec_md_blockquote_keeps_sentence_verbatim_but_wraps_url() -> None:
    # The issue is explicit: blockquote copy keeps the sentence verbatim (period
    # included) — only the URL gets wrapped, only the *heading* loses punctuation.
    out = render.render(_hostile_frame(), "spec-md")
    assert "> League of Agents is live at <https://league-of-agents.ai>." in out


def test_spec_md_wraps_bare_url_in_honesty_condition() -> None:
    out = render.render(_hostile_frame(), "spec-md")
    assert "- check <http://status.example.com> for uptime." in out


def test_spec_md_wraps_bare_url_in_claim_bullet() -> None:
    out = render.render(_hostile_frame(), "spec-md")
    assert "- players who visit <https://league-of-agents.ai>" in out


def test_spec_md_wraps_bare_url_in_follow_up_text() -> None:
    out = render.render(_hostile_frame(), "spec-md")
    assert "- [follow_up] follow up at <https://example.com/todo>" in out


def test_spec_md_hostile_input_is_markdownlint_clean() -> None:
    # The hand-rolled MD022/MD032/MD036 check still holds on hostile input too.
    assert_markdownlint_clean(render.render(_hostile_frame(), "spec-md"))


def test_spec_md_does_not_mutate_frame_claim_text() -> None:
    # #64 acceptance: "Frame JSON keeps original claim text; only rendered
    # markdown is adjusted." Rendering must never write back into the Frame.
    frame = _hostile_frame()
    before = [c.text for c in frame.claims]
    render.render(frame, "spec-md")
    after = [c.text for c in frame.claims]
    assert before == after
    assert frame.title == "League of Agents is live at https://league-of-agents.ai."


# ── resolve-parked-vagueness (#53-esd t7): resolved items render with their ──
# resolution; deliverables excludes them from surviving open items ───────────

GOLDENS = Path(__file__).parent / "goldens"


def _resolved_vagueness_frame() -> Frame:
    """A frame with open + resolved vagueness across multiple kinds — a
    resolved unknown_blocking (the exact issue-45/57 shape), a still-open
    unknown_nonblocking, and a resolved follow_up (previously the only kind
    spec_md rendered at all).
    """
    f = Frame(slug="resolved", title="Resolved Vagueness")
    f.add_claim("announcement", "Shipped the resolve move", origin="user")
    blocking = f.add_vagueness("what happens on double resolve", "unknown_blocking")
    f.resolve_vagueness(blocking.id, "refuse with a hint, exit 1")
    f.add_vagueness("scale unknown", "unknown_nonblocking")  # stays open
    follow_up = f.add_vagueness("follow up on docs", "follow_up")
    f.resolve_vagueness(follow_up.id, "docs updated in t8")
    return f


def test_frame_md_renders_resolved_vagueness_with_resolution_verbatim() -> None:
    out = render.render(_resolved_vagueness_frame(), "frame-md")
    assert "## Open vagueness" in out
    assert (
        "- [unknown_blocking] what happens on double resolve"
        " — resolved: refuse with a hint, exit 1" in out
    )
    assert "- [follow_up] follow up on docs — resolved: docs updated in t8" in out


def test_frame_md_still_open_item_carries_no_resolved_marker() -> None:
    out = render.render(_resolved_vagueness_frame(), "frame-md")
    lines = out.splitlines()
    idx = lines.index("- [unknown_nonblocking] scale unknown")
    assert "resolved" not in lines[idx]


def test_frame_md_resolved_vagueness_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render.render(_resolved_vagueness_frame(), "frame-md"))


def test_spec_md_renders_resolved_vagueness_section_with_resolution_verbatim() -> None:
    out = render.render(_resolved_vagueness_frame(), "spec-md")
    assert "## Resolved vagueness" in out
    assert (
        "- [unknown_blocking] what happens on double resolve"
        " — resolved: refuse with a hint, exit 1" in out
    )
    assert "- [follow_up] follow up on docs — resolved: docs updated in t8" in out


def test_spec_md_resolved_follow_up_is_excluded_from_open_parks_section() -> None:
    # The only vagueness item of kind follow_up is resolved — the open-parks
    # section must not fabricate it as still open. Its resolved form (with
    # the "— resolved:" suffix) belongs only in "## Resolved vagueness", so
    # checking the bare (unsuffixed) bullet form is absent distinguishes the
    # two without depending on any particular heading name.
    out = render.render(_resolved_vagueness_frame(), "spec-md")
    assert "- [follow_up] follow up on docs\n" not in out


def test_spec_md_open_nonblocking_park_renders_labeled_by_kind() -> None:
    # #93/#49 (flipped): spec_md previously never rendered unknown_blocking/
    # unknown_nonblocking kinds unless resolved, so this exact still-open,
    # unresolved nonblocking park silently vanished from the exported spec —
    # precisely the residual-risk kind that legitimately coexists with a
    # converged frame. It now renders, grouped/labeled by kind.
    out = render.render(_resolved_vagueness_frame(), "spec-md")
    assert "## Open parks" in out
    assert "- [unknown_nonblocking] scale unknown" in out


def test_spec_md_resolved_vagueness_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render.render(_resolved_vagueness_frame(), "spec-md"))


def test_spec_md_wraps_bare_url_in_resolved_vagueness_resolution() -> None:
    f = Frame(slug="urlres", title="URL Resolution")
    v = f.add_vagueness("check this later", "follow_up")
    f.resolve_vagueness(v.id, "see https://example.com/decision for the writeup")
    out = render.render(f, "spec-md")
    assert (
        "- [follow_up] check this later"
        " — resolved: see <https://example.com/decision> for the writeup" in out
    )


def test_frame_md_resolved_item_with_empty_resolution_renders_no_marker() -> None:
    # Never fabricate: a resolved flag with no resolution text (a malformed
    # record — the CLI resolve move always requires --decision) must not
    # produce a dangling "— resolved:" with nothing after it.
    f = Frame(slug="edge", title="Edge")
    v = f.add_vagueness("mystery", "unknown_nonblocking")
    v.resolved = True
    out = render.render(f, "frame-md")
    assert "- [unknown_nonblocking] mystery" in out
    assert "resolved:" not in out


def test_spec_md_resolved_item_with_empty_resolution_is_omitted() -> None:
    f = Frame(slug="edge2", title="Edge2")
    v = f.add_vagueness("mystery2", "unknown_blocking")
    v.resolved = True
    out = render.render(f, "spec-md")
    assert "## Resolved vagueness" not in out
    assert "mystery2" not in out


def test_spec_md_omits_resolved_vagueness_section_when_none_resolved() -> None:
    out = render.render(_frame(), "spec-md")
    assert "## Resolved vagueness" not in out


def test_golden_resolved_vagueness_frame_md() -> None:
    expected = (GOLDENS / "resolved_vagueness_frame.md").read_text(encoding="utf-8")
    assert render.render(_resolved_vagueness_frame(), "frame-md") == expected


def test_golden_resolved_vagueness_spec_md() -> None:
    expected = (GOLDENS / "resolved_vagueness_spec.md").read_text(encoding="utf-8")
    assert render.render(_resolved_vagueness_frame(), "spec-md") == expected


# ── real markdownlint-cli2 check on a resolved blocking park (AC1's ──────────
# "an exported spec from a frame with a resolved blocking park passes
# markdownlint" honesty condition) — driven at the renderer level directly,
# since the convergence-gate skip for resolved items (t3/t4) is a later,
# parallel task this one does not depend on; devague export's CLI-level gate
# is out of scope here. Skips cleanly when the binary is not on PATH, mirroring
# tests/test_export_markdownlint_integration.py.
_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_MD_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.yaml"


@pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)
def test_resolved_blocking_park_spec_passes_real_markdownlint_cli2(tmp_path: Path) -> None:
    out = render.render(_resolved_vagueness_frame(), "spec-md")
    spec_path = tmp_path / "resolved-blocking-park.md"
    spec_path.write_text(out, encoding="utf-8")
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_MD_CONFIG), str(spec_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ── issue-backlog-sweep t3: all four park kinds, resolved hard questions, ────
# rejected-claim exclusion, dead-seed flagging (#93, #49, #83, #84 c33) ───────


def _all_four_park_kinds_frame() -> Frame:
    f = Frame(slug="allkinds", title="All Park Kinds")
    f.add_claim("announcement", "Shipped all four park kinds", origin="user")
    f.add_vagueness("residual risk one", "unknown_nonblocking")
    f.add_vagueness("residual risk two", "unknown_blocking")
    f.add_vagueness("explicitly out of scope", "out_of_scope")
    f.add_vagueness("later follow-up", "follow_up")
    return f


def test_spec_md_lists_every_open_park_kind_labeled_by_kind() -> None:
    # Acceptance criterion 1: a frame carrying open parks of all four kinds
    # exports a spec listing each park, labeled by kind.
    out = render.render(_all_four_park_kinds_frame(), "spec-md")
    assert "## Open parks" in out
    assert "- [unknown_nonblocking] residual risk one" in out
    assert "- [unknown_blocking] residual risk two" in out
    assert "- [out_of_scope] explicitly out of scope" in out
    assert "- [follow_up] later follow-up" in out


def test_spec_md_all_four_park_kinds_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render.render(_all_four_park_kinds_frame(), "spec-md"))


def test_spec_md_resolved_hard_question_renders_with_resolved_marker() -> None:
    # Acceptance criterion 2 (part 1, #49): a converged frame has no
    # unresolved blocking hard question, yet the pre-fix renderer showed every
    # hard question as if still open. A resolved one now carries a marker
    # instead of reading as a live blocker.
    f = Frame(slug="resolvedhq", title="Resolved HQ")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    q = f.add_hard_question(ann, "will this scale?", blocking=True)
    q.resolved = True
    out = render.render(f, "spec-md")
    assert "## Hard questions" in out
    assert "- will this scale? (resolved)" in out
    assert "(blocking)" not in out


def test_spec_md_hard_question_on_rejected_claim_is_absent_issue_83_repro() -> None:
    # Acceptance criterion 2 (part 2): the #83 repro shape — capture,
    # interrogate --risk, reject, converge, export — must never leak the
    # rejected claim's hard question into the exported spec.
    f = Frame(slug="repro83", title="Repro 83")
    f.add_claim("announcement", "Shipped", origin="user")
    c = f.add_claim("boundary", "the policy gate must receive rewritten args", origin="llm")
    f.set_status(c.id, "confirmed")
    f.add_hard_question(c, "risk: a hook could launder a denied command", blocking=False)
    f.set_status(c.id, "rejected")
    out = render.render(f, "spec-md")
    assert "## Hard questions" not in out
    assert "launder a denied command" not in out


def test_spec_md_hard_question_on_non_rejected_claim_still_renders() -> None:
    # Control for the #83 fix: only the rejected claim's questions are
    # dropped — a confirmed claim's still keep rendering.
    f = Frame(slug="control83", title="Control 83")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    f.add_hard_question(ann, "an ordinary open question", blocking=False)
    out = render.render(f, "spec-md")
    assert "## Hard questions" in out
    assert "- an ordinary open question" in out


def test_spec_md_scope_seed_citing_rejected_claim_renders_rejected_marker() -> None:
    # Acceptance criterion 3 (#84's fourth criterion, c33/h26): a scope entry
    # whose seeds cite a claim that was later rejected must render a visible
    # rejected marker, not a bare dead id.
    f = Frame(slug="deadseed", title="Dead Seed")
    f.add_claim("announcement", "Shipped", origin="user")
    c = f.add_claim("boundary", "will be rejected", origin="user")
    f.add_scope_entry("some/surface.py", "a finding", seeds=[c.id])
    f.set_status(c.id, "rejected")
    out = render.render(f, "spec-md")
    assert f"`{c.id}` (rejected)" in out


def test_spec_md_scope_seed_citing_live_claim_stays_a_bare_id() -> None:
    # Control for criterion 3: a seed citing a claim that is still confirmed
    # (never rejected) keeps rendering as the plain backticked id.
    f = Frame(slug="liveseed", title="Live Seed")
    f.add_claim("announcement", "Shipped", origin="user")
    c = f.add_claim("boundary", "stays confirmed", origin="user")
    f.add_scope_entry("some/surface.py", "a finding", seeds=[c.id])
    out = render.render(f, "spec-md")
    assert f"`{c.id}`" in out
    assert f"`{c.id}` (rejected)" not in out


# ── issue-backlog-sweep t7: scope --seeds accepts question ids (#84's ────────
# "smaller, related gap") — the seeded question must render, distinguishably
# from a claim seed, in the exported scope-exploration section ─────────────-


def test_spec_md_scope_seed_citing_hard_question_renders_question_marker() -> None:
    f = Frame(slug="qseed", title="Question Seed")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    q = f.add_hard_question(ann, "will this scale?", blocking=True)
    f.add_scope_entry("some/surface.py", "a finding that seeded a question", seeds=[q.id])
    out = render.render(f, "spec-md")
    assert f"`{q.id}` (question)" in out


def test_spec_md_scope_seed_citing_resolved_hard_question_renders_resolved_marker() -> None:
    # A resolved question seed is distinguished from a still-open one — the
    # answer is part of what the scope entry seeded.
    f = Frame(slug="qseedresolved", title="Question Seed Resolved")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    q = f.add_hard_question(ann, "will this scale?", blocking=True)
    f.add_scope_entry("some/surface.py", "a finding that seeded a question", seeds=[q.id])
    f.resolve_hard_question(ann.id, q.id, "yes, load-tested at 10x")
    out = render.render(f, "spec-md")
    assert f"`{q.id}` (question, resolved)" in out
    assert f"`{q.id}` (question)\n" not in out  # not the still-open form


def test_spec_md_rendering_never_mutates_park_or_hard_question_state() -> None:
    # Acceptance criterion 4 (#87 h18/c22): escaping and the new park/hard-
    # question rendering are presentational only — the frame's own fields
    # (what `show --json` reads) must be untouched by a spec-md render.
    f = _all_four_park_kinds_frame()
    ann = f.claims[0]
    f.add_hard_question(ann, "_underscored_risk_ with a leading # too", blocking=True)
    before_vagueness = [(v.kind, v.text, v.resolved) for v in f.open_vagueness]
    before_hq = [(q.text, q.resolved, q.blocking) for c in f.claims for q in c.hard_questions]
    render.render(f, "spec-md")
    after_vagueness = [(v.kind, v.text, v.resolved) for v in f.open_vagueness]
    after_hq = [(q.text, q.resolved, q.blocking) for c in f.claims for q in c.hard_questions]
    assert before_vagueness == after_vagueness
    assert before_hq == after_hq
