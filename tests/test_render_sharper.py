"""Sharper frame renderers: per-item instruction blocks + scope provenance (#53 t6).

Covers c11 (sharper exports), h4 (sharper's definition is decision c14, confirmed
by the user before any renderer change lands), c8 + h12 (exported spec shows scope
provenance and renders instructions verbatim, checkable on artifacts alone), c3
(every claim/honesty condition can carry its own instruction and exports read
sharp), and h2/h3 (instructions and scope findings round-trip verbatim; an item
without one renders nothing — never fabricated filler).

``render/spec_md.py`` and ``render/frame_md.py`` gained: (1) a nested
``- instruction: <verbatim text>`` bullet under any claim or honesty condition
that carries one — absent entirely when the item has none; and (2) a
``## Scope exploration`` section listing each ``frame.scope_entries`` record
(id, surface, finding, seeded claim ids) — omitted entirely when there are none.
"""

from __future__ import annotations

from pathlib import Path

from devague.frame import Frame
from devague.render.frame_md import render_frame
from devague.render.spec_md import render_spec
from tests.test_render import assert_markdownlint_clean

GOLDENS = Path(__file__).parent / "goldens"


def _bare_frame() -> Frame:
    """A frame with no instructions and no scope entries — the pre-t6 shape.

    Used to pin that an item without an instruction (and a frame without scope
    entries) renders byte-identically to the renderer before this change.
    """
    f = Frame(slug="r", title="Rich Feature")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    f.add_honesty(ann, "must be honest", origin="user")
    f.add_claim("boundary", "scope is X only", origin="user")
    f.add_claim("non_goal", "does not call an LLM", origin="user")
    f.add_claim("non_goal", "no external services", origin="user")
    f.add_claim("assumption", "frames fit in memory", origin="user")
    f.add_claim("decision", "batch is transactional", origin="user")
    req = f.add_claim("requirement", "review lists proposed items", origin="user")
    f.add_honesty(req, "review never mutates state", origin="user")
    return f


# Captured from the renderer before t6 (git show HEAD:devague/render/spec_md.py /
# frame_md.py against `_bare_frame()`) — locks in that the no-instruction,
# no-scope-entries path stays byte-identical.
_BARE_SPEC_BASELINE = (
    "# Rich Feature\n"
    "\n"
    "> Shipped\n"
    "\n"
    "## Requirements\n"
    "\n"
    "- review lists proposed items\n"
    "  - honesty: review never mutates state\n"
    "\n"
    "## Honesty conditions\n"
    "\n"
    "- must be honest\n"
    "\n"
    "## Scope / boundaries\n"
    "\n"
    "- scope is X only\n"
    "\n"
    "## Non-goals\n"
    "\n"
    "- does not call an LLM\n"
    "- no external services\n"
    "\n"
    "## Assumptions\n"
    "\n"
    "- frames fit in memory\n"
    "\n"
    "## Decisions\n"
    "\n"
    "- batch is transactional\n"
)

_BARE_FRAME_BASELINE = (
    "# Announcement Frame — Rich Feature\n"
    "\n"
    "slug: `r` · status: `drafting`\n"
    "\n"
    "## Announcement\n"
    "\n"
    "- Shipped\n"
    "  - honesty: must be honest\n"
    "\n"
    "## Requirements\n"
    "\n"
    "- review lists proposed items\n"
    "  - honesty: review never mutates state\n"
    "\n"
    "## Assumptions\n"
    "\n"
    "- frames fit in memory\n"
    "\n"
    "## Boundaries\n"
    "\n"
    "- scope is X only\n"
    "\n"
    "## Non-goals\n"
    "\n"
    "- does not call an LLM\n"
    "- no external services\n"
    "\n"
    "## Decisions\n"
    "\n"
    "- batch is transactional\n"
)


def test_no_instruction_no_scope_spec_md_byte_identical_to_baseline() -> None:
    assert render_spec(_bare_frame()) == _BARE_SPEC_BASELINE


def test_no_instruction_no_scope_frame_md_byte_identical_to_baseline() -> None:
    assert render_frame(_bare_frame()) == _BARE_FRAME_BASELINE


