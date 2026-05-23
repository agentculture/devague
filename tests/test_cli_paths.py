from __future__ import annotations

import re

from devague.cli._paths import dated_name


def test_dated_name_uses_created_date_prefix() -> None:
    assert dated_name("2026-05-23T11:29:36Z", "my-slug") == "2026-05-23-my-slug.md"


def test_dated_name_falls_back_to_today_when_created_missing() -> None:
    name = dated_name("", "my-slug")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-my-slug\.md", name)


def test_dated_name_falls_back_when_created_malformed() -> None:
    name = dated_name("not-a-date", "my-slug")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-my-slug\.md", name)
