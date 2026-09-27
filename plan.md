# TriviaTap: Build Plan

**TriviaTap** is a standalone product: Kahoot-style live multiplayer quiz on Frappe. Guests join with PIN or QR, no login. Server-authoritative anti-cheat.

Naming: product/brand = TriviaTap everywhere. App `trivia_tap`, module `TriviaTap`, DocType prefix `TT`, event prefix `tt_`, Redis prefix `tt:`.

## 1. Research: what Kahoot/Quizizz do

### Kahoot (game-show model, our core template)

- Host starts a game: big screen shows game PIN + QR code + join URL.
- Players go to join page, enter PIN (or scan QR which prefills it), pick a nickname, land in lobby. No account needed.
- Lobby: names pop onto host screen as they join. Host can kick players and lock the lobby. Nickname generator option avoids inappropriate names.
- Game: all players get each question simultaneously with a countdown (default 20s, per-question override). Up to 1000 points per question, scaled by answer speed. Some question types carry no points.
- Between questions: correct answer reveal, answer distribution bar chart, top-5 leaderboard, streak callouts ("X is on a 3 answer streak"), position-change messages.
- End: top-3 podium with animation.
- Classic mode: question + options on the shared host screen, players see only 4 colored shape buttons. Remote-friendly variant shows full question on player device too.

### Quizizz (juice model, our v2 inspiration)

- Every player sees the question on own device, works without shared screen.
- Power-ups: x2 points, immunity (second chance), power play. Earned by streaks/correct answers.
- Memes between questions, customizable avatars, music.
- Nickname generator gives 3 safe options to pick from.

### What we take

| v1 (core game) | v2 (juice) |
|---|---|
| PIN + QR join, nickname, lobby | Avatars |
| Kick + lobby lock + name filter | Nickname generator |
| Synced questions, per-question timer | Memes between questions |
| Speed-scaled points (Kahoot formula) | Power-ups |
| Streak bonus | Music/sfx |
| Answer distribution + top-5 between questions | Team mode |
| Top-3 podium | Shared-screen mode (question only on host screen) |
| Host controls: skip, end early | Question images |

v1 player device shows the full question (remote-friendly). Colored shape buttons for options keep the Kahoot feel.

## 2. Architecture (Frappe specifics)

- App `trivia_tap`, module `TriviaTap`. Stable Frappe v16, no nightly/experimental features.
- **Push:** `frappe.publish_realtime(event, data, room=...)` for everything server to client. One event name per session: `tt_session_{pin}`, payload carries `type` field (lobby_update, countdown, question, question_closed, leaderboard, podium, kicked, session_ended). Client subscribes once, switches on type.
- **Pull:** every client to server action is a whitelisted HTTP API with `allow_guest=True` where needed. Never socket emit for actions (custom socket handlers are experimental/nightly in Frappe).
- **Game loop:** one RQ background job per active session (`queue="long"`, `job_id=f"tt_session_{name}"`, `deduplicate=True`). Loop: publish question, sleep window, close, score, publish stats, next. Timeout sized to quiz length (questions x seconds + margin).
- **Timing:** no per-second server ticks. Question payload carries server-set `deadline_ts` (epoch float). Client renders its own countdown. Server validates every submit against Redis state.
- **Hot state in Redis** (`frappe.cache`), keyed per session: active question index, question opened_at, deadline_ts, session status. DB is the durable record; Redis is the fast gate for submit validation.
- **Guest sockets, Phase 0 spike:** verify a guest (no login) socket.io connection receives events published to our room on v16. Expected path: website room / explicit room param. If guests cannot receive room events on stable v16, fallback is a 1s short-poll state API for players (host stays on socket). Decide in the spike, do not build both.

### Live session flow

1. Host (logged-in Desk user with Quiz Host role) creates TT Session from a quiz. PIN generated, status Lobby.
2. Player: GET join page, enters PIN + nickname (or QR link prefills PIN). `join_session` API validates PIN, lobby open, nickname unique + clean, creates TT Participant, returns `participant_token`. Token stored in localStorage. Lobby update published.
3. Host locks lobby (optional) and starts. Status Active, game loop enqueued.
4. Per question: loop writes Redis state, publishes `question` (text + options, NO correct answer, deadline_ts, index, total), sleeps until deadline + grace, closes question in Redis, scores answers, publishes `question_closed` (correct option, distribution, top-5, streaks).
5. Host advances (or auto-advance after N seconds, host setting). Loop continues.
6. After last question: final ranks computed, `podium` published (top 3 + full leaderboard), status Ended, results persisted.

Host drop does not kill the game: the loop is server-driven, host can reload and resume control (host screen state API). Manual "end session" API for the host.

## 3. Database design (DocTypes)

### TT Quiz (the content)

Authored in Desk by hosts. `autoname: format:TT-{####}`.

| field | type | notes |
|---|---|---|
| title | Data, reqd | |
| description | Small Text | |
| default_time_limit | Int, default 20 | seconds per question |
| questions | Table -> TT Question | |

