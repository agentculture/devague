"""Unified CLI entry point for specifix.

Error-propagation contract: every handler raises
:class:`specifix.cli._errors.SpecifixError` on failure; ``main()`` catches it
via :func:`_dispatch` and routes through :mod:`specifix.cli._output`. Unknown
exceptions are wrapped into a ``SpecifixError`` so no Python traceback leaks.

Argparse errors (unknown verb, missing required arg) also route through the
structured format — :class:`_SpecifixArgumentParser` overrides ``.error()``.
Whether errors render as text or JSON depends on whether ``--json`` appears in
the raw argv (:func:`main` sets ``_SpecifixArgumentParser._json_hint`` before
``parse_args``).
"""

from __future__ import annotations

import argparse
import sys

from specifix import __version__
from specifix.cli._errors import EXIT_USER_ERROR, SpecifixError
from specifix.cli._output import emit_error


class _SpecifixArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that routes errors through :func:`emit_error`."""

    _json_hint: bool = False

    def error(self, message: str) -> None:  # type: ignore[override]
        err = SpecifixError(
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
    parser = _SpecifixArgumentParser(
        prog="specifix",
        description="specifix — owns spec creation for changes (greenfield).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_SpecifixArgumentParser)

    from specifix.cli._commands import explain as _explain_cmd
    from specifix.cli._commands import learn as _learn_cmd
    from specifix.cli._commands import whoami as _whoami_cmd

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _whoami_cmd.register(sub)

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    """Invoke the registered handler and translate exceptions to exit codes.

    A handler may return ``None`` (treated as success, exit 0) or an ``int``
    used directly as the exit code. Failures MUST raise :class:`SpecifixError`;
    any other exception is wrapped so no Python traceback leaks.
    """
    json_mode = bool(getattr(args, "json", False))
    try:
        rc = args.func(args)
    except SpecifixError as err:
        emit_error(err, json_mode=json_mode)
        return err.code
    except Exception as err:  # noqa: BLE001 - last-resort; wrap and route cleanly
        wrapped = SpecifixError(
            code=EXIT_USER_ERROR,
            message=f"unexpected: {err.__class__.__name__}: {err}",
            remediation="file a bug at https://github.com/agentculture/specifix/issues",
        )
        emit_error(wrapped, json_mode=json_mode)
        return wrapped.code
    return rc if rc is not None else 0


def main(argv: list[str] | None = None) -> int:
    _SpecifixArgumentParser._json_hint = _argv_has_json(argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
