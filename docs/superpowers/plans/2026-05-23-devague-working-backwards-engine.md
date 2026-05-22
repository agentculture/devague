# devague Working-Backwards Engine Implementation Plan (Phases 1–3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build devague's working-backwards engine — a deterministic state machine over a Frame of claims, honesty conditions, and open vagueness, exposed as CLI moves, that converges into a buildable spec.

**Architecture:** The `devague` CLI is deterministic (no LLM calls): it mutates/renders Frame state and evaluates a convergence gate. The resident Claude agent drives it. Frames persist as JSON under `.devague/frames/<slug>.json`; rendering/export go through a `Renderer` registry (markdown now, more later).

**Tech Stack:** Python ≥3.12, uv, hatchling, pytest + pytest-xdist, argparse, stdlib only.

**Prerequisite:** the rename plan (`2026-05-23-devague-rename.md`) is merged — the package is `devague/`, error class `DevagueError`, parser `_DevagueArgumentParser`.

**Design input:** `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`.

---

## File map

| File | Responsibility |
|------|----------------|
| `devague/frame.py` | Frame/Claim/Vagueness/HonestyCondition/HardQuestion dataclasses, kind/status constants, id allocation, status transitions, to_dict/from_dict |
| `devague/store.py` | `.devague/frames/` paths, save/load JSON, slugify, current-frame pointer |
| `devague/convergence.py` | `ConvergenceResult` + `evaluate(frame)` gate logic |
| `devague/render/__init__.py` | Renderer registry: `register`/`formats`/`render` |
| `devague/render/frame_md.py` | `render_frame` — Announcement Frame markdown |
| `devague/render/spec_md.py` | `render_spec` — buildable spec markdown |
| `devague/cli/_frames.py` | `resolve(slug)` → Frame (maps misses to `DevagueError`) |
| `devague/cli/_commands/{new,capture,interrogate,confirm,reject,park,converge,export,show,list_frames}.py` | one move per module, each `register(sub)` |
| `devague/cli/_commands/{learn,explain}.py` | rewrite stub bodies to teach the method |
| `tests/test_frame.py`, `test_store.py`, `test_convergence.py`, `test_render.py`, `test_cli_moves.py`, `test_cli_converge_export.py` | tests |

Common test fixture: tests that touch storage use `monkeypatch.chdir(tmp_path)` so `.devague/` is written under a temp dir.

---

## Task 1: Frame domain model

**Files:** Create `devague/frame.py`; Test `tests/test_frame.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_frame.py
from __future__ import annotations

from devague.frame import Frame, from_dict, to_dict


def test_add_claim_user_is_confirmed_llm_is_proposed() -> None:
    f = Frame(slug="s", title="t")
    a = f.add_claim("announcement", "we shipped X", origin="user")
    b = f.add_claim("audience", "devs", origin="llm")
    assert a.id == "c1" and a.status == "confirmed"
    assert b.id == "c2" and b.status == "proposed"


def test_add_honesty_and_hard_question_and_vagueness_ids() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x")
    h = f.add_honesty(c, "must be measurable", origin="llm")
    q = f.add_hard_question(c, "what if empty?", blocking=True)
    v = f.add_vagueness("unsure about scale", "unknown_blocking")
    assert h.id == "h1" and h.status == "proposed"
    assert q.id == "q1" and q.blocking is True and q.resolved is False
    assert v.id == "v1" and v.kind == "unknown_blocking"


def test_set_status_finds_claim_or_honesty() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("audience", "devs", origin="llm")
    h = f.add_honesty(c, "cond", origin="llm")
    assert f.set_status("c1", "confirmed") is True and c.status == "confirmed"
    assert f.set_status("h1", "confirmed") is True and h.status == "confirmed"
    assert f.set_status("nope", "confirmed") is False


def test_roundtrip_to_from_dict() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")
    f.add_honesty(c, "cond")
    f.add_hard_question(c, "q?", blocking=True)
    f.add_vagueness("v", "follow_up", claim_id="c1")
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.claims[0].honesty_conditions[0].text == "cond"
```

- [ ] **Step 2: Run it — expect failure**

Run: `uv run pytest tests/test_frame.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'devague.frame'`.

- [ ] **Step 3: Implement `devague/frame.py`**

