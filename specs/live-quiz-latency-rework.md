# Live Quiz — Latency + Scalability Rework

## Context

The live quiz flow (`specs/live-quiz-flow.md`) has a sound core: server-authoritative,
socket.io push to guests, clock-skew-immune local countdown. The client is **already
push-based** (`frontend/src/game.js` `useSessionRoom`), not polling — the latency is on the
server, in two places.

**A. Hot-path cost (felt as reveal lag).**
1. N+1 write loops: `engine.close_question` (engine.py:149-171) runs 1–2 serial
   `frappe.db.set_value` UPDATEs *per participant*; `finish_session` (engine.py:243-244)
   runs 1 *per participant*. The `question_closed` push is `after_commit=True`, so the
   reveal waits out the whole serial loop. Grows linearly with player count.
2. O(players²) socket fan-out: `api.submit_answer` broadcasts `answer_count` on *every*
   answer (api.py:243-250); each broadcast fans to every socket.
3. Per-submit link validation: `submit_answer` full ORM insert (api.py:231-240) fires
   `validate_links` on TT Answer's `session`/`participant` Link fields → 2 extra SELECTs,
   both already validated upstream (api.py:214-216).

**B. Structural ceiling (why it gets worse under load).** `run_game_loop` is one
long-lived RQ job per game that busy-waits through every phase (`time.sleep` +
`POLL_SECONDS=0.25` Redis polling), holding a worker for the game's entire duration
(engine.py:43-63, enqueued engine.py:25-40). Against `background_workers: 3`, **>3
concurrent games starve the queue** and every game slows down.

