# Phase 4b: Host conveniences (CSV export + session history)

Slice 2 of Phase 4 juice. See `phase-4-juice.md` for the umbrella.

## Goal

After a game ends the host can see past sessions and pull the results out as a CSV. Smallest slice in Phase 4, almost entirely reuse of existing leaderboard queries.

## Tracer bullet

1. `export_results(session)` returns a CSV download for one ended session, linked from the existing podium screen. **Feedback: host clicks a button on the podium and gets a real file.**
2. `/host/history` list of the host's past sessions, each row linking to a read-only recap with the final leaderboard and the same export button.

## APIs (`trivia_tap/api.py`, host-only, logged in)

- `list_sessions(limit=20, start=0)` — the host's own sessions, newest first: pin, quiz title, status, `started_at`, `ended_at`, participant count. Paged, because history grows without bound.
- `get_session_recap(session)` — final leaderboard (reuses `get_leaderboard`) plus per-question accuracy: for each question, the answer distribution and percent correct.
- `export_results(session)` — sets `frappe.response` to a CSV filecontent response, the standard Frappe download path, no custom file writing.

All three go through the existing `get_host_session` helper, so ownership is checked in exactly one place.

## CSV shape

One row per participant, one column per question, so a teacher can paste it straight into a gradebook:

```
nickname,rank,score,q1,q2,...,qN
alice,1,2928,correct,wrong,...
```

Cell values: `correct`, `wrong`, or empty when the player never answered. A second sheet is not worth it, per-question stats live in the recap screen instead.

## Screens

- `/host/history` — session list, newest first, "load more" paging.
- `/host/history/:name` — recap: quiz title, date, player count, final leaderboard, per-question accuracy bars, export button.
- Podium screen gains the same export button.

## Tests

- `export_results` on a played session emits one row per participant with correct per-question cells, including the empty cell for a non-answerer.
- `list_sessions` returns only the calling host's sessions, and pages correctly.
- `get_session_recap` accuracy math matches the raw `TT Answer` rows.
- A non-owner host calling any of the three gets a permission error.

## Exit criteria

- Host plays a game, opens history, sees the session, opens the recap, downloads a CSV that opens cleanly in a spreadsheet.
- Live gameplay is untouched: no new query runs during an active session.
