"""Plan persistence: JSON under .devague/plans/, plus a current-plan pointer.

The peer of :mod:`devague.store`. Paths are cwd-relative so plans live in the repo
being specced, alongside the frames they derive from. A plan's slug is its source
frame's slug verbatim (1:1 link); plans and frames live in separate directories, so
the shared slug never collides.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from devague.frame import parse_schema_version
from devague.plan import PLAN_SCHEMA_VERSION, Plan, from_dict, to_dict
from devague.store import validate_slug

PLANS_DIR = Path(".devague/plans")
CURRENT_PLAN = Path(".devague/current_plan")


class IncompatiblePlanSchemaError(ValueError):
    """A persisted plan declares a schema_version this devague cannot read."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path_for(slug: str) -> Path:
    return PLANS_DIR / f"{validate_slug(slug)}.json"


def save(plan: Plan) -> Path:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    # Stamp the version this binary actually writes: a plan loaded under an older
    # label then mutated with newer fields must not be rewritten under that older
    # label, or the fail-closed load gate (schema_version > PLAN_SCHEMA_VERSION)
    # is defeated and an old binary silently drops the newer payload (data loss).
    plan.schema_version = PLAN_SCHEMA_VERSION
    plan.updated = _now()
    if not plan.created:
        plan.created = plan.updated
    p = path_for(plan.slug)
    p.write_text(json.dumps(to_dict(plan), indent=2) + "\n", encoding="utf-8")
    CURRENT_PLAN.write_text(plan.slug + "\n", encoding="utf-8")
    return p


def load(slug: str) -> Plan:
    p = path_for(slug)
    if not p.exists():
        raise FileNotFoundError(slug)
    raw = json.loads(p.read_text(encoding="utf-8"))
    # Check the declared schema_version against the RAW dict before constructing
    # the domain object: a genuinely newer-schema plan file must fail closed with
    # IncompatiblePlanSchemaError, not an opaque TypeError from from_dict trying to
    # build a nested dataclass it doesn't fully recognise yet (t2, the plan-side
    # twin of store.load's same hardening).
    version = parse_schema_version(raw, PLAN_SCHEMA_VERSION)
    if version > PLAN_SCHEMA_VERSION:
        raise IncompatiblePlanSchemaError(
            f"plan {slug!r} uses schema_version {version}, but this "
            f"devague supports up to {PLAN_SCHEMA_VERSION}; upgrade devague to read it"
        )
    plan = from_dict(raw)
    validate_slug(plan.slug)  # reject a tampered file whose internal slug escapes
    validate_slug(plan.frame_slug)  # the linked frame slug must be safe to load too
    if plan.slug != slug:
        # The embedded slug drives save() and the current-plan pointer; a file
        # whose internal slug disagrees with its filename could silently redirect
        # a later save onto a different plan, so reject it.
        raise ValueError(f"plan slug mismatch: file {slug!r} declares slug {plan.slug!r}")
    return plan


def list_slugs() -> list[str]:
    if not PLANS_DIR.exists():
        return []
    return sorted(p.stem for p in PLANS_DIR.glob("*.json"))


def current_slug() -> str | None:
    if CURRENT_PLAN.exists():
        return CURRENT_PLAN.read_text(encoding="utf-8").strip() or None
    return None
