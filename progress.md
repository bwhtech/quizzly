# Progress

## Phase 10: Answer Explainer (2026-08-19)

Spec: `specs/phase-10-answer-explainer.md`. Optional explanation text + image per
question, shown on the reveal after the question closes, gated by a session toggle.

### Done

- `QZ Question` gains `explanation` (Small Text) and `explanation_image` (Attach
  Image). `QZ Session` gains `show_explainer` (Check, default 1).
- `engine.explainer_payload` is the single gate: empty dict unless the session
  wants an explainer and the question carries one. Rides `question_closed`,
  `get_host_state` (closed branch), and `get_result`. Never touches
  `question_payload`, so no pre-close payload can leak the answer.
- Auto-advance holds the reveal for `EXPLAIN_STATS_SECONDS` (12s) instead of
  `STATS_SECONDS` (5s), but only when an explainer is actually going to show.
- `set_auto_advance` replaced by `set_session_option(session, option, enabled)`
  with a `SESSION_OPTIONS` allowlist; the three session toggles share it.
- Host reveal renders an explainer card between the options and the distribution
  bars; player result renders it under the rank line. Editor gets a textarea and
  an image uploader per question, both added to `QUESTION_FIELDS`.
- Tests: 6 in `test_engine.py` (payload carried/omitted, toggle off, no leak in
  the open-question payload, both hold lengths), 6 in `test_game_ux.py` (both
  reconnect paths, option allowlist, host-only), 1 in `test_authoring.py`
  (explainer survives a reorder). Full suite green.

### Exit criteria verified

Played in a real browser on quizzly.localhost, host screen + player device:
quiz authored in the SPA editor with explainer text and an uploaded image, both
render on the reveal, a question without one shows the reveal unchanged with no
gap, both host and player reload mid-reveal and keep the card, and with the
toggle off the card is gone and `get_host_state` carries no explainer keys at
all. Checked on the wire during an open question: the guest `get_state` response
contains neither the explanation text nor the image path.

### Notes

- Two bugs the browser caught that the Python tests could not: the lobby's
  Auto-advance button still called the deleted `toggleAutoAdvance`, and passing a
  ref into `toggleOption(option, current)` from the template broke because Vue
  unwraps refs there, so `current.value` was always undefined and every toggle
  sent `enabled: 1`. Host toggles now live in one `options` object keyed by field
  name, and the handler takes only the option name.
- The explainer toggle sits in both the lobby control row and the in-game row, so
  a host can set it before starting or flip it mid-game.
- First cut stacked the explainer card above the distribution bars and pushed the
  host controls below the fold on a 1080p screen, which is unusable on a
  projector. The reveal now splits into two columns below the options (explainer
  left, stats right), the explainer image is capped in `vh`, and a question image
  yields to the explainer image on the reveal. Checked at 1280x720, 1366x768 and
  1920x1080 with a question carrying both images: no page scroll.

## Live Quiz Rework Phase 4: Trim Submit + Throttle answer_count (2026-07-23)

Spec: `specs/live-quiz-rework/phase-4-submit-and-count.md`. Cut the last two
per-answer costs, and fixed the guest-socket blocker Phase 3 flagged.

### Done

- `submit_answer` (`api.py`): insert now uses `ignore_links=True` (session-active
  and participant-by-token are already validated; the `(participant,
  question_row)` unique index still backstops duplicates). Removed the per-submit
  `answer_count` broadcast block entirely.
- Ticker (`engine.py`): `maybe_push_answer_count` broadcasts the live "N answered"
  count from the ticker instead, but only while a question is open, only on
  change, and at most every `ANSWER_COUNT_THROTTLE` (0.3s). Result: a few
  updates/sec total, flat regardless of player count. Throttle state + immutable
  pins live process-local in `run_ticker` (single deduplicated job), pruned each
  pass to the live session set so finished games don't leak.

### Root-cause fix: guest sockets received no live events (Phase 3 blocker)

- Symptom (Phase 3 note): with the real async ticker, players never advance
  `get_ready` -> `question`; they only limp via `get_state` resync.
- Reproduced with a guest socket.io client against the live socketio server: it
  receives `website`-room events but **nothing** on `qz_session_<pin>`, so no
  game events ever arrive live. Host "worked" only because the frontend resync
  watchdog papers over it for slow lobby changes, not fast question transitions.
- Root cause: `apps/quizzly/package.json` has `"type": "module"`, so Node loads
  `realtime/handlers.js` as ESM. The frappe socketio server `require()`s it as
  CommonJS and gets `{}` instead of the handler function; `app_handler(socket)`
  throws and is swallowed, so `qz_join`/`qz_leave` never register and no socket
  ever joins the session room.
- Fix: `apps/quizzly/realtime/package.json` = `{"type":"commonjs"}` overrides the
  module type for just that directory, so the CJS handler loads again without
  disturbing the ESM app root the frontend build relies on. Verified at the
  `require()` level (now returns `function quizzly_handlers`). **Needs a socketio
  restart to take effect** (the running server cached the failed load).

### Tests

- `run-tests --app quizzly`: 59 green. The engine test that filtered out
  `answer_count` events is unaffected (no such events emitted now).
- Lint: pre-commit clean on all changed files.

### Pending

- Browser E2E (3+ guests: counter climbs via ticker, players advance to
  questions and answer) is blocked on a `bench` restart to reload the socketio
  handler. Run after restart per the rework rule (no merge until browser green).

## Live Quiz Rework Phase 3: Batch Scoring Writes (2026-07-23)

Spec: `specs/live-quiz-rework/phase-3-batch-scoring.md`. Killed the N+1 write
loops so reveal time stops scaling with player count.

### Done

- `close_question`: the participant loop now builds two in-memory dicts and no
  longer does I/O per participant. `answer_updates` (`{answer: {is_correct,
  points}}`) and `participant_updates` (`{participant: {score, streak}}`,
  streak-reset-to-0 for non-answerers in the same dict) flush through two
  `frappe.db.bulk_update` calls after the loop. Same commit + `question_closed`
  push as before.
