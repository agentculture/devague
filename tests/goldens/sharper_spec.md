# Sharper Golden

> we shipped the sharper method
> instruction: run the dogfood script end to end

## Audience

- operators driving /think
  - instruction: confirm by grepping skill frontmatter for the audience note

## Requirements

- exports render instruction blocks verbatim
  - instruction: run `uv run devague export` and diff against the golden fixture
  - honesty: an absent instruction renders nothing
    - instruction: capture a claim with no instruction and assert no new bullet appears

## Honesty conditions

- must be observed end to end

## Scope / boundaries

- renderer changes stay inside render slash star dot py

## Non-goals

- not a wizard

## Assumptions

- the operating agent performs the exploration

## Scope exploration

- `s1` — `devague render spec_md dot py`: no instruction or scope rendering existed before t6
  - seeds: `c3`
- `s2` — `devague render frame_md dot py`: same renderer gap as `spec_md.py`

## Decisions

- sharper means instruction blocks and scope provenance
