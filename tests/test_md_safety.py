"""Unit tests for ``devague.render._md_safety`` — the render-time markdown-safety
helpers behind #64 (``devague export`` / ``devague plan export`` emitted markdown
that failed markdownlint's MD026 no-trailing-punctuation and MD034 no-bare-urls)
and #87 (verbatim claim/task text containing underscore identifiers or other
markdown control characters failed MD037/MD050 or corrupted rendered structure).

These pin the exact stripping/wrapping rules against markdownlint-cli2's actual
default behavior (verified empirically against markdownlint v0.40.0, the version
vendored by markdownlint-cli2 v0.21.0): MD026's default punctuation set is
".,;:!" (all punctuation minus '?', per markdownlint's `allPunctuationNoQuestion`
helper) and MD034 leaves a URL alone only when it is already wrapped in ``<...>``,
is the destination of a ``[text](url)`` link, or sits inside a code span.

``md_safe_text`` (#87) covers the remaining verbatim-passthrough exposure named
in the issue and its MD050 follow-up comment: underscore/dunder identifiers
(``_read_file``, ``__init__.py``) are wrapped in code spans rather than
backslash-escaped (the issue's stated preference — reads better *and* fixes
both MD037 and MD050 in one move, since Markdown never parses inside a code
span), while the remaining control characters (``*``, ``[``, ``]``, a stray
backtick, a leading ``#``) fall back to backslash-escaping. Text already inside
a code span must pass through byte-for-byte unchanged (claim text routinely
mixes prose and backticked tokens — this is c32/h25 from the
issue-backlog-sweep frame), and applying the function twice must be a no-op
(the same h25 condition, plus the general render-time-only contract already
proven for autolink_urls/heading_safe).
"""

from __future__ import annotations

from devague.render._md_safety import autolink_urls, heading_safe, md_safe_text

# ── heading_safe (MD026) ──────────────────────────────────────────────────────


def test_heading_safe_strips_trailing_period() -> None:
    assert heading_safe("Ship the feature.") == "Ship the feature"


def test_heading_safe_strips_trailing_bang() -> None:
    assert heading_safe("Ship it!") == "Ship it"


def test_heading_safe_strips_trailing_colon() -> None:
    assert heading_safe("Ship it:") == "Ship it"


def test_heading_safe_strips_trailing_semicolon() -> None:
    assert heading_safe("Ship it;") == "Ship it"


def test_heading_safe_strips_trailing_comma() -> None:
    # MD026's default punctuation set includes ',' too, not only '.:;!'.
    assert heading_safe("Ship it,") == "Ship it"


def test_heading_safe_keeps_trailing_question_mark() -> None:
    # markdownlint's MD026 default excludes '?' — a rhetorical-question heading
    # is not flagged, so stripping it would be an unrequested content change.
    assert heading_safe("Ship it?") == "Ship it?"


def test_heading_safe_strips_only_trailing_run() -> None:
    # Punctuation mid-sentence must survive untouched — only the trailing run goes.
    assert heading_safe("Ship it. Fast.") == "Ship it. Fast"


def test_heading_safe_noop_on_clean_text() -> None:
    text = "Ship the feature"
    assert heading_safe(text) == text


def test_heading_safe_strips_multiple_trailing_punctuation_chars() -> None:
    assert heading_safe("Really ship it!!!") == "Really ship it"


# ── autolink_urls (MD034) ─────────────────────────────────────────────────────


def test_autolink_wraps_bare_https_url() -> None:
    assert autolink_urls("see https://example.com") == "see <https://example.com>"


def test_autolink_wraps_bare_http_url() -> None:
    assert autolink_urls("see http://example.com") == "see <http://example.com>"


def test_autolink_leaves_already_wrapped_url_untouched() -> None:
    text = "see <https://example.com>"
    assert autolink_urls(text) == text


def test_autolink_leaves_markdown_link_destination_untouched() -> None:
    text = "see [the site](https://example.com) for more"
    assert autolink_urls(text) == text


def test_autolink_leaves_code_span_untouched() -> None:
    text = "run `curl https://example.com`"
    assert autolink_urls(text) == text


def test_autolink_wraps_url_inside_plain_parens() -> None:
    # Plain parens (no preceding "[text]") do NOT protect a bare URL — markdownlint
    # still flags it (verified against markdownlint-cli2 directly).
    assert autolink_urls("(https://example.com)") == "(<https://example.com>)"


def test_autolink_keeps_trailing_sentence_punctuation_outside_the_wrap() -> None:
    assert autolink_urls("see https://example.com.") == "see <https://example.com>."