- `finish_session`: ranks persist via one `frappe.db.bulk_update("QZ
  Participant", {name: {"rank": rank}})` instead of one `set_value` per player.
- `bulk_update` builds chunked CASE-WHEN UPDATEs and does **not** commit
  internally, so the ticker's `qz_tick` savepoint isolation (Phase 2) is intact.
  It also no-ops on an empty dict, so a question nobody answered is safe.

### Tests

- `run-tests --app quizzly`: 22 engine + 15 game-ux tests green. Scores, streaks,
  ranks, and podium identical to before — batching changed no number.
- Load check (`scripts`-style console driver, 200 participants, half correct):
  `close_question` went **207.9 ms -> 36.7 ms**. The residual is the answer
  fetch, not the writes; write time no longer scales with player count.

### Browser E2E (quizzly.localhost)

- Host + 3 guests (Alice/Bob/Cara) played "General Knowledge" driven by the real
  async `long` RQ worker (not the synchronous driver Phases 1-2 fell back to).
  The shared ticker marched through all 5 questions and rendered a correct podium
  with ranks 1/2/3 on both host and player screens. `finish_session`'s batched
  rank write and `close_question`'s batched score writes ran with **zero** Error
  Log entries.
- Pre-existing, out-of-scope: with the real async ticker, the **player** view
  never advances from `get_ready` to the `question` phase (options never render),
  so guests can't answer and everyone scores 0. Host advances fine and gets every
  event. This is a player realtime/state issue untouched by this diff (which only
  edits `close_question`/`finish_session` DB writes) and predates it. Flagged for
  a separate fix; does not affect scoring correctness, which the unit suite gates.

## Live Quiz Rework Phase 2: Multi-Game Scale (2026-07-21)

Spec: `specs/live-quiz-rework/phase-2-multi-game-scale.md`. Proved the shared
ticker drives many concurrent games on the same workers with no starvation, the
payoff of Phase 1's redesign.

### Done

- `run_ticker` gained per-session isolation: each session's step runs under a
  `qz_tick` savepoint inside its own try/except, commits on success, and on error
  rolls back to the savepoint + `log_error`s and continues. One bad game can no
  longer stall or kill the ticker for the others.
- Fixed a real ticker bug the self-heal path was hiding: `get_state` read through
  Frappe's process-local cache (`use_local_cache` default True), so in the
  long-lived ticker a session whose state had expired in Redis still returned its
  last-seen dict forever. The `if not state: srem` self-heal never fired and the
  ticker spun on the vanished session. `get_state` now reads with
  `use_local_cache=False`, like `pop_control` already does.
- Lifecycle was already airtight from Phase 1 and confirmed so: `active_sessions`
  is `srem`'d on finish, on `end`, and on abandon (all route through
  `finish_session`); the ticker `srem`s any session whose state has vanished; and
  `enqueue_game_loop` always re-enqueues the deduped `qz_ticker`, so starting any
  new game self-heals a dead ticker and picks up every registered session.
  `is_abandoned` still settles a session the ticker somehow dropped.

### Tests

- `test_ticker_survives_bad_session`: seeds a bogus session that raises every pass
  alongside a real game; the real game still reaches the podium. Note: the guard
  must roll back to the **savepoint**, not call bare `frappe.db.rollback()`, which
  would discard the whole test transaction (and, in prod, sibling sessions' writes
  from the same pass).

### Browser E2E (quizzly.localhost)

- 5 concurrent games: 5 isolated browser guests joined 5 lobbies, all started, all
  rendered the same live question simultaneously (Q1 of 5), auto-advanced through
  all five questions, and every player reached the podium ("You won").
- Backend proof via `scripts/concurrent_games.py` (console driver, phases driven by
  the real `long` RQ worker): 5 games marched in lockstep get_ready -> question ->
  closed for q0..q4, with **exactly one** `qz_ticker` job the entire run
  (`max concurrent qz_ticker jobs observed: 1`).

## Live Quiz Rework Phase 1: Ticker Tracer (2026-07-21)

Spec: `specs/live-quiz-rework/phase-1-ticker-tracer.md`. Replaced the per-game
busy-wait loop (`run_game_loop`, one RQ job per session) with a shared ticker
plus a per-session Redis state machine.

### Done

- `run_ticker`: one self-looping RQ job (`job_id="qz_ticker"`, `deduplicate=True`,
  queue `long`). Each pass reads `qz:active_sessions`, per session pops control and
  advances when a control fired or `now >= next_ts`, commits, sleeps `TICK_SECONDS`
  (0.5). Exits when the active set is empty.
- `advance_session(session_doc, state, control)` dispatches on `state["phase"]`
  (`get_ready` -> `question` -> `stats` -> next / finish). `end` control finishes
  any phase.
- `get_ready` / `open_question` / `close_question` lost their internal while/sleep
  loops; they now just write state (extended with `phase` and `next_ts`) and push.
  `close_question` reads `auto_advance` fresh to size the stats wait.
- `enqueue_game_loop` seeds the first `get_ready` state, `sadd`s the session, then
  enqueues the shared ticker. `finish_session` `srem`s on the way out.
- Deleted `run_game_loop`, `wait_question_window`, `wait_before_next`, `POLL_SECONDS`.
- Tests green (`test_engine`, `test_game_ux`): `TestGameLoop` now drives the game via
  `enqueue_game_loop` + `run_ticker`; added coverage for auto-advance-off hold and
  advance-on-last-question finish.

### Browser E2E (quizzly.localhost)

- Full game played host + guest: get_ready pause -> question + countdown -> reveal
  -> auto-advance -> podium. Host **skip** closed the question within ~0.5s; the
  ticker exited with no lingering job after finish.
