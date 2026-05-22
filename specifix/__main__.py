"""Allow running specifix as ``python -m specifix``."""

import sys

from specifix.cli import main

if __name__ == "__main__":
    sys.exit(main())
