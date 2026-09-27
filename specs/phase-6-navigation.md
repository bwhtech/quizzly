# Phase 6: Navigation

## Goal

The app has screens but no way to move between them. Every link that exists today was added ad hoc by the screen that needed it (`← Back to hosting` on the quiz list, `← All quizzes` in the editor, `Edit quizzles` on the picker), so where you can go depends on where you happen to be. A host cannot tell who they are logged in as, cannot log out, and cannot leave a live game without ending it. A player has a leave button in the lobby and on the podium, but not while questions are running.

This phase gives the host one persistent bar and the player one persistent way out. No new backend, no new data.

## Non-goals

- No sidebar, no hamburger menu, no route-level nav config. Four host screens do not need a nav framework.
- No breadcrumb component. The host tree is two levels deep; a back link is a breadcrumb that fits.
- No player navigation beyond leaving. A player is in exactly one game and has nowhere else to be.

## Tracer bullet

1. `components/HostBar.vue`, mounted on `/host`, `/host/quizzes`, `/host/quizzes/:name`. Wordmark links to `/host`, quizzes link, user's name, logout. **Feedback: a host clicks between hosting and authoring from any host screen without using browser back.**
2. Live-game exit: the host bar collapses during an active session to the game's own state, and `End game` gets a confirm.
3. Player: `Leave game` moves into the persistent player header, so it exists in every phase.

## Host bar

One component, rendered by the three host screens (not by a layout route: `App.vue` is a bare `<router-view />` and turning it into a layout host to save three lines of markup costs more than it saves).

Contents, left to right:

- **TriviaTap** wordmark, links to `/host`.
- `Host` / `Quizzes` links, current route marked with the existing `data-on` treatment that `.ctl` already uses for toggles.
- Right side: `window.session_user` (the boot value the router already reads) and a `Log out` link to `/api/method/logout?redirect-to=/trivia-tap/join`, the framework's own logout path. No custom endpoint.

The bar is hidden whenever `/host` holds a live session (`session` truthy in `Host.vue`). A projector screen showing a lobby, question, or podium is the whole point of that screen, and a nav bar on it is a thing 40 people in a room look at instead of the PIN.

## Leaving a live game

Today `End game` ends it with one click and no confirm, which is destructive and irreversible mid-question. Two changes:

- `End game` asks for confirmation, naming the cost ("Ends the game for all N players").
- After a game ends, the podium already exists; it gains a `Back to hosting` link to `/host` so the host returns to the picker without a reload. `get_host_state` with no argument already resumes a live session on reload, so nothing is lost either way.

## Player

`Leave game` moves out of the lobby and podium screens into the persistent header next to the score, so a player who wants out during a question has a way out. Same `leave()` call, same confirm-free behaviour (leaving is cheap: re-joining with the PIN works while the lobby is unlocked).

The header is hidden on `kicked`, which stays as is: there is no game left to leave.

## Route guard

Unchanged. `/host*` already bounces Guest to login with a redirect back. The one gap: a logged-in user without the Quiz Host role gets a raw permission error from the first API call. `/host` catches it and says to log in with a host account, `/host/quizzes` says the same, and the editor does not. Make the message identical in all three, from one place.

## Tests

Navigation is markup, so the value is in the two behavioural bits:

- Host bar is absent from `/host` while a session is live and present when it is not.
- `Leave game` in the player header calls `leave_session` and lands on `/join` from the `question` phase, not only from the lobby.

Both are component-level, in the browser via `/agent-browser`. No new Python tests: no backend changes.

## Exit criteria

- From any host screen, reach any other host screen in one click, and see which one you are on.
- Host name is visible and logout works, landing on `/join`.
- The bar disappears the moment a session goes live and comes back when it ends.
- A player leaves mid-question and is gone from the host's player list.
- `pre-commit run --all-files` clean.

## Deferred

- **Session history nav.** `/host/history` is specced in phase 4b and not built. When it ships it is a third link in the bar and nothing else changes, which is the point of putting the bar in one component now.
- **Mobile host bar.** The links fit at 390px as plain text. Collapse it when a fourth or fifth link makes it wrap.