- Env note: this bench's `long` RQ queue had no worker and was clogged with hanging
  jobs from another site, so the browser run drove `run_ticker` synchronously via
  `bench execute` (same realtime path). The RQ enqueue/dedup itself is unchanged
  standard `frappe.enqueue`.

### Branches

- Work committed on `feat/live-quiz-ticker` (spec commit + implementation commit).
- Branched `experimental` off it and merged `feat/live-quiz-ticker` in (fast-forward,
  same commits). Both branches local only, not pushed.

## Phase 9: README with screenshots (2026-07-20)

Spec: `specs/phase-9-documentation.md`. The README was still the app-scaffold
default. It is now the front door: hero image, what-it-is, a collapsed gallery
of eight screenshots, features, stack, dev setup, testing, contributing.

### Done

- Eight screenshots in `docs/images/`, all from one real session against
  `quizzly.localhost` (520 KB total). Host shots at 1440x900, player shots at
  390x844 with DPR 2, one player shot in dark theme. Podium needed 1440x1010
  to fit its leaderboard and button in a single frame.
- `scripts/seed_demo.py`: creates the "General Knowledge" demo quiz. Run with
  `bench --site quizzly.localhost console < scripts/seed_demo.py`.
- `scripts/demo_bots.py`: joins seven named players over the guest HTTP API and
  answers questions for them at plausible accuracies, so the lobby,
  distribution and podium look like a real game. Both scripts are throwaway
  tooling for pictures, not fixtures.
- No CI badges: this repo has no git remote yet, so the badge URLs would not
  resolve. Add them with the remote.

### Verified

`bench --site quizzly.localhost run-tests --app quizzly`: 56 tests, all green.
`pre-commit run --all-files`: clean. Every command in the README was run as
written.

### Notes

- The bench runs a single `bench worker` serving short, default and long. The
  game loop is enqueued on `long`, and while that worker was busy with another
  site's scheduled jobs the loop never started, so `is_abandoned` fired at 30s
  and every session jumped straight to an all-zero podium. Captures needed a
  dedicated `frappe worker --queue long` alongside it. Not an app bug, but a
  real deployment constraint: a live game needs a worker that is not competing
  with scheduled jobs.
- The podium screen scrolls inside its own container, not the window, so with
  eight players a 900px-tall viewport clips the tail of the leaderboard and the
  "New game" button. Reachable, but only if you know to scroll there.

## CI workflow fixes (2026-07-20)

Spec: `specs/phase-8-ci.md`, written after comparing our workflows against `frappe/wiki`. We already had wiki's server-test and linter jobs, on newer action and MariaDB versions than theirs. The one real gap is Playwright E2E, which wiki has and we don't, and which matters more here than there: quizzly is two browsers and a socket server, and the seam between them is exactly what `bench run-tests` cannot see.

The E2E harness is not built. It is half a day of work (root `package.json`, config, auth setup, two-context helpers, socketio under CI, countdown-timer flake), and `/agent-browser` already covers every fix manually, so the gap is "no unattended gate", not "untested app". Deferred until someone else contributes or a realtime regression ships unnoticed.

Three config fixes shipped now, no new dependency:

- `ci.yml` concurrency group was `develop-quizzly-${{ github.event.number }}`. That expands to empty on `push`, so every push to develop shared one group key and cancelled the run before it. Now `${{ github.event.number || github.ref }}`.
- `ci.yml` gained `paths-ignore` for `**.js`, `**.vue`, `**.css`, `**.ts`. Frontend-only changes no longer build a bench to run python tests that cannot have changed.
- Dropped the `cypress/.*` exclude from the eslint pre-commit hook. Inherited from boilerplate; no such directory ever existed here.

### Verified

Both files parse as YAML. `paths-ignore` and the concurrency key only demonstrate themselves on a real PR, so neither is verified beyond that.

## Theme toggle on the player side (2026-07-20)

The light theme shipped with a control on the host bar and in the lobby row, so only a logged-in host could switch. Players got whatever `prefers-color-scheme` said and no way out of it, which is backwards: the host is on one laptop they control, the players are on twenty phones in a room whose brightness nobody polled.

- `ThemeButton.vue` wraps the existing `cycleTheme` from `theme.js`. Icon-only (🌗 auto, ☀️ light, 🌙 dark) with the label in `aria-label` and `title`, matching the mute button next to it rather than the host bar's text pill, because the player header is a phone header with no room for words.
- Placed in the `Play.vue` header beside mute, and absolutely positioned top-right on `Join.vue`, which has no chrome of its own. `HostBar.vue` and `Host.vue` then dropped their "Theme: auto" text buttons for the same component, so one glyph means one thing everywhere in the app.
- The component carries no styling of its own, only the glyph, the cycling and the label. The host wears it as a `ctl` pill, the players as a bare header icon, and `.ctl` is plain CSS that sits after Tailwind's utilities in `index.css`, so a component with default padding could not be overridden into a pill anyway. The player pages repeat the four utility classes rather than the component growing a variant prop.
- No state added. `theme.js` already persists to `localStorage` and applies on load, so a player's choice survives join, the whole game, and a reload.

### Verified

Real join at 390x844: toggled on the join screen (auto → light), joined a live session with a PIN from `create_session`, and the choice carried into the play header, where cycling to dark repainted the lobby. Host side at 1280x800: the pill in the quizzes bar and the one in the lobby control row both cycle and repaint. Test sessions deleted afterwards.

## Phase 7: avatar carousel (2026-07-20)

Spec: `specs/phase-7-avatar-carousel.md`. Shipped as specced, `Join.vue` only, no backend.