def test_autolink_keeps_trailing_comma_outside_the_wrap() -> None:
    assert autolink_urls("see https://example.com, then go") == (
        "see <https://example.com>, then go"
    )


def test_autolink_handles_multiple_urls_in_one_string() -> None:
    text = "see https://a.example and https://b.example"
    assert autolink_urls(text) == "see <https://a.example> and <https://b.example>"


def test_autolink_noop_on_text_without_urls() -> None:
    text = "no links here at all"
    assert autolink_urls(text) == text


def test_autolink_is_idempotent() -> None:
    once = autolink_urls("see https://example.com.")
    twice = autolink_urls(once)
    assert once == twice


def test_autolink_mixed_wrapped_and_bare_urls() -> None:
    text = "already <https://safe.example> but bare https://bare.example here"
    assert autolink_urls(text) == (
        "already <https://safe.example> but bare <https://bare.example> here"
    )


# ── composition: heading text needs both fixes ────────────────────────────────


def test_heading_safe_autolinks_then_strips_trailing_period_after_url() -> None:
    # A URL-ending heading needs the URL wrapped *and* the resulting trailing '.'
    # stripped — verified against markdownlint-cli2 that "# Ship <url>." still
    # trips MD026 even though the URL itself is safe.
    out = heading_safe("Ship https://example.com.")
    assert out == "Ship <https://example.com>"


# ── md_safe_text: identifier wrapping (#87, MD037/MD050) ─────────────────────


def test_md_safe_text_wraps_leading_underscore_identifier() -> None:
    # The exact repro token from the #87 issue body.
    assert md_safe_text("calls _read_file here") == "calls `_read_file` here"


def test_md_safe_text_wraps_dunder_file_identifier() -> None:
    # The exact repro token from the #87 MD050 follow-up comment: a dunder
    # file name trips strong-style emphasis, not just MD037.
    text = "no functional export is added to shell/fs/__init__.py"
    expected = "no functional export is added to shell/fs/`__init__.py`"
    assert md_safe_text(text) == expected


def test_md_safe_text_wraps_multiple_identifiers_in_one_string() -> None:
    text = "_read_file and __init__.py both matter"
    expected = "`_read_file` and `__init__.py` both matter"
    assert md_safe_text(text) == expected


def test_md_safe_text_does_not_wrap_plain_words() -> None:
    text = "no underscores appear in this sentence at all"
    assert md_safe_text(text) == text


# ── md_safe_text: remaining control characters (#87 fallback) ────────────────


def test_md_safe_text_escapes_stray_asterisk() -> None:
    assert md_safe_text("a * b") == r"a \* b"


def test_md_safe_text_escapes_stray_open_bracket() -> None:
    assert md_safe_text("a [ b") == r"a \[ b"


def test_md_safe_text_escapes_stray_close_bracket() -> None:
    assert md_safe_text("a ] b") == r"a \] b"


def test_md_safe_text_escapes_stray_backtick() -> None:
    # A single, unpaired backtick cannot form a code span — it is a stray
    # literal character and must be backslash-escaped like the other control
    # characters, not left to accidentally pair with a later backtick.
    assert md_safe_text("a ` b") == r"a \` b"


def test_md_safe_text_escapes_leading_hash() -> None:
    # A leading '#' would be parsed as an ATX heading marker if the verbatim
    # text ever lands at the start of a rendered line.
    assert md_safe_text("# Heading") == r"\# Heading"


def test_md_safe_text_only_escapes_leading_hash_not_mid_text() -> None:
    # A '#' that is not at the very start of the text has no heading meaning
    # and must survive untouched.
    text = "see issue #87 for details"
    assert md_safe_text(text) == text


# ── md_safe_text: code spans are never touched ────────────────────────────────


def test_md_safe_text_leaves_already_backticked_identifier_unchanged() -> None:
    # Claim text routinely mixes prose with backticked tokens — an escaper
    # that wraps or escapes inside an existing code span would corrupt it
    # (c32/h25, issue-backlog-sweep).
    text = "call `_read_file` directly"
    assert md_safe_text(text) == text


def test_md_safe_text_leaves_already_backticked_control_chars_unchanged() -> None:
    text = "run `a[b]*c` verbatim"
    assert md_safe_text(text) == text


def test_md_safe_text_mixed_prose_and_backticked_tokens() -> None:
    # Bare identifier gets wrapped; the already-backticked one is untouched.
    text = "_read_file calls into `_write_file` next"
    expected = "`_read_file` calls into `_write_file` next"
    assert md_safe_text(text) == expected


# ── md_safe_text: idempotence (double application is a no-op, h25) ───────────