The clean event-driven alternative (one short delayed job per phase boundary) is **not
available**: Frappe explicitly disables the RQ scheduler (`background_jobs.py:370` — "Always
disable RQ scheduler") and `frappe.enqueue` has no delay/`enqueue_at` parameter. So the
scalable design is a **single shared ticker** that advances all active sessions — one
worker slot for N games instead of one per game.

Goal: cut reveal lag to near-flat vs player count (Phase 1) and remove the worker-per-game
ceiling (Phase 2). All changes localized to `trivia_tap/engine.py` and `trivia_tap/api.py`.

---

## Phase 1 — Hot-path fixes (do first, independently shippable)

### 1a. Batch scoring writes — `engine.close_question`
Replace the per-participant `set_value` loop with in-memory accumulation + two
`frappe.db.bulk_update` calls. Confirmed API: `frappe.db.bulk_update(doctype, {docname:
{field: value}})` → chunked CASE-WHEN SQL (frappe/database/database.py:1020).
- Loop builds `answer_updates = {answer.name: {"is_correct", "points"}}` and
  `participant_updates = {p.name: {"score", "streak"}}` (streak-reset-to-0 for
  non-answerers goes in the same dict) — no I/O inside the loop.
- After loop: `frappe.db.bulk_update("TT Answer", answer_updates)` and
  `frappe.db.bulk_update("TT Participant", participant_updates)`, then the existing single
  commit + push. Commit drops from ~2P queries to ~2.

### 1b. Batch ranks — `engine.finish_session` (engine.py:239-263)
Replace the per-participant rank loop with one
`frappe.db.bulk_update("TT Participant", {name: {"rank": rank}})`.

### 1c. Move `answer_count` off the submit path
Delete the `answer_count` `publish_session_event` from `api.submit_answer`
(api.py:243-250). Submit then does only `mark_answered` + insert. The count is instead
broadcast (throttled) by the loop/ticker that already runs — see Phase 2 (in the interim
pre-Phase-2 state, emit it from `wait_question_window`'s tick, ≥~300ms apart, only when the
count changed).

### 1d. Skip redundant link validation — `api.submit_answer`
`.insert(ignore_permissions=True, ignore_links=True)`. Duplicate protection still enforced
by the `(participant, question_row)` unique index.

---

## Phase 2 — Shared ticker (removes worker-per-game ceiling)

Convert the per-game imperative loop into a **per-session state machine advanced by one
shared ticker job**. Reuses the existing phase bodies; only the timing/wait mechanism changes.

### Active-session registry (Redis)
- `tt:active_sessions` set (reuse `frappe.cache.sadd`/`smembers`/`srem`, as the answered-set
  already does). Add on start, remove on finish/abandon.
- Extend the per-session Redis state (`set_state`) to carry `phase`, `index`, `next_ts`
  (wall-clock time the next transition is due) alongside the existing `question_row`,
  `deadline_ts`, `window_ms`.

### The ticker — `engine.run_ticker`
One self-looping RQ job, `job_id="tt_ticker"`, `deduplicate=True`, on the `long` queue:
```
while True:
    sessions = frappe.cache.smembers("tt:active_sessions")
    if not sessions: break                 # idle -> exit; next game re-enqueues it
    now = time.time()
    for s in sessions:
        state = get_state(s)
        if not state: srem(s); continue
        control = pop_control(s, ("skip", "advance", "end"))
        if control or now >= state["next_ts"]:
            advance_session(s, control)     # transition; sets next phase+next_ts, or srem on finish
        else:
            maybe_push_answer_count(s, state)   # throttled, only during open question
    frappe.db.commit()                      # flush after_commit realtime for this pass
    time.sleep(TICK_SECONDS)                 # 0.5s; one worker total for all games
```
`enqueue_game_loop` becomes: seed initial state (`phase="get_ready"`, `index=0`,
`next_ts=now+GETREADY_SECONDS`), `sadd` to `tt:active_sessions`, then
`frappe.enqueue("trivia_tap.engine.run_ticker", queue="long", job_id="tt_ticker",
deduplicate=True)` — the dedup guarantees at most one ticker regardless of how many games
start. Called from `api.start_session` as today.

### `advance_session(session, control)` — the state machine
Dispatch on `state["phase"]`, reusing the current function bodies with their `while/sleep`
wait loops stripped out:
- `end` control (any phase) → `finish_session` + `srem`.
- `get_ready` & due → `open_question(index)`; set `phase="question"`,
  `next_ts = deadline_ts + GRACE_SECONDS`.
- `question` & (due or `skip`) → `close_question(index)`; set `phase="stats"`,
  `next_ts = now + STATS_SECONDS` if `auto_advance` else `now + ADVANCE_WAIT_CAP`.
- `stats` & (due or `advance`) → if last index → `finish_session` + `srem`; else
  `get_ready(index+1)`, `phase="get_ready"`, `next_ts = now + GETREADY_SECONDS`.

`get_ready` / `open_question` / `close_question` / `finish_session` keep their existing
push + write logic (now batched per Phase 1); they lose only their internal wait loops.
`POLL_SECONDS` and the three busy-wait loops (`get_ready` 92-96, `wait_question_window`
122-129, `wait_before_next` 200-212) are deleted. `run_game_loop` is removed.

### Timing / correctness
- `TICK_SECONDS = 0.5` → phase boundaries and host commands fire within 0.5s; reveal after
  timer-zero is ≤0.5s + existing 1s grace, comparable to today. Drop to 0.25s if snappier
  host feel is wanted (still one worker).
- Submit gate is unaffected: it validates against `deadline_ts + GRACE` in Redis
  (api.py:221), independent of exactly when `close_question` fires.
- Crash recovery unchanged and self-healing: existing `engine.is_abandoned`
  (host/player-load settles a dead game). If the ticker dies, the next `start_session`
  re-enqueues it (dedup no-ops while alive) and it picks up every session in
  `tt:active_sessions`. Single ticker = no two workers mutate one session.

---

## Explicitly skipped
- **Push-before-persist reveal decoupling** — after 1a the commit is cheap; pushing scores
  before durability adds a crash-consistency edge case for little gain.
- **Replacing `.insert()` with raw SQL** — TT Answer is hook-free; with `ignore_links=True`
  the ORM insert is essentially the raw INSERT. Keep the safety net.
- **Running our own rq-scheduler for exact per-phase delayed jobs** — fights the framework
  (Frappe disables it deliberately); the shared ticker gives the same scalability with 0.5s
  granularity, which is fine for phase boundaries.

## Verification
1. `bench --site trivia-tap.localhost run-tests --app trivia_tap` — confirm scoring/rank/finish
   results unchanged after batching and the state-machine port.
2. `/agent-browser` (headless), `trivia-tap.localhost`, Administrator/admin: host a quiz, join
   3+ guest tabs, play through — each question **reveal** appears promptly, host
   **answer-count** ticks smoothly, skip/advance/end feel snappy.
3. **Scalability check** (the point of Phase 2): start 5+ concurrent games (multiple host
   tabs) and confirm all advance normally with `background_workers: 3` — old code would
   starve at >3. Confirm only one `tt_ticker` job exists.
4. Larger simulated field (script many `submit_answer`s) → reveal time flat vs player count.
5. Per CLAUDE.md: Telegram message with before/after reveal screenshots.

## Key files
- `trivia_tap/engine.py` — new `run_ticker`/`advance_session` state machine; batched
  `close_question`/`finish_session`; delete `run_game_loop` + the three wait loops +
  `POLL_SECONDS`; `enqueue_game_loop` seeds state + registers session + dedup-enqueues ticker.
- `trivia_tap/api.py` — `submit_answer` (drop answer_count push, add `ignore_links=True`);
  `start_session` unchanged call site.
