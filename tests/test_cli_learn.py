"""Tests for the `devague learn` command — teaches the working-backwards method."""

from __future__ import annotations

import json

import pytest

from devague.cli import main


def test_learn_documents_assign_to_workforce_invocation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The learn output contains assign-to-workforce guidance for fanning out
    a converged plan's waves to a workforce.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    # Must mention the assign-to-workforce concept.
    assert "assign-to-workforce" in out
    # Must mention when to fan out: converged plans with parallel waves.
    assert "converged plan" in out or "convergence" in out
    assert "wave" in out or "parallel" in out
    # Must mention the three human gates: spec, implementation split plan, final PR.
    assert "gate" in out or "spec" in out
    # Must mention worktree isolation for safety.
    assert "worktree" in out


def test_learn_json_includes_assign_to_workforce_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The --json payload carries assign-to-workforce guidance as a distinct section."""
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # Must include a documented section about assign-to-workforce.
    assert "assign_to_workforce" in payload or "assign-to-workforce" in str(payload).lower()


# The six origin skills, in six-leg workflow order (devague#53 esd).
SKILL_NAMES = (
    "scope",
    "think",
    "spec-to-plan",
    "assign-to-workforce",
    "deviate",
    "summarize-delivery",
)

# Method-only skills ship a SKILL.md and NO scripts/<name>.sh resolver — they
# invoke the devague CLI directly. The other three are CLI-driving and DO ship
# a scripts/<name>.sh resolver.
METHOD_ONLY_NAMES = ("scope", "deviate", "summarize-delivery")
CLI_DRIVING_NAMES = ("think", "spec-to-plan", "assign-to-workforce")


def test_bare_learn_includes_skills_authoring_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Bare `learn` keeps the method overview AND appends the authoring section."""
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    # Method overview is still present (the canonical first question).
    assert "What's the announcement?" in out
    # Authoring section is appended.
    assert "Authoring your operator skills" in out
    for name in SKILL_NAMES:
        assert name in out


def test_learn_skills_teaches_authoring_recipe(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`learn skills` emits the recipe, the consent rules, and all six skills."""
    rc = main(["learn", "skills"])
    assert rc == 0
    out = capsys.readouterr().out
    # Recipe: file layout + frontmatter incl. the culture-backend `type:` gotcha.
    assert "SKILL.md" in out
    assert "scripts/" in out
    assert "type: command" in out
    # Consent + no-clobber language is present.
    lower = out.lower()
    assert "permission" in lower
    assert "overwrite" in lower or "clobber" in lower
    for name in SKILL_NAMES:
        assert name in out
    # The method-only structural nuance is taught, not silently dropped.
    assert "method-only" in lower


def test_learn_skills_no_stale_three_wording(capsys: pytest.CaptureFixture[str]) -> None:
    """The recipe no longer claims devague ships three operator skills."""
    rc = main(["learn", "skills"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "driven by three operator skills" not in out
    assert "the three skills:" not in out
    assert "source urls of all three" not in out
    # All six names are present somewhere in the rendered text.
    for name in SKILL_NAMES:
        assert name in out


def test_learn_skills_all_lists_canonical_source_urls(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`learn skills:all` lists every skill with its canonical source URLs —
    CLI-driving skills get a script URL, method-only skills do not.
    """
    rc = main(["learn", "skills:all"])
    assert rc == 0
    out = capsys.readouterr().out
    for name in SKILL_NAMES:
        assert f"/{name}/SKILL.md" in out
    for name in CLI_DRIVING_NAMES:
        assert f"/{name}/scripts/{name}.sh" in out
    for name in METHOD_ONLY_NAMES:
        assert f"/{name}/scripts/{name}.sh" not in out
    assert "method-only" in out.lower()


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_learn_skills_one_is_focused(name: str, capsys: pytest.CaptureFixture[str]) -> None:
    """`learn skills:<name>` focuses on a single skill and shows its source
    (a script URL for CLI-driving skills, none for method-only skills).
    """
    rc = main(["learn", f"skills:{name}"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"/{name}/SKILL.md" in out
    if name in METHOD_ONLY_NAMES:
        assert f"/{name}/scripts/{name}.sh" not in out
        assert "method-only" in out.lower()
    else:
        assert f"/{name}/scripts/{name}.sh" in out
    # The other skills' source blocks are not emitted.
    others = [n for n in SKILL_NAMES if n != name]
    for other in others:
        assert f"/{other}/SKILL.md" not in out


def test_learn_unknown_topic_errors(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown learn topic exits non-zero with a hint and no traceback."""
    rc = main(["learn", "bogus"])
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "unknown learn topic" in err
    assert "hint:" in err
    assert "traceback" not in err


def test_learn_unknown_skill_errors(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown skill name under `skills:` exits non-zero with the valid names."""
    rc = main(["learn", "skills:bogus"])
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "unknown skill" in err
    for name in SKILL_NAMES:
        assert name in err


@pytest.mark.parametrize(
    "topic",
    [
        "skills",
        "skills:all",
        "skills:think",
        "skills:scope",
        "skills:deviate",
        "skills:summarize-delivery",
    ],
)
def test_learn_skills_json_payload(topic: str, capsys: pytest.CaptureFixture[str]) -> None:
    """`learn skills* --json` carries a structured authoring payload, and shares
    the bare payload's tool/version identity (one schema across the family).
    Method-only skills carry no `script_raw` key; CLI-driving skills do.
    """
    rc = main(["learn", topic, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # Same identifying metadata as bare `learn --json` — no schema divergence.
    assert payload["tool"] == "devague"
    assert payload["version"]
    assert payload["topic"] == topic
    assert "consent" in payload and payload["consent"]
    assert "authoring" in payload
    # Each skill carries its canonical raw-source URLs; method-only skills
    # carry no script_raw (there is no script to link to).
    for s in payload["operator_skills"]:
        assert s["skill_md_raw"].endswith(f"/{s['name']}/SKILL.md")
        if s["name"] in METHOD_ONLY_NAMES:
            assert s.get("method_only") is True
            assert "script_raw" not in s
        else:
            assert s.get("method_only") is False
            assert s["script_raw"].endswith(f"/{s['name']}/scripts/{s['name']}.sh")


def test_bare_learn_json_has_skills_key(capsys: pytest.CaptureFixture[str]) -> None:
    """The bare `learn --json` payload now carries a `skills` section with all six."""
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "skills" in payload
    assert {s["name"] for s in payload["skills"]["operator_skills"]} == set(SKILL_NAMES)
