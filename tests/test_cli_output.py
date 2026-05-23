"""Tests for the stdout/stderr output helpers."""

from __future__ import annotations

import io
import json

from devague.cli._errors import DevagueError
from devague.cli._output import emit_diagnostic, emit_error, emit_result


def test_emit_result_text_adds_trailing_newline() -> None:
    buf = io.StringIO()
    emit_result("hello", json_mode=False, stream=buf)
    assert buf.getvalue() == "hello\n"


def test_emit_result_json() -> None:
    buf = io.StringIO()
    emit_result({"a": 1}, json_mode=True, stream=buf)
    assert json.loads(buf.getvalue()) == {"a": 1}


def test_emit_error_text_with_remediation() -> None:
    buf = io.StringIO()
    emit_error(
        DevagueError(code=1, message="bad", remediation="fix it"),
        json_mode=False,
        stream=buf,
    )
    assert buf.getvalue() == "error: bad\nhint: fix it\n"


def test_emit_error_text_without_remediation() -> None:
    buf = io.StringIO()
    emit_error(DevagueError(code=1, message="bad"), json_mode=False, stream=buf)
    assert buf.getvalue() == "error: bad\n"


def test_emit_error_json() -> None:
    buf = io.StringIO()
    emit_error(
        DevagueError(code=2, message="bad", remediation="fix"),
        json_mode=True,
        stream=buf,
    )
    assert json.loads(buf.getvalue()) == {
        "code": 2,
        "message": "bad",
        "remediation": "fix",
    }


def test_emit_diagnostic_adds_newline() -> None:
    buf = io.StringIO()
    emit_diagnostic("working", stream=buf)
    assert buf.getvalue() == "working\n"
