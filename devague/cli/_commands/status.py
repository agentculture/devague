"""``devague status`` — where the frame stands + the recommended next move.

A read-only value-add verb that composes ``list`` and ``converge``: it reports
the selected frame, the convergence verdict (blockers and warnings), and, when
not converged, the next move for the first gap. This logic used to live in the
``think`` skill wrapper's embedded Python (issue #30); internalising it makes it
deterministic and unit-testable and removes the wrapper's temp-file +
stdout-ordering hazards. ``status`` never mutates state — like ``review`` it only
reports (the ``drafting``↔``converged`` transition stays in ``converge``).
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_diagnostic
from devague.cli._status import StatusLabels, emit_empty, emit_status
from devague.contested import find_contested_markers, marker_to_dict, sorted_markers
from devague.convergence import evaluate
from devague.obligation_evidence import met_obligation_refs_for_frame

_LABELS = StatusLabels(
    noun="frame",
    ready_key="ready_for_spec",
    export_move="devague export   # write the buildable spec",
    empty_text=(
        "no frames yet — start one:\n"
        '  devague new "<announcement>"\n'
        "  first question: \"What's the announcement? Pretend this shipped"
        ' successfully — what would you announce?"'
    ),
)


def cmd_status(args: argparse.Namespace) -> int:
    json_mode = getattr(args, "json", False)
    slugs = store.list_slugs()
    if not slugs:
        emit_empty(_LABELS, json_mode=json_mode)
    else:
        # A bad --frame raises here (before any stdout) so the error reaches stderr.
        frame = resolve(args.frame)
        # Unmet-obligation warnings (bvts t7): the evidence state is loaded here,
        # at the edge, and handed to the pure gate — same fail-open terms as the
        # contested derivation below.
        met, met_diagnostics = met_obligation_refs_for_frame(frame.slug)
        for diag in met_diagnostics:
            emit_diagnostic(diag)
        result = evaluate(frame, met_obligations=met)
        # Contested-by-deviation derivation (#92): read-only, fails open — a
        # broken plan/delivery ledger anywhere in the join degrades to "no
        # markers from that source" plus a stderr diagnostic, never a crash.
        markers, diagnostics = find_contested_markers(frame)
        for diag in diagnostics:
            emit_diagnostic(diag)
        contested = [marker_to_dict(m) for m in sorted_markers(markers)]
        emit_status(
            _LABELS,
            selected=frame.slug,
            total=len(slugs),
            result=result,
            json_mode=json_mode,
            contested=contested,
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("status", help="Where the frame stands + the recommended next move.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_status)
