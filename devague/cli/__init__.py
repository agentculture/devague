"""Unified CLI entry point for devague.

Error-propagation contract: every handler raises
:class:`devague.cli._errors.DevagueError` on failure; ``main()`` catches it
via :func:`_dispatch` and routes through :mod:`devague.cli._output`. Unknown
exceptions are wrapped into a ``DevagueError`` so no Python traceback leaks.

Argparse errors (unknown verb, missing required arg) also route through the
structured format — :class:`_DevagueArgumentParser` overrides ``.error()``.
Whether errors render as text or JSON depends on whether ``--json`` appears in
the raw argv (:func:`main` sets ``_DevagueArgumentParser._json_hint`` before
``parse_args``).
"""

from __future__ import annotations

import argparse
import sys

from devague import __version__
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._output import emit_error


class _DevagueArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that routes errors through :func:`emit_error`."""

    _json_hint: bool = False

    def error(self, message: str) -> None:  # type: ignore[override]
        err = DevagueError(
            code=EXIT_USER_ERROR,
            message=message,
            remediation=f"run '{self.prog} --help' to see valid arguments",
        )
        emit_error(err, json_mode=type(self)._json_hint)
        raise SystemExit(err.code)


def _argv_has_json(argv: list[str] | None) -> bool:
    tokens = argv if argv is not None else sys.argv[1:]
    return any(t == "--json" or t.startswith("--json=") for t in tokens)


def _build_parser() -> argparse.ArgumentParser:
    parser = _DevagueArgumentParser(
        prog="devague",
        description="devague — turns a vague idea into a buildable spec by working backwards.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_DevagueArgumentParser)

    from devague.cli._commands import capture as _capture_cmd
    from devague.cli._commands import confirm as _confirm_cmd
    from devague.cli._commands import converge as _converge_cmd
    from devague.cli._commands import explain as _explain_cmd
    from devague.cli._commands import export as _export_cmd
    from devague.cli._commands import interrogate as _interrogate_cmd
    from devague.cli._commands import learn as _learn_cmd
    from devague.cli._commands import list_frames as _list_cmd
    from devague.cli._commands import new as _new_cmd
    from devague.cli._commands import park as _park_cmd
    from devague.cli._commands import plan as _plan_cmd
    from devague.cli._commands import question as _question_cmd
    from devague.cli._commands import reject as _reject_cmd
    from devague.cli._commands import review as _review_cmd
    from devague.cli._commands import show as _show_cmd
    from devague.cli._commands import status as _status_cmd

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _new_cmd.register(sub)
    _capture_cmd.register(sub)
    _interrogate_cmd.register(sub)
    _confirm_cmd.register(sub)
    _reject_cmd.register(sub)
    _review_cmd.register(sub)
    _question_cmd.register(sub)
    _park_cmd.register(sub)
    _converge_cmd.register(sub)
    _export_cmd.register(sub)
    _plan_cmd.register(sub)
    _status_cmd.register(sub)
    _show_cmd.register(sub)
    _list_cmd.register(sub)

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    """Invoke the registered handler and translate exceptions to exit codes.

    A handler may return ``None`` (treated as success, exit 0) or an ``int``
    used directly as the exit code. Failures MUST raise :class:`DevagueError`;
    any other exception is wrapped so no Python traceback leaks.
    """
    json_mode = bool(getattr(args, "json", False))
    try:
        rc = args.func(args)
    except DevagueError as err:
        emit_error(err, json_mode=json_mode)
        return err.code
    except Exception as err:  # noqa: BLE001 - last-resort; wrap and route cleanly
        wrapped = DevagueError(
            code=EXIT_USER_ERROR,
            message=f"unexpected: {err.__class__.__name__}: {err}",
            remediation="file a bug at https://github.com/agentculture/devague/issues",
        )
        emit_error(wrapped, json_mode=json_mode)
        return wrapped.code
    return rc if rc is not None else 0


def main(argv: list[str] | None = None) -> int:
    _DevagueArgumentParser._json_hint = _argv_has_json(argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