```python
"""The Frame domain model — claims, honesty conditions, hard questions, vagueness.

Pure data + transitions, no I/O. Persistence lives in :mod:`devague.store`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

CLAIM_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "why_it_matters",
    "boundary",
    "success_signal",
    "open_question",
)
SPEC_AFFECTING_KINDS = tuple(k for k in CLAIM_KINDS if k != "open_question")
VAGUENESS_KINDS = (
    "unknown_nonblocking",
    "unknown_blocking",
    "out_of_scope",
    "follow_up",
)
CLAIM_STATUSES = ("proposed", "confirmed", "rejected", "parked")


@dataclass
class HonestyCondition:
    id: str
    text: str
    status: str = "proposed"  # proposed | confirmed | rejected


@dataclass
class HardQuestion:
    id: str
    text: str
    resolved: bool = False
    blocking: bool = False


@dataclass
class Claim:
    id: str
    kind: str
    text: str
    origin: str = "user"  # user | llm
    status: str = "confirmed"  # proposed | confirmed | rejected | parked
    honesty_conditions: list[HonestyCondition] = field(default_factory=list)
    hard_questions: list[HardQuestion] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


@dataclass
class Vagueness:
    id: str
    text: str
    kind: str
    claim_id: Optional[str] = None


@dataclass
class Frame:
    slug: str
    title: str
    status: str = "drafting"  # drafting | converged | exported
    created: str = ""
    updated: str = ""
    claims: list[Claim] = field(default_factory=list)
    open_vagueness: list[Vagueness] = field(default_factory=list)

    @staticmethod
    def _next(items: list, prefix: str) -> str:
        n = 0
        for it in items:
            if it.id.startswith(prefix):
                try:
                    n = max(n, int(it.id[len(prefix):]))
                except ValueError:
                    pass
        return f"{prefix}{n + 1}"

    def _all_honesty(self) -> list[HonestyCondition]:
        return [h for c in self.claims for h in c.honesty_conditions]

    def _all_hard_questions(self) -> list[HardQuestion]:
        return [q for c in self.claims for q in c.hard_questions]

    def add_claim(self, kind: str, text: str, origin: str = "user") -> Claim:
        if kind not in CLAIM_KINDS:
            raise ValueError(f"unknown claim kind: {kind}")
        status = "proposed" if origin == "llm" else "confirmed"
        claim = Claim(id=self._next(self.claims, "c"), kind=kind, text=text, origin=origin, status=status)
        self.claims.append(claim)
        return claim

    def find_claim(self, cid: str) -> Optional[Claim]:
        return next((c for c in self.claims if c.id == cid), None)

    def find_honesty(self, hid: str) -> Optional[HonestyCondition]:
        return next((h for h in self._all_honesty() if h.id == hid), None)

    def add_honesty(self, claim: Claim, text: str, origin: str = "llm") -> HonestyCondition:
        status = "confirmed" if origin == "user" else "proposed"
        h = HonestyCondition(id=self._next(self._all_honesty(), "h"), text=text, status=status)
        claim.honesty_conditions.append(h)
        return h

    def add_hard_question(self, claim: Claim, text: str, blocking: bool = False) -> HardQuestion:
        q = HardQuestion(id=self._next(self._all_hard_questions(), "q"), text=text, blocking=blocking)
        claim.hard_questions.append(q)
        return q

    def add_vagueness(self, text: str, kind: str, claim_id: Optional[str] = None) -> Vagueness:
        if kind not in VAGUENESS_KINDS:
            raise ValueError(f"unknown vagueness kind: {kind}")
        v = Vagueness(id=self._next(self.open_vagueness, "v"), text=text, kind=kind, claim_id=claim_id)
        self.open_vagueness.append(v)
        return v

    def set_status(self, item_id: str, status: str) -> bool:
        claim = self.find_claim(item_id)
        if claim is not None:
            claim.status = status
            return True
        honesty = self.find_honesty(item_id)
        if honesty is not None:
            honesty.status = status
            return True
        return False


def to_dict(frame: Frame) -> dict:
    return dataclasses.asdict(frame)


def from_dict(d: dict) -> Frame:
    claims = [
        Claim(
            id=c["id"],
            kind=c["kind"],
            text=c["text"],
            origin=c.get("origin", "user"),
            status=c.get("status", "confirmed"),
            honesty_conditions=[HonestyCondition(**h) for h in c.get("honesty_conditions", [])],
            hard_questions=[HardQuestion(**q) for q in c.get("hard_questions", [])],
            links=list(c.get("links", [])),
        )
        for c in d.get("claims", [])
    ]
    vag = [Vagueness(**v) for v in d.get("open_vagueness", [])]
    return Frame(
        slug=d["slug"],
        title=d["title"],
        status=d.get("status", "drafting"),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        claims=claims,
        open_vagueness=vag,
    )
```

- [ ] **Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_frame.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add devague/frame.py tests/test_frame.py
git commit -m "feat: add Frame domain model (claims, honesty, vagueness)"
```

---

## Task 2: Frame store (persistence)

**Files:** Create `devague/store.py`; Test `tests/test_store.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
from __future__ import annotations

import pytest

from devague import store
from devague.frame import Frame


def test_slugify_caps_and_sanitises() -> None:
    assert store.slugify("Hello, World!") == "hello-world"
    assert store.slugify("   ") == "frame"
    assert len(store.slugify("x" * 200)) <= 50


def test_save_load_roundtrip_and_current(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "shipped X")
    store.save(f)
    assert store.current_slug() == "demo"
    assert store.list_slugs() == ["demo"]
    loaded = store.load("demo")
    assert loaded.title == "Demo"
    assert loaded.created and loaded.updated  # timestamps stamped on save


def test_load_missing_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load("nope")
```

- [ ] **Step 2: Run it — expect failure**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'devague.store'`.

- [ ] **Step 3: Implement `devague/store.py`**

```python
"""Frame persistence: JSON under .devague/frames/, plus a current-frame pointer.

Paths are cwd-relative so the frames live in the repo being specced.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from devague.frame import Frame, from_dict, to_dict

FRAMES_DIR = Path(".devague/frames")
CURRENT = Path(".devague/current")


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = s[:50].strip("-")
    return s or "frame"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path_for(slug: str) -> Path:
    return FRAMES_DIR / f"{slug}.json"


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
    return from_dict(json.loads(p.read_text(encoding="utf-8")))


def list_slugs() -> list[str]:
    if not FRAMES_DIR.exists():
        return []
    return sorted(p.stem for p in FRAMES_DIR.glob("*.json"))


def current_slug() -> str | None:
    if CURRENT.exists():
        return CURRENT.read_text(encoding="utf-8").strip() or None
    return None
```

- [ ] **Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_store.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Gitignore the local current-frame pointer**

Append to `.gitignore` (frames themselves are committed artifacts; the pointer is machine-local):

```gitignore

# devague: local current-frame pointer (frames under .devague/frames/ are committed)
.devague/current
```

- [ ] **Step 6: Commit**

```bash
git add devague/store.py tests/test_store.py .gitignore
git commit -m "feat: add Frame JSON store with current-frame pointer"
```

---

## Task 3: Convergence gate

