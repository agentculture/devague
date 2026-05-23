"""DevagueError and exit-code policy.

Every failure inside devague raises :class:`DevagueError`. The top-level
``main()`` catches it, formats via :mod:`devague.cli._output`, and exits with
:attr:`DevagueError.code`. This centralises the exit-code policy and
guarantees no Python traceback leaks to stderr.
"""

from __future__ import annotations

from dataclasses import dataclass

# Exit-code policy:
#   0  = success
#   1  = user-input error (bad flag, missing required arg, unknown path)
#   2  = environment / setup error (tool not installed, file unreadable)
#   3+ = reserved for future categorisation
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_ENV_ERROR = 2


@dataclass
class DevagueError(Exception):
    """Structured error raised within devague; carries a remediation hint."""

    code: int
    message: str
    remediation: str = ""

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }
