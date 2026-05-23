from __future__ import annotations

from devague.cli._paths import UNDATED_PREFIX, dated_name


def test_dated_name_uses_created_date_prefix() -> None:
    assert dated_name("2026-05-23T11:29:36Z", "my-slug") == "2026-05-23-my-slug.md"


def test_dated_name_falls_back_to_stable_sentinel_when_created_missing() -> None:
    # A run-varying fallback (e.g. today) would break idempotence; the sentinel is
    # constant, so re-exporting always lands on the same file. (Qodo #27 review.)
    assert dated_name("", "my-slug") == f"{UNDATED_PREFIX}-my-slug.md"


def test_dated_name_falls_back_to_stable_sentinel_when_created_malformed() -> None:
    assert dated_name("not-a-date", "my-slug") == f"{UNDATED_PREFIX}-my-slug.md"


def test_dated_name_fallback_is_idempotent_across_calls() -> None:
    assert dated_name("garbage", "my-slug") == dated_name("garbage", "my-slug")
