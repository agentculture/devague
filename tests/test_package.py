"""Package-level smoke test."""

from __future__ import annotations

import devague


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(devague.__version__, str)
    assert devague.__version__
