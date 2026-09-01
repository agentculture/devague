"""Next-move hints — a small, overrideable stderr nudge after every successful
verb (issue next-leg-hints, task t1).

Motivation: the operator (an LLM agent driving the CLI move by move) has to
reconstruct "what's next?" from `CLAUDE.md`/skill docs on every turn. A
one-line stderr hint after each successful command closes that loop cheaply,
without touching stdout (agents parsing structured output must see it
byte-identical) and without the CLI orchestrating anything (#20) — it only
*names* the next move; it never runs it.

Emission is centralized: :func:`emit_next_hint` is called exactly once, from
:func:`devague.cli._dispatch`, after ``args.func(args)`` returns success.
No command module in :mod:`devague.cli._commands` calls it or
:func:`devague.cli._output.emit_diagnostic` for this purpose — grepping that
package for a hint call site should come up empty (t1 acceptance criterion 2).

Vocabulary
----------
Every verb falls into one of three buckets:

- **Exempt** — ``status`` and ``plan status`` (and the bare ``plan`` group
  parser, which only prints help and mutates nothing): these already answer
  "what's next?" as their entire purpose, so a hint after them would be a
  pointless echo.
- **Leg-ending** — a verb whose successful run closes out one of the
  eight-leg flow's legs (``scope`` -> ``think`` -> ``challenge`` ->
  ``spec-to-plan`` -> ``assign-to-workforce`` -> ``deviate`` ->
  ``validate-delivery`` -> ``summarize-delivery``). These hint the next leg
  by name (a skill, or the concrete follow-on command) instead of the
  generic within-leg default.
- **Within-leg** — everything else: hints ``devague status`` (flat verbs) or
  ``devague plan status`` (plan subverbs), the same read-only "where do
  things stand" move the `think` / `spec-to-plan` skills already lean on.

``deviate`` / ``evidence`` / ``delta`` are multi-mode verbs — one CLI verb
covers filing a new record, ``--list``-ing existing ones, and
``--confirm``/``--reject`` adjudication (r1, the open design point this task
owns). Decision: **only a successful filing run is leg-ending.** Listing or
adjudicating an existing record does not, by itself, mean the validate-
delivery leg is done — the operator may still have more evidence/deltas to
file, or more deviations to adjudicate, before the run is genuinely ready to
hand off to ``devague summary`` / ``/summarize-delivery``. Hinting the next
leg on every ``--list`` would be presumptuous (and noisy: a status-checking
loop would see the "go to the next leg" hint on every poll). So ``--list``
and ``--confirm``/``--reject`` runs of these three verbs fall through to the
ordinary within-leg default, while a bare positional/record-flag filing run
gets the leg-ending text. This mirrors how each command module itself tells
filing apart from listing/adjudicating (``args.what`` for ``deviate``,
``args.obligation`` for ``evidence``, ``args.kind`` for ``delta`` — see
:func:`_filed`).

One refinement on that (PR #110 review): an ``--origin llm`` filing lands
``proposed``, and both the ``/deviate`` and ``/validate-delivery`` skills
require the human ``--confirm`` *before* the leg advances. Such a run
therefore hints that adjudication rather than the next leg — recording is
not approval, and the hint must not nudge past a human gate.

Config lives in :mod:`devague.cli._hint_config` (t2): a global on/off
(``DEVAGUE_HINTS`` env, or ``[tool.devague] hints = false`` in the consuming
repo's ``pyproject.toml``) and per-verb replacement text
(``[tool.devague.hints]``). That module is consulted only from
:func:`emit_next_hint` below, at emission-decision time — the pure
:func:`hint_for` table lookup above is unaffected by config, so its existing
exhaustive parametrized tests keep pinning the *default* text unconditionally.
"""

from __future__ import annotations

import argparse

from devague.cli import _hint_config
from devague.cli._output import emit_diagnostic

_NEXT_PREFIX = "next: "

# Flat (top-level) verbs whose successful run ends a leg — see module
# docstring. Anything not listed here (and not exempt) gets `_FLAT_DEFAULT`.
_FLAT_LEG_END: dict[str, str] = {
    "export": "run /challenge or /spec-to-plan",
    "summary": "run /summarize-delivery",
    "today": "commit docs/current-spec.md",
}

# deviate / evidence / delta: leg-ending text used ONLY when the call just
# filed a new record (r1 decision above) — never on --list/--confirm/--reject.
_MULTI_MODE_LEG_END: dict[str, str] = {
    "deviate": "resume the fan-out",
    "evidence": "run devague summary and /summarize-delivery",
    "delta": "run devague summary and /summarize-delivery",
}

