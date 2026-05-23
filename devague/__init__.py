"""devague — turns a vague feature idea into a buildable spec by working backwards."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _v

try:
    __version__ = _v("devague")
except PackageNotFoundError:  # pragma: no cover  — editable install without metadata
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
