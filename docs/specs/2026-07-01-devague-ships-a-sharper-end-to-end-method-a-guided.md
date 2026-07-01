# devague ships a sharper end-to-end method

> devague ships a sharper end-to-end method: a guided scope-exploration stage before the announcement frame, per-item instructions on every claim and task, sharper spec and plan exports, and a guided plan-to-fanout leg that carries those instructions to the workforce.

## Audience

- devague operators — the agent driving /think and /spec-to-plan — plus the humans who own the three gates, and the per-task workforce subagents who receive the instructions

## Before → After

- Before: today the frame starts cold at the announcement with no scope survey; claims and tasks carry only their summary text; exports leave the reader to re-derive how to act on each item; and plan waves emits task ids whose context assign-to-workforce must reconstruct by hand
- After: an idea's scope is explored and mapped before the frame is built; every claim, honesty condition, and plan task can carry its own working instruction; exports read sharp — every item actionable, no boilerplate; and the plan-to-fanout leg hands the workforce per-task instructions instead of bare summaries

## Why it matters

- scope grounded up front means convergence measures real coverage instead of vibes, and per-item instructions make every exported artifact executable by a cheaper model without re-deriving the design

## Requirements

- a scope-exploration stage precedes the frame: before or right after 'new', the operator surveys the repo/context the idea touches and the findings seed boundary, non-goal, and assumption claims that cite what was explored
  - honesty: a frame built with scope exploration contains boundary and non-goal claims that cite the surfaces actually explored — provenance, not generic disclaimers
- claims and plan tasks accept an optional per-item instruction — how to verify or implement that item — stored in frame/plan state and rendered verbatim in exports; an absent instruction renders nothing
  - honesty: instructions round-trip: capture, store, export renders them verbatim; an item without an instruction renders nothing rather than fabricated filler
- sharper exports: the rendered spec-md and plan-md make every item directly actionable, with the definition of sharper agreed with the user before build
  - honesty: sharper has a written definition the user confirmed before any renderer change lands
  - honesty: the tightened gate stays deterministic: it checks structural sharpness signals — instruction present on spec-affecting items, a measurable success signal, claim text meeting explicit structural rules — never LLM text judgment inside the CLI
- the plan-to-fanout leg is guided end-to-end: plan waves output carries each task's instruction and acceptance criteria, and the assign-to-workforce skill consumes that payload as the per-subagent brief
  - honesty: an assign-to-workforce subagent receives its task's instruction and acceptance criteria in its brief with no operator paraphrasing required

## Honesty conditions

- an operator can run idea to scope to spec to plan to fanout end-to-end and every handoff carries the per-item instructions without manual re-entry
- each named audience actually touches the shipped surface: the operator agent runs the new moves, the gate-owning humans review the sharper artifacts, and workforce subagents receive the instruction payloads
- the after-state is observable in one dogfooded run: a real idea goes scope, frame, sharper spec, plan, fanout using only the shipped surface
- the before-state pains are citable gaps in today's code: no scope move exists, neither store has an instruction field, and assign-to-workforce reconstructs task context by hand
- coverage reported by the gate maps to scope that was actually explored — convergence measures explored territory, not just whatever text happened to be captured
- the shipped diff contains no LLM calls, no subagent spawning, and no worktree management anywhere inside the devague package
- every success signal is checkable on artifacts alone: the exported spec shows scope provenance, the exported plan renders instruction blocks, and a fanout brief quotes them verbatim

## Success signals

- a spec produced with the new process shows scope-exploration provenance on its boundary and non-goal claims; every exported plan task renders an instruction block; and an assign-to-workforce run consumes those instructions as the subagent brief without the operator re-typing context

## Scope / boundaries

- the CLI stays deterministic and non-orchestrating per issue 20: scope exploration is an agent/skill-side stage and fanout guidance lives in the assign-to-workforce skill — no LLM calls and no orchestration land inside the CLI

## Non-goals

- not a wizard: scope exploration does not become a mandatory fixed first stage; the move-driven adaptive arc stays intact and small ideas can still skip straight to the announcement

## Assumptions

- scope exploration is performed by the operating agent reading the repo and context — it adds no new CLI dependencies and no LLM calls inside devague

## Decisions

- sharper results means both legs: exports render every item actionable with instruction blocks and no boilerplate, and the convergence gate tightens to flag vague untestable claim text
- scope exploration lands as a new deterministic CLI move — devague scope — that records explored surfaces and findings as first-class state with provenance; the operating agent performs the actual exploration
- per-item instructions attach to both frame claims and plan tasks via an optional instruction field, with a schema_version bump in both stores, flowing spec to plan to fanout

## Hard questions

- does the added scope stage slow the lightweight case — small ideas that today go announcement to converge in minutes?
- LLM-proposed instructions must stay proposed too — does the user confirm loop scale when every claim and task can carry one?
- which structural checks can a deterministic CLI actually run to catch woolly text, and what is the false-positive story when they misfire on legitimate prose?
