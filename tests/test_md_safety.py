"""Unit tests for ``devague.render._md_safety`` — the render-time markdown-safety
helpers behind #64 (``devague export`` / ``devague plan export`` emitted markdown
that failed markdownlint's MD026 no-trailing-punctuation and MD034 no-bare-urls).

These pin the exact stripping/wrapping rules against markdownlint-cli2's actual
default behavior (verified empirically against markdownlint v0.40.0, the version
vendored by markdownlint-cli2 v0.21.0): MD026's default punctuation set is
".,;:!" (all punctuation minus '?', per markdownlint's `allPunctuationNoQuestion`
helper) and MD034 leaves a URL alone only when it is already wrapped in ``<...>``,
is the destination of a ``[text](url)`` link, or sits inside a code span.
"""

from __future__ import annotations

from devague.render._md_safety import autolink_urls, heading_safe

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
