#!/usr/bin/env bash
# spec-to-plan.sh — drive devague's spec→plan engine (the /spec-to-plan skill).
#
# The skill is named `spec-to-plan`; the product/CLI it drives is `devague` (the
# idea→spec half lives in the sibling /think skill). This wrapper forwards every
# move to `devague plan <move>` verbatim, and adds one value-add subcommand —
# `status` — that reads the plan convergence gate and names the recommended next
# move. It is the forward leg: seed a plan from a *converged* frame, then work it
# into a buildable plan.
#
# Origin: authored and maintained in agentculture/devague. steward pulls this
# skill from here and broadcasts it to the rest of the AgentCulture mesh, so it
# is written to run anywhere — portable bash, no devague-checkout assumptions.
#
# Plans persist under .devague/ in the current directory (alongside frames), so
# run from the repo you are speccing.

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
spec-to-plan.sh — drive devague's spec→plan engine (the /spec-to-plan skill).

Usage:
  spec-to-plan.sh <move> [args...]   forward a `devague plan` move
  spec-to-plan.sh status [--plan S]  where the plan stands + the next move
  spec-to-plan.sh help               this help

Moves (forwarded to `devague plan`; run `devague plan learn` for the method):
  new          start a plan from a CONVERGED frame (--frame <slug>)
  task         add a task (--accept / --dep / --covers, --origin user|llm)
  accept       add an acceptance criterion to a task
  depend       record that a task depends on another (--on)
  cover        mark a task as covering a coverage target (c*/h*)
  confirm      confirm a task                          (USER-only decision)
  reject       reject a task
  risk         record a first-class plan risk
  converge     check whether the plan can export
  export       write the buildable plan (only after converge passes)
  show / list  render a plan / list plans
  learn        teach the method   |   explain <move>  explain one move

Plans persist under .devague/ in the current directory — run from the repo you
are speccing. Results go to stdout, diagnostics to stderr; pass --json to any
move for structured output.

Note: `status` is a wrapper-only verb; everything else is forwarded verbatim as
`devague plan <move>`, so new plan moves work without editing this script.

Prior leg: a plan is seeded from a converged frame produced by the /think skill.
EOF
}

# ── status: read the plan convergence gate and recommend the next move ──────
cmd_status() {
    local list_json conv_out conv_err conv_rc req_plan="" prev="" tmp_err

    for arg in "$@"; do
        case "$prev" in --plan) req_plan="$arg" ;; esac
        case "$arg" in --plan=*) req_plan="${arg#--plan=}" ;; esac
        prev="$arg"
    done

    list_json="$("${DEVAGUE[@]}" plan list --json 2>/dev/null || true)"

    tmp_err="$(mktemp)"
    set +e
    conv_out="$("${DEVAGUE[@]}" plan converge --json "$@" 2>"$tmp_err")"
    conv_rc=$?
    set -e
    conv_err="$(cat "$tmp_err")"
    rm -f "$tmp_err"

    DEVAGUE_LIST_JSON="$list_json" \
        DEVAGUE_CONV_JSON="$conv_out" \
        DEVAGUE_CONV_ERR="$conv_err" \
        DEVAGUE_CONV_RC="$conv_rc" \
        DEVAGUE_REQ_PLAN="$req_plan" \
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
req_plan = os.environ.get("DEVAGUE_REQ_PLAN", "").strip()
try:
    conv_rc = int(os.environ.get("DEVAGUE_CONV_RC", "0") or "0")
except ValueError:
    conv_rc = 0

plans = lst.get("plans") or []
current = lst.get("current")

if not plans:
    print("no plans yet — seed one from a converged frame:")
    print('  devague plan new --frame "<slug>"')
    print("  (the frame must have converged in the /think skill first)")
    sys.exit(0)

shown = req_plan or current or "(none selected)"
total = len(plans)
print(f"plan: {shown}    ({total} plan{'s' if total != 1 else ''} total)")

if conv is None:
    # A non-zero converge exit is a real error (deleted/regressed source frame,
    # bad --plan) — relay devague's own error:/hint: lines instead of masking it.
    if conv_rc != 0 and conv_err:
        sys.stderr.write(conv_err + "\n")
        sys.exit(conv_rc)
    print("convergence: unknown (could not evaluate the plan)")
    print("next move: devague plan show     # inspect the plan")
    sys.exit(0)

if conv.get("ready_for_plan"):
    print("convergence: PASSED ✓")
    for w in conv.get("warnings") or []:
        print(f"  ⚠ {w}")
    print("next move: devague plan export   # write the buildable plan")
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
            # Forward everything else to `devague plan <move>` verbatim, so the
            # CLI's own parser owns the plan surface.
            resolve_devague
            exec "${DEVAGUE[@]}" plan "$@"
            ;;
    esac
}

main "$@"