**Files:** Create `devague/convergence.py`; Test `tests/test_convergence.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_convergence.py
from __future__ import annotations

from devague.convergence import evaluate
from devague.frame import Frame


def _full_frame() -> Frame:
    f = Frame(slug="s", title="t")
    for kind in ("announcement", "audience", "after_state", "before_state", "boundary", "success_signal"):
        c = f.add_claim(kind, f"{kind} text", origin="user")  # user => confirmed
        f.add_honesty(c, "must hold", origin="user")  # user => confirmed
    return f


def test_full_frame_converges() -> None:
    res = evaluate(_full_frame())
    assert res.passed is True and res.missing == []


def test_missing_required_kinds_reported() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")
    res = evaluate(f)
    assert res.passed is False
    assert any("audience" in m for m in res.missing)
    assert any("after_state" in m for m in res.missing)


def test_proposed_claim_blocks() -> None:
    f = _full_frame()
    f.add_claim("boundary", "maybe not this", origin="llm")  # proposed
    res = evaluate(f)
    assert res.passed is False
    assert any("still proposed" in m for m in res.missing)


def test_confirmed_claim_without_honesty_blocks() -> None:
    f = _full_frame()
    c = f.add_claim("success_signal", "extra signal", origin="user")  # confirmed, no honesty
    res = evaluate(f)
    assert res.passed is False
    assert any(c.id in m and "honesty" in m for m in res.missing)


def test_blocking_vagueness_and_hard_question_block() -> None:
    f = _full_frame()
    f.add_vagueness("scale?", "unknown_blocking")
    res = evaluate(f)
    assert any("blocking vagueness" in m for m in res.missing)
    f2 = _full_frame()
    f2.add_hard_question(f2.claims[0], "what if zero?", blocking=True)
    res2 = evaluate(f2)
    assert any("blocking hard question" in m for m in res2.missing)
```

- [ ] **Step 2: Run it — expect failure**

Run: `uv run pytest tests/test_convergence.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'devague.convergence'`.

- [ ] **Step 3: Implement `devague/convergence.py`**

```python
"""The convergence gate: is a frame solid enough to export a buildable spec?"""

from __future__ import annotations

from dataclasses import dataclass, field

from devague.frame import SPEC_AFFECTING_KINDS, Frame


@dataclass
class ConvergenceResult:
    passed: bool
    missing: list[str] = field(default_factory=list)


def evaluate(frame: Frame) -> ConvergenceResult:
    missing: list[str] = []
    confirmed = [c for c in frame.claims if c.status == "confirmed"]
    confirmed_kinds = {c.kind for c in confirmed}

    for required in ("announcement", "audience", "after_state"):
        if required not in confirmed_kinds:
            missing.append(f"missing confirmed '{required}' claim")
    if "before_state" not in confirmed_kinds and "why_it_matters" not in confirmed_kinds:
        missing.append("missing 'before_state' or 'why_it_matters' claim")
    if "boundary" not in confirmed_kinds:
        missing.append("missing a 'boundary' / non-goal claim")
    if "success_signal" not in confirmed_kinds:
        missing.append("missing a 'success_signal' claim")

    for c in frame.claims:
        if c.kind in SPEC_AFFECTING_KINDS and c.status == "proposed":
            missing.append(f"claim {c.id} still proposed (confirm, reject, or park it)")

    for c in confirmed:
        if c.kind in SPEC_AFFECTING_KINDS and not any(
            h.status == "confirmed" for h in c.honesty_conditions
        ):
            missing.append(f"claim {c.id} has no confirmed honesty condition")

    for v in frame.open_vagueness:
        if v.kind == "unknown_blocking":
            missing.append(f"blocking vagueness {v.id} unresolved")

    for c in frame.claims:
        for q in c.hard_questions:
            if q.blocking and not q.resolved:
                missing.append(f"blocking hard question {q.id} on {c.id} unresolved")

    return ConvergenceResult(passed=not missing, missing=missing)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_convergence.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add devague/convergence.py tests/test_convergence.py
git commit -m "feat: add convergence gate"
```

---

## Task 4: Renderer registry + markdown renderers

**Files:** Create `devague/render/__init__.py`, `devague/render/frame_md.py`, `devague/render/spec_md.py`; Test `tests/test_render.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render.py
from __future__ import annotations

import pytest

from devague import render
from devague.cli._errors import DevagueError
from devague.frame import Frame


def _frame() -> Frame:
    f = Frame(slug="s", title="My Feature")
    a = f.add_claim("announcement", "Shipped fast specs", origin="user")
    f.add_honesty(a, "must be honest", origin="user")
    f.add_claim("audience", "developers", origin="user")
    f.add_vagueness("scale unknown", "follow_up")
    return f


def test_formats_include_frame_and_spec() -> None:
    assert "frame-md" in render.formats()
    assert "spec-md" in render.formats()


def test_render_frame_md_has_sections() -> None:
    out = render.render(_frame(), "frame-md")
    assert "# Announcement Frame — My Feature" in out
    assert "## Announcement" in out
    assert "Shipped fast specs" in out
    assert "## Open vagueness" in out


def test_render_spec_md_has_title_and_audience() -> None:
    out = render.render(_frame(), "spec-md")
    assert out.startswith("# My Feature")
    assert "## Audience" in out
    assert "developers" in out


def test_unknown_format_raises() -> None:
    with pytest.raises(DevagueError):
        render.render(_frame(), "nope")
```

- [ ] **Step 2: Run it — expect failure**

Run: `uv run pytest tests/test_render.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'devague.render'`.

- [ ] **Step 3: Implement `devague/render/frame_md.py`**

