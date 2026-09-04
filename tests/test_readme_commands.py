"""Pin ``README.md`` to the shipped CLI and to its own structural promises.

Every ``devague ...`` line inside a fenced ``bash`` block is validated against
the *real* argparse parser the CLI builds (``devague.cli._build_parser``, used
in-process — no ``subprocess`` fallback needed since the factory is exposed):
the top-level verb must exist as a subparser, a nested ``plan <sub>`` must
exist as a sub-subparser, and every ``--flag`` token on the line must be a
known option of that (sub)parser.

Fenced ``console`` blocks are *captured output*, not input — README.md uses
them to show a terminal session (``$ devague ...`` commands interleaved with
their captured output and ``next: ...`` hints). Per the brief, those command
lines are not re-validated against the parser here; the module only asserts
each such block opens with a comment naming the devague version that produced
the capture, so a stale capture is at least flagged as stale.

Follows the shape of ``tests/test_spec_to_plan_skill.py``: module-level
``REPO_ROOT``, read the file, plain asserts with messages — no fixtures.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from devague.cli import _build_parser

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

_FENCE_RE = re.compile(r"^```(?P<lang>\S+)\n(?P<body>.*?)^```\s*$", re.MULTILINE | re.DOTALL)

_EXPECTED_H2 = [
    "## What devague does",
    "## Why it works",
    "## How to use it",
    "## Impact: what lands where",
]


def _readme_text() -> str:
    assert README.is_file(), f"missing {README}"
    return README.read_text(encoding="utf-8")


def _fenced_blocks(text: str, lang: str) -> list[str]:
    """Return the raw bodies of every ```<lang> fenced block, in order."""
    return [m.group("body") for m in _FENCE_RE.finditer(text) if m.group("lang") == lang]


def _devague_command_lines(bash_block: str) -> list[str]:
    """Extract logical ``devague ...`` command lines from a ``bash`` fence body.

    Handles trailing ``# comment`` (via ``shlex`` comment stripping), ``...``
    elision lines (skipped — they are not commands), and ``\\``-continued
    lines (joined before tokenizing).
    """
    commands: list[str] = []
    pending = ""
    for raw_line in bash_block.splitlines():
        line = raw_line.strip()
        if pending:
            line = f"{pending} {line}"
            pending = ""
        if not line or line == "...":
            continue
        if line.endswith("\\"):
            pending = line[:-1].strip()
            continue
        if not line.startswith("devague"):
            continue
        commands.append(line)
    assert not pending, f"unterminated line continuation in block: {bash_block!r}"
    return commands


def _tokenize(command_line: str) -> list[str]:
    """Split a ``devague ...`` line into tokens, stripping a trailing comment."""
    return shlex.split(command_line, comments=True)


def _find_subparsers_action(parser) -> "argparse._SubParsersAction | None":  # noqa: F821
    for action in parser._actions:  # noqa: SLF001 - argparse offers no public walk API
        if (
            action.choices
            and hasattr(action, "choices")
            and action.__class__.__name__ == ("_SubParsersAction")
        ):
            return action
    return None


def _known_flags(parser) -> set[str]:
    return set(parser._option_string_actions.keys())  # noqa: SLF001


def _assert_line_matches_parser(tokens: list[str], top_sub, top_parser) -> None:
    assert tokens, "empty command line"
    assert tokens[0] == "devague", f"expected 'devague', got {tokens[0]!r}"
    rest = tokens[1:]
    assert rest, f"missing verb: {tokens!r}"
    verb = rest[0]
    if verb.startswith("--"):
        # A bare top-level option (e.g. `devague --version`), not a subverb.
        known = _known_flags(top_parser)
        flag = verb.split("=", 1)[0]
        assert flag in known, f"unknown top-level flag {flag!r} in {' '.join(tokens)!r}"
        return
    assert verb in top_sub.choices, f"unknown verb {verb!r} in {' '.join(tokens)!r}"
    verb_parser = top_sub.choices[verb]

    body = rest[1:]
    target_parser = verb_parser
    if verb == "plan":
        assert body, f"'devague plan' needs a subverb: {' '.join(tokens)!r}"
        nested_sub = _find_subparsers_action(verb_parser)
        assert nested_sub is not None, "'plan' parser has no nested subparsers"
        subverb = body[0]
        assert (
            subverb in nested_sub.choices
        ), f"unknown 'devague plan' subverb {subverb!r} in {' '.join(tokens)!r}"
        target_parser = nested_sub.choices[subverb]
        body = body[1:]

    known = _known_flags(target_parser)
    for token in body:
        if token.startswith("--"):
            flag = token.split("=", 1)[0]
            assert flag in known, (
                f"unknown flag {flag!r} for 'devague "
                f"{verb}{'' if verb != 'plan' else ' ' + subverb}' "
                f"in line {' '.join(tokens)!r} (known: {sorted(known)})"
            )


def _bash_command_lines() -> list[str]:
    text = _readme_text()
    lines: list[str] = []
    for block in _fenced_blocks(text, "bash"):
        lines.extend(_devague_command_lines(block))
    return lines


# ── acceptance criterion 1: every devague line in a ```bash fence parses ──────