- Every slot keeps the large size and only the face inside scales (`scale-[0.62]` unselected, `scale-100` selected). Sizing the button itself would reflow the row on every tap and jump the strip under the thumb; a transform does not reflow, so the row height and the join button below it stay put.
- The ring, background, scale and opacity all moved onto a `<span>` inside the button. The button is now just the fixed slot, so the gold ring hugs the big face instead of a full-size slot around a shrunken one.
- Centring became a `watch` on the selection with `flush: "post"` (plus the existing `onMounted` call, since an `immediate` watcher fires before the DOM exists). `motion-safe:scroll-smooth` animates it, and is `motion-safe` because CSS `scroll-behavior` is not covered by the global reduced-motion transition-duration override.
- Strip moved out of the desktop right column (`md:col-span-2`) and dropped its `md:max-w-sm` cap, so desktop reads PIN, nickname, faces, join, the same order a phone already had.
- Then the desktop layout went away entirely: `Join.vue` has no `md:` classes left. The two-column grid was only ever there to balance the tall 6-column avatar block, and once the faces were a strip the wide form was two stretched inputs next to each other and nothing else. One centred `max-w-sm` column at every width, so what a host sees on a laptop is what the players see on their phones. Same reason the strip keeps its gutter bleed on desktop now: the cut-off faces at the edge are what say it scrolls, at any width.

- Strip trim: `.no-scrollbar` (new utility in `index.css`, `scrollbar-width: none` plus the `-webkit-scrollbar` rule) hides the desktop bar under the row, which was redundant next to the cut-off faces at the gutter. `pb-1` became `py-1.5`, because `overflow-x: auto` also clips vertically and the selected face's ring was losing its top edge. Gap tightened to `gap-1`, since a shrunken 27px face inside a 44px slot already carries most of the spacing.

### Verified

Headless browser at 390x844 and 1280 wide. Phone: opening random pick lands centred and big, tapping the last face in the roster scrolls the strip to its end (`scrollLeft` 890 of max 890) with the join button unmoved. Desktop: strip is the full-width row between the inputs and the join button. `pre-commit` clean on the changed file.

## Phase 5 leftovers: light theme and avatar strip (2026-07-20)

Spec: `specs/phase-5-visual-identity.md`, both sections rewritten from "Deferred" to what shipped. Phase 5 now has nothing outstanding.

### Light theme

- The spec's plan was to make all eight tokens flip. That was the wrong split, and building it showed why: the four answer inks are the brand. A player learns "red is top-left" once, and a tile that changes hue with the room breaks the one thing the colour scheme exists to do. They do not theme at all.
- What themes is the ground and what sits on it: `night` / `dusk` / `haze` / `paper`, plus `alert` / `accent` / `ok`. The second trio is the ember, gold and lagoon hues *as text on the ground*, which has to carry 4.5:1 and so darkens where the fill below it cannot. One token could not be both a vivid tile and legible small text on white; splitting the roles is what the original plan missed.
- Fixed, never themed: `ember`, `lagoon`, `gold`, `orchid` (the tiles), `sunk` (the ink they carry), `card` (the QR quiet zone, which needs a light ground in either theme).
- Tokens are RGB channel triplets, not hex, so Tailwind's opacity modifiers keep working: `text-paper/40` is used 13 times.
- `prefers-color-scheme` picks the default. A Theme control on the host bar and in the lobby control row overrides it in both directions and persists in `localStorage`. The OS preference alone was not enough: the case this exists for is a bright room, and the laptop driving the projector is usually still set to dark. It is in the lobby row as well as the bar because the bar is hidden once a game starts, which is exactly when a host notices the screen washing out.
- Deleted `SHAPES[].hex` in passing: dead since phase 5, nothing read it.

### Avatar scroll strip

- One horizontal `overflow-x: auto` row with `snap-x`, capped `max-w-sm` on desktop. It bleeds past the page gutter on a phone, because the faces cut off at both edges are the only thing that says it scrolls.
- The opening pick is random and lands anywhere in the roster, so the selected button scrolls itself into view on mount. Without that the strip opens on the first face and nothing looks chosen.

### Verified

Full game in a real browser, host at 1440x900 and two guests: picker, lobby, read time, question (with and without an image), reveal, leaderboard, podium, plus both player views, in light and again in dark to check for regressions. Join screen at a real 390x844 viewport in both themes: the strip is one row and the join button clears the fold. Toggle checked to persist across a reload. 56 tests green, `pre-commit run --all-files` clean.

### Known gap

`--color-scheme` emulation reverted to dark partway through a browser session more than once, so the OS-preference path was confirmed on the join page and the toggle carried the rest of the run. The two paths set the same tokens.

## Fix: host screen on a phone (2026-07-20)

No spec. `Host.vue` only, no API and no doctype change. Every host screen was sized for a projector and broke at 390px.

### Done

- Lobby: PIN `text-6xl` up to `sm:text-8xl`, QR `size-40` up to `sm:size-48`, padding and gaps scaled, and the PIN block centres under the QR on a phone. The copy button moved inside the join-host `<p>` as an inline element, so it follows the last line when the URL wraps instead of floating beside the first.
- Question: the question text takes its own full-width row below the timer ring and the answer counter (`flex-wrap` plus `order-last w-full sm:order-none`). Beside a 96px ring and a counter it had a column too narrow to read two words in. The question image caps at 22vh under `sm`, which keeps all four options on screen without scrolling.
- Results and podium: display sizes scaled, podium columns `w-24` up to `sm:w-36`, and leaderboard rows got `gap-3` with `truncate` on the nickname and `shrink-0` on the score, which used to collide.

### Verified

Live on `quizzly.localhost` at 390x844: lobby with and without a player, get-ready, question, closed stats, podium. Desktop at 1440x900 renders identically to before on the lobby and question screens.

### Notes

- The bench `long` queue is backed up with jobs from other sites behind a single worker, so `run_game_loop` never gets picked up: a started game sits on "Starting…" until `is_abandoned` settles it and the host lands on the podium. Testing ran the loop directly with `bench execute quizzly.engine.run_game_loop`. Bench config, not app code.

## Phase 6: Navigation (2026-07-19)

Spec: `specs/phase-6-navigation.md`. Frontend only, no API and no doctype change.

### Done

