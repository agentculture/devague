"""Tests for the next-move hint override config (issue next-leg-hints, task
t2): ``tool.devague`` in the consuming repo's ``./pyproject.toml`` plus the
``DEVAGUE_HINTS`` env var (env wins), fail-open.

Covers plan targets: c6 h2 c19 h13.

Layers:

- Pure unit tests over :mod:`devague.cli._hint_config` (``hints_enabled`` /
  ``override_text``) driven by ``tmp_path`` + ``monkeypatch.chdir`` +
  ``monkeypatch.delenv``/``setenv`` — no devague state involved.
- A dedicated fail-open test (AC3): a missing, unreadable, and syntactically
  broken ``pyproject.toml`` all leave the exit code untouched and default
  hints intact.
- A real end-to-end pair (AC1, AC2, AC4) driving ``devague.cli.main`` against
  on-disk state in a ``tmp_path`` CWD, comparing captured stderr byte-for-byte
  rather than eyeballing or substring-matching it.
"""

from __future__ import annotations

import os
import stat

import pytest

from devague.cli import _hint_config, main
from devague.cli._hint_config import hints_enabled, override_text

# ── pure unit tests: hints_enabled ──────────────────────────────────────────


def _no_env(monkeypatch) -> None:
    monkeypatch.delenv("DEVAGUE_HINTS", raising=False)


