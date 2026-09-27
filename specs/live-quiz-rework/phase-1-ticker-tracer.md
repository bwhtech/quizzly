# Phase 1 — Ticker Tracer (architecture proof)

The riskiest change first. Replace the per-game busy-wait loop with a shared **ticker +
per-session state machine**, and prove it drives **one** game through every phase, end to
end, in the browser. No perf work yet — a thin slice that validates the new control flow.

## Goal (the slice)
`api.start_session` → seed Redis state → `run_ticker` (one shared job) → `advance_session`
walks the state machine → existing phase functions push over realtime → browser plays a
full game: lobby → get_ready → question → reveal → next → podium. Host skip/advance/end work.

## Proves
The new architecture is sound: a session's phase lives in Redis, an external ticker advances
it on time and on host command, and the existing realtime/client layers need no change. If
this slice feels right, the rest is perf and scale on top of a proven spine.

## Changes (`trivia_tap/engine.py`)
- Add `run_ticker`: self-looping RQ job, `job_id="tt_ticker"`, `deduplicate=True`, queue
  `long`. Each pass: read `tt:active_sessions`; per session read state, `pop_control`,
  and if a control fired or `now >= state["next_ts"]` call `advance_session`; then
  `frappe.db.commit()` (flush after_commit pushes); `time.sleep(TICK_SECONDS)` (0.5).
  Exit loop when the set is empty.
- Add `advance_session(session, control)` — dispatch on `state["phase"]`:
  - `end` → `finish_session` + `srem`.
  - `get_ready` & due → `open_question(index)`; `phase="question"`, `next_ts=deadline_ts+GRACE_SECONDS`.
  - `question` & (due or `skip`) → `close_question(index)`; `phase="stats"`,
    `next_ts = now + (STATS_SECONDS if auto_advance else ADVANCE_WAIT_CAP)`.
  - `stats` & (due or `advance`) → last index → `finish_session`+`srem`; else next index
    `get_ready`, `phase="get_ready"`, `next_ts=now+GETREADY_SECONDS`.
- Strip the internal `while/sleep` loops out of `get_ready`/`open_question`/`close_question`
  (keep their push + write bodies). Extend `set_state` payload with `phase`, `index`, `next_ts`.
- `enqueue_game_loop`: seed initial state, `sadd` session to `tt:active_sessions`, then
  `frappe.enqueue("trivia_tap.engine.run_ticker", job_id="tt_ticker", deduplicate=True, queue="long")`.
- Delete `run_game_loop` and `POLL_SECONDS` once green.

Scope guard: **one game only** here. Batching (Phase 3) and answer_count throttle (Phase 4)
are untouched — keep per-participant `set_value` and per-submit `answer_count` for now so
the diff stays about control flow.

## Test (end-to-end feedback)
1. `bench --site trivia-tap.localhost run-tests --app trivia_tap` — existing game tests must pass
   against the new engine (they exercise the phase functions).
2. `/agent-browser` headless, `trivia-tap.localhost`, Administrator/admin: host one quiz, join
   1 guest, play a full game. Watch: get_ready pause, question + countdown, reveal + stats,
   auto-advance, podium. Then repeat testing host **skip**, **advance** (auto_advance off),
   and **end** mid-game.
3. Confirm exactly one `tt_ticker` RQ job exists during play and it exits after the game ends.

## Done when
One full game plays start to finish via the ticker, all three host commands act within
~0.5s, tests green, no lingering `tt_ticker` job after finish.