- `components/HostBar.vue` on `/host`, `/host/quizzes`, `/host/quizzes/:name`: wordmark, Host/Quizzes links with the existing `data-on` active treatment, the logged-in user, and logout through the framework's own `logout` method. Rendered by the three screens rather than by a layout route, because `App.vue` is a bare `<router-view />` and turning it into a layout host would cost more than the three lines of markup it saves.
- The bar is hidden the moment `/host` holds a live session. A lobby, question, or podium is what 40 people in a room look at, and nav on it competes with the PIN.
- The per-screen back links it replaces are gone (`← Back to hosting`, `← All quizzes`), as is the picker's `Edit quizzes` link; the picker keeps a `New quiz` CTA only while the host has no quizzes.
- `readError(e)` in `api.js` now backs every host screen's catch. A non-host used to get whatever the framework said, which names doctypes and permissions; the editor did not translate it at all.
- `End game` names the cost: "End the game for all N players". A mid-game leave keeps the participant row on purpose (scores), so the count stays truthful after someone walks out.
- Player `Leave` moved from the lobby and podium screens into the persistent header, so it exists during a question too. Hidden on the podium, where `Back to join` is already the primary action, and on `kicked`, where the header does not render.

### Verified

End to end on `quizzly.localhost`: host nav across all three screens with the active pill correct, bar gone the instant a game started and back after `New game`, a player leaving mid-question and landing on `/join`, logout landing on `/join`, and a logged-out `/host` bouncing to login with the redirect intact. 56 tests green, `pre-commit run --all-files` clean.

### Deferred

- **Session history nav.** `/host/history` is specced in phase 4b and unbuilt. It becomes one more link in the bar and nothing else, which is the point of having the bar in one component now.
- **Mobile host bar.** Plain text links fit at 390px. Collapse it when a fourth or fifth link makes it wrap.

## Phase 4a: Content authoring (2026-07-19)

Spec: `specs/phase-4a-content-authoring.md`. The last slice of phase 4, shipped after 4b/4c and phase 5. Removes the Desk-only authoring constraint: a host now writes and plays a quiz without leaving the SPA.

### Done