def test_md_safe_text_is_idempotent_on_identifiers() -> None:
    once = md_safe_text("_read_file and __init__.py")
    twice = md_safe_text(once)
    assert once == twice


def test_md_safe_text_is_idempotent_on_control_chars() -> None:
    once = md_safe_text("a * b [ c ] d ` e")
    twice = md_safe_text(once)
    assert once == twice


def test_md_safe_text_is_idempotent_on_leading_hash() -> None:
    once = md_safe_text("# Heading")
    twice = md_safe_text(once)
    assert once == twice


def test_md_safe_text_is_idempotent_on_mixed_content() -> None:
    once = md_safe_text(
        "tests/test_honesty.py machine-enforces the posture with two regexes: "
        "_CLAIM bans affirmative text and a leading # would break a heading, "
        "also [brackets] and *asterisks* and a stray ` backtick"
    )
    twice = md_safe_text(once)
    assert once == twice


def test_md_safe_text_noop_on_clean_text() -> None:
    text = "Ship the feature with no special characters"
    assert md_safe_text(text) == text


# ── #94: md_safe_text composed with autolink_urls (URLs carrying underscores) ─
#
# The renderers compose these two passes in *opposite* orders — spec_md.py runs
# ``autolink_urls(md_safe_text(text))`` while plan_md.py and summary_md.py run
# ``md_safe_text(autolink_urls(text))``. Before #94 neither pass knew about the
# other, so an underscore inside a URL path was treated as an identifier to wrap
# in a code span: the plan order corrupted the link
# ("<https://e.com/`some_path`>") and the spec order truncated it at the first
# underscore ("<https://e.com/>`some_path`"), silently pointing a committed
# artifact's link at the wrong address. Both orders must now leave the URL
# byte-identical and agree with each other.


def _both_orders(text: str) -> tuple[str, str]:
    """(plan_md/summary_md order, spec_md order) for the same input."""
    return md_safe_text(autolink_urls(text)), autolink_urls(md_safe_text(text))


def test_underscore_url_survives_plan_order_composition() -> None:
    plan_order, _ = _both_orders("see https://example.com/some_path/file_name for details")
    assert plan_order == "see <https://example.com/some_path/file_name> for details"


def test_underscore_url_survives_spec_order_composition() -> None:
    _, spec_order = _both_orders("see https://example.com/some_path/file_name for details")
    assert spec_order == "see <https://example.com/some_path/file_name> for details"


def test_dunder_url_survives_both_orders() -> None:
    text = "https://raw.githubusercontent.com/org/repo/main/__init__.py"
    plan_order, spec_order = _both_orders(text)
    assert plan_order == f"<{text}>"
    assert spec_order == f"<{text}>"


def test_both_composition_orders_agree_on_underscore_urls() -> None:
    for text in (
        "docs at https://example.com/a_b",
        "see https://example.com/some_path/file_name for details",
        "https://raw.githubusercontent.com/org/repo/main/__init__.py",
        "trailing https://example.com/a_b. next sentence",
        "two https://e.com/a_b and https://f.com/c_d urls",
    ):
        plan_order, spec_order = _both_orders(text)
        assert plan_order == spec_order, text


def test_url_protection_does_not_disable_identifier_wrapping_elsewhere() -> None:
    # The carve-out is scoped to the URL itself — prose identifiers outside it
    # must still be wrapped, or the #87 fix would regress.
    plan_order, spec_order = _both_orders("https://example.com/a_b then _read_file in prose")
    assert plan_order == spec_order
    assert "<https://example.com/a_b>" in plan_order
    assert "`_read_file`" in plan_order


def test_url_inside_code_span_stays_literal_in_both_orders() -> None:
    text = "code `https://example.com/a_b` stays literal, _read_file wraps"
    plan_order, spec_order = _both_orders(text)
    assert plan_order == spec_order
    assert "`https://example.com/a_b`" in plan_order
    assert "<https://example.com/a_b>" not in plan_order


def test_markdown_link_destination_still_escapes_to_literal_prose() -> None:
    # Protecting the URL must not turn a claim that merely *mentions* link
    # syntax into a live link — the brackets keep their pre-#94 escaping.
    plan_order, spec_order = _both_orders("a [link](https://example.com/a_b) and _read_file")
    assert plan_order == spec_order
    assert plan_order.startswith("a \\[link\\](https://example.com/a_b)")


def test_composition_is_idempotent_in_both_orders() -> None:
    text = "see https://example.com/some_path/file_name and _read_file"
    plan_order, spec_order = _both_orders(text)
    assert md_safe_text(plan_order) == plan_order
    assert autolink_urls(spec_order) == spec_order
