# Phase 2 — Multi-Game Scale (the payoff)

Prove the shared ticker drives **many concurrent games** on the same 3 workers with no
starvation — the whole reason for Phase 1's redesign.

## Goal (the slice)
Start 5+ games at once. One `tt_ticker` job advances all of them; each plays normally.
Old code pinned one worker per game and starved at >3 (`background_workers: 3`).

## Proves
Worker-per-game ceiling is gone: N games cost one worker slot, not N.

## Changes (`trivia_tap/engine.py`)
Mostly validation of Phase 1's registry — plus the loose ends that only bite with >1 game:
- `tt:active_sessions` lifecycle airtight: `srem` on finish **and** on `end`/abandon;
  `advance_session` `srem`s a session whose state vanished (`if not state`).
- Ticker resilience: a per-session exception in a pass must not kill the ticker for the
  others — wrap each session's `advance_session` in try/except, log, continue.
- Self-heal: if the ticker job is dead but sessions are active, the next `start_session`
  re-enqueues it (dedup no-ops while alive) and it picks up every registered session.
  Confirm `engine.is_abandoned` still settles a session the ticker somehow dropped.

## Test (end-to-end feedback)
1. `/agent-browser`: open 5 host tabs, start 5 games, join a guest to each, play
   concurrently. All advance phases on time; none stalls. Confirm **one** `tt_ticker` job.
2. Kill the worker mid-multi-game; start a new game → ticker revives and resumes all live
   sessions (or `is_abandoned` settles the stuck ones on next load). No zombie games.
3. `bench ... run-tests --app trivia_tap` green.

## Done when
5+ concurrent games play cleanly on 3 workers under a single ticker, ticker survives a
per-session error, and a killed ticker self-heals.
