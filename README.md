# devague

**`devague` is a command-line tool** that turns a vague feature idea into a
buildable **spec**, then that spec into a buildable **plan** — by working
backwards, then forwards. It is a small, deterministic Python CLI (no LLM calls
inside it, fully unit-tested) — not an agent, service, or daemon. You install it
and run `devague` from the repository you are speccing; state is plain JSON under
`.devague/`.

```text
vague idea ──▶ buildable spec ──▶ buildable plan ──▶ build
```

## Install

```bash
uv tool install devague      # or: pipx install devague / pip install devague
devague --version
```

## Two engines, one CLI

- **Frame engine** (idea→spec) — start from the announcement ("pretend it
  shipped"), capture and pressure-test claims, park open vagueness, and `export`
  a spec only once the frame *converges*. Flat verbs: `devague new` /
  `capture` / `amend` / `interrogate` / `confirm` / `park` / `scope` /
  `lapse` / `oblige` / `converge` / `export` / …
- **Plan engine** (spec→plan) — seed a plan from a converged frame, cover every
  target with tasks that carry acceptance criteria and an acyclic dependency
  order, and `export` a plan only once it *converges*. Nested group:
  `devague plan new` / `task` / `cover` / `defer` / `converge` / `export` / …

Alongside them sits the **delivery ledger** (plan→what actually shipped) —
append-only records of how execution really went: `devague deviate` (mid-run
departures from the confirmed plan), `oblige` (mark a claim's or acceptance
criterion's behavioral obligation), `evidence` (a behavioral test met — or
failed — an obligation, with the coverage/fidelity/execution/sensitivity
strength ladder), `delta` (a behavior the run added, amended, or removed),
`summary` (the render-only delivery summary), and `today` (project the
behavior ledger into the committed, undated `docs/current-spec.md`).

Nothing gets deleted to make a gate go green. A parked unknown, a blocking
hard question, and a coverage target that belongs to a later milestone each
have an explicit close-out move — `park --resolve`, `interrogate <cN>
--resolve <qN>`, and `plan defer` — that keeps the item on the record with
the decision that closed it, and drops it out of the gate.

Run `devague learn` (or `devague plan learn`) to learn the method, and `devague
explain <move>` for any single move.

## Human Review Loop

LLM-proposed claims and honesty conditions stay `proposed` until **you**
confirm them — that anti-fabrication rule is the point of the method. The review
loop makes that human step ergonomic at scale:

```bash
devague review                 # list every proposed (unconfirmed) item, with ids
devague review --json          # same, structured
devague confirm c2 h1 h3       # confirm many ids in one transactional call
devague reject c4 c5           # reject many ids in one call
devague confirm --from-review .devague/reviews/<slug>.md   # apply an edited review file
```

`review` is **not** gated on convergence and never mutates state. It writes a
durable, explicitly non-authoritative artifact you can review out of band, then
apply: each item is emitted with a `pending` marker — change it to `confirm` or
`reject` and feed the file back with `confirm --from-review`. `pending` lines are
never auto-confirmed; a batch is transactional (one bad id ⇒ nothing changes).
Rejecting a claim sweeps its still-live honesty conditions and unresolved hard
questions with it (`c4 -> rejected (also rejected: h3, q1)`), so rejected
content leaves the review pool and the exported spec together. The plan side
mirrors all of this: `devague plan confirm t1 t2 t3` / `plan reject …` are
multi-id and transactional too.

Open questions / pending decisions live as durable working state too:

```bash
devague question "should batch confirm be transactional?"   # record a pending decision
devague question --list                                     # review them
devague question --resolve q1 --decision "yes, transactional"
```

Applying a resolved decision into the frame stays an explicit move (e.g.
`devague capture --kind decision "…"` then `devague confirm`).

### `.devague/` — what's committed vs working state

| Path | Committed? |
|------|-----------|
| `.devague/frames/`, `.devague/plans/` | yes — the converged frame/plan state |
| `.devague/reviews/<slug>.md` | no — local review working state |
| `.devague/questions/<slug>.md` | no — local pending-decision working state |
| `.devague/current`, `.devague/current_plan` | no — local pointers |

devague keeps `reviews/` and `questions/` out of git for you (it manages
`.gitignore`). Promote one into `docs/` only if you intentionally want it
committed.

## Driving it from an agent

Inside AgentCulture, an assistant drives this CLI through a family of operator
skills that cover the **eight-leg flow** end to end, in order: **`/scope`**
(idea→explored scope, the optional opening leg), **`/think`** (idea→spec),
**`/challenge`** (a risk-scaled blind-spot discovery pass between /think and
/spec-to-plan), **`/spec-to-plan`** (spec→plan), **`/assign-to-workforce`**
(plan→parallel implementation), **`/deviate`** (the execution-time leg — stop
an in-flight fan-out the moment it must diverge from the confirmed plan, get
explicit human approval via `devague deviate`, and resume),
**`/validate-delivery`** (the execution-to-evidence leg — run the plan's
behavioral tests agent-side once waves merge, and file evidence and
behavioral deltas via the CLI; unmet is unmet), and
**`/summarize-delivery`** (execution→a committed accountability artifact).
`/challenge` is method-only — no wrapper script, no new CLI verb; findings
route through moves the CLI already exposes. `/validate-delivery` is
method-only too (the CLI never runs a test itself), but its filings land
through the record-only delivery verbs — `devague oblige` / `evidence` /
`delta` — with `llm`-origin filings landing `proposed` for human
adjudication, same anti-fabrication contract as everywhere else. The CLI-driving pair — `/think` and `/spec-to-plan` — add a
portable wrapper and a `status` next-move helper over the convergence gate;
the CLI is the deterministic affordance and the agent decides the next move.

Cutting across all eight legs is `devague lapse` (issue #97) — file a
reasoning-degradation lapse (an assumption silently substituted for a check)
the moment it happens, instead of reconstructing a corrections record from
memory once the run ends. It is never a gate: filing is friction-free
(`llm`-origin lands `proposed`, a user-authored one auto-approves), it never
blocks convergence on either engine, and only an **approved** entry is ever
cited as confidence evidence in `/summarize-delivery`'s Delivery Claims
section.

These skills serve two audiences: **operators** — the main agent that drives
the deterministic CLI move by move across all eight legs — and the **humans**
who own the three standing gates: the exported spec, the go/no-go on the
implementation split plan (including any mid-run deviation approved against
it via `/deviate`), and the final PR review. See `CLAUDE.md` for that workflow
and `docs/superpowers/specs/` for the design docs.