```python
"""Renderer: the Announcement Frame as markdown."""

from __future__ import annotations

from devague.frame import Frame

_SECTIONS = [
    ("announcement", "Announcement"),
    ("audience", "Audience"),
    ("after_state", "After-state experience"),
    ("why_it_matters", "Why it matters"),
    ("before_state", "Before-state pain"),
    ("boundary", "Boundaries / non-goals"),
    ("success_signal", "Success signals"),
    ("open_question", "Open questions"),
]


def render_frame(frame: Frame) -> str:
    out = [
        f"# Announcement Frame — {frame.title}",
        "",
        f"_slug: {frame.slug} · status: {frame.status}_",
        "",
    ]
    for kind, heading in _SECTIONS:
        claims = [c for c in frame.claims if c.kind == kind and c.status != "rejected"]
        if not claims:
            continue
        out.append(f"## {heading}")
        for c in claims:
            mark = "" if c.status == "confirmed" else f" _({c.status})_"
            out.append(f"- {c.text}{mark}")
            for h in c.honesty_conditions:
                hm = "" if h.status == "confirmed" else f" _({h.status})_"
                out.append(f"  - honesty: {h.text}{hm}")
            for q in c.hard_questions:
                qm = "blocking" if q.blocking else "open"
                out.append(f"  - Q ({qm}): {q.text}")
        out.append("")
    if frame.open_vagueness:
        out.append("## Open vagueness")
        for v in frame.open_vagueness:
            out.append(f"- [{v.kind}] {v.text}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
```

- [ ] **Step 4: Implement `devague/render/spec_md.py`**

```python
"""Renderer: the buildable spec as markdown, derived from a converged frame."""

from __future__ import annotations

from devague.frame import Frame


def _texts(frame: Frame, kind: str) -> list[str]:
    return [c.text for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def render_spec(frame: Frame) -> str:
    out: list[str] = [f"# {frame.title}", ""]
    ann = _texts(frame, "announcement")
    if ann:
        out += ["> " + ann[0], ""]
    aud = _texts(frame, "audience")
    if aud:
        out += ["## Audience", *[f"- {t}" for t in aud], ""]
    out += ["## Before → After", ""]
    for t in _texts(frame, "before_state"):
        out.append(f"- Before: {t}")
    for t in _texts(frame, "after_state"):
        out.append(f"- After: {t}")
    out.append("")
    why = _texts(frame, "why_it_matters")
    if why:
        out += ["## Why it matters", *[f"- {t}" for t in why], ""]
    reqs = [h.text for c in frame.claims for h in c.honesty_conditions if h.status == "confirmed"]
    if reqs:
        out += ["## Requirements / honesty conditions", *[f"- {t}" for t in reqs], ""]
    succ = _texts(frame, "success_signal")
    if succ:
        out += ["## Success signals", *[f"- {t}" for t in succ], ""]
    bnd = _texts(frame, "boundary")
    if bnd:
        out += ["## Non-goals", *[f"- {t}" for t in bnd], ""]
    hqs = [q for c in frame.claims for q in c.hard_questions]
    if hqs:
        out += [
            "## Hard questions",
            *[f"- {q.text}" + (" (blocking)" if q.blocking else "") for q in hqs],
            "",
        ]
    follow = [v.text for v in frame.open_vagueness if v.kind in ("follow_up", "out_of_scope")]
    if follow:
        out += ["## Open / follow-up", *[f"- {t}" for t in follow], ""]
    return "\n".join(out).rstrip() + "\n"
```

- [ ] **Step 5: Implement `devague/render/__init__.py`**

```python
"""Renderer registry: frame/spec → text, selected by --format.

New output modalities (NotebookLM, HTML, user stories) register here.
"""

from __future__ import annotations

from typing import Callable

from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.frame import Frame

_REGISTRY: dict[str, Callable[[Frame], str]] = {}


def register(name: str, fn: Callable[[Frame], str]) -> None:
    _REGISTRY[name] = fn


def formats() -> list[str]:
    return sorted(_REGISTRY)


def render(frame: Frame, fmt: str) -> str:
    if fmt not in _REGISTRY:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown format: {fmt}",
            f"available formats: {', '.join(formats())}",
        )
    return _REGISTRY[fmt](frame)


# Register the built-in renderers (import-time side effect).
from devague.render import frame_md as _frame_md  # noqa: E402
from devague.render import spec_md as _spec_md  # noqa: E402

register("frame-md", _frame_md.render_frame)
register("spec-md", _spec_md.render_spec)
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest tests/test_render.py -q`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add devague/render/ tests/test_render.py
git commit -m "feat: add renderer registry with frame-md and spec-md renderers"
```

---

## Task 5: Frame resolver helper

**Files:** Create `devague/cli/_frames.py`. (Covered by the move tests in Tasks 6–9; no standalone test file.)

- [ ] **Step 1: Implement `devague/cli/_frames.py`**

```python
"""Resolve the target frame for a move: explicit --frame, else the current frame."""

from __future__ import annotations

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.frame import Frame


def resolve(slug: str | None) -> Frame:
    slug = slug or store.current_slug()
    if not slug:
        raise DevagueError(
            EXIT_USER_ERROR,
            "no frame selected",
            'run \'devague new "<announcement>"\' or pass --frame <slug>',
        )
    try:
        return store.load(slug)
    except FileNotFoundError:
        raise DevagueError(
            EXIT_USER_ERROR, f"no such frame: {slug}", "run 'devague list' to see frames"
        ) from None
```

- [ ] **Step 2: Commit**

```bash
git add devague/cli/_frames.py
git commit -m "feat: add frame resolver helper"
```

---

## Task 6: `new` and `capture` moves

**Files:** Create `devague/cli/_commands/new.py`, `devague/cli/_commands/capture.py`; Modify `devague/cli/__init__.py`; Test `tests/test_cli_moves.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_moves.py
from __future__ import annotations

import json

import pytest

from devague import store
from devague.cli import main


def test_new_creates_frame_with_announcement(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["new", "Shipped instant specs", "--json"])
    assert rc == 0
    f = store.load(store.current_slug())
    assert f.claims[0].kind == "announcement"
    assert f.claims[0].status == "confirmed"