### TT Question (child, istable)

| field | type | notes |
|---|---|---|
| question_text | Small Text, reqd | |
| option_1..option_4 | Data, reqd | canonical order, server-side only |
| correct_option | Select 1\n2\n3\n4, reqd | NEVER serialized to players until close |
| time_limit | Int | blank = quiz default |
| points_multiplier | Select 0\n1\n2, default 1 | 0 = fun question, 2 = double |

Child rows have stable `name` (row id); answers reference it.

### TT Session (one running game)

`autoname: hash`. Fields:

| field | type | notes |
|---|---|---|
| quiz | Link TT Quiz, reqd | |
| host | Link User, reqd | set server-side to session creator |
| game_pin | Data, unique | 6 digits, generated, reused pins avoided while active |
| status | Select Lobby\nActive\nEnded\nCancelled | |
| lobby_locked | Check | |
| auto_advance | Check, default 1 | else host advances |
| randomize_answer_order | Check, default 1 | per-participant display shuffle |
| current_question | Int, default -1 | index into quiz questions |
| started_at / ended_at | Datetime | |

### TT Participant

`autoname: hash`.

| field | type | notes |
|---|---|---|
| session | Link TT Session, reqd | |
| nickname | Data, reqd | unique per session (validated in controller) |
| token_hash | Data | sha256 of participant_token; raw token never stored |
| score | Int, default 0 | |
| streak | Int, default 0 | current correct streak |
| rank | Int | final rank, set at end |
| kicked | Check | kicked tokens rejected on all APIs |
| joined_at | Datetime | |

### TT Answer

`autoname: hash`.

| field | type | notes |
|---|---|---|
| session | Link TT Session, reqd | |
| participant | Link TT Participant, reqd | |
| question_row | Data, reqd | child row name of TT Question |
| selected_option | Select 1\n2\n3\n4 | |
| is_correct | Check | computed server-side |
| response_ms | Int | server receive time minus question opened_at |
| points | Int | computed server-side |

**Composite unique constraint** (participant, question_row) via `on_doctype_update()`:

```python
# tt_answer.py
def on_doctype_update():
    frappe.db.add_unique("TT Answer", ["participant", "question_row"])
```

Duplicate submits die at the DB level regardless of race conditions.

### Redis keys (hot path, not DocTypes)

```
tt:{session}:state        -> {status, q_index, question_row, opened_at, deadline_ts}   TTL: window + 30s
tt:{session}:answered:{q} -> SET of participant names (fast duplicate pre-check)       TTL: window + 30s
```

### Permissions

- TT Quiz, TT Session: role Quiz Host (create/write own), System Manager all. `if_owner` for hosts.
- TT Participant, TT Answer: no direct role access for anyone but System Manager. All reads/writes go through whitelisted APIs. Guests never touch the REST resource API.
- correct_option: exists only in TT Question, which guests can never read. Question delivery API builds the payload explicitly, field never included.

## 4. API surface (whitelisted)

Guest APIs (`allow_guest=True`, rate-limited via `frappe.rate_limiter`):

| endpoint | args | does |
|---|---|---|
| `join_session` | pin, nickname | validate lobby open + not locked, nickname clean/unique, create participant, return token + session snapshot |
| `get_state` | pin, token | current state for reconnect: status, current question (no answer), deadline_ts, own score. Also the polling fallback |
| `submit_answer` | pin, token, question_row, selected_option | full validation gauntlet (below), store answer, return ack only (no correctness leak) |
| `leave_session` | pin, token | mark left, lobby update |

Host APIs (login + Quiz Host role, host must own session):

| endpoint | does |
|---|---|
| `create_session` | from quiz, generate PIN |
| `lock_lobby` / `unlock_lobby` | |
| `kick_participant` | sets kicked, publishes `kicked` targeted payload |
| `start_session` | enqueue game loop |
| `next_question` | when auto_advance off |
| `skip_question` | close current early |
| `end_session` | abort loop, straight to podium |

### submit_answer validation gauntlet (order matters)

1. Rate limit per token.
2. Session exists, status Active.
3. Token hash matches a participant of this session, not kicked.
4. Redis state: question_row equals the currently active question.
5. `server_now <= deadline_ts + 1.0` (grace for network only).
6. Redis answered-set pre-check, then DB insert; unique constraint is the final word.
7. Score computed server-side, from server timestamps.

Return only `{"ok": true}`. Correctness revealed to everyone at question close, never per-submit.

## 5. Scoring (server-side only)

Kahoot formula, computed at question close time or on submit:

```
if incorrect: 0, streak = 0
if correct:
    base = round((1 - (response_ms / window_ms) / 2) * 1000)   # 500..1000
    streak += 1
    bonus = min(streak - 1, 5) * 50                            # 0..250
    points = (base + bonus) * points_multiplier
```

response_ms is server receive time minus server opened_at. Client timing never used.

## 6. Anti-cheat summary

