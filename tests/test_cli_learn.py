"""Tests for the `devague learn` command — teaches the working-backwards method."""

from __future__ import annotations

import json
import re

import pytest

from devague.cli import main
from devague.cli._commands.learn import LAPSE_CODES_FOR_REVIEW, MOVES, REVIEW_COMMANDS


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


def test_learn_names_repo_owned_worktree_root(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`devague learn` teaches where fan-out worktrees live: one repo-owned root
    beside the repo directory (`.worktrees.<repo-name>`), never a shared
    `../worktrees/` (which collides across repos and reads as deletable scratch)
    and never inside the repo (where `git add -A` / `git clean -fdx` reach it).
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert ".worktrees.<repo-name>" in out
    # The rationale must survive, not just the path: this is why the root is
    # repo-owned rather than shared.
    lowered = out.lower()
    assert "../worktrees/" in lowered
    assert "git add -a" in lowered or "in-repo" in lowered


def test_learn_worktree_snippet_is_self_contained(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The taught shell snippet must define `repo_root` before using it (#89).

    An operator copies this verbatim. With `repo_root` undefined the snippet
    does not fail loudly — `$(dirname "")` is `.` and `$(basename "")` is
    empty, so `wt_root` silently becomes `./.worktrees.`: a relative, in-repo
    path with no repo name, i.e. exactly the layout this guidance forbids.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "wt_root=" in out, "guidance should teach the wt_root snippet"
    # Wherever wt_root is derived from repo_root, repo_root must be defined.
    assert "repo_root=$(git rev-parse --show-toplevel)" in out


def test_learn_json_includes_assign_to_workforce_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The --json payload carries assign-to-workforce guidance as a distinct section."""
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # Must include a documented section about assign-to-workforce.
    assert "assign_to_workforce" in payload or "assign-to-workforce" in str(payload).lower()


def test_learn_names_park_resolve_close_out(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` names the `park --resolve` close-out move wherever it
    teaches `park` — the fix for issues 45/55/57/60 (a decided blocking park
    must not read as a permanent dead end).
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "park --resolve" in out
    assert "--decision" in out


def test_plan_learn_names_risk_resolve_close_out(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague plan learn` names the `risk --resolve` close-out move — the
    plan-side twin of `park --resolve`.
    """
    rc = main(["plan", "learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--resolve" in out
    assert "--decision" in out
    assert "risk" in out


# The eight origin skills, in eight-leg workflow order (devague#73, bvts t14 —
# `validate-delivery` is the seventh leg, between `deviate` and
# `summarize-delivery`).
SKILL_NAMES = (
    "scope",
    "think",
    "challenge",
    "spec-to-plan",
    "assign-to-workforce",
    "deviate",
    "validate-delivery",
    "summarize-delivery",
)

# Method-only skills ship a SKILL.md and NO scripts/<name>.sh resolver — they
# invoke the devague CLI directly. The other three are CLI-driving and DO ship
# a scripts/<name>.sh resolver.
METHOD_ONLY_NAMES = (
    "scope",
    "challenge",
    "deviate",
    "validate-delivery",
    "summarize-delivery",
)
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
        "skills:challenge",
        "skills:deviate",
        "skills:validate-delivery",
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
    assert "consent" in payload
    assert payload["consent"]
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


# --- Behavioral validation: obligations, evidence, deltas, strength ladder, today ---


def test_learn_teaches_obligation_lifecycle(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` teaches planting obligations on both the think and plan
    legs, and that they land 'proposed' under --origin llm like every other
    LLM-proposed record.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "oblige" in out
    assert "plan oblige" in out
    lowered = out.lower()
    assert "proposed" in lowered


def test_learn_teaches_agent_side_test_run(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` teaches that behavioral tests run agent-side, never
    inside the devague CLI itself (issue #20).
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "agent-side" in out
    assert "validate-delivery" in out


def test_learn_teaches_evidence_verbatim_outcomes(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` teaches that a failing evidence outcome is filed as a
    fail, never smoothed into a pass or omitted — the operating-rules section
    states this as an explicit anti-fabrication rule.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    lowered = out.lower()
    assert "--outcome fail" in lowered or "outcome pass|fail" in lowered
    assert "never smoothed" in lowered or "never omitted" in lowered


def test_learn_teaches_delta_provenance(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` teaches that behavioral deltas carry --caused-by
    provenance back to a claim, deviation, or prior delta.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--caused-by" in out
    assert "delta" in out.lower()


def test_learn_teaches_unmet_is_unmet_never_gates(capsys: pytest.CaptureFixture[str]) -> None:
    """The operating rules state the unmet-obligation warning never blocks
    export or plan convergence — warnings never gate.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "unmet is unmet" in out
    assert (
        "never gate" in out
        or "never a blocker" in out
        or "not stop" in out.replace("does not stop", "not stop")
    )


def test_learn_teaches_today_projection(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` teaches `devague today` as the read-only current-behavior
    projection, rendered after adjudication.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "devague today" in out
    assert "docs/current-spec.md" in out


def test_learn_teaches_strength_ladder(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` teaches the four-rung strength ladder — coverage,
    fidelity, execution, sensitivity — and that it is assessed by the agent,
    never inflated.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    for level in ("coverage", "fidelity", "execution", "sensitivity"):
        assert level in out
    assert "never inflated" in out or "never claim a higher rung" in out


def test_learn_states_two_audiences(capsys: pytest.CaptureFixture[str]) -> None:
    """`devague learn` names both audiences it serves: the operator driving the
    CLI, and the human who owns every confirm/reject and go/no-go decision.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "operator" in out
    assert "human" in out


def test_learn_json_includes_behavioral_validation_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The --json payload carries the behavioral-validation guidance and the
    strength ladder as distinct, structured sections.
    """
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "behavioral_validation" in payload
    assert payload["behavioral_validation"]["plant_obligations"]
    assert "strength_ladder" in payload
    levels = {entry["level"] for entry in payload["strength_ladder"]}
    assert levels == {"coverage", "fidelity", "execution", "sensitivity"}


# --- AC2: every command the refreshed learn output names actually exists on
# the real CLI surface, pinned by running each named verb with --help. ---


@pytest.mark.parametrize("verb", sorted(MOVES))
def test_every_named_move_has_working_help(verb: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Every top-level verb `learn` names in MOVES resolves on the real CLI
    surface — 'devague <verb> --help' must exit 0, never an argparse error.
    """
    with pytest.raises(SystemExit) as exc:
        main([verb, "--help"])
    assert exc.value.code == 0


def test_learn_verb_itself_has_working_help(capsys: pytest.CaptureFixture[str]) -> None:
    """'devague learn --help' exits 0 on the real CLI surface."""
    with pytest.raises(SystemExit) as exc:
        main(["learn", "--help"])
    assert exc.value.code == 0


def test_plan_oblige_verb_has_working_help(capsys: pytest.CaptureFixture[str]) -> None:
    """'devague plan oblige --help' — the nested plan-side verb `learn` names
    alongside the flat 'oblige' — exits 0 on the real CLI surface.
    """
    with pytest.raises(SystemExit) as exc:
        main(["plan", "oblige", "--help"])
    assert exc.value.code == 0


# --- `devague learn review` — the reviewer seam (bvts t14) --------------------


def _review_text(capsys: pytest.CaptureFixture[str]) -> str:
    rc = main(["learn", "review"])
    assert rc == 0
    return capsys.readouterr().out


def test_learn_review_teaches_obligations_as_the_checklist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC1: obligations are the reviewer's ready-made checklist, and unmet ones
    arrive precomputed as visibly-untested convergence warnings.
    """
    out = _review_text(capsys)
    lowered = out.lower()
    assert "checklist" in lowered
    assert "obligation" in lowered
    assert "untested" in lowered
    assert "warning" in lowered


def test_learn_review_states_the_checklist_is_a_floor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2: the enumerated records are a floor, not a ceiling — a finding
    outside them is still a finding.
    """
    out = _review_text(capsys).lower()
    assert "floor, not a ceiling" in out


def test_learn_review_teaches_three_way_fidelity_audit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC1: the three-way comparison — claim text vs recorded behavior text vs
    what the test actually asserts — read from the test source in the PR, with
    the behavioral-test convention naming how the test is found.
    """
    out = _review_text(capsys)
    lowered = out.lower()
    assert "three-way" in lowered
    assert "claim text" in lowered
    assert "recorded behavior" in lowered
    assert "asserts" in lowered
    # The behavioral-test convention: a marker or a dedicated folder.
    assert "@pytest.mark.behavioral" in out
    assert "tests/behavioral/" in out
    # The test source as it stands in the PR, never the recorded text alone.
    assert "test source" in lowered


def test_learn_review_teaches_strength_verification_and_stale_runs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC1: each ladder level is checked against its recorded basis, execution
    is re-run, and a run reference behind the PR head demotes the claim.
    """
    out = _review_text(capsys)
    lowered = out.lower()
    for level in ("coverage", "fidelity", "execution", "sensitivity"):
        assert level in lowered
    assert "--run-commit" in out
    assert "pr head" in lowered
    assert "demote" in lowered
    assert "passing long ago is not passing now" in lowered
    assert "never accepted above its basis" in lowered or "above its basis" in lowered


def test_learn_review_teaches_delta_completeness_both_directions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC1: both directions — an undeclared behavioral change and a fabricated
    delivery — are findings, derived from the diff and the ledger actually read.
    """
    out = _review_text(capsys).lower()
    assert "undeclared behavioral change" in out
    assert "fabricated delivery" in out
    assert "both directions" in out
    assert "diff" in out


def test_learn_review_teaches_propose_never_confirm(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2: findings land as PR comments, proposed lapses, or superseding
    evidence; the gate-3 human adjudicates; an approved lapse caps strength.
    """
    out = _review_text(capsys)
    lowered = out.lower()
    assert "pr comment" in lowered
    assert "grader-unverified" in out
    assert "provenance-missing" in out
    assert "--origin llm" in out
    assert "caps" in lowered
    assert "gate 3" in lowered or "gate-3" in lowered
    # The reviewer never confirms their own finding.
    assert "never" in lowered
    assert "confirm" in lowered


def test_learn_review_teaches_retraction_on_the_record(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2 / the honesty bar quoted verbatim from the spec: a finding retracted
    under pushback is retracted ON the record, never deleted.
    """
    out = _review_text(capsys).lower()
    assert "retracted on the record" in out
    assert "not deleted" in out or "never deleted" in out
    assert "append-only" in out


def test_learn_review_is_self_contained_about_its_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC3 (first direction): every command the topic relies on is named in the
    rendered text with its `devague ` prefix.
    """
    out = _review_text(capsys)
    assert REVIEW_COMMANDS, "the review topic must name the commands it relies on"
    for parts, _purpose in REVIEW_COMMANDS:
        assert "devague " + " ".join(parts) in out


@pytest.mark.parametrize("parts", [parts for parts, _ in REVIEW_COMMANDS])
def test_learn_review_named_command_exists(parts: tuple[str, ...]) -> None:
    """AC3 (the pin): every command the review topic names resolves on the real
    CLI surface — '<command> --help' exits 0, never an argparse error.
    """
    with pytest.raises(SystemExit) as exc:
        main([*parts, "--help"])
    assert exc.value.code == 0


def test_learn_review_text_names_no_unknown_devague_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC3 (second direction): the topic mentions `devague` only in command
    position, and every such mention is one of the declared REVIEW_COMMANDS —
    so the taught text can never drift into naming a command that isn't real.
    """
    out = _review_text(capsys)
    declared = {" ".join(parts) for parts, _ in REVIEW_COMMANDS}
    mentioned = set()
    for match in re.finditer(r"\bdevague ((?:plan )?[a-z][a-z-]*)", out):
        mentioned.add(match.group(1))
    assert mentioned, "the topic should name at least one devague command"
    assert mentioned <= declared, f"undeclared devague commands taught: {mentioned - declared}"


def test_learn_review_lapse_codes_match_the_real_vocabulary() -> None:
    """`learn` keeps its own literal copy of the lapse codes (it never imports a
    domain module) — pin it equal to the real vocabulary so the taught codes
    cannot drift away from the ones `devague lapse --code` accepts.
    """
    from devague.frame import LAPSE_CODES

    assert LAPSE_CODES_FOR_REVIEW == LAPSE_CODES


def test_learn_review_json_payload(capsys: pytest.CaptureFixture[str]) -> None:
    """`learn review --json` carries the audit method as structured sections and
    shares the learn family's tool/version/topic identity.
    """
    rc = main(["learn", "review", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "devague"
    assert payload["version"]
    assert payload["topic"] == "review"
    review = payload["review"]
    for key in (
        "checklist",
        "fidelity_audit",
        "strength_verification",
        "delta_completeness",
        "propose_never_confirm",
    ):
        assert review[key]
    commands = {" ".join(entry["command"]): entry["purpose"] for entry in review["commands"]}
    assert commands
    for parts, purpose in REVIEW_COMMANDS:
        assert commands[" ".join(parts)] == purpose


def test_learn_review_topic_listed_in_unknown_topic_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unknown topic's hint names `review` alongside the skills topics."""
    rc = main(["learn", "bogus"])
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "review" in err


def test_bare_learn_points_at_the_review_topic(capsys: pytest.CaptureFixture[str]) -> None:
    """Bare `learn` surfaces the reviewer seam so a gate-3 reviewer can find it."""
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "learn review" in out
