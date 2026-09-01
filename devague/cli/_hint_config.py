"""Hint override config — ``tool.devague`` in the consuming repo's
``./pyproject.toml`` plus the ``DEVAGUE_HINTS`` env var (issue next-leg-hints,
task t2).

Motivation: t1 hardcoded default-on, every-verb hinting with no opt-out. Some
operators/CI contexts want the hints silenced entirely, or want a verb's
default text replaced with something more specific to their repo. This module
is the read-only lookup for both; it never persists anything (no `.devague`
state is touched) and it is consulted fresh on every invocation, so a config
edit takes effect on the very next command with no cache to invalidate.

Two knobs:

- **Global on/off.** ``DEVAGUE_HINTS=off`` (or ``0``/``false``, case-
  insensitive) silences every hint. Absent that, ``[tool.devague] hints =
  false`` in ``./pyproject.toml`` does the same. The env var wins when both
  are set: it is checked first, and only an explicit *off* value short-
  circuits — any other env value is ignored (not an error), falling through
  to the pyproject check.
- **Per-verb replacement text.** ``[tool.devague.hints]`` — a table, not the
  boolean above (the two never coexist in one file: the same ``hints`` key
  is either a bool or a table, mirroring the two use cases) — replaces one
  verb's hint text verbatim. Keys are the same strings :mod:`devague.cli.
  _hints` addresses its own tables with: a flat verb name (``"export"``) or
  ``"plan:<subverb>"`` (``"plan:export"``). An unknown key is silently
  ignored — it never errors and never appears in output.

Fail-open, mirroring :mod:`devague.contested`'s ``load_*_safely`` convention
(claim c34/h27 there; AC3 here): a missing ``pyproject.toml``, one this
process lacks permission to read, or one that fails to parse as TOML all
degrade to "no config" — defaults apply, and the calling verb's exit code is
never affected. This module works only on the CWD's ``pyproject.toml`` (the
consuming repo's, not devague's own) — that is what "consuming repo's ./
pyproject.toml" means in the task brief, and why every lookup re-resolves
``Path.cwd()`` rather than caching a path at import time.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

__all__ = ["hints_enabled", "override_text"]

_ENV_VAR = "DEVAGUE_HINTS"
_ENV_OFF_VALUES = {"off", "0", "false"}


def _env_says_off() -> bool:
    """True iff ``DEVAGUE_HINTS`` is set to one of the recognized off-values
    (case-insensitive). Any other value — including unset — is not "off"
    here; an unrecognized non-off value is deliberately not distinguished
    from unset, since both simply defer to the pyproject check.
    """
    value = os.environ.get(_ENV_VAR)
    if value is None:
        return False
    return value.strip().lower() in _ENV_OFF_VALUES


def _load_devague_table() -> dict:
    """Best-effort load of the ``[tool.devague]`` table from the CWD's
    ``pyproject.toml``. Returns ``{}`` on any missing/unreadable/unparsable
    file, or when the table simply isn't there — never raises.
    """
    try:
        # Path.cwd() itself raises OSError when the working directory has been
        # deleted or unmounted, so it lives inside the guard too — emit_next_hint
        # runs *after* the dispatch guard, and a raise here would turn an
        # otherwise successful command into a traceback (PR #110 review).
        raw = (Path.cwd() / "pyproject.toml").read_bytes()
    except OSError:
        return {}
    try:
        # TOMLDecodeError and UnicodeDecodeError are both ValueError subclasses.
        parsed = tomllib.loads(raw.decode("utf-8"))
    except ValueError:
        return {}
    tool = parsed.get("tool")
    if not isinstance(tool, dict):
        return {}
    devague_table = tool.get("devague")
    if not isinstance(devague_table, dict):
        return {}
    return devague_table


def hints_enabled() -> bool:
    """Whether hints should emit at all for this invocation.

    Precedence: ``DEVAGUE_HINTS`` off-values beat everything and disable
    immediately (no pyproject read needed). Otherwise ``[tool.devague]
    hints = false`` disables. Anything else — including a missing/broken
    pyproject.toml — leaves hints enabled (fail-open default).
    """
    if _env_says_off():
        return False
    table = _load_devague_table()
    return table.get("hints") is not False


def override_text(key: str) -> str | None:
    """The verbatim replacement hint text for ``key`` under
    ``[tool.devague.hints]``, or ``None`` if there is no usable string
    override for it (missing table, missing key, a non-string value, or a
    value that would break the one-line hint contract — all ignored rather
    than erroring).

    A hint is documented as exactly one ``next: ...`` stderr line, so an
    override carrying an embedded newline (a TOML multi-line string, or an
    escaped ``\\n``) is discarded and the default text applies — a
    continuation line would carry no ``next:`` prefix and be unattributable
    to hint output by any line-oriented consumer (PR #110 review). Ignoring
    it is the same fail-open treatment a non-string value already gets.
    """
    table = _load_devague_table()
    hints = table.get("hints")
    if not isinstance(hints, dict):
        return None
    text = hints.get(key)
    if not isinstance(text, str):
        return None
    if "\n" in text or "\r" in text:
        return None
    return text
