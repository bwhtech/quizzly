# Phase 16: Brand theme from the logo

## Goal

The app looks like its logo. Phase 5 dressed the game in a purple night sky
with an ember call to action. Phase 13 then gave TriviaTap a mint green logo
with black ink lines, and the two no longer match.

## Direction: mint and ink

The logo has three colours: a mint gradient, a near-black ink line, and white.
The theme takes all three.

### Ground

The purple tint goes. The ground is the logo's ink, tinted slightly green so it
sits next to the mint.

| Token   | Dark      | Light     | Role                       |
| ------- | --------- | --------- | -------------------------- |
| `night` | `#0D1311` | `#F6FBF8` | Page ground                |
| `dusk`  | `#17211D` | `#E8F4EE` | Raised surfaces, inputs    |
| `haze`  | `#2A3A33` | `#C7DED3` | Hairlines, pill borders    |
| `paper` | `#EEF8F3` | `#0D1311` | Text on the ground         |
| `accent`| `#20EEA0` | `#0A7A52` | Brand text, focus, eyebrows|

`accent` was gold. It is now mint, and the light value darkens to hold 4.5:1
as small text on `night`.

### Brand mint

- `mint` (`#20EEA0`): fixed, the flat brand colour for rings and borders.
- `bg-brand`: the logo's own gradient, `#6BF57F` to `#11DDB9`. Every primary
  action uses it with `sunk` ink: Join game, Log in, `.ctl-go`. Ember stops
  being the call to action and keeps only answer 1, urgency and danger.
- `sunk` and `card` follow the logo's ink and white: `#0A100E` and `#F2FBF6`.

### What does not change

The four answer inks (ember, lagoon, gold, orchid). Phase 5 holds: a player
learns "red is top-left" once. `alert` and `ok` keep their hues too.

### Lockup

Join and Log in show the logo beside the wordmark, so a guest meets the logo on
the first screen and not only in the host bar.

## Non-goals

- No layout, engine or API changes. Tokens, a few class swaps, and the lockup.