def test_capture_adds_classified_claim(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    rc = main(["capture", "--kind", "audience", "developers", "--origin", "llm", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "audience"
    assert payload["status"] == "proposed"


def test_capture_without_frame_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["capture", "--kind", "audience", "devs"])
    assert exc.value.code == 1
```

Note: `main()` returns the exit code for handler errors, but `DevagueError` from a handler is caught by `_dispatch` and returned (not raised). The `capture_without_frame` case raises `SystemExit` only if argparse fails — here the handler raises `DevagueError`, so adjust: assert on the return code instead.

Replace the third test body with:

```python
def test_capture_without_frame_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["capture", "--kind", "audience", "devs"])
    assert rc == 1
    assert "no frame selected" in capsys.readouterr().err
```

- [ ] **Step 2: Run it — expect failure**

Run: `uv run pytest tests/test_cli_moves.py -q`
Expected: FAIL — unknown command `new` / `capture` routed through the structured error (the verbs aren't registered yet).

- [ ] **Step 3: Implement `devague/cli/_commands/new.py`**

```python
"""``devague new`` — start a frame from an announcement (the first move)."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._output import emit_result
from devague.frame import Frame


def cmd_new(args: argparse.Namespace) -> int:
    title = args.title or args.announcement
    frame = Frame(slug=store.slugify(title), title=title)
    frame.add_claim("announcement", args.announcement, origin="user")
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"slug": frame.slug, "title": title, "claims": 1}, json_mode=True)
    else:
        emit_result(f"created frame '{frame.slug}' (announcement = c1)", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("new", help="Start a frame from an announcement.")
    p.add_argument("announcement", help="Pretend it shipped: what would you announce?")
    p.add_argument("--title", help="Frame title (defaults to the announcement).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_new)
```

- [ ] **Step 4: Implement `devague/cli/_commands/capture.py`**

```python
"""``devague capture`` — record and classify a claim."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import CLAIM_KINDS


def cmd_capture(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    claim = frame.add_claim(args.kind, args.text, origin=args.origin)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(
            {"id": claim.id, "kind": claim.kind, "status": claim.status}, json_mode=True
        )
    else:
        emit_result(f"captured {claim.id} ({claim.kind}, {claim.status})", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("capture", help="Record and classify a claim.")
    p.add_argument("text", help="The claim text.")
    p.add_argument("--kind", required=True, choices=CLAIM_KINDS, help="Claim kind.")
    p.add_argument("--origin", choices=("user", "llm"), default="user", help="Who proposed it.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_capture)
```

- [ ] **Step 5: Register both verbs in `devague/cli/__init__.py`**

In `_build_parser()`, extend the deferred-import block so it reads:

```python
    from devague.cli._commands import capture as _capture_cmd
    from devague.cli._commands import explain as _explain_cmd
    from devague.cli._commands import learn as _learn_cmd
    from devague.cli._commands import new as _new_cmd

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _new_cmd.register(sub)
    _capture_cmd.register(sub)
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest tests/test_cli_moves.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add devague/cli/_commands/new.py devague/cli/_commands/capture.py devague/cli/__init__.py tests/test_cli_moves.py
git commit -m "feat: add new and capture moves"
```

---

## Task 7: `interrogate`, `confirm`, `reject`, `park` moves

**Files:** Create `devague/cli/_commands/{interrogate,confirm,reject,park}.py`; Modify `devague/cli/__init__.py`; Modify `tests/test_cli_moves.py`.

- [ ] **Step 1: Append failing tests to `tests/test_cli_moves.py`**

```python
def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])  # announcement = c1


def test_interrogate_adds_proposed_honesty(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["interrogate", "c1", "--honesty", "must be measurable", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["added"][0]["kind"] == "honesty"
    assert payload["added"][0]["status"] == "proposed"


def test_confirm_and_reject_transition_status(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    assert main(["confirm", "c2"]) == 0
    assert store.load(store.current_slug()).find_claim("c2").status == "confirmed"
    assert main(["reject", "c2"]) == 0
    assert store.load(store.current_slug()).find_claim("c2").status == "rejected"


def test_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["confirm", "zzz"])
    assert rc == 1
    assert "no such" in capsys.readouterr().err


def test_park_adds_vagueness(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["park", "scale is unclear", "--kind", "unknown_blocking", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "unknown_blocking"
    assert payload["id"] == "v1"
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run pytest tests/test_cli_moves.py -q`
Expected: FAIL — `interrogate`/`confirm`/`reject`/`park` not registered.

- [ ] **Step 3: Implement `devague/cli/_commands/interrogate.py`**

```python
"""``devague interrogate`` — pressure-test a claim with honesty conditions / hard questions."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result


def cmd_interrogate(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    claim = frame.find_claim(args.claim_id)
    if claim is None:
        raise DevagueError(
            EXIT_USER_ERROR, f"no such claim: {args.claim_id}", "run 'devague show'"
        )
    added: list[dict] = []
    if args.honesty:
        h = frame.add_honesty(claim, args.honesty, origin=args.origin)
        added.append({"kind": "honesty", "id": h.id, "status": h.status})
    if args.risk:
        q = frame.add_hard_question(claim, f"risk: {args.risk}", blocking=False)
        added.append({"kind": "hard_question", "id": q.id, "status": "open"})
    if args.hard_question:
        q = frame.add_hard_question(claim, args.hard_question, blocking=args.blocking)
        added.append(
            {"kind": "hard_question", "id": q.id, "status": "blocking" if q.blocking else "open"}
        )
    if args.contradicts:
        q = frame.add_hard_question(claim, f"contradiction with {args.contradicts}?", blocking=True)
        added.append({"kind": "hard_question", "id": q.id, "status": "blocking"})
    if not added:
        raise DevagueError(
            EXIT_USER_ERROR,
            "nothing to interrogate",
            "pass --honesty / --hard-question / --risk / --contradicts",
        )
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"claim": claim.id, "added": added}, json_mode=True)
    else:
        emit_result(
            f"interrogated {claim.id}: " + ", ".join(f"{a['kind']} {a['id']}" for a in added),
            json_mode=False,
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("interrogate", help="Attach honesty conditions / hard questions to a claim.")
    p.add_argument("claim_id", help="Claim id (e.g. c1).")
    p.add_argument("--honesty", help="An honesty condition (what must be true).")
    p.add_argument("--hard-question", dest="hard_question", help="A hard question.")
    p.add_argument("--risk", help="A risk (recorded as a non-blocking hard question).")
    p.add_argument("--contradicts", help="Claim id this contradicts (records a blocking question).")
    p.add_argument("--blocking", action="store_true", help="Mark the hard question blocking.")
    p.add_argument("--origin", choices=("user", "llm"), default="llm", help="Who proposed the honesty condition.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_interrogate)
```

- [ ] **Step 4: Implement `devague/cli/_commands/confirm.py` and `reject.py`**

`confirm.py`:

```python
"""``devague confirm`` — confirm a claim or honesty condition (user-only transition)."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result


def _transition(args: argparse.Namespace, status: str) -> int:
    frame = resolve(args.frame)
    if not frame.set_status(args.id, status):
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such claim or honesty condition: {args.id}",
            "run 'devague show'",
        )
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": args.id, "status": status}, json_mode=True)
    else:
        emit_result(f"{args.id} -> {status}", json_mode=False)
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    return _transition(args, "confirmed")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("confirm", help="Confirm a claim or honesty condition.")
    p.add_argument("id", help="Claim id (c*) or honesty id (h*).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_confirm)
```

`reject.py`:

```python
"""``devague reject`` — reject a claim or honesty condition."""

from __future__ import annotations

import argparse

from devague.cli._commands.confirm import _transition


def cmd_reject(args: argparse.Namespace) -> int:
    return _transition(args, "rejected")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("reject", help="Reject a claim or honesty condition.")
    p.add_argument("id", help="Claim id (c*) or honesty id (h*).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_reject)
```

- [ ] **Step 5: Implement `devague/cli/_commands/park.py`**

```python
"""``devague park`` — move uncertainty into first-class open vagueness."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import VAGUENESS_KINDS


def cmd_park(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    v = frame.add_vagueness(args.text, args.kind, claim_id=args.claim)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": v.id, "kind": v.kind}, json_mode=True)
    else:
        emit_result(f"parked {v.id} ({v.kind})", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("park", help="Record open vagueness instead of forcing an answer.")
    p.add_argument("text", help="The uncertainty.")
    p.add_argument("--kind", required=True, choices=VAGUENESS_KINDS, help="Vagueness kind.")
    p.add_argument("--claim", help="Link to a claim id.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_park)
```

- [ ] **Step 6: Register the four verbs in `devague/cli/__init__.py`**

Extend the import + register block:

```python
    from devague.cli._commands import capture as _capture_cmd
    from devague.cli._commands import confirm as _confirm_cmd
    from devague.cli._commands import explain as _explain_cmd
    from devague.cli._commands import interrogate as _interrogate_cmd
    from devague.cli._commands import learn as _learn_cmd
    from devague.cli._commands import new as _new_cmd
    from devague.cli._commands import park as _park_cmd
    from devague.cli._commands import reject as _reject_cmd

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _new_cmd.register(sub)
    _capture_cmd.register(sub)
    _interrogate_cmd.register(sub)
    _confirm_cmd.register(sub)
    _reject_cmd.register(sub)
    _park_cmd.register(sub)
```

- [ ] **Step 7: Run tests — expect pass**

Run: `uv run pytest tests/test_cli_moves.py -q`
Expected: PASS (7 tests).

- [ ] **Step 8: Commit**

```bash
git add devague/cli/_commands/interrogate.py devague/cli/_commands/confirm.py devague/cli/_commands/reject.py devague/cli/_commands/park.py devague/cli/__init__.py tests/test_cli_moves.py
git commit -m "feat: add interrogate, confirm, reject, park moves"
```

---

## Task 8: `show` and `list` moves

**Files:** Create `devague/cli/_commands/show.py`, `devague/cli/_commands/list_frames.py`; Modify `devague/cli/__init__.py`; Modify `tests/test_cli_moves.py`.

- [ ] **Step 1: Append failing tests**

```python
def test_show_renders_frame_markdown(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["show"])
    assert rc == 0
    assert "# Announcement Frame" in capsys.readouterr().out


def test_show_json_emits_frame_dict(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["show", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["claims"][0]["kind"] == "announcement"


def test_list_marks_current(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "shipped-instant-specs" in out
    assert "*" in out  # current marker
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run pytest tests/test_cli_moves.py -k "show or list" -q`
Expected: FAIL — `show`/`list` not registered.

- [ ] **Step 3: Implement `devague/cli/_commands/show.py`**

```python
"""``devague show`` — render the current frame (markdown, or --json for raw state)."""

from __future__ import annotations

import argparse

from devague import render
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import to_dict


def cmd_show(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    if getattr(args, "json", False):
        emit_result(to_dict(frame), json_mode=True)
        return 0
    emit_result(render.render(frame, args.format), json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("show", help="Render the current frame.")
    p.add_argument("--format", default="frame-md", help="Renderer format (default: frame-md).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit the raw frame as JSON.")
    p.set_defaults(func=cmd_show)
```

- [ ] **Step 4: Implement `devague/cli/_commands/list_frames.py`**

```python
"""``devague list`` — list frames and mark the current one."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._output import emit_result


def cmd_list(args: argparse.Namespace) -> int:
    slugs = store.list_slugs()
    current = store.current_slug()
    if getattr(args, "json", False):
        emit_result({"frames": slugs, "current": current}, json_mode=True)
        return 0
    if not slugs:
        emit_result("no frames yet", json_mode=False)
        return 0
    lines = [("* " if s == current else "  ") + s for s in slugs]
    emit_result("\n".join(lines), json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("list", help="List frames.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_list)
```

- [ ] **Step 5: Register in `devague/cli/__init__.py`**

Add to the import block and register calls:

```python
    from devague.cli._commands import list_frames as _list_cmd
    from devague.cli._commands import show as _show_cmd
```

```python
    _show_cmd.register(sub)
    _list_cmd.register(sub)
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest tests/test_cli_moves.py -q`
Expected: PASS (all move tests).

- [ ] **Step 7: Commit**

```bash
git add devague/cli/_commands/show.py devague/cli/_commands/list_frames.py devague/cli/__init__.py tests/test_cli_moves.py
git commit -m "feat: add show and list moves"
```

---

## Task 9: `converge` and `export` moves

**Files:** Create `devague/cli/_commands/converge.py`, `devague/cli/_commands/export.py`; Modify `devague/cli/__init__.py`; Test `tests/test_cli_converge_export.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_converge_export.py
from __future__ import annotations

import json
from pathlib import Path

from devague import store
from devague.cli import main


def _converged(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])  # c1 announcement (confirmed)
    main(["interrogate", "c1", "--honesty", "announcement is true", "--origin", "user"])
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    # confirm an honesty condition on every confirmed spec-affecting claim
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])


def test_converge_reports_gaps_then_passes(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False and payload["missing"]

    _converged(monkeypatch, tmp_path)
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True


def test_export_blocked_until_converged(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])
    rc = main(["export"])
    assert rc == 1
    assert "has not converged" in capsys.readouterr().err


def test_export_writes_spec_when_converged(tmp_path, monkeypatch) -> None:
    _converged(monkeypatch, tmp_path)
    rc = main(["export"])
    assert rc == 0
    out = Path("docs/specs") / f"{store.current_slug()}.md"
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("# Specs in minutes")
    assert store.load(store.current_slug()).status == "exported"
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run pytest tests/test_cli_converge_export.py -q`
Expected: FAIL — `converge`/`export` not registered.

- [ ] **Step 3: Implement `devague/cli/_commands/converge.py`**

```python
"""``devague converge`` — evaluate the convergence gate."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.convergence import evaluate


def cmd_converge(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    result = evaluate(frame)
    if result.passed and frame.status == "drafting":
        frame.status = "converged"
        store.save(frame)
    if getattr(args, "json", False):
        emit_result({"passed": result.passed, "missing": result.missing}, json_mode=True)
    elif result.passed:
        emit_result("converged ✓", json_mode=False)
    else:
        emit_result(
            "not converged:\n" + "\n".join(f"  - {m}" for m in result.missing), json_mode=False
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("converge", help="Check whether the frame can export a spec.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_converge)
```

- [ ] **Step 4: Implement `devague/cli/_commands/export.py`**

```python
"""``devague export`` — write the buildable spec, only if the frame has converged."""

from __future__ import annotations

import argparse
from pathlib import Path

from devague import render, store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.convergence import evaluate

SPECS_DIR = Path("docs/specs")


def cmd_export(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    result = evaluate(frame)
    if not result.passed:
        raise DevagueError(
            EXIT_USER_ERROR,
            "frame has not converged; cannot export",
            "resolve: " + "; ".join(result.missing),
        )
    text = render.render(frame, args.format)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SPECS_DIR / f"{frame.slug}.md"
    out_path.write_text(text, encoding="utf-8")
    frame.status = "exported"
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"path": str(out_path), "format": args.format}, json_mode=True)
    else:
        emit_result(f"exported spec to {out_path}", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("export", help="Export the buildable spec (requires convergence).")
    p.add_argument("--format", default="spec-md", help="Renderer format (default: spec-md).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_export)
```

- [ ] **Step 5: Register in `devague/cli/__init__.py`**

Add to the import block and register calls:

```python
    from devague.cli._commands import converge as _converge_cmd
    from devague.cli._commands import export as _export_cmd
```

```python
    _converge_cmd.register(sub)
    _export_cmd.register(sub)
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest tests/test_cli_converge_export.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add devague/cli/_commands/converge.py devague/cli/_commands/export.py devague/cli/__init__.py tests/test_cli_converge_export.py
git commit -m "feat: add converge and export moves"
```

---

## Task 10: Real `learn` / `explain` bodies

**Files:** Modify `devague/cli/_commands/learn.py`, `devague/cli/_commands/explain.py`; Modify `tests/test_cli_stubs.py` (rename to `tests/test_cli_affordances.py`).

- [ ] **Step 1: Replace `tests/test_cli_stubs.py` with `tests/test_cli_affordances.py`**

```bash
git mv tests/test_cli_stubs.py tests/test_cli_affordances.py
```

Replace its contents with:

```python
"""Tests for the agent-affordance verbs: learn / explain."""

from __future__ import annotations

import json

import pytest

from devague.cli import main


def test_learn_describes_moves(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "working backwards" in out
    assert "capture" in out and "converge" in out


def test_learn_json_lists_moves(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "devague"
    assert "capture" in payload["moves"]


def test_explain_a_move(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "converge"])
    assert rc == 0
    assert "converge" in capsys.readouterr().out.lower()


def test_explain_unknown_move_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "nope"])
    assert rc == 1
    assert "unknown" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run pytest tests/test_cli_affordances.py -q`
Expected: FAIL — current stub bodies don't mention moves / `explain` takes no topic arg.

- [ ] **Step 3: Implement `devague/cli/_commands/learn.py`**

```python
"""``devague learn`` — teach the working-backwards method and the moves."""

from __future__ import annotations

import argparse

from devague import __version__
from devague.cli._output import emit_result

MOVES = {
    "new": "Start a frame from the announcement (pretend it shipped).",
    "capture": "Record and classify a claim (audience, after_state, boundary, ...).",
    "interrogate": "Pressure-test a claim: honesty conditions, hard questions, contradictions.",
    "confirm": "Confirm a claim or honesty condition (user-only — no fabricated rigor).",
    "reject": "Reject a claim or honesty condition.",
    "park": "Move uncertainty into first-class open vagueness instead of forcing an answer.",
    "converge": "Check whether the frame is solid enough to export a spec.",
    "export": "Write the buildable spec — only once the frame converges.",
    "show": "Render the Announcement Frame.",
    "list": "List frames.",
}

_TEXT = (
    "devague turns a vague idea into a buildable spec by working backwards.\n"
    "Start from the announcement, then build an Announcement Frame by capturing\n"
    "claims, interrogating them, parking what's still vague, and converging.\n"
    "The arc — rough capture -> pressure-test -> convergence -> spec — emerges\n"
    "from the moves; it is not a fixed wizard. You (the agent) choose the next\n"
    "move; devague tracks state. LLM-proposed claims and honesty conditions stay\n"
    "'proposed' until the user confirms them.\n\nMoves:\n"
    + "\n".join(f"  {name:<11} {desc}" for name, desc in MOVES.items())
)


def cmd_learn(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        emit_result(
            {"tool": "devague", "version": __version__, "moves": list(MOVES), "summary": _TEXT},
            json_mode=True,
        )
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("learn", help="Teach devague's working-backwards method.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
```

- [ ] **Step 4: Implement `devague/cli/_commands/explain.py`**

```python
"""``devague explain <move>`` — print docs for a single move."""

from __future__ import annotations

import argparse

from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._commands.learn import MOVES
from devague.cli._output import emit_result


def cmd_explain(args: argparse.Namespace) -> int:
    desc = MOVES.get(args.move)
    if desc is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown move: {args.move}",
            f"available moves: {', '.join(MOVES)}",
        )
    if getattr(args, "json", False):
        emit_result({"move": args.move, "description": desc}, json_mode=True)
    else:
        emit_result(f"{args.move}: {desc}", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("explain", help="Explain a devague move.")
    p.add_argument("move", help="A move name (e.g. converge).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_explain)
```

- [ ] **Step 5: Run tests — expect pass**

Run: `uv run pytest tests/test_cli_affordances.py -q`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add devague/cli/_commands/learn.py devague/cli/_commands/explain.py tests/test_cli_affordances.py
git commit -m "feat: real learn/explain bodies teaching the working-backwards moves"
```

---

## Task 11: Full-suite verification, CLAUDE.md, CHANGELOG

**Files:** Modify `CLAUDE.md`, `CHANGELOG.md`.

- [ ] **Step 1: Run the whole gate**

```bash
uv run pytest -n auto --cov=devague --cov-report=term -q
uv run flake8 --config=.flake8 devague/ tests/
uv run black --check devague/ tests/ && uv run isort --check-only --profile black devague/ tests/
markdownlint-cli2 "**/*.md"
```

Expected: all tests pass; coverage ≥ 70%; flake8/black/isort/markdownlint clean. If black or isort report changes, run them without `--check`, then re-run pytest.

- [ ] **Step 2: End-to-end smoke (manual)**

From the repo root (so `uv run` resolves the project), exercise the chain, then
clean up the artifacts it writes:

```bash
uv run devague new "Specs in minutes"
uv run devague capture --kind audience "developers" --origin user
uv run devague converge      # reports the remaining gaps
rm -rf .devague docs/specs   # cleanup — these are smoke-test artifacts
```

Expected: `new` creates `.devague/frames/specs-in-minutes.json`; `converge`
lists the remaining gaps.

- [ ] **Step 3: Update `CLAUDE.md` Status + add a working-backwards section**

In `CLAUDE.md`, update **Status** to note the engine has landed (moves `new`/`capture`/`interrogate`/`confirm`/`reject`/`park`/`converge`/`export`/`show`/`list`), and add a short **Working-backwards method** section: the agent drives the deterministic CLI, starts from the announcement, always routes honesty conditions through user `confirm`, and only `export`s after `converge` passes. Reference `docs/superpowers/specs/2026-05-23-devague-working-backwards-design.md`.

- [ ] **Step 4: Prepend a CHANGELOG entry**

```markdown
## [0.3.0] - 2026-05-23

### Added

- The working-backwards engine: a deterministic Frame state machine
  (`devague/frame.py`, `store.py`, `convergence.py`) and the moves
  `new` / `capture` / `interrogate` / `confirm` / `reject` / `park` /
  `converge` / `export` / `show` / `list`, plus a pluggable renderer
  registry (`frame-md`, `spec-md`). `export` is gated on convergence;
  LLM-proposed claims and honesty conditions require user confirmation.
- Real `learn` / `explain` bodies teaching the method and the moves.
```

Bump `pyproject.toml` `version` to `0.3.0`.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md CHANGELOG.md pyproject.toml
git commit -m "docs: document the working-backwards engine; bump to 0.3.0"
```

---

## Self-review

- **Spec coverage:** Frame model (Task 1), storage decision `.devague/frames/<slug>.json` (Task 2), convergence gate criteria (Task 3), pluggable renderer seam + frame/spec markdown (Task 4), all moves incl. confirm/reject/park (Tasks 6–9), full state machine v1 (all moves present), spec export to `docs/specs/` gated on convergence (Task 9), real learn/explain (Task 10). ✓
- **Placeholders:** none — every code step has complete code; every run step has a command + expected result. ✓
- **Type consistency:** `Frame`/`Claim`/`Vagueness`/`HonestyCondition`/`HardQuestion`, `add_claim`/`add_honesty`/`add_hard_question`/`add_vagueness`/`find_claim`/`find_honesty`/`set_status`, `to_dict`/`from_dict`, `store.save`/`load`/`current_slug`/`slugify`/`list_slugs`, `evaluate`/`ConvergenceResult`, `render.render`/`formats`/`register`, `resolve` — names used identically across tasks. CLI verb modules each expose `register(sub)` + `cmd_*`, matching the existing chassis. ✓
- **Deferred (per spec):** extra output modalities, automated contradiction detection, multi-frame ergonomics, mesh delegation — not in these tasks, by design. ✓

## Execution boundary

One PR (or split Tasks 1–4 "engine core" and Tasks 6–11 "CLI moves" into two PRs if review prefers smaller diffs). Open via the `cicd` skill once Task 11 Step 1 is green.