# `devague plan <subverb>` keys, namespaced "plan:<subverb>" per the brief.
# The same three verbs when the filing run was `--origin llm`: the record lands
# `proposed`, not approved, so the next move is the human adjudication the
# `/deviate` and `/validate-delivery` skills both require before the leg
# advances — hinting the next leg here would nudge past that gate (PR #110
# review). Adjudicating (`--confirm`/`--reject`) is still not itself leg-ending;
# it falls through to the within-leg default, per r1.
_MULTI_MODE_PROPOSED: dict[str, str] = {
    "deviate": "get the user's devague deviate --confirm, then resume the fan-out",
    "evidence": "get the user's devague evidence --confirm, then run devague summary",
    "delta": "get the user's devague delta --confirm, then run devague summary",
}

_PLAN_LEG_END: dict[str, str] = {
    "plan:export": "run /assign-to-workforce",
    "plan:waves": "run /assign-to-workforce",
}

_FLAT_DEFAULT = "run devague status"
_PLAN_DEFAULT = "run devague plan status"

# Verbs that never get a hint at all.
_EXEMPT_FLAT = {"status"}
_EXEMPT_PLAN_SUBVERBS = {"status"}


def _filed(command: str, args: argparse.Namespace) -> bool:
    """True iff a multi-mode verb's *filing* path just ran (r1), as opposed to
    its ``--list``/``--confirm``/``--reject`` path. Mirrors each command
    module's own mode discriminator (never re-derives the logic — just reads
    the same namespace attribute the handler itself branched on) so the hint
    always agrees with what the command actually did:

    - ``deviate``: filing sets the positional ``what`` (see
      :func:`devague.cli._commands.deviate.cmd_deviate`).
    - ``evidence``: filing requires ``--obligation`` (see
      :func:`devague.cli._commands.evidence.cmd_evidence`).
    - ``delta``: filing requires ``--kind`` (see
      :func:`devague.cli._commands.delta.cmd_delta`).
    """
    if command == "deviate":
        return bool(getattr(args, "what", None))
    if command == "evidence":
        return bool(getattr(args, "obligation", None))
    if command == "delta":
        return bool(getattr(args, "kind", None))
    return False


def hint_for(args: argparse.Namespace) -> str | None:
    """The next-move hint text for a successfully dispatched command, or
    ``None`` if this command is exempt from hinting.

    Reads only ``args.command`` / ``args.plan_command`` (and, for the three
    multi-mode verbs, the same mode-discriminating attribute each handler
    already reads) — never mutates ``args``, never touches any store.
    """
    command = getattr(args, "command", None)
    if command is None:
        return None
    if command == "plan":
        plan_command = getattr(args, "plan_command", None)
        # A bare `devague plan` (no subverb) only prints help; nothing
        # happened to hint a next move about.
        if plan_command is None or plan_command in _EXEMPT_PLAN_SUBVERBS:
            return None
        key = f"plan:{plan_command}"
        return _PLAN_LEG_END.get(key, _PLAN_DEFAULT)
    if command in _EXEMPT_FLAT:
        return None
    if command in _MULTI_MODE_LEG_END and _filed(command, args):
        proposed = getattr(args, "origin", None) == "llm"
        return (_MULTI_MODE_PROPOSED if proposed else _MULTI_MODE_LEG_END)[command]
    if command in _FLAT_LEG_END:
        return _FLAT_LEG_END[command]
    return _FLAT_DEFAULT


def _key_for(args: argparse.Namespace) -> str | None:
    """The same key shape :data:`_FLAT_LEG_END` / :data:`_PLAN_LEG_END` (and
    :mod:`devague.cli._hint_config`'s per-verb override table) address —
    ``None`` when there is nothing to key an override lookup on.
    """
    command = getattr(args, "command", None)
    if command is None:
        return None
    if command == "plan":
        plan_command = getattr(args, "plan_command", None)
        return f"plan:{plan_command}" if plan_command is not None else None
    return command


def emit_next_hint(args: argparse.Namespace) -> None:
    """Emit the one-line ``next: ...`` stderr hint for a successful dispatch.

    Called exactly once, from :func:`devague.cli._dispatch` — never from a
    command module (t1 acceptance criterion 2). A no-op for an exempt verb
    or when hints are disabled via :mod:`devague.cli._hint_config`
    (``DEVAGUE_HINTS`` or ``[tool.devague] hints = false``, t2). A per-verb
    override under ``[tool.devague.hints]`` replaces the default text
    verbatim; an exempt verb has no hint to override in the first place, so
    the config lookups below only run once there is text to act on.
    """
    text = hint_for(args)
    if text is None:
        return
    if not _hint_config.hints_enabled():
        return
    key = _key_for(args)
    if key is not None:
        override = _hint_config.override_text(key)
        if override is not None:
            text = override
    emit_diagnostic(f"{_NEXT_PREFIX}{text}")
