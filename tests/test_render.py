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


def test_unknown_format_raises() -> None:
    with pytest.raises(DevagueError):
        render.render(_frame(), "nope")
