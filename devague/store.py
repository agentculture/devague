"""Frame persistence: JSON under .devague/frames/, plus a current-frame pointer.

Paths are cwd-relative so the frames live in the repo being specced.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from devague.frame import SCHEMA_VERSION, Frame, from_dict, to_dict

FRAMES_DIR = Path(".devague/frames")
CURRENT = Path(".devague/current")
REVIEWS_DIR = Path(".devague/reviews")
QUESTIONS_DIR = Path(".devague/questions")

# devague manages .gitignore so review/question working state is uncommitted by
# default (decision c19, issue #17). The user opts in to promote one into docs.
_IGNORE_HEADER = "# devague working state (not committed by default)"


class IncompatibleSchemaError(ValueError):
    """A persisted frame declares a schema_version this devague cannot read."""


# A safe slug is a bounded, lowercase, hyphen-separated token with no path
# separators or `.` segments — so it can never escape FRAMES_DIR / SPECS_DIR.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = s[:50].strip("-")
    return s or "frame"


def validate_slug(slug: str) -> str:
    """Return ``slug`` if it is filesystem-safe, else raise ``ValueError``.

    Guards every path built from a slug (``--frame``, ``.devague/current``, a
    persisted ``frame.slug``) against path traversal and absolute paths.
    """
    if not _SLUG_RE.fullmatch(slug or ""):
        raise ValueError(f"invalid frame slug: {slug!r}")
    return slug


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path_for(slug: str) -> Path:
    return FRAMES_DIR / f"{validate_slug(slug)}.json"


def ensure_ignored(*patterns: str) -> None:
    """Idempotently add ``patterns`` to ./.gitignore (devague-managed block).

    Keeps ``.devague/`` working-state dirs uncommitted by default without
    clobbering an existing .gitignore (decision c19, issue #17).
    """
    gi = Path(".gitignore")
    existing = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    missing = [p for p in patterns if p not in existing]
    if not missing:
        return
    out = list(existing)
    if out and out[-1].strip():
        out.append("")
    if _IGNORE_HEADER not in existing:
        out.append(_IGNORE_HEADER)
    out.extend(missing)
    gi.write_text("\n".join(out) + "\n", encoding="utf-8")


def review_path(slug: str) -> Path:
    return REVIEWS_DIR / f"{validate_slug(slug)}.md"


def write_review(slug: str, content: str) -> Path:
    """Persist a review artifact to .devague/reviews/<slug>.md (uncommitted)."""
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_ignored(".devague/reviews/")
    p = review_path(slug)
    p.write_text(content, encoding="utf-8")
    return p


def questions_path(slug: str) -> Path:
    return QUESTIONS_DIR / f"{validate_slug(slug)}.md"


def write_questions(slug: str, content: str) -> Path:
    """Persist a pending-decisions file to .devague/questions/<slug>.md (uncommitted)."""
    QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_ignored(".devague/questions/")
    p = questions_path(slug)
    p.write_text(content, encoding="utf-8")
    return p


def unique_slug(base: str) -> str:
    """Return ``base`` if free, else the first ``base-N`` (N>=2) that is unused."""
    base = base or "frame"
    if not path_for(base).exists():
        return base
    n = 2
    while path_for(f"{base}-{n}").exists():
        n += 1
    return f"{base}-{n}"


def save(frame: Frame) -> Path:
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    frame.updated = _now()
    if not frame.created:
        frame.created = frame.updated
    p = path_for(frame.slug)
    p.write_text(json.dumps(to_dict(frame), indent=2) + "\n", encoding="utf-8")
    CURRENT.write_text(frame.slug + "\n", encoding="utf-8")
    return p


def load(slug: str) -> Frame:
    p = path_for(slug)
    if not p.exists():
        raise FileNotFoundError(slug)
    frame = from_dict(json.loads(p.read_text(encoding="utf-8")))
    validate_slug(frame.slug)  # reject a tampered file whose internal slug escapes
    if frame.schema_version > SCHEMA_VERSION:
        raise IncompatibleSchemaError(
            f"frame {slug!r} uses schema_version {frame.schema_version}, but this "
            f"devague supports up to {SCHEMA_VERSION}; upgrade devague to read it"
        )
    return frame


def list_slugs() -> list[str]:
    if not FRAMES_DIR.exists():
        return []
    return sorted(p.stem for p in FRAMES_DIR.glob("*.json"))


def current_slug() -> str | None:
    if CURRENT.exists():
        return CURRENT.read_text(encoding="utf-8").strip() or None
    return None
