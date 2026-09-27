# Phase 3 — Batch Scoring Writes (reveal latency)

Kill the N+1 write loops so reveal time stops growing with player count.

## Goal (the slice)
`close_question` and `finish_session` persist all participants in batched
`frappe.db.bulk_update` calls instead of one `set_value` per participant. Same scores,
same podium — just flat write time.

## Proves
Reveal latency is flat vs player count; the `question_closed` push (after_commit) no longer
waits out a serial per-player loop.

## Changes (`trivia_tap/engine.py`)
- `close_question`: loop builds two dicts in memory (no I/O) —
  `answer_updates = {answer.name: {"is_correct", "points"}}`,
  `participant_updates = {p.name: {"score", "streak"}}` (streak-reset-to-0 for
  non-answerers in the same dict) — then
  `frappe.db.bulk_update("TT Answer", answer_updates)` +
  `frappe.db.bulk_update("TT Participant", participant_updates)`, existing commit + push.
- `finish_session`: one `frappe.db.bulk_update("TT Participant", {name: {"rank": rank}})`.
- API confirmed: `frappe.db.bulk_update(doctype, {name: {field: value}})` → chunked
  CASE-WHEN SQL (frappe/database/database.py:1020).

## Test (end-to-end feedback)
1. `bench ... run-tests --app trivia_tap` — scoring/streak/rank/podium results **identical**
   to before (this is the correctness gate; batching must not change any number).
2. `/agent-browser`: play a game with 3+ guests, confirm reveal + podium correct and prompt.
3. Load check: script many `submit_answer`s (e.g. 100 participants), time `close_question`
   before vs after — should go from ~linear to near-flat.

## Done when
Identical scores/ranks, reveal prompt, and `close_question` time no longer scales with
player count.
