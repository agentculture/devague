from __future__ import annotations

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


def test_unknown_format_raises() -> None:
    with pytest.raises(DevagueError):
        render.render(_frame(), "nope")
