"""Allow running devague as ``python -m devague``."""

import sys

from devague.cli import main

if __name__ == "__main__":
    sys.exit(main())
