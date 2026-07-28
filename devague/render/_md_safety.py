"""Shared rendering-time markdown-safety helpers for the export renderers (#64,
#87).

``devague export`` (spec-md, ``docs/specs/*.md``) and ``devague plan export``
(plan-md, ``docs/plans/*.md``) both interpolate free-form claim/task/honesty
prose straight into markdown — headings, blockquotes, and bullets. Prose
written as a sentence ("Ship the feature.") trips markdownlint's MD026
(no-trailing-punctuation) when it lands in a heading, a URL written bare
("see https://example.com") trips MD034 (no-bare-urls) wherever it lands, and
prose naming a Python identifier ("_read_file", "__init__.py") trips MD037
(no-space-in-emphasis) or MD050 (strong-style) because Markdown reads a pair
of underscores as emphasis markers. Downstream repos that commit exported
specs/plans and gate PRs on markdownlint were hand-fixing every export (or
excluding the generated directory from lint entirely) until this landed.

Every function here is applied **only** at render time — the underlying
Frame/Plan JSON keeps the original text verbatim (rendering never mutates
state, #87 acceptance criteria).

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

# Regions ``md_safe_text`` must never reach inside (#94). ``autolink_urls`` and
# ``md_safe_text`` are composed by the renderers in *both* orders — spec_md
# runs ``autolink_urls(md_safe_text(text))`` while plan_md/summary_md run
# ``md_safe_text(autolink_urls(text))`` — so ``md_safe_text`` has to be safe
# whether a URL still looks bare or has already been wrapped in ``<...>``.
# Without this carve-out an underscore inside a URL is treated as an
# identifier and wrapped in a code span, which corrupts the link in one order
# ("<https://e.com/`a_b`>") and truncates it at the first underscore in the
# other ("<https://e.com/>`a_b`"). Alternation order matters: code spans are
# matched first so a URL inside backticks stays governed by the code-span
# rule, then already-wrapped autolinks, then bare URLs. Only the URL itself is
# protected — surrounding markdown control characters keep being escaped
# exactly as before, so a claim mentioning "[text](url)" still renders as
# literal prose rather than becoming a live link.
_PROTECTED_RE = re.compile(
    r"`[^`]*`"  # code span
    r"|<https?://[^\s<>]*>"  # already-autolinked URL
    r"|https?://[^\s<>()]+"  # bare URL
)


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


# ── md_safe_text (#87: MD037/MD050 + stray control characters) ───────────────

# A contiguous run of identifier-ish characters that contains at least one
# underscore — covers both leading-underscore names (``_read_file``) and
# dunder names (``__init__``). The character classes on either side of the
# mandatory ``_`` are themselves allowed to contain underscores too, so the
# match always extends to the full contiguous run rather than stopping at the
# first underscore. An optional trailing ``.<ext>`` (a small, deliberately
# conservative allowlist of common file extensions) lets a dunder *file name*
# such as ``__init__.py`` wrap as a single token instead of splitting at the
# dot — the exact shape named in the #87 MD050 follow-up comment.
_IDENTIFIER_RE = re.compile(
    r"[A-Za-z0-9_]*_[A-Za-z0-9_]*" r"(?:\.(?:py|md|rst|json|ya?ml|toml|cfg|ini|sh|js|ts|rb|go))?"
)

# Markdown control characters that corrupt rendered document structure when a
# verbatim field contains them (the #87 issue's fallback list: '*' opens
# emphasis, '[' / ']' open link/reference syntax). Underscore is deliberately
# excluded here — it is handled by identifier wrapping above, not blanket
# escaping. The negative lookbehind skips a character already escaped by a
# prior application, which is what makes double application a no-op (h25).
_STRAY_CONTROL_CHAR_RE = re.compile(r"(?<!\\)([*\[\]])")

# A backtick that survives to this point is by construction NOT part of a
# matched code span (those are carved out and left untouched before this ever
# runs, same technique as autolink_urls) — a stray, unpaired literal backtick
# that must be escaped so it can never accidentally pair with a later one.
_STRAY_BACKTICK_RE = re.compile(r"(?<!\\)`")


def _escape_segment(segment: str) -> str:
    """Escape + wrap one *non-code-span* slice of text.

    Order matters for idempotence: stray backticks and stray control
    characters are escaped first (their patterns cannot match any character
    the identifier wrap or its own inserted backticks introduce), then
    identifiers are wrapped in fresh code spans last. On a second pass those
    fresh spans are recognized as pre-existing code spans by ``md_safe_text``
    before ``_escape_segment`` ever sees their contents again.
    """
    segment = _STRAY_BACKTICK_RE.sub(r"\\`", segment)
    segment = _STRAY_CONTROL_CHAR_RE.sub(r"\\\1", segment)
    segment = _IDENTIFIER_RE.sub(lambda m: f"`{m.group(0)}`", segment)
    return segment


def md_safe_text(text: str) -> str:
    """Render-only escaping for verbatim claim/task/instruction text (#87).

    - Underscore- and dunder-bearing identifiers (``_read_file``,
      ``__init__.py``) are wrapped in code spans rather than backslash-escaped
      — the fix the #87 issue comment prefers: it reads better in the
      rendered artifact *and* fixes both MD037 (no-space-in-emphasis) and
      MD050 (strong-style) in one move, since Markdown never parses inside a
      code span.
    - The remaining markdown control characters named in the issue as having
      "the same exposure" (``*``, ``[``, ``]``, a stray backtick, a leading
      ``#``) fall back to backslash-escaping.
    - Text already inside a code span (a matched backtick pair) is left
      completely untouched, byte-for-byte — devague claim text routinely
      mixes prose with backticked tokens (c32/h25, issue-backlog-sweep), so
      this must never double-wrap or re-escape what is already a code span.
    - URLs are left untouched too, whether still bare or already wrapped in
      ``<...>`` by ``autolink_urls`` (#94). An underscore inside a URL path is
      part of the address, not an identifier to wrap — reaching inside would
      corrupt or truncate the link, and it does so in both of the orders the
      renderers compose these two passes in.
    - Pure and idempotent: ``md_safe_text(md_safe_text(x)) == md_safe_text(x)``
      for any ``x`` (h25) — the underlying Frame/Plan JSON is never touched,
      only the rendered copy.
    """
    parts: list[str] = []
    last = 0
    for m in _PROTECTED_RE.finditer(text):
        parts.append(_escape_segment(text[last : m.start()]))
        parts.append(m.group(0))  # code span or URL: verbatim, never touched
        last = m.end()
    parts.append(_escape_segment(text[last:]))
    result = "".join(parts)
    # A leading '#' would be read as an ATX heading marker if this text ever
    # lands at the true start of a rendered line. Checking the *result's*
    # first character (not the original text[0]) keeps this idempotent: once
    # escaped, the string starts with '\\', not '#', so a second pass is a
    # no-op.
    if result.startswith("#"):
        result = "\\" + result
    return result
