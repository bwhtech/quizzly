# Phase 4c: Player fun (avatars, nickname generator, sound)

Slice 3 of Phase 4 juice. See `phase-4-juice.md` for the umbrella.

## Goal

Joining and playing feel like a game rather than a form. No engine changes: scoring, timing, and payload contracts are all untouched.

## Tracer bullet

1. `avatar` field on `TT Participant`, picked on the join screen, rendered on the host lobby and leaderboard. **Feedback: a player's face shows up on the big screen.**
2. Nickname generator: three safe suggestions on the join screen, tap to accept, still free to type your own.
3. Sound: lobby music, countdown tick, answer sfx, podium sting, with a mute toggle that persists.

## Avatars

Picked from a pack, never uploaded. No file storage from users, no moderation problem, no upload endpoint.

### Pack system

The pack is the unit of configuration: swapping art style, editing the roster, or adding avatars must never require a code change.

A pack is one JSON manifest in `trivia_tap/avatar_packs/<pack>.json`:

```json
{
  "id": "notionists",
  "name": "Notionists",
  "kind": "dicebear",
  "style": "notionists",
  "license": "CC0 1.0",
  "attribution": null,
  "avatars": ["fox", "otter", "..."]
}
```

- Active pack from `site_config.trivia_tap_avatar_pack`, defaulting to the shipped one. One setting, no DocType, because this changes roughly never.
- `avatars` is the ordered roster the picker renders and the server validates against. Adding an avatar is one line in the manifest.
- `kind: "dicebear"` packs are pre-rendered to static SVG by `yarn build:avatars`, output committed under `trivia_tap/public/avatars/<pack>/<id>.svg`. `kind: "static"` packs skip the script and just ship an image folder, which is how a bought 3D pack drops in later.

Pre-rendering, rather than generating in the browser, keeps the DiceBear libraries out of the runtime bundle entirely and makes both pack kinds identical at runtime: an id resolves to an `<img>` URL.

Python owns the manifest and hands it to the SPA through the existing `www/trivia_tap.py` boot context, so there is a single source of truth and no extra request on the join path.

### Default pack

DiceBear `notionists`, CC0 1.0, no attribution required. 2D vector rather than the 3D-render reference look, which is a commercial category with no free equivalent. At the sizes avatars actually render here (48px in the host grid, 32px in the play header) the difference is close to invisible, and the pack system makes a later swap a one-setting change.

### Model and payloads

- `TT Participant.avatar` — Data, stores the chosen avatar id, validated in the controller against the active pack roster. An unknown id is rejected rather than silently defaulted, because it would otherwise render as a blank on the host screen.
- `join_session` accepts an optional `avatar`, defaulting to one derived from the nickname hash so an old client still gets something reasonable.
- `lobby_update`, leaderboard, and podium payloads carry `avatar` alongside `nickname`.

## Nickname generator

Client-side, from a curated adjective + noun word list shipped in the SPA (`frontend/src/nicknames.js`). Three options, a reroll button, all guaranteed to pass the Phase 3 profanity filter because the word list is curated.

Server behaviour is unchanged: `join_session` still validates and still rejects duplicates and dirty names, so the generator is a convenience and never a trust boundary.

## Sound

Synthesised with the Web Audio API, not shipped as audio files. The cues needed here are short tones, so an oscillator covers them in a few lines with no binary assets, no licensing question, and nothing to preload.

- Cues: 5-second countdown tick, answer-submitted blip, correct and wrong stings, podium arpeggio.
- Lobby background music is out of scope: a listenable loop is a real composition, not a synth line, so it waits for an actual asset.
- Mute toggle on both host and player, persisted in localStorage, defaulting to **on for host, off for player**. Phones in a classroom all unmuting at once is a bad time.
- Audio starts only after a user gesture, satisfying browser autoplay policy: the join tap and the host start tap both count.

## Screens

- `/join` — nickname field with three suggestion chips and a reroll, avatar picker grid below.
- `/play` — avatar shown in the header, next to the score.
- `/host` — avatars in the lobby player grid, in the live leaderboard, and on the podium.

## Tests

- `join_session` with a valid avatar stores it; with an unknown avatar id it errors; with none it derives a stable one from the nickname.
- Lobby and leaderboard payloads carry `avatar`.
- Every id in the active pack manifest has a rendered file on disk, which is the check that catches a manifest edited without re-running the build script.
- Nickname generator output passes the profanity filter for the entire word list (a loop over the list, cheap and it catches a bad word slipping into the file later).

## Exit criteria

- Two players join with distinct avatars and generated names, both visible on the host screen through lobby, game, and podium.
- Sound plays on both sides, mute persists across reload.
- A client that sends no avatar and never plays sound still completes a full game.
