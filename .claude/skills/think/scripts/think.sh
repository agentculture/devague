#!/usr/bin/env bash
# think.sh — drive devague's working-backwards idea→spec engine (the /think skill).
#
# The skill is named `think`; the product/CLI it drives is `devague` (the spec→plan
# half lives in the sibling /spec-to-plan skill, which drives `devague plan`).
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
think.sh — drive devague's working-backwards idea→spec engine (the /think skill).

Usage:
  think.sh <move> [args...]    forward a devague move
  think.sh status [--frame S]  where the frame stands + the next move
  think.sh help                this help

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

Next leg: once a frame exports a spec, hand off to the /spec-to-plan skill
(`devague plan ...`) to turn that spec into a buildable plan.
EOF
}

# ── status: read the convergence gate and recommend the next move ──────────
cmd_status() {
    local list_json conv_out conv_err conv_rc req_frame="" prev="" tmp_err

    # Pull the requested --frame (if any) so the header names the same frame
    # that convergence is evaluated for; converge still receives it via "$@".
    for arg in "$@"; do
        case "$prev" in --frame) req_frame="$arg" ;; esac
        case "$arg" in --frame=*) req_frame="${arg#--frame=}" ;; esac
        prev="$arg"
    done

    list_json="$("${DEVAGUE[@]}" list --json 2>/dev/null || true)"

    # Capture converge's stdout, stderr, and exit code separately. converge
    # exits 0 even when "not passed", so a non-zero code is a *real* error
    # (bad/missing --frame, corrupt frame) we must surface, not swallow.
    tmp_err="$(mktemp)"
    set +e
    conv_out="$("${DEVAGUE[@]}" converge --json "$@" 2>"$tmp_err")"
    conv_rc=$?
    set -e
    conv_err="$(cat "$tmp_err")"
    rm -f "$tmp_err"

    DEVAGUE_LIST_JSON="$list_json" \
        DEVAGUE_CONV_JSON="$conv_out" \
        DEVAGUE_CONV_ERR="$conv_err" \
        DEVAGUE_CONV_RC="$conv_rc" \
        DEVAGUE_REQ_FRAME="$req_frame" \
        python3 - <<'PY'
import json
import os
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
conv_err = os.environ.get("DEVAGUE_CONV_ERR", "").strip()
req_frame = os.environ.get("DEVAGUE_REQ_FRAME", "").strip()
try:
    conv_rc = int(os.environ.get("DEVAGUE_CONV_RC", "0") or "0")
except ValueError:
    conv_rc = 0

frames = lst.get("frames") or []
current = lst.get("current")

if not frames:
    print("no frames yet — start one:")
    print('  devague new "<announcement>"')
    print('  first question: "What\'s the announcement? Pretend this shipped'
          ' successfully — what would you announce?"')
    sys.exit(0)

shown = req_frame or current or "(none selected)"
total = len(frames)
print(f"frame: {shown}    ({total} frame{'s' if total != 1 else ''} total)")

if conv is None:
    # A non-zero converge exit on an existing frame is a genuine error —
    # relay devague's own error:/hint: lines to stderr instead of masking it.
    if conv_rc != 0 and conv_err:
        sys.stderr.write(conv_err + "\n")
        sys.exit(conv_rc)
    print("convergence: unknown (could not evaluate the frame)")
    print("next move: devague show     # inspect the frame")
    sys.exit(0)

if conv.get("ready_for_spec"):
    print("convergence: PASSED ✓")
    for w in conv.get("warnings") or []:
        print(f"  ⚠ {w}")
    print("next move: devague export   # write the buildable spec")
    sys.exit(0)

blockers = conv.get("blockers") or []
print(f"convergence: NOT passed — {len(blockers)} gap(s):")
for b in blockers:
    print(f"  - {b}")
for w in conv.get("warnings") or []:
    print(f"  ⚠ {w}")

moves = conv.get("required_next_moves") or []
if moves:
    print()
    print("recommended next move (first gap):")
    print(f"  {moves[0]}")
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
