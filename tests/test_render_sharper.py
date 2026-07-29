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


def _backtick_surface_frame() -> Frame:
    """A frame whose scope surface carries its own code span (issue 97 dogfood):
    blind-wrapping it in another backtick pair renders broken spans (MD038).
    """
    f = Frame(slug="b", title="Backtick Surface")
    ann = f.add_claim("announcement", "Shipped", origin="user")
    f.add_honesty(ann, "must be honest", origin="user")
    f.add_scope_entry(
        "challenge pass / failure-mode lens: frame.py `__post_init__` validation",
        "probe: an unknown kind raises ValueError at construction",
    )
    return f


def test_backtick_bearing_surface_is_not_double_wrapped_in_spec_md() -> None:
    out = render_spec(_backtick_surface_frame())
    # The surface renders with its own code span intact, not nested in another.
    assert "frame.py `__post_init__` validation" in out
    assert "— `challenge pass" not in out


def test_backtick_bearing_surface_is_not_double_wrapped_in_frame_md() -> None:
    out = render_frame(_backtick_surface_frame())
    assert "frame.py `__post_init__` validation" in out
    assert "— `challenge pass" not in out


def test_backtick_bearing_surface_spec_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render_spec(_backtick_surface_frame()))


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


# ── Lapse ledger (issue #97 t3): frame_md renders it, spec_md never does ─────
#
# devague show (frame_md) gets a new "## Lapse ledger" section listing every
# filed lapse's id, code, status, and what — omitted entirely when
# frame.lapses is empty, mirroring _scope_lines' omitted-when-empty shape.
# Unlike summary_md's approved/pending/rejected discipline (a rejected
# deviation/lapse is dropped there), frame_md is the working-state view, so
# every lapse renders here regardless of status — the same way open_vagueness
# shows both resolved and unresolved items in one flat list.
#
# spec_md.py gets NO code change: the exported spec overwrites the same dated
# file on every re-export, so execution-time lapses rendering there would
# rewrite the what-to-build artifact. That is pinned below as a pure
# regression test — filing lapses in every status must never change
# render_spec's output.


def _frame_with_lapses() -> Frame:
    """A frame carrying one lapse in each status: approved (l1), proposed
    (l2), and rejected (l3)."""
    f = _bare_frame()
    f.add_lapse("grader-unverified", "graded without a rubric", origin="user")  # l1: approved
    f.add_lapse("control-absent", "no control group used", origin="llm")  # l2: proposed
    rejected = f.add_lapse(
        "n-below-claim", "claimed generality from n=1", origin="user"
    )  # l3, then rejected
    f.set_lapse_status(rejected.id, "rejected")
    return f


def test_lapse_ledger_absent_in_frame_md_when_no_lapses() -> None:
    out = render_frame(_bare_frame())
    assert "## Lapse ledger" not in out


def test_lapse_ledger_lists_id_code_status_and_what_in_frame_md() -> None:
    out = render_frame(_frame_with_lapses())
    assert "## Lapse ledger" in out
    assert "`l1`" in out
    assert "`grader-unverified`" in out
    assert "(approved)" in out
    assert "graded without a rubric" in out
    assert "`l2`" in out
    assert "(proposed)" in out
    assert "no control group used" in out
    assert "`l3`" in out
    assert "(rejected)" in out
    assert "claimed generality from n=1" in out


def test_lapse_ledger_frame_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render_frame(_frame_with_lapses()))


def test_lapse_ledger_never_appears_in_spec_md() -> None:
    out = render_spec(_frame_with_lapses())
    assert "## Lapse ledger" not in out
    assert "l1" not in out
    assert "l2" not in out
    assert "l3" not in out


def test_filing_lapses_does_not_change_render_spec_output() -> None:
    """Acceptance criterion 3 (issue #97 t3): re-exporting the spec after
    filing lapses must produce a byte-identical spec-md. Files a lapse in
    every status (approved, proposed, rejected) on an already-rendered frame
    and diffs render_spec's output before/after."""
    f = _sharper_frame()
    before = render_spec(f)
    f.add_lapse("grader-unverified", "graded without a rubric", origin="user")  # approved
    f.add_lapse("control-absent", "no control group used", origin="llm")  # proposed
    rejected = f.add_lapse("n-below-claim", "claimed generality from n=1", origin="user")
    f.set_lapse_status(rejected.id, "rejected")
    after = render_spec(f)
    assert after == before
