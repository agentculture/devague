"""stdout / stderr helpers with a strict split.

Rule: **results go to stdout, diagnostics and errors go to stderr.** Agents
parsing specifix output can rely on this invariant. JSON mode routes structured
payloads to the same streams — it never mixes them.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from specifix.cli._errors import SpecifixError


def emit_result(data: Any, *, json_mode: bool, stream: TextIO | None = None) -> None:
    """Write a command result to stdout (text or JSON), newline-terminated."""
    s = stream if stream is not None else sys.stdout
    if json_mode:
        json.dump(data, s, ensure_ascii=False)
        s.write("\n")
        return
    text = data if isinstance(data, str) else str(data)
    s.write(text)
    if not text.endswith("\n"):
        s.write("\n")


def emit_error(err: SpecifixError, *, json_mode: bool, stream: TextIO | None = None) -> None:
    """Write a :class:`SpecifixError` to stderr (text or JSON)."""
    s = stream if stream is not None else sys.stderr
    if json_mode:
        json.dump(err.to_dict(), s, ensure_ascii=False)
        s.write("\n")
        return
    s.write(f"error: {err.message}\n")
    if err.remediation:
        s.write(f"hint: {err.remediation}\n")


def emit_diagnostic(message: str, *, stream: TextIO | None = None) -> None:
    """Write a human diagnostic (progress, summary) to stderr."""
    s = stream if stream is not None else sys.stderr
    s.write(message if message.endswith("\n") else message + "\n")
