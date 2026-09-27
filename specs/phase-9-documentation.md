# Phase 9: Documentation + README with Screenshots

## Goal

The repo has a build plan (`plan.md`), a phase log (`progress.md`), and 13
specs. What it does not have is anything that tells a stranger what TriviaTap is
in thirty seconds. `README.md` is still the app-scaffold default: four lines
about installation and pre-commit, no product description, no picture.

TriviaTap is a visual product. Two screens, live, in colour. A README without
screenshots undersells it more than it would undersell a library.

So: rewrite `README.md` as the front door, and capture a small set of real
screenshots from a real running game to go in it.

## Non-goals

- **No docs site.** No mkdocs, no docusaurus, no `docs/` content tree beyond
  the images folder. One README is the whole documentation surface until
  someone asks a question it cannot answer.
- **No API reference.** The whitelisted APIs in `trivia_tap/api.py` are internal
  to the SPA, not a public contract. Documenting them now freezes a moving
  target.
- **No architecture doc.** `plan.md` section 2 already carries the
  architecture, and `progress.md` carries the decisions. Link them, do not
  duplicate them.
- **No CONTRIBUTING.md.** The pre-commit section in the README covers it.
- **No mock or Figma screenshots.** Everything shown is a real screen from a
  real session against `trivia-tap.localhost`, or it does not ship.
- **No video / GIF.** A hero PNG plus a collapsed gallery. Motion capture is a
  maintenance burden and bloats the repo.

## Tracer bullet

1. Seed a demo quiz, start a session, screenshot the host lobby. Drop that one
   image into the README under the title. **Feedback: the capture pipeline and
   the image path both work before a full gallery exists.**
2. Capture the rest of the set from the same session.
3. Rewrite the README prose around the images.

## Screenshot capture

### Where they live

`docs/images/*.png`, committed to the repo, referenced from the README with
relative paths (`docs/images/host-lobby.png`). Relative paths render on GitHub
and in any local markdown viewer, and they survive a fork. No external asset
host, no CDN dependency.

Budget: keep the whole folder under ~2 MB. PNG, downscaled to 1600px wide max.
Anything heavier gets re-exported, not committed.

### How they are captured

Use the `/agent-browser` skill, headless, against `trivia-tap.localhost:8000`,
logged in as `Administrator` / `admin` for host shots. Two browser contexts:
host and player, same as the phase 8 harness.

Fixed viewports so the set looks like one product and not five:

- Host / desktop shots: 1440x900.
- Player shots: 390x844 (phone portrait). Players are on phones; showing the
  player screen at desktop width is a lie about how the product is used.

Capture in both themes only where the theme is the point (see the theme shot
below). Everything else: light theme, so the gallery is visually consistent.

### Demo content

Screenshots need content that does not look like test junk. Seed one quiz
before capturing:

- Title: something neutral and obviously demo ("General Knowledge").
- 5 questions, real text, plausible options, no `foo` / `test 1` / `asdf`.
- Player nicknames in the lobby: 6-8 varied, clean names with distinct
  avatars, so the lobby and podium look populated.

Seeding is a throwaway script in `scripts/`, not a fixture. It exists to make
pictures, and it is fine if it rots.

### The set

| File | Screen | What it must show |
| --- | --- | --- |
| `host-lobby.png` | Host, session in Lobby | Giant PIN, QR / join link, populated participant chips with avatars |
| `player-join.png` | Player, join page | PIN + nickname entry, avatar carousel |
| `host-question.png` | Host, question live | Question text, four coloured options, countdown, answer count |
| `player-answer.png` | Player, question live | The four shape buttons as a player actually sees them |
| `host-leaderboard.png` | Host, between questions | Correct answer reveal, answer distribution, top-5 |
| `host-podium.png` | Host, session ended | Top-3 podium |
| `quiz-editor.png` | Host, quiz editor | Question list + editing a question |
| `theme.png` | Player, question live, dark | Same screen as `player-answer.png` in dark theme |

`host-lobby.png` doubles as the hero image at the top of the README.

Eight shots. If a screen cannot be made to look good in one frame, fix the
screen (per the project's pixel-perfection rule) rather than cropping around
it, or drop the shot.

## README structure

Replace the file. Target length: one screen of prose plus the gallery, not a
manual.

1. **Header block**, centred: app name, one-line tagline ("Live multiplayer
   quiz, no login required"), CI + Linter badges, hero image.
2. **What it is**: 2-3 sentences. Guests join with a PIN or QR, no account.
   Gameplay is server-authoritative, so the answer never reaches the client
   before the question closes.
3. **Screenshots**: a `<details><summary>` block holding the remaining seven
   images, so the README stays short by default.
4. **Features**: a short bulleted list, one line each. PIN / QR guest join;
   live lobby with kick and lock; synced questions with per-question timers;
   speed-scaled scoring with streak bonuses; answer distribution and
   leaderboard between questions; podium; avatar picker; light and dark theme;
   in-app quiz authoring.
5. **Under the hood**: Frappe Framework, Vue 3 + frappe-ui, socket.io for
   push, Redis for hot session state, RQ for the game loop. One line each,
   linked.
6. **Development setup**: bench install steps (keep the existing block, it is
   correct), plus `yarn dev` for the frontend and the note that the SPA is
   served at `/trivia-tap`.
7. **Testing**: how to run `bench --site trivia-tap.localhost run-tests --app
   trivia_tap`, and the `allow_tests` config it needs.
8. **Contributing**: the existing pre-commit block, unchanged.
9. **License**: MIT, unchanged.

Anything about a phase, a spec, or a deferred shortcut belongs in
`progress.md`, not here.

## Also in scope

- `plan.md` and `progress.md` get a one-line pointer from the README so the
  detail is findable, not buried.
- Delete the stale "### CI" section from the current README if it no longer
  matches `.github/workflows/`; otherwise correct it to the real workflow
  names.

## Exit criteria

- `README.md` renders correctly on GitHub: hero image visible, gallery
  expands, badges resolve, no broken relative paths.
- All eight images exist in `docs/images/`, are from a real session, and the
  folder is under 2 MB.
- No image shows placeholder text, a test nickname, or a console error
  overlay.
- Every command in the README has been run verbatim and works.