- `QZ Question.image` (Attach Image). `question_payload` carries `image_url`, null when absent, so an image-free quiz publishes exactly what it published before. Rendered contained above the answer grid on both screens: 40vh on the projector, 26vh on the phone, so options never leave the fold.
- Authoring runs on `frappe.client.*` (`get`, `insert`, `save`, `delete`), plus one endpoint, `list_quizzes`, for the per-quiz question count. Four hand-written CRUD APIs were built first and then deleted: they re-implemented the framework, and their by-hand ownership check duplicated `if_owner` on `QZ Quiz`. They were not a smaller attack surface either, since `frappe.client.save` is whitelisted for every logged-in user regardless.
- Two rules the standard path imposes on the client, both found by testing and now pinned: send the loaded doc back as it came (frappe refuses a save that drops `creation` or `owner`, and rejects a stale `modified`, which is concurrent-edit protection the hand-written `save_quiz` silently lacked), and rebuild the question rows without `name` or `idx` (frappe keeps an `idx` it is given, so rows carrying the old one ignore a reorder).
- Validation split by kind. The `QZ Quiz` controller owns integrity (at least one question, non-blank text and options, `correct_option` in 1..4) so nothing on any path can write a quiz the engine cannot play. The editor owns the 5..120 second range with native `min`/`max` and a clamp, because it is an authoring taste: engine tests use 1 to 2 second questions on purpose, and putting the range in the controller broke 26 of them for no gain.
- `/host/quizzes` (list, create, delete) and `/host/quizzes/:name` (editor). Options are edited inside the four game-coloured pills with the correct-option radio in place, so the author sees the player's screen while writing. Image upload is frappe-ui's `FileUploader` against the framework's `upload_file`, no custom endpoint.
- The `/host` quiz picker now reads `list_quizzes` instead of `frappe.client.get_list` and links to the editor.
- Tests: 5 in `tests/test_authoring.py`, covering only what this app adds to the standard path (reorder through `frappe.client.save` landing in `idx` order, the controller's rejections, the question count, `LinkExistsError` on a played quiz, `image_url` present and null). 56 green across the app.

### Exit criteria verified

Quiz written entirely in the SPA (two questions, a checkerboard PNG uploaded onto the first), then hosted and played to podium with a real guest in a second browser: image on both host and player question screens, answers scored (1379), podium reached. Desk never opened. The image-free question rendered identically to before. `pre-commit run --all-files` clean.

### Fixed while testing

- The editor showed `0` in an unset time-limit field, because an unset Frappe Int reads back as 0. It now loads as empty and shows the quiz default as the placeholder.
- Native radios inside the coloured answer pills rendered as a white disc with a blue dot: frappe-ui's stylesheet fills inputs, and `accent-color` alone could not fix the ground. They are `appearance-none` circles drawn from the border now.
- A refused delete printed the framework's link error verbatim, HTML and all, so the host read raw `<a href>` markup pointing into Desk. The list now catches `LinkExistsError` by `exc_type` and says the quiz has been played.

### Deferred

- **Drag-reorder.** Up/down buttons instead, no dependency. Build drag when a host writes ~30-question quizzes and moving a row means crossing a screenful.
- **Uploaded images are not attached to the parent quiz**, because a new quiz has no name yet when the picture is picked. They are ordinary public `File` rows, so a removed image leaves a file behind. Attach them (and clean up) when the file list gets noisy.

## Phase 5: Visual identity (2026-07-19)

Spec: `specs/phase-5-visual-identity.md`. Engine untouched; CSS, markup, and one new component.

### Done

- Night-sky direction replaces the Kahoot lookalike. Eight tokens in `tailwind.config.js` (`night`, `dusk`, `haze`, `paper`, `ember`, `lagoon`, `gold`, `orchid`); the four answer inks differ in hue and lightness so they survive a washed-out projector and colourblind players.
- Answer marks are now bolt, spark, moon, hex. `svgFill` stays a spelled-out literal per shape, same reason as before: Tailwind only generates class names it can see.
- Type: Bricolage Grotesque display, Instrument Sans body, Martian Mono for PIN, timers, scores, ranks. Loaded in `frontend/index.html` with system fallbacks.
- Signature: `components/DrainRing.vue`, one conic-gradient arc behind a radial mask. Time drains out of a ring instead of sliding along a bar, at three sizes across the phone and the projector, pulsing under 5 seconds.
- Player question screen is full-bleed 2x2 tiles below a slim question strip, so a thumb reaches any corner.
- Host read time got its own centred screen with a gold countdown; it was a bare left-aligned line with no timer, because the host never started a countdown on `get_ready`. Now it does, on both the live event and `applyState`.
- Answer distribution bars sit in `dusk` tracks aligned to the answer grid. Before, a 0-vote bar was a hairline floating in a void.
- Host controls use `.ctl` / `.ctl-go` in `index.css` rather than frappe-ui `Button`, which only ships a light theme.
- Quality floor: one gold `:focus-visible` outline for every control, `prefers-reduced-motion` collapsing the ring pulse, podium rise, and bar growth, responsive to 390px.
- Fixed a pre-existing ruff UP033 in passing: `avatars.load_pack` now uses `functools.cache`.

### Verified

Full 4-question game in a real browser, host at 1440x900 plus two guest phones at 390x844: quiz picker, lobby with QR and player chips, read time, question, locked-in, reveal with distribution and leaderboard, podium, both host and player views. `pre-commit run --all-files` clean.

### Deferred

Both are written up in the spec with the trigger condition, not just the idea.

- **Light theme.** App is dark-only. Build it when someone hosts in a bright room and reports it washing out; the answer inks would need their own light-ground values, not an inversion.
- **Avatar picker as a scroll strip.** The 6-column grid fits at 24 avatars. Build it when a pack ships more than ~30 and the join button drops below the fold.

## Fixes found in end-to-end testing (2026-07-19)

A full host + two-player run in a real browser turned up three defects, all now fixed.

- **Host stuck on a dead game.** A session whose loop worker died stayed `Active` forever, and `get_live_host_session` kept handing it back, so the quiz picker never returned and "New game" was a no-op. `end_session` was no better: it only set a Redis control flag that no loop was left to read. `engine.is_abandoned` now names the condition (Active, no loop state, older than the state TTL), `get_live_host_session` reaps every abandoned session it walks past, `get_host_state` settles a remembered one into its podium, and `end_active_session` ends a loopless game directly instead of flagging it. Five tests in `test_game_ux.py`, including one that a Lobby waiting for players is never reaped.
- **Countdown bar was invisible.** Both the host and player timer bars used `bg-ink-gray-9`, which frappe-ui defines as an ink (text) token only, so the fill computed to `rgba(0,0,0,0)` and the bar always read as empty. Now `bg-surface-gray-7`.
- **Locked-in shape rendered black.** The confirmation shape built its SVG class at runtime with `fill.replace("bg-", "fill-")`, so Tailwind never saw those class names and only generated the ones that happened to appear elsewhere: red worked, blue, amber and green came out black. `SHAPES` now carries an `svgFill` literal per shape.
- **A quiet socket froze a screen for good.** Two player tabs stopped receiving events mid-game and never recovered: the design has no polling fallback, and `useSessionRoom` only re-joined the room on a `connect` event that never came. It now tracks the time of the last event and re-joins (plus resyncs) after 20 seconds of silence, so a lost room membership or a reconnect that never lands costs one `get_state` instead of the rest of the game. Long pauses between questions are normal, hence the generous threshold; verified in the browser that a silent stats pause triggers exactly one resync per interval and an active game triggers none.
- **Result badge was unreadable.** The correct/wrong circle used `bg-surface-green-3` and `bg-surface-red-3`, two tokens with opposite lightness, so no single glyph colour worked: a black ✓ on dark green, then a white ✕ on pale red. Both now use the strong game palette (`bg-green-600` / `bg-red-500`) with white glyphs.
- **Tests leaked their fixtures onto the site.** Engine steps commit mid-test, so the framework rollback left every test quiz and session behind; the host's quiz picker had grown to 26 stray "Engine Quiz" entries and 6 sessions stuck `Active`. `GameTestCase.tearDown` now deletes what it created, and the existing junk was purged.

### Verified

Full 4-question game, host plus two guests, played through get-ready, live answer counts, reveal with distribution, streak callout and podium. Scores matched the engine (Ada 2043, Grace 2041).

## Phase 4c: Player fun (2026-07-19)

Phase 4 was split into four independently shippable slices (`specs/phase-4a..4d`); this is the third.

### Done

- Avatar packs. A pack is a JSON manifest in `quizzly/avatar_packs/` holding the roster, the background palette, and the framing; `site_config.quizzly_avatar_pack` picks the active one. `quizzly/avatars.py` loads it and hands it to the SPA through the existing portal boot context, so the roster has one source of truth and the join path costs no extra request. Shipped pack is DiceBear `notionists` (CC0, 24 avatars).
- `yarn build:avatars` pre-renders `kind: "dicebear"` packs to static SVG under `quizzly/public/avatars/<pack>/`, output committed. The DiceBear libraries are devDependencies only and never reach the runtime bundle; at runtime an avatar id is just an `<img>` URL, which is also how a bought `kind: "static"` pack drops in with no code change.
- `QZ Participant.avatar`, validated in the controller against the active roster. `join_session` takes an optional `avatar` and falls back to a crc32-of-nickname pick. `avatar` now rides along on lobby updates, leaderboards, top-5, streak callouts, podium, and `get_state`.
- Nickname generator: three suggestions with a reroll on the join screen. Word lists live in `quizzly/nicknames.py` and reach the SPA through the boot context.
- Sound synthesised with Web Audio (`frontend/src/sound.js`): countdown tick, submit blip, correct/wrong stings, podium arpeggio, plus a persisted mute toggle on both screens.
- Tests: 9 new (`test_avatars.py`, `test_nicknames.py`). 45 green across the app.

### Exit criteria verified

Full 4-question game in headless Chrome (host + two players) against the live site: both players picked distinct avatars and generated nicknames, and those avatars showed on the host lobby chips, the live leaderboard, the player header, and both podiums. No console errors from the audio path. Contact sheet of all 24 avatars reviewed at render size.

### Notes

- No free avatar library matches the 3D-rendered reference look (Inner Teens); that style is a commercial category. The pack system exists so that decision stays reversible: swapping to a bought 3D pack is a manifest plus a folder.
- `notionists` draws half-body portraits that read as a cropped torso in a circle. Framing (`scale: 140`, `translateY: 25`) is per-pack manifest data, chosen by rendering a comparison sheet.
- An unknown avatar id is rejected rather than defaulted, so a stale client or a manifest entry that was never rendered fails loudly instead of showing a blank circle. A test asserts every manifest id has a file on disk.
- `quizzly/avatars.py` (module) and `quizzly/avatar_packs/` (data) are deliberately not the same name; a module and a package directory sharing a name in one directory breaks imports.
- Players default to muted and the host defaults to audible: a classroom of phones all unmuting at once is a bad time.
- Lobby background music is dropped from scope. A listenable loop is a composition, not a synth line.
- Cleared three stale `Active` sessions from earlier phase testing; `get_live_host_session` picks the newest live session, so an abandoned one hides the quiz picker forever. Worth a real fix (auto-expire) if it recurs outside tests.

## Phase 3: Game UX (2026-07-19)

### Done

- Player screen (`Play.vue`) is one state machine: lobby -> get-ready -> question -> locked-in -> result -> podium, plus a kicked terminal state. Kahoot shapes (triangle/diamond/circle/square, colour keyed to the canonical option id), local countdown bar, per-player answer shuffle seeded by the participant token, result interstitial with correct/wrong, points, streak, rank and top-5.
- Host screen (`Host.vue`): lobby with giant PIN, client-side QR (`qrcode`), join URL, name grid, lock/kick/auto-advance/start; game view with live answer count, timer bar, correct-answer reveal, distribution bar chart, top-5 and streak callouts, next/skip/end; podium with a 1-2-3 stand and the full leaderboard.
- Engine: a 3-second `get_ready` read-the-question pause before each question (own Redis phase, so reconnect lands in it too). `question` payloads now carry `window_ms` (clients count down from receipt, so client clock skew cannot matter) and `randomize_answer_order`.
- New APIs: `get_host_state` (whole host screen in one call; finds the host's live session when no name is passed, so a reload restores mid-game), `get_result` (own outcome for the interstitial, keeping per-player data out of the broadcast), `set_auto_advance` (loop re-reads the flag each pause, so it can flip mid-game). `get_state` gained rank/leaderboard and now resolves Ended sessions so a player who reloads on the podium keeps it.
- Nickname profanity filter in `quizzly/profanity.py`, applied in `join_session`: leetspeak folded, matched as a substring against a curated wordlist.
- Tests: 9 new in `tests/test_game_ux.py` (filter both ways, host state in lobby/mid-question/non-host, own result and rank, podium after reload). 36 green across the app.

### Exit criteria verified

Full 4-question game driven in headless Chrome with three browser sessions (host + two players) against the live site and a real RQ worker: get-ready countdown, shapes, per-player shuffle confirmed different for each player, correct/wrong interstitials with points, distribution chart, "Ada is on a 3 answer streak" callout, podium. Player and host both reloaded mid-question and landed back in the right phase with the right remaining time; both also restored the podium after reload. Profanity filter rejected `Sh1tLord` in the real join form.

### Notes

- Socket reconnects used to go silently deaf: socket.io reconnects on its own but the server-side room membership is gone, and `qz_join` was only emitted on mount. Found in E2E when a backgrounded host tab stopped receiving events and missed the podium. `useSessionRoom` now re-emits `qz_join` on every `connect` and resyncs from the state API.
- A centered flex column (`justify-center`) clips its own top when the content overflows; the host game view uses `m-auto` on an inner wrapper instead.
- Percentage heights collapse inside an `items-end` flex row (the parent's height is content-derived), which is why the first distribution chart rendered blank.
- frappe-ui's tailwind preset caps `fontSize` at `3xl`; `5xl` and `6xl` joined the existing `4xl`/`8xl` overrides.
- The game loop occupies one `long`-queue worker for the whole game. On this bench a single shared worker serves short/default/long, so an unrelated stuck job stalls every game; deployment wants dedicated long workers.

## Phase 2: Game Engine (2026-07-19)

### Done

- `quizzly/engine.py`: RQ game loop (`queue="long"`, `job_id=qz_session_{name}`, `deduplicate`, timeout sized to quiz length). Per question: Redis state write, `question` publish (no correct answer, server `deadline_ts`), sleep-with-poll until deadline + 1s grace, close, score, `question_closed` publish (correct option, distribution, top-5, streak callouts >= 3), then auto-advance after 5s stats or wait for host (capped at 5 min, then advances anyway). After last question: ranks persisted, `podium` published, status Ended, Redis state cleared.
- Redis keys per spec: `qz:{session}:state` (dict, TTL window+30s), `qz:{session}:answered:{question_row}` (set, duplicate pre-check), plus `qz:{session}:control` for host commands (`skip`/`advance`/`end`) polled by the loop. Host controls never touch the loop process directly; the flag survives web/worker process boundary.
- Scoring: Kahoot formula, `response_ms` clamped to window so grace submits floor at 500 base. Streak bonus capped at 250, multiplier 0/1/2. Non-answerers get streak reset at close.
- APIs: host `start_session` (Lobby -> Active, enqueue loop, rejects empty lobby), `next_question`, `skip_question`, `end_session` (Lobby -> Cancelled, Active -> control flag). Guest `submit_answer` (full gauntlet in spec order, returns only `{"ok": true}`, publishes `answer_count`) and `get_state` (reconnect: phase, question sans answer, `remaining_seconds`, own score/answered). Both token-scoped rate-limited.
- Tests: 19 in `tests/test_engine.py`, all green. Whole spec checklist covered: late/duplicate/wrong-question/kicked rejection, DB unique constraint as final word (Redis pre-check bypassed), scoring boundaries + streak reset + multipliers, no `correct` substring in any pre-close payload, reconnect remaining time, full loop to podium with scripted answers.

### Exit criteria verified

Full game played start to podium over HTTP against the live site with the real RQ worker (2 players, 2 questions): questions arrived with correct remaining time, correct answer absent from payloads, duplicate submits got 417, scores/streaks/ranks persisted exactly per formula (checked in DB: 946 + 1982 = 2928, streak 2, rank 1), session Ended with podium event.

### Notes

- Loop commits after each publish so `after_commit` realtime events flush from the worker; submits land in separate web transactions and are visible at close.
- `wait_before_next` accepts host `advance` even during the 5s stats pause; auto-advance mode ignores stray flags.
- Host game-screen state API deliberately deferred to phase 3 (spec lists only guest `get_state`); host reconnect currently rides on the socket events.

## Phase 1: Content + Session Shell (2026-07-19)

### Done

- All five DocTypes per spec: `QZ Quiz` (+ child `QZ Question`), `QZ Session`, `QZ Participant`, `QZ Answer`. Permissions as specified: Quiz Host `if_owner` on Quiz/Session, System Manager only on Participant/Answer. `QZ Answer` gets a DB-level unique index on (participant, question_row) via `on_doctype_update`.
- `quizzly/api.py`: host APIs `create_session`, `lock_lobby`, `unlock_lobby`, `kick_participant`, `get_lobby` (host-only via session.host check); guest APIs `join_session`, `leave_session` (`allow_guest`, IP rate-limited 10/min). Tokens: 32-byte random, sha256 stored, raw returned once. Lobby changes publish `lobby_update` (and `kicked`) to room `qz_session_{pin}` with `after_commit=True`.
- Nickname uniqueness (per session, non-kicked) validated in the `QZ Participant` controller; kicked nicknames are freed for reuse.
- `quizzly/www/quizzly.py` boot context injects `csrf_token` + `site_name` so frappe-ui requests work for logged-in hosts.
- Frontend: `Join.vue` (PIN prefilled from `?pin=`, nickname, error display), `Play.vue` (waiting room, live lobby count, kicked banner, leave), `Host.vue` (quiz picker, giant PIN, join link, live participant chips, lock toggle, click-to-kick). Player identity kept in localStorage (`player.js`), thin `api.js` wrapper over `frappeRequest`.
- Tests: 8 integration tests in `quizzly/tests/test_api.py`, all green (`bench --site quizzly.localhost run-tests --module quizzly.tests.test_api`; needed `set-config allow_tests true` once).

### Exit criteria verified

All checked E2E: over HTTP+socket (node client: join publishes `lobby_update` into the room), and in a real headless browser (two tabs, host + player): PIN/QR-link join, name pops on host screen live, wrong PIN 404, locked lobby 417 (error shown in UI), duplicate nickname 409, kick 200 with player seeing "The host removed you" and the kicked token rejected (403).

### Notes

- frappe-ui's tailwind preset caps `fontSize` at `3xl` (24px); display sizes (`4xl`, `8xl`) added in `tailwind.config.js` for the big PIN.
- `frappe.rate_limiter.rate_limit` no-ops when `frappe.request` is absent, so direct calls in tests skip rate limits.
- Deliberate shortcuts: host lobby state is in-memory (page refresh loses the session view; rejoin comes with `get_state` in phase 2); `leave_session` deletes the participant row and only in Lobby status.

## Phase 0: Foundation + Spike (2026-07-19)

### Done

- App `quizzly` installed on `quizzly.localhost` (module `Quizzly`).
- Role `Quiz Host` created via fixture (`quizzly/fixtures/role.json`, synced on migrate).
- SPA scaffold in `frontend/`: Vue 3 + frappe-ui + Vite, socket.io-client, vue-router with `/join`, `/play`, `/host` stubs. Production build outputs to `quizzly/public/frontend` and writes `quizzly/www/quizzly.html`. Served at `/quizzly/*` via `website_route_rules`. Verified: `yarn build` passes, `/quizzly/join` returns the SPA, `yarn dev` runs.

### Spike decision: socket push for players. WON.

Question: can a guest (no login) socket.io connection receive events published to a custom room?

Answer: **yes**, verified empirically on this bench (frappe develop, v17):

- Guest sockets authenticate with the `sid=Guest` cookie. `frappe.realtime.get_user_info` returns `installed_apps` from the site (not the user), so app-level socket handlers load for guests too.
- The realtime node server loads `apps/<app>/realtime/handlers.js` per connecting socket. `quizzly/realtime/handlers.js` registers `qz_join` / `qz_leave`, which join/leave room `qz_session_{pin}` (PIN validated as 6 digits).
- Test: node socket.io-client connected as Guest, emitted `qz_join 123456`, then `frappe.publish_realtime(event="qz_session_123456", room="qz_session_123456")` from the server. Event received by the guest client.

Consequence: players subscribe over socket.io (`qz_join` after joining a session). No 1s polling fallback is built. `get_state` stays planned for reconnect only.

### Notes

- Bench runs frappe **v17.x-develop**, not stable v16 as plan.md assumes. Spike result applies to this version.
- `bench start` must be restarted after installing a new app: web workers only pick up the editable install at interpreter startup (symptom: `ModuleNotFoundError: No module named 'quizzly'` on every request).
- Found and cleared a stale global `maintenance_mode: 1` in `common_site_config.json` that 503'd every site on the bench.
