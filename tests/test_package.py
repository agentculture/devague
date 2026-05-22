"""Package-level smoke test."""

from __future__ import annotations

import specifix


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(specifix.__version__, str)
    assert specifix.__version__