def test_every_readme_bash_devague_line_matches_the_shipped_cli() -> None:
    parser = _build_parser()
    top_sub = _find_subparsers_action(parser)
    assert top_sub is not None, "top-level devague parser has no subparsers"

    lines = _bash_command_lines()
    assert lines, "expected at least one 'devague ...' line inside a ```bash fence"

    misses: list[str] = []
    for line in lines:
        tokens = _tokenize(line)
        try:
            _assert_line_matches_parser(tokens, top_sub, parser)
        except AssertionError as exc:  # collect every miss for one readable report
            misses.append(f"{line!r}: {exc}")

    assert not misses, "README.md bash commands out of sync with the shipped CLI:\n" + "\n".join(
        misses
    )


def test_at_least_one_bash_command_line_was_actually_checked() -> None:
    # A regression guard against the extractor silently matching nothing (which
    # would make the criterion-1 test vacuously pass).
    assert len(_bash_command_lines()) >= 5


# ── acceptance criterion 2: structural promises ────────────────────────────


def test_exactly_one_mermaid_fence() -> None:
    text = _readme_text()
    assert len(_fenced_blocks(text, "mermaid")) == 1


def test_eight_leg_numbered_list_follows_the_mermaid_fence_in_flow_order() -> None:
    text = _readme_text()
    mermaid_match = next(m for m in _FENCE_RE.finditer(text) if m.group("lang") == "mermaid")
    after = text[mermaid_match.end() :]

    numbered = re.findall(r"^(\d+)\.\s+\*\*`([^`]+)`\*\*", after, re.MULTILINE)
    numbered = numbered[:8]
    assert len(numbered) == 8, f"expected 8 numbered legs directly after mermaid, got {numbered}"

    expected_order = list(range(1, 9))
    actual_order = [int(n) for n, _ in numbered]
    assert actual_order == expected_order, f"legs out of order: {numbered}"

    expected_legs = [
        "/scope",
        "/think",
        "/challenge",
        "/spec-to-plan",
        "/assign-to-workforce",
        "/deviate",
        "/validate-delivery",
        "/summarize-delivery",
    ]
    actual_legs = [leg for _, leg in numbered]
    assert actual_legs == expected_legs, f"legs mismatch: {actual_legs}"

    # The list must appear with no other numbered list intervening — i.e. it is
    # the first "N. " content encountered right after the mermaid fence, aside
    # from blank lines.
    before_first_item = after[: after.index("1. **`/scope`**")]
    assert before_first_item.strip() == "", (
        "non-blank content between the mermaid fence and the eight-leg list: "
        f"{before_first_item!r}"
    )


_VERSION_COMMENT_RE = re.compile(r"^#\s*devague\s+\d+\.\d+\.\d+\s*$")


def test_every_console_capture_block_opens_with_a_devague_version_comment() -> None:
    text = _readme_text()
    console_blocks = _fenced_blocks(text, "console")
    assert console_blocks, "expected at least one ```console capture block"
    for block in console_blocks:
        first_line = block.splitlines()[0].strip() if block.splitlines() else ""
        assert _VERSION_COMMENT_RE.match(first_line), (
            "```console block does not open with a '# devague X.Y.Z' comment: " f"{first_line!r}"
        )


def test_exactly_three_console_capture_blocks() -> None:
    text = _readme_text()
    assert len(_fenced_blocks(text, "console")) == 3


def test_h2_sections_appear_in_order() -> None:
    text = _readme_text()
    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    assert headings == _EXPECTED_H2, f"H2 sections out of order or mismatched: {headings}"
