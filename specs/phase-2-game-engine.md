# Phase 2: Game Engine

## Goal

Full server-authoritative game loop: questions publish with deadlines, answers validated and scored, stats and podium published, results persisted.

## Game loop

One RQ background job per active session: `queue="long"`, `job_id=f"tt_session_{name}"`, `deduplicate=True`. Timeout sized to quiz length (questions x seconds + margin).

Loop per question:

1. Write Redis state.
2. Publish `question` (text + options, NO correct answer, deadline_ts, index, total) on `tt_session_{pin}`.
3. Sleep until deadline + grace.
4. Close question in Redis, score answers.
5. Publish `question_closed` (correct option, distribution, top-5, streak callouts).
6. Advance: auto-advance after N seconds (host setting) or wait for host `next_question`.

After last question: compute final ranks, publish `podium` (top 3 + full leaderboard), status Ended, persist results.

Host drop does not kill the game: loop is server-driven, host can reload and resume via host screen state API.

## Timing

No per-second server ticks. Question payload carries server-set `deadline_ts` (epoch float). Client renders its own countdown. Server validates every submit against Redis state.

## Redis state (hot path)

```
tt:{session}:state        -> {status, q_index, question_row, opened_at, deadline_ts}   TTL: window + 30s
tt:{session}:answered:{q} -> SET of participant names (fast duplicate pre-check)       TTL: window + 30s
```

Via `frappe.cache`. DB is the durable record; Redis is the fast gate for submit validation.

## APIs

Guest (`allow_guest=True`, rate-limited):

| endpoint | args | does |
|---|---|---|
| `get_state` | pin, token | current state for reconnect: status, current question (no answer), deadline_ts, own score. Also the polling fallback |
| `submit_answer` | pin, token, question_row, selected_option | full validation gauntlet, store answer, return ack only (no correctness leak) |

Host:

| endpoint | does |
|---|---|
| `start_session` | enqueue game loop |
| `next_question` | when auto_advance off |
| `skip_question` | close current early |
| `end_session` | abort loop, straight to podium |

## submit_answer validation gauntlet (order matters)

1. Rate limit per token.
2. Session exists, status Active.
3. Token hash matches a participant of this session, not kicked.
4. Redis state: question_row equals the currently active question.
5. `server_now <= deadline_ts + 1.0` (grace for network only).
6. Redis answered-set pre-check, then DB insert; unique constraint is the final word.
7. Score computed server-side, from server timestamps.

Return only `{"ok": true}`. Correctness revealed to everyone at question close, never per-submit.

## Scoring (server-side only, Kahoot formula)

```
if incorrect: 0, streak = 0
if correct:
    base = round((1 - (response_ms / window_ms) / 2) * 1000)   # 500..1000
    streak += 1
    bonus = min(streak - 1, 5) * 50                            # 0..250
    points = (base + bonus) * points_multiplier
```

`response_ms` is server receive time minus server opened_at. Client timing never used.

## Anti-cheat (enforced this phase)

1. Correct answer never in any payload until question closed.
2. Server-set deadline, 1s network grace, all timestamps server-side.
3. DB composite unique (participant, question_row): duplicates impossible.
4. Active-question gate in Redis: cannot answer past/future questions.
5. Question bank unreadable by guests; payloads hand-built in API code.
6. Rate limiting on all guest APIs.
7. Scores computed and persisted server-side only.
8. Canonical option ids on the wire; per-participant display shuffle is client-side (seeded by token), defeats neighbor-copying without touching scoring.

Residual risk: one human, several devices/tabs, several nicknames. Host kick + lobby lock is the mitigation. Accepted.

## Test checklist

- Submit after deadline+grace rejected.
- Duplicate submit rejected (API race: fire two in parallel, DB constraint holds).
- Submit for non-active question rejected.
- Kicked token rejected everywhere.
- Scoring: boundary response times (0ms, window, window+grace), streak reset, multiplier 0 and 2.
- Correct answer absent from every payload before close (assert on serialized events).
- Reconnect mid-question gets correct remaining time.

## Exit criteria

- Full game playable start to podium via API calls (raw UI acceptable).
- Entire test checklist green.
