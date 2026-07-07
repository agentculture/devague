# Announcement Frame — Sharper Golden

slug: `sharper` · status: `drafting`

## Announcement

- we shipped the sharper method
  - instruction: run the dogfood script end to end
  - honesty: must be observed end to end

## Audience

- operators driving /think
  - instruction: confirm by grepping skill frontmatter for the audience note

## Requirements

- exports render instruction blocks verbatim
  - instruction: run `uv run devague export` and diff against the golden fixture
  - honesty: an absent instruction renders nothing
    - instruction: capture a claim with no instruction and assert no new bullet appears

## Assumptions

- the operating agent performs the exploration

## Boundaries

- renderer changes stay inside render slash star dot py

## Non-goals

- not a wizard

## Decisions

- sharper means instruction blocks and scope provenance

## Scope exploration

- `s1` — `devague render spec_md dot py`: no instruction or scope rendering existed before t6
  - seeds: `c3`
- `s2` — `devague render frame_md dot py`: same renderer gap as spec_md.py