def test_hints_enabled_default_true_with_no_config(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert hints_enabled() is True


def test_hints_enabled_false_when_pyproject_disables(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = false\n")
    assert hints_enabled() is False


def test_hints_enabled_true_when_pyproject_hints_true(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = true\n")
    assert hints_enabled() is True


@pytest.mark.parametrize("value", ["off", "OFF", "Off", "0", "false", "FALSE", "False"])
def test_hints_enabled_false_on_env_off_values_case_insensitive(
    value, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVAGUE_HINTS", value)
    assert hints_enabled() is False


@pytest.mark.parametrize("value", ["on", "1", "true", "quiet", "yes", ""])
def test_hints_enabled_ignores_non_off_env_values(value, tmp_path, monkeypatch) -> None:
    # An unrecognized (or blank) env value is not an error and is not
    # treated as "off" — it falls through to the pyproject check, which
    # here has no config at all, so hints stay enabled.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVAGUE_HINTS", value)
    assert hints_enabled() is True


def test_env_off_beats_pyproject_true(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVAGUE_HINTS", "off")
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = true\n")
    assert hints_enabled() is False


def test_env_unset_defers_to_pyproject_false(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = false\n")
    assert hints_enabled() is False


def test_env_non_off_value_still_defers_to_pyproject_false(tmp_path, monkeypatch) -> None:
    # "on both set" precedence per AC1 is about env *disabling*; a non-off
    # env value doesn't override pyproject in the other direction either —
    # it's simply ignored, and pyproject's false still applies.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVAGUE_HINTS", "loud")
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = false\n")
    assert hints_enabled() is False


# ── pure unit tests: override_text ──────────────────────────────────────────


def test_override_text_replaces_verbatim(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.devague.hints]\nexport = "go run our custom next step"\n'
    )
    assert override_text("export") == "go run our custom next step"


def test_override_text_supports_plan_namespaced_keys(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.devague.hints]\n"plan:export" = "custom plan export hint"\n'
    )
    assert override_text("plan:export") == "custom plan export hint"


def test_override_text_unknown_key_is_ignored(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[tool.devague.hints]\nexport = "x"\n')
    assert override_text("capture") is None


def test_override_text_none_with_no_config(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert override_text("export") is None


def test_override_text_none_when_hints_is_bool_not_table(tmp_path, monkeypatch) -> None:
    # The two shapes never coexist — `hints` as the global bool switch means
    # there is no per-verb table to look up, so this degrades cleanly.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = false\n")
    assert override_text("export") is None


def test_override_text_non_string_value_is_ignored(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.devague.hints]\nexport = 42\n")
    assert override_text("export") is None


# ── AC3: fail-open on missing / unreadable / broken pyproject.toml ─────────


def test_fail_open_missing_pyproject(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "pyproject.toml").exists()
    assert hints_enabled() is True
    assert override_text("export") is None


def test_fail_open_syntactically_broken_pyproject(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("this is [ not valid toml at all\n===")
    assert hints_enabled() is True
    assert override_text("export") is None


def test_fail_open_unreadable_pyproject(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool.devague]\nhints = false\n")
    if os.geteuid() == 0:
        pytest.skip("running as root: chmod-based unreadability can't be enforced")
    path.chmod(0o000)
    try:
        assert hints_enabled() is True
        assert override_text("export") is None
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_fail_open_pyproject_missing_tool_table(tmp_path, monkeypatch) -> None:
    _no_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    assert hints_enabled() is True
    assert override_text("export") is None


def test_fail_open_dedicated_verb_exit_code_unaffected(tmp_path, monkeypatch, capsys) -> None:
    """AC3's dedicated test: driving a real verb through main() with a
    broken pyproject.toml in the CWD never changes its exit code — only
    whether/what the hint says.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVAGUE_HINTS", raising=False)
    (tmp_path / "pyproject.toml").write_text("[[[ broken toml")

    rc = main(["new", "Ship it", "--title", "t2-failopen"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "next: run devague status" in captured.err


# ── AC4: byte-identical stderr with hints disabled vs. hints-on minus hint line ──


def _stderr_for(argv: list[str], tmp_path, monkeypatch, capsys, *, hints_off: bool) -> str:
    monkeypatch.chdir(tmp_path)
    if hints_off:
        monkeypatch.setenv("DEVAGUE_HINTS", "off")
    else:
        monkeypatch.delenv("DEVAGUE_HINTS", raising=False)
    rc = main(argv)
    captured = capsys.readouterr()
    assert rc == 0, f"{argv!r} failed: {captured.err!r}"
    return captured.err


def _strip_hint_lines(err: str) -> str:
    return "\n".join(ln for ln in err.splitlines() if not ln.startswith("next:"))


@pytest.mark.parametrize(
    ("label", "argv"),
    [
        ("new", ["new", "Ship next-leg hint config", "--title", "t2-e2e"]),
        ("capture", ["capture", "--kind", "audience", "operators", "--origin", "user"]),
        ("converge", ["converge"]),
        ("status", ["status"]),  # already exempt: both runs should have zero hint lines
    ],
)
def test_stderr_byte_identical_hints_off_vs_hints_on_minus_hint_line(
    label, argv, tmp_path, monkeypatch, capsys
) -> None:
    # Build up identical on-disk state twice (once per hints mode) so both
    # runs of the parametrized verb see the same starting point.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVAGUE_HINTS", raising=False)
    main(["new", "seed state", "--title", "t2-seed"])
    capsys.readouterr()

    err_on = _stderr_for(argv, tmp_path, monkeypatch, capsys, hints_off=False)
    err_off = _stderr_for(argv, tmp_path, monkeypatch, capsys, hints_off=True)

    assert err_off == _strip_hint_lines(err_on)
    if label != "status":
        assert "next:" in err_on
    assert "next:" not in err_off


def test_env_off_silences_hint_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVAGUE_HINTS", "off")
    rc = main(["new", "Ship it", "--title", "t2-off"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "next:" not in captured.err


def test_pyproject_hints_false_silences_hint_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVAGUE_HINTS", raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = false\n")
    rc = main(["new", "Ship it", "--title", "t2-pyproject-off"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "next:" not in captured.err


def test_env_wins_over_pyproject_true_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEVAGUE_HINTS", "off")
    (tmp_path / "pyproject.toml").write_text("[tool.devague]\nhints = true\n")
    rc = main(["new", "Ship it", "--title", "t2-env-wins"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "next:" not in captured.err


def test_per_verb_override_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVAGUE_HINTS", raising=False)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.devague.hints]\nnew = "go capture your first claim"\n'
    )
    rc = main(["new", "Ship it", "--title", "t2-override"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "next: go capture your first claim" in captured.err
    assert "next: run devague status" not in captured.err


def test_unknown_override_key_falls_back_to_default_end_to_end(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVAGUE_HINTS", raising=False)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.devague.hints]\nnot_a_real_verb = "should never show"\n'
    )
    rc = main(["new", "Ship it", "--title", "t2-unknown-key"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "next: run devague status" in captured.err
    assert "should never show" not in captured.err


# ── _hints._key_for: same key shape the override table addresses ───────────


def test_key_for_flat_verb() -> None:
    import argparse

    from devague.cli._hints import _key_for

    assert _key_for(argparse.Namespace(command="export")) == "export"


def test_key_for_plan_subverb() -> None:
    import argparse

    from devague.cli._hints import _key_for

    ns = argparse.Namespace(command="plan", plan_command="export")
    assert _key_for(ns) == "plan:export"


def test_key_for_bare_plan_group_is_none() -> None:
    import argparse

    from devague.cli._hints import _key_for

    ns = argparse.Namespace(command="plan", plan_command=None)
    assert _key_for(ns) is None


def test_key_for_command_none_is_none() -> None:
    import argparse

    from devague.cli._hints import _key_for

    assert _key_for(argparse.Namespace(command=None)) is None


def test_hint_config_module_importable_as_expected_name() -> None:
    # Sanity: the brief names this module `_hint_config.py`.
    assert _hint_config.__name__ == "devague.cli._hint_config"
