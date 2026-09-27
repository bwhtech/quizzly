<div align="center">

# <img alt="" src="trivia_tap/public/images/trivia-tap-logo.png" width="40" height="40" align="center" /> TriviaTap

**Live multiplayer quiz, no login required**

<img alt="Host lobby with the game PIN, QR code and players joining" src="docs/images/host-lobby.png" />

</div>

## What it is

TriviaTap is a live quiz game built on the Frappe Framework. A host puts the game
PIN on the big screen, players join from their phones with the PIN or by
scanning the QR code, and nobody needs an account.

Gameplay is server-authoritative. The correct answer never reaches a player's
device before the question closes, scores are computed from a server-set
deadline, and every submission is validated against the server's own view of
the game.

<details>
<summary>Screenshots</summary>

**Joining from a phone**

<img alt="Join screen with PIN, nickname suggestions and avatar picker" src="docs/images/player-join.png" width="320" />

**A question, live on both screens**

<img alt="Host screen showing a question, countdown and answer count" src="docs/images/host-question.png" />

<img alt="Player screen showing four coloured answer buttons" src="docs/images/player-answer.png" width="320" />

**Between questions**

<img alt="Correct answer revealed with the answer distribution" src="docs/images/host-stats.png" />

<img alt="Scoreboard with the top five after the question" src="docs/images/host-leaderboard.png" />

**Final results**

<img alt="Podium with the top three players and the full leaderboard" src="docs/images/host-podium.png" />

**Writing a quiz**

<img alt="Quiz editor with question text, four options and the correct answer marked" src="docs/images/quiz-editor.png" />

**Light and dark**

<img alt="Player question screen in dark theme" src="docs/images/theme.png" width="320" />

</details>

## Features

- Guests join with a PIN or QR code, no account and no app install
- Live lobby: names appear as players join, host can lock it or kick anyone
- Questions land on every device at once, with a per-question timer
- Speed-scaled scoring with streak bonuses, in the style of the games it borrows from
- Answer distribution, correct answer reveal and top-five leaderboard between questions
- Top-three podium at the end, plus the full ranking
- Avatar picker and nickname suggestions for players
- Light and dark theme, everywhere
- Quizzes are written in the app, no Desk trip needed

## Under the hood

- [Frappe Framework](https://github.com/frappe/frappe) for the backend, DocTypes and permissions
- [Vue 3](https://vuejs.org) and [frappe-ui](https://github.com/frappe/frappe-ui) for the single-page app
- [Socket.IO](https://socket.io) to push every state change to hosts and players
- Redis for the hot session state each answer is validated against
- RQ for the single shared ticker that drives every live game loop

## Development setup

1. Set up a bench by following the
   [installation steps](https://frappeframework.com/docs/user/en/installation)
   and start the server with `bench start`.

2. In another terminal, from your bench directory:

```bash
bench get-app https://github.com/bwhtech/trivia_tap --branch develop
bench --site your-site.localhost install-app trivia_tap
```

The app is served at `/trivia-tap` on your site. For frontend work, run the Vite
dev server against it:

```bash
cd apps/trivia_tap/frontend
yarn install
yarn dev
```

## Testing

```bash
bench --site your-site.localhost set-config allow_tests true
bench --site your-site.localhost run-tests --app trivia_tap
```

## Contributing

This app uses `pre-commit` for code formatting and linting. Please
[install pre-commit](https://pre-commit.com/#installation) and enable it for
this repository:

```bash
cd apps/trivia_tap
pre-commit install
```

Pre-commit is configured to use ruff, eslint, prettier and pyupgrade.

`plan.md` holds the build plan and architecture, `specs/` holds the spec for
each phase, and `progress.md` logs what was actually built.

## License

MIT
