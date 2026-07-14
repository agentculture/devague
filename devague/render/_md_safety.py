"""Shared rendering-time markdown-safety helpers for the export renderers (#64).

``devague export`` (spec-md, ``docs/specs/*.md``) and ``devague plan export``
(plan-md, ``docs/plans/*.md``) both interpolate free-form claim/task/honesty
prose straight into markdown — headings, blockquotes, and bullets. Prose
written as a sentence ("Ship the feature.") trips markdownlint's MD026
(no-trailing-punctuation) when it lands in a heading, and a URL written bare
("see https://example.com") trips MD034 (no-bare-urls) wherever it lands.
Downstream repos that commit exported specs/plans and gate PRs on
markdownlint were hand-fixing every export until this landed.

Both functions are applied **only** at render time — the underlying Frame/Plan
JSON keeps the original text verbatim (rendering never mutates state).

The exact rules here are pinned against markdownlint-cli2 v0.21.0
(markdownlint v0.40.0) behavior, verified empirically, not just read from docs.
"""

from __future__ import annotations

import re

# markdownlint's MD026 default punctuation set is "all punctuation minus '?'"
# (ASCII + full-width) — see markdownlint's `allPunctuationNoQuestion` helper
# (`allPunctuation.replace(/[?？]/gu, "")`, where `allPunctuation` is
# ".,;:!?。，；：！？"). '?' is intentionally excluded — a heading ending in '?'
# is not flagged, so it is never stripped here.
_HEADING_TRAILING_PUNCT_RE = re.compile(r"\s*[.,;:!。，；：！]+$")

# A bare http(s) URL, not already the destination of a markdown link
# ("...](url)") and not already inside "<...>" — both excluded via a
# fixed-width negative lookbehind. The character class stops at whitespace,
# angle brackets, and parens so a match never swallows surrounding markdown
# syntax.
_BARE_URL_RE = re.compile(r"(?<!<)(?<!\]\()https?://[^\s<>()]+")

# Trailing characters GFM's autolink-literal extension (the thing MD034 is
# built on) does not treat as part of the URL — kept *outside* the "<...>"
# wrap so the rendered text tokenizes the same way markdownlint itself would.
_URL_TRAILING_PUNCT = ".,;:!?'\""

# Code spans (`...`) are left untouched — a URL inside backticks is literal
# text, never a markdownlint "bare URL", and rewriting it would change
# rendered content markdownlint never asked us to change.
_CODE_SPAN_RE = re.compile(r"`[^`]*`")


def _strip_url_trailing_punct(url: str) -> tuple[str, str]:
    """Split a matched URL into ``(url, trailing)`` the way GFM's
    autolink-literal extension would: trailing sentence punctuation, and an
    unmatched closing paren, are not part of the URL.
    """
    trail = ""
    while url:
        ch = url[-1]
        if ch in _URL_TRAILING_PUNCT:
            trail = ch + trail
            url = url[:-1]
        elif ch == ")" and url.count("(") < url.count(")"):
            trail = ch + trail
            url = url[:-1]
        else:
            break
    return url, trail


def _autolink_segment(segment: str) -> str:
    def _wrap(match: "re.Match[str]") -> str:
        url, trail = _strip_url_trailing_punct(match.group(0))
        return f"<{url}>{trail}"

    return _BARE_URL_RE.sub(_wrap, segment)


def autolink_urls(text: str) -> str:
    """Wrap bare ``http(s)://`` URLs in ``<...>`` (MD034).

    Skips a URL that is already inside ``<>``, already the destination of a
    ``[text](url)`` markdown link, or already inside a code span. Plain
    parens with no preceding ``[text]`` do **not** protect a bare URL —
    markdownlint still flags those, and so do we.
    """
    if "https://" not in text and "http://" not in text:
        return text
    parts: list[str] = []
    last = 0
    for m in _CODE_SPAN_RE.finditer(text):
        parts.append(_autolink_segment(text[last : m.start()]))
        parts.append(m.group(0))  # code span: verbatim, never rewritten
        last = m.end()
    parts.append(_autolink_segment(text[last:]))
    return "".join(parts)


def heading_safe(text: str) -> str:
    """Render-only heading text: URLs autolinked first (MD034), then any
    trailing punctuation markdownlint's MD026 flags is stripped.

    URLs must be wrapped before the punctuation strip runs — a heading ending
    in a bare URL still needs MD034's fix, and once wrapped, a trailing
    sentence '.' immediately after the closing '>' still trips MD026 (pinned
    empirically against markdownlint-cli2: ``# Ship <url>.`` still errors).
    """
    return _HEADING_TRAILING_PUNCT_RE.sub("", autolink_urls(text))
