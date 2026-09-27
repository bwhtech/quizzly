# Phase 4d: Game modes (shared-screen + team)

Slice 4 of Phase 4 juice, and the heaviest. See `phase-4-juice.md` for the umbrella.

## Goal

Two new ways to run the same quiz: shared-screen (classic Kahoot, one projector) and team mode (players grouped, team scores). Both off by default, both leaving solo remote play exactly as it is today.

## Tracer bullet

Shared-screen first, it is a payload change and nothing more. Team mode second, it is the only thing in Phase 4 that touches scoring.

1. `shared_screen` flag on `TT Session`, host toggles it in the lobby, player question payload drops `question_text` and option labels. **Feedback: a game runs with the projector holding the question and phones holding only shapes.**
2. `team_mode` flag, teams assigned in the lobby, leaderboard aggregates by team. **Feedback: a two-team game reaches a team podium.**

## Shared-screen mode

`TT Session.shared_screen` — Check, settable only while status is `Lobby`.

The engine is untouched. `publish_question` strips `question_text`, `image_url`, and the option `label` fields from the player payload when the flag is on, keeping option ids and colors. Host payload is unchanged.

Stripping happens server-side. Sending the text and hiding it in CSS would leak the question to anyone with devtools, which in a classroom is every third student.

Player question view renders four large shape buttons filling the screen, no text. The get-ready and result interstitials stay as they are.

## Team mode

`TT Session.team_mode` — Check, settable only while status is `Lobby`.
`TT Participant.team` — Data, the team name, empty in solo mode.

New DocType is not worth it: a team is a name and a color, both derivable from a fixed palette, and it has no lifecycle of its own outside a session.

### Assignment

Host picks a team count (2..4) in the lobby. Players are auto-balanced on join, round-robin by join order, and the host can drag a player between teams before start. Auto-balance first, because a class of 30 hand-assigned is a minute of dead air.

### Scoring

Per-player scoring, streaks, and the answer gauntlet are all completely unchanged. Team score is a sum, computed at read time in `get_leaderboard`, never stored, so there is no second number that can drift out of sync with the answers.

- Team score = sum of member scores.
- Team rank = by team score, ties broken by earliest last-answer time, matching the existing player tiebreak.
- Streak callouts stay per player.

`TT Answer` gains nothing. Team membership is resolved through `TT Participant`.

### Presentation

- Player: team name and color in the header, team standing in the result interstitial under their own score.
- Host: leaderboard switches to teams with an expandable member list, podium shows top-3 teams.

## API changes

- `create_session` accepts optional `shared_screen`, `team_mode`, `team_count`.
- New `set_teams(session, assignments)` — host-only, lobby-only, bulk reassignment.
- `get_leaderboard(session)` returns team-aggregated rows when `team_mode` is on, keeping the same row shape so the callers do not branch.
- `lobby_update` and `get_state` carry `team` when set.

## Tests

- Shared-screen: player payload contains no `question_text`, no option labels, no `image_url`; host payload still does. Asserted as a substring scan over the whole payload, the same way Phase 2 asserts `correct` never leaks.
- Team mode: two teams, scripted answers, team totals equal the sum of member scores and team ranks are correct, including a tie.
- Team assignment round-robins on join and rejects reassignment once status is `Active`.
- Solo game with both flags off produces payloads byte-identical to v1.

## Exit criteria

- A shared-screen team game runs start to team podium with 4 players in 2 teams.
- Both flags off, every Phase 2 and Phase 3 test still passes untouched.