1. Correct answer never in any payload until question closed.
2. Server-set deadline, 1s network grace, all timestamps server-side.
3. DB composite unique (participant, question_row): duplicates impossible.
4. Active-question gate in Redis: cannot answer past/future questions.
5. Tokens: 32-byte random, only sha256 stored, kicked flag kills token.
6. Per-participant answer-order shuffle on display (seeded by token client-side); canonical option ids on the wire, so shuffle defeats neighbor-copying, not scoring.
7. Question bank unreadable by guests; payloads hand-built in API code.
8. Rate limiting on all guest APIs; nickname profanity filter.
9. Scores computed and persisted server-side only.

Residual: one human, several devices/tabs, several nicknames. Host kick + lobby lock is the mitigation; only proctoring would close it fully. Accepted.

## 7. Frontend (Vue SPA)

Vue 3 + frappe-ui + Vite SPA in `frontend/`. frappe-ui gives Frappe-aware composables (`useCall`, `useList`, `useDoc`) and a Vite plugin with dev proxy + DocType type generation. socket.io-client for realtime.

Wiring (standard Frappe SPA pattern):

- SPA lives in `apps/trivia_tap/frontend/`; production build outputs to `apps/trivia_tap/trivia-tap/public/frontend` (`bench build --app trivia_tap`).
- Served via `website_route_rules` in hooks.py: `{"from_route": "/trivia-tap/<path:app_path>", "to_route": "trivia_tap"}`.
- Vite dev server proxies `/api` to the running `bench start` backend.

Two route groups:

Player (guest, mobile-first):
- `/join` PIN entry (QR link `/join?pin=XXXXXX` prefills), nickname screen.
- `/play` one screen, state machine: lobby -> get-ready countdown -> question (4 colored shape buttons, local countdown bar) -> locked-in wait -> result interstitial (correct/wrong, +points, rank, top-5) -> podium.
- Reconnect: token in localStorage, `get_state` on load rejoins mid-game.

Host (logged in, big-screen-first):
- `/host` quiz picker -> session created: lobby screen with giant PIN + QR (client-side QR lib) + join URL + player names grid + lock/kick/start.
- Game view: current question, live answer count, distribution reveal, top-5, next/skip/end controls.
- Podium screen: top 3 animation, full leaderboard, export results.

Quiz authoring: Frappe Desk in v1 (free CRUD UI on TT Quiz). Custom authoring UI in SPA later.

## 8. Build phases

### Phase 0: foundation + spike
- bench app `trivia_tap`, site, module TriviaTap, roles.
- SPA scaffold.
- SPIKE: guest socket.io receives room-published events on v15? Yes: socket push for players. No: 1s short-poll `get_state` for players, socket for host. Decide, delete the losing path.

### Phase 1: content + session shell
- DocTypes: TT Quiz, TT Question, TT Session, TT Participant, TT Answer (+ unique index).
- Host APIs: create_session, PIN generation. Join API + token issue.
- Lobby end-to-end: join via PIN/QR, names appear live on host screen, kick, lock.

### Phase 2: game engine
- RQ game loop, Redis state, question publish with deadline.
- submit_answer with full gauntlet. Scoring + streaks.
- question_closed payload: correct answer, distribution, top-5, streak callouts.
- Podium + persisted results.

### Phase 3: game UX
- Player screens polished: countdown bar, shape buttons, interstitials, podium.
- Host screens: distribution charts, leaderboard, controls (skip, end, auto-advance toggle).
- Reconnect flows both sides. Host-drop resilience.
- Nickname profanity filter.

### Phase 4: juice (v2)
- Avatars, nickname generator, memes between questions, sounds.
- Power-ups, team mode, shared-screen mode, question images.
- Results export (CSV) for host, session history.

## 9. Test checklist (engine)

- Submit after deadline+grace rejected.
- Duplicate submit rejected (API race: fire two in parallel, DB constraint holds).
- Submit for non-active question rejected.
- Kicked token rejected everywhere.
- Wrong PIN / locked lobby / duplicate nickname rejected.
- Scoring: boundary response times (0ms, window, window+grace), streak reset, multiplier 0 and 2.
- Correct answer absent from every payload before close (assert on serialized events).
- Reconnect mid-question gets correct remaining time.

## References

- Kahoot host flow: https://support.kahoot.com/hc/en-us/articles/360039422694-How-to-host-a-live-kahoot
- Kahoot join: https://support.kahoot.com/hc/en-us/articles/360039890713-Kahoot-join-How-to-join-a-Kahoot-game
- Kahoot live settings: https://support.kahoot.com/hc/en-us/articles/115016055107-Live-game-settings
- Kahoot vs Quizizz: https://triviamaker.com/kahoot-vs-quizziz/ , https://quizizz.com/home/quizizz-vs-kahoot
- Frappe realtime: https://docs.frappe.io/framework/user/en/api/realtime
- Frappe background jobs: https://docs.frappe.io/framework/user/en/api/background_jobs