def _sharper_frame() -> Frame:
    """A frame exercising per-item instructions (claim + honesty) and scope entries."""
    f = Frame(slug="sharper", title="Sharper Golden")
    ann = f.add_claim("announcement", "we shipped the sharper method", origin="user")
    ann.instruction = "run the dogfood script end to end"
    f.add_honesty(ann, "must be observed end to end", origin="user")

    aud = f.add_claim("audience", "operators driving /think", origin="user")
    aud.instruction = "confirm by grepping skill frontmatter for the audience note"

    req = f.add_claim("requirement", "exports render instruction blocks verbatim", origin="user")
    req.instruction = "run `uv run devague export` and diff against the golden fixture"
    h = f.add_honesty(req, "an absent instruction renders nothing", origin="user")
    h.instruction = "capture a claim with no instruction and assert no new bullet appears"

    f.add_claim("boundary", "renderer changes stay inside render slash star dot py", origin="user")
    f.add_claim("non_goal", "not a wizard", origin="user")
    f.add_claim("assumption", "the operating agent performs the exploration", origin="user")
    f.add_claim(
        "decision",
        "sharper means instruction blocks and scope provenance",
        origin="user",
    )

    f.add_scope_entry(
        "devague render spec_md dot py",
        "no instruction or scope rendering existed before t6",
        seeds=[req.id],
    )
    f.add_scope_entry("devague render frame_md dot py", "same renderer gap as spec_md.py")
    return f


def test_claim_instruction_rendered_verbatim_in_spec_md() -> None:
    out = render_spec(_sharper_frame())
    assert "  - instruction: run `uv run devague export` and diff against the golden fixture" in out


def test_honesty_instruction_rendered_verbatim_in_spec_md() -> None:
    out = render_spec(_sharper_frame())
    assert (
        "    - instruction: capture a claim with no instruction and assert no new bullet appears"
        in out
    )


def test_claim_without_instruction_has_no_instruction_line_in_spec_md() -> None:
    out = render_spec(_sharper_frame())
    lines = out.splitlines()
    idx = lines.index("- not a wizard")
    # The non_goal claim carries no instruction — the following line must not be one.
    assert not lines[idx + 1].strip().startswith("- instruction:")


def test_claim_instruction_rendered_verbatim_in_frame_md() -> None:
    out = render_frame(_sharper_frame())
    assert "  - instruction: confirm by grepping skill frontmatter for the audience note" in out


def test_honesty_instruction_rendered_verbatim_in_frame_md() -> None:
    out = render_frame(_sharper_frame())
    assert (
        "    - instruction: capture a claim with no instruction and assert no new bullet appears"
        in out
    )


def test_scope_section_present_in_spec_md_when_entries_exist() -> None:
    out = render_spec(_sharper_frame())
    assert "## Scope exploration" in out
    assert "`s1`" in out and "devague render spec_md dot py" in out
    assert "no instruction or scope rendering existed before t6" in out
    assert "seeds: `c3`" in out  # req is the third claim added -> c3
    assert "`s2`" in out and "devague render frame_md dot py" in out


def test_scope_section_present_in_frame_md_when_entries_exist() -> None:
    out = render_frame(_sharper_frame())
    assert "## Scope exploration" in out
    assert "`s1`" in out and "seeds: `c3`" in out


def test_scope_section_absent_in_spec_md_when_no_entries() -> None:
    out = render_spec(_bare_frame())
    assert "## Scope exploration" not in out


def test_scope_section_absent_in_frame_md_when_no_entries() -> None:
    out = render_frame(_bare_frame())
    assert "## Scope exploration" not in out


def test_scope_entry_without_seeds_omits_seeds_line() -> None:
    out = render_spec(_sharper_frame())
    # s2 carries no seeds -> no "seeds:" line directly under its bullet.
    lines = out.splitlines()
    idx = next(i for i, ln in enumerate(lines) if ln.startswith("- `s2`"))
    assert idx + 1 == len(lines) or not lines[idx + 1].strip().startswith("- seeds:")


def test_sharper_spec_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render_spec(_sharper_frame()))


def test_sharper_frame_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render_frame(_sharper_frame()))


def test_golden_spec_md() -> None:
    expected = (GOLDENS / "sharper_spec.md").read_text(encoding="utf-8")
    assert render_spec(_sharper_frame()) == expected


def test_golden_frame_md() -> None:
    expected = (GOLDENS / "sharper_frame.md").read_text(encoding="utf-8")
    assert render_frame(_sharper_frame()) == expected
