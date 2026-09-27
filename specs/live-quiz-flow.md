# Live Quiz Flow

How a live quiz runs end to end.

## Big picture

Server-authoritative. One RQ background job (`run_game_loop`) drives the whole game per session. Clients never tick their own clock. Redis (`frappe.cache`) is the fast gate; the DB is the durable record. Realtime push over socket rooms keyed by game PIN.

## Lifecycle

**1. Host creates session** (`api.create_session`)
Pick a quiz. Creates a `TT Session` with a random 6-digit `game_pin`, status `Lobby`.

**2. Guests join** (`api.join_session`, guest-allowed)
PIN + nickname + avatar, no login. Profanity check on nickname. Server mints a secret token and stores only its SHA256 hash. The player keeps the token as their identity. A lobby update is pushed to everyone.

**3. Host starts** (`api.start_session`)
Status → `Active`. Enqueues the game loop job on the `long` queue. `engine.run_game_loop` now owns the game.

**4. Game loop, per question** (`engine.run_game_loop`)
- `get_ready` — 3s "read the question" pause (Kahoot style).
- `open_question` — sets Redis state, pushes the question payload with `deadline_ts` and `window_ms`. The correct answer is never in the payload.
- `wait_question_window` — sleeps until deadline + 1s grace. Wakes early on host `skip`/`end`.
- `close_question` — scores everyone, pushes distribution + top 5 + streaks.
- `wait_before_next` — 5s stats pause, then auto-advance, or waits (capped at 5 min) for the host's Next.

**5. Players answer** (`api.submit_answer`, guest)
Validates: session active, question open, before deadline + grace. `mark_answered` uses a Redis set as a fast duplicate gate. Inserts a `TT Answer` with `response_ms`. A unique constraint is the second duplicate guard. Live answer count is pushed.

**6. Scoring** (`engine.compute_points`)
Kahoot formula: `base = (1 - (response_ms / window_ms) / 2) * 1000`. Faster answers score more. Streak bonus is `min(streak - 1, 5) * 50`, times the question multiplier. Wrong answer scores 0 and resets the streak.

**7. Finish** (`engine.finish_session`)
Ranks all participants, writes ranks, pushes the podium (top 3 + full leaderboard). Clears Redis state.

## Two control channels

- **Redis state** (`tt:{session}:state`) — current phase, deadline, question. TTL outlives each phase, so no state means no live loop.
- **Redis control** (`tt:{session}:control`) — host commands (`skip` / `advance` / `end`) that the loop polls every 0.25s.

## Clever bits

- **Clock-skew immune**: clients count down from `window_ms`, not the server `deadline_ts`.
- **Crash recovery** (`engine.is_abandoned`): if the worker dies mid-game, the next host/player load settles the session and shows the podium. No zombie games.
- **Reload safe**: `get_host_state` / `get_state` rebuild the whole screen from Redis + DB on refresh.

## Key files

- `trivia_tap/engine.py` — game loop, hot state, scoring, realtime publish.
- `trivia_tap/api.py` — whitelisted endpoints for host and players.
- DocTypes: `TT Session`, `TT Quiz`, `TT Question`, `TT Participant`, `TT Answer`.
