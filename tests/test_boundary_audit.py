"""t14 boundary audit: no LLM calls, no subagent spawning, no worktree management.

The devague package is deterministic (#20): the CLI records and evaluates state,
never orchestrates. This audit is the grep evidence, committed as a test so a
future import can't drift past it. Network imports are separately guarded by
test_offline.py; bandit runs in CI (security-checks workflow).

Teaching *text* may mention worktrees or fan-out — the audit guards behavior
(imports and process-spawning calls), not vocabulary.
"""

from __future__ import annotations

import re
from pathlib import Path

# LLM/SDK clients and process-spawning machinery have no business in devague/.
_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(subprocess|pty|multiprocessing|anthropic|openai)\b",
    re.MULTILINE,
)
# os-level process spawning (os.system, os.popen, os.exec*, os.spawn*, os.fork).
_FORBIDDEN_OS_CALL = re.compile(r"\bos\.(system|popen|exec\w*|spawn\w*|fork)\s*\(")


def _package_sources() -> list[Path]:
    files = sorted(Path("devague").rglob("*.py"))
    assert files, "audit must run from the repo root"
    return files


def test_no_llm_or_process_spawning_imports() -> None:
    offenders = [
        f"{py}: {m.group(0).strip()}"
        for py in _package_sources()
        if (m := _FORBIDDEN_IMPORT.search(py.read_text(encoding="utf-8")))
    ]
    assert offenders == [], f"forbidden import in devague/: {offenders}"


def test_no_os_level_process_spawning() -> None:
    offenders = [
        f"{py}: {m.group(0)}"
        for py in _package_sources()
        if (m := _FORBIDDEN_OS_CALL.search(py.read_text(encoding="utf-8")))
    ]
    assert offenders == [], f"process-spawning call in devague/: {offenders}"
