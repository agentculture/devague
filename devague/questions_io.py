"""Pending-decision working state: ``.devague/questions/<slug>.md`` (CLI-owned).

A durable, **uncommitted** list of open questions / pending user decisions raised
while working a frame (issue #14/#17, decision c20). The CLI owns the markdown
format so it round-trips (``parse`` ⇄ ``render``). A resolved decision is applied
back into the frame with the normal moves (e.g. ``devague capture --kind decision
"<the decision>"`` then ``devague confirm``); resolving here only records it.
"""

from __future__ import annotations

import re

# Bounded whitespace only (single literal spaces, rest stripped in parse) so the
# pattern is linear — no \s+…\s+…\.* shape that trips ReDoS heuristics.
_LINE = re.compile(r"^- \[(?P<mark>[ x])\] `(?P<id>q\d+)`:(?P<rest>.*)$")
_DECIDED = " — decided: "

_BANNER = (
    "> **Working state — not committed by default.** Open questions / pending "
    "decisions for this frame. Apply a decision into the frame with the normal "
    'moves (e.g. `devague capture --kind decision "…"` then `devague confirm`), '
    "then mark it resolved here with `devague question --resolve <id>`."
)


def parse(text: str) -> list[dict]:
    items: list[dict] = []
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        rest = m.group("rest")
        resolved = m.group("mark") == "x"
        decision = None
        if resolved and _DECIDED in rest:
            # render() appends the decided tail last, so split from the right —
            # otherwise a question whose *text* contains the delimiter corrupts.
            rest, decision = rest.rsplit(_DECIDED, 1)
        items.append(
            {"id": m.group("id"), "text": rest.strip(), "resolved": resolved, "decision": decision}
        )
    return items


def next_id(items: list[dict]) -> str:
    nums = [int(i["id"][1:]) for i in items if i["id"][1:].isdigit()]
    return f"q{(max(nums) + 1) if nums else 1}"


def render(slug: str, items: list[dict]) -> str:
    out = [f"# Pending decisions — {slug}", "", _BANNER, ""]
    open_items = [i for i in items if not i["resolved"]]
    done_items = [i for i in items if i["resolved"]]
    out += ["## Open", ""]
    out += [f"- [ ] `{i['id']}`: {i['text']}" for i in open_items] or ["None."]
    out += [""]
    if done_items:
        out += ["## Resolved", ""]
        for i in done_items:
            tail = f"{_DECIDED}{i['decision']}" if i["decision"] else ""
            out.append(f"- [x] `{i['id']}`: {i['text']}{tail}")
        out += [""]
    return "\n".join(out).rstrip() + "\n"
