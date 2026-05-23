#!/usr/bin/env bash
# devague.sh — operate the devague working-backwards spec tool.
#
# devague turns a vague feature idea into a buildable spec by working backwards.
# This wrapper is the agent-facing operator for the deterministic devague CLI:
# it resolves the CLI portably, forwards every move verbatim, and adds one
# value-add subcommand — `status` — that reads the convergence gate and names
# the recommended next move.
#
# Origin: authored and maintained in agentculture/devague. steward pulls this
# skill from here and broadcasts it to the rest of the AgentCulture mesh, so it
# is written to run anywhere — portable bash, no devague-checkout assumptions.
#
# Frames persist under .devague/ in the current directory, so run from the repo
# you are speccing.

set -euo pipefail

# ── resolve the devague CLI (mesh-first, then local-dev fallback) ───────────
DEVAGUE=()
resolve_devague() {
    if command -v devague >/dev/null 2>&1; then
        DEVAGUE=(devague)            # installed tool — the normal mesh case
        return 0
    fi
    # Local-dev fallback: inside the devague checkout, run via uv.
    local dir="$PWD"
    while [ -n "$dir" ] && [ "$dir" != "/" ]; do
        if [ -f "$dir/pyproject.toml" ] \
            && grep -q '^name = "devague"' "$dir/pyproject.toml" 2>/dev/null; then
            if command -v uv >/dev/null 2>&1; then
                DEVAGUE=(uv run devague)
                return 0
            fi
            break
        fi
        dir=$(dirname "$dir")
    done
    cat >&2 <<'EOF'
error: devague CLI not found.
hint: install it with `uv tool install devague` (or `pipx install devague`),
      or run from inside the devague checkout with `uv` available.
      https://github.com/agentculture/devague
EOF
    return 1
}

usage() {
    cat <<'EOF'
devague.sh — operate the devague working-backwards spec tool.

Usage:
  devague.sh <move> [args...]    forward a devague move
  devague.sh status [--frame S]  where the frame stands + the next move
  devague.sh help                this help

Moves (forwarded to the devague CLI; run `devague learn` for the full method):
  new          start a frame from the announcement ("pretend it shipped")
  capture      record + classify a claim (--kind audience|after_state|...)
  interrogate  pressure-test a claim (--honesty / --hard-question / --risk)
  confirm      confirm a claim or honesty condition  (USER-only decision)
  reject       reject a claim or honesty condition
  park         record open vagueness instead of forcing an answer
  converge     check whether the frame can export a spec
  export       write the buildable spec (only after converge passes)
  show / list  render a frame / list frames
  learn        teach the method   |   explain <move>  explain one move

Frames persist under .devague/ in the current directory — run from the repo
you are speccing. Results go to stdout, diagnostics to stderr; pass --json to
any move for structured output.

Note: `status` is a wrapper-only verb (the CLI has no `status`); everything
else is forwarded verbatim, so new devague moves work without editing this
script.
EOF
}

# ── status: read the convergence gate and recommend the next move ──────────
cmd_status() {
    local list_json conv_json
    list_json="$("${DEVAGUE[@]}" list --json 2>/dev/null || true)"
    conv_json="$("${DEVAGUE[@]}" converge --json "$@" 2>/dev/null || true)"
    DEVAGUE_LIST_JSON="$list_json" DEVAGUE_CONV_JSON="$conv_json" python3 - <<'PY'
import json
import os
import re
import sys


def load(name):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


lst = load("DEVAGUE_LIST_JSON") or {}
conv = load("DEVAGUE_CONV_JSON")

frames = lst.get("frames") or []
current = lst.get("current")

if not frames:
    print("no frames yet — start one:")
    print('  devague new "<announcement>"')
    print('  first question: "What\'s the announcement? Pretend this shipped'
          ' successfully — what would you announce?"')
    sys.exit(0)

total = len(frames)
print(f"frame: {current or '(none selected)'}    "
      f"({total} frame{'s' if total != 1 else ''} total)")

if conv is None:
    print("convergence: unknown (could not evaluate — is a frame selected?)")
    print("next move: devague show     # inspect the frame")
    sys.exit(0)

if conv.get("passed"):
    print("convergence: PASSED ✓")
    print("next move: devague export   # write the buildable spec")
    sys.exit(0)

missing = conv.get("missing") or []
print(f"convergence: NOT passed — {len(missing)} gap(s):")
for gap in missing:
    print(f"  - {gap}")


def suggest(gap):
    m = re.search(r"missing confirmed '([a-z_]+)' claim", gap)
    if m:
        kind = m.group(1)
        return (f'devague capture --kind {kind} "<text>"'
                f'    then: devague confirm <id>')
    if "before_state" in gap and "why_it_matters" in gap:
        return 'devague capture --kind why_it_matters "<text>"'
    if "boundary" in gap:
        return 'devague capture --kind boundary "<text>"'
    if "success_signal" in gap:
        return 'devague capture --kind success_signal "<text>"'
    m = re.search(r"claim (c\d+) still proposed", gap)
    if m:
        cid = m.group(1)
        return f"devague confirm {cid}    (or: devague reject {cid})"
    m = re.search(r"claim (c\d+) has no confirmed honesty condition", gap)
    if m:
        cid = m.group(1)
        return (f'devague interrogate {cid} --honesty "<what must be true>"'
                f'    then the USER runs: devague confirm <hN>')
    m = re.search(r"blocking vagueness (v\d+)", gap)
    if m:
        return (f"resolve {m.group(1)}: capture+confirm the answer, "
                f"or re-park it as non-blocking")
    m = re.search(r"blocking hard question (q\d+) on (c\d+)", gap)
    if m:
        return (f"resolve {m.group(1)} on {m.group(2)}: answer it, then "
                f"capture/confirm the resulting claim")
    return "devague show     # inspect and decide"


if missing:
    print()
    print("recommended next move (first gap):")
    print(f"  {suggest(missing[0])}")
PY
}

main() {
    case "${1:-help}" in
        help | -h | --help)
            usage
            return 0
            ;;
        status)
            shift
            resolve_devague
            cmd_status "$@"
            ;;
        *)
            # Forward everything else to the CLI verbatim (including --version,
            # and any future devague move), so its own parser owns the surface.
            resolve_devague
            exec "${DEVAGUE[@]}" "$@"
            ;;
    esac
}

main "$@"
