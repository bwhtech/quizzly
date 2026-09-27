# Phase 0: Foundation + Spike

## Goal

Bench app scaffolded, SPA scaffolded, and the guest-socket question answered before any game code is written.

## Tasks

### App setup

- Bench app `trivia_tap`, module `TriviaTap`, installed on a site.
- Stable Frappe v16, no nightly or experimental features.
- Roles created: `Quiz Host`.
- Naming conventions locked in: DocType prefix `TT`, event prefix `tt_`, Redis prefix `tt:`.

### SPA scaffold

- Vue 3 + frappe-ui + Vite SPA in `apps/trivia_tap/frontend/`. frappe-ui provides Frappe-aware composables (`useCall`, `useList`, `useDoc`) and a Vite plugin with dev proxy + DocType type generation.
- Served via `website_route_rules` in hooks.py: `{"from_route": "/trivia-tap/<path:app_path>", "to_route": "trivia_tap"}`. Production build outputs to `apps/trivia_tap/trivia-tap/public/frontend` (`bench build --app trivia_tap`).
- socket.io-client included.
- Route groups stubbed with vue-router: player (`/join`, `/play`) and host (`/host`).

### SPIKE: guest socket delivery (decides Phase 2/3 transport)

Question: can a guest (no login) socket.io connection receive events published to our room on stable v16?

- Expected path: website room or explicit room param with `frappe.publish_realtime(event, data, room=...)`.
- One event name per session: `tt_session_{pin}`, payload carries a `type` field (lobby_update, countdown, question, question_closed, leaderboard, podium, kicked, session_ended). Client subscribes once, switches on type.
- **Yes:** socket push for players.
- **No:** 1s short-poll `get_state` API for players, socket stays for host.

Decide in the spike. Delete the losing path. Do not build both.

## Exit criteria

- App installs cleanly, role exists, SPA dev server runs.
- Spike decision documented (which transport won and why).
