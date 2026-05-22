"""Tests for SpecifixError and the exit-code policy."""

from __future__ import annotations

from specifix.cli._errors import (
    EXIT_ENV_ERROR,
    EXIT_SUCCESS,
    EXIT_USER_ERROR,
    SpecifixError,
)


def test_exit_code_constants() -> None:
    assert EXIT_SUCCESS == 0
    assert EXIT_USER_ERROR == 1
    assert EXIT_ENV_ERROR == 2


def test_specifix_error_is_an_exception() -> None:
    err = SpecifixError(code=1, message="bad input", remediation="try --help")
    assert isinstance(err, Exception)
    assert str(err) == "bad input"


def test_specifix_error_to_dict() -> None:
    err = SpecifixError(code=2, message="missing tool", remediation="install it")
    assert err.to_dict() == {
        "code": 2,
        "message": "missing tool",
        "remediation": "install it",
    }


def test_remediation_defaults_to_empty() -> None:
    err = SpecifixError(code=1, message="x")
    assert err.remediation == ""
