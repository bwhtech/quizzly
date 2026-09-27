# Phase 4 — Trim Submit Path + Throttle answer_count

Cut the two remaining per-answer costs: redundant link validation on insert, and the
O(players²) `answer_count` broadcast storm.

## Goal (the slice)
`submit_answer` does only the Redis dedupe gate + a lean insert. The live "N answered"
counter is broadcast by the ticker, throttled, instead of once per submission.

## Proves
Submit path is minimal and answer-count network load is flat regardless of player count,
with no loss of the live counter's usefulness.

## Changes
`trivia_tap/api.py` — `submit_answer`:
- Add `ignore_links=True` to the insert: `.insert(ignore_permissions=True, ignore_links=True)`.
  Session-active + participant-by-token already validated (api.py:214-216); the
  `(participant, question_row)` unique index still backstops duplicates.
- Remove the `answer_count` `publish_session_event` block (api.py:243-250).

`trivia_tap/engine.py` — ticker:
- In each pass, for a session in the open-question phase, `maybe_push_answer_count`: read
  `answered_count`, and if it changed since last push **and** ≥~300ms elapsed, broadcast the
  new count. At most a few updates/sec total, independent of player count.

## Test (end-to-end feedback)
1. `/agent-browser`: play with 3+ guests; host's live answer count still climbs smoothly as
   guests answer (now driven by the ticker, not per-submit). Duplicate submit still rejected.
2. `bench ... run-tests --app trivia_tap` green (adjust any test asserting a per-submit
   answer_count broadcast).
3. Load check: many concurrent submits → confirm answer_count broadcasts are throttled
   (a few/sec), not one-per-submit.

## Done when
Submit does insert + dedupe only, the host counter stays live via the ticker, duplicates
still rejected, and broadcast volume is flat under load.
