# Phase 13: Rename to TriviaTap

## Goal

The app is now **TriviaTap**, with a new logo: a white question mark with eyes on
a green rounded square. Every place a player, a host, or a developer meets the
old name, the old prefix, or the old logo shows the new one.

## What changes

| Thing | Before | After |
|---|---|---|
| App name (package, `app_name`, pyproject) | `quizzly` | `trivia_tap` |
| App title | Quizzly | TriviaTap |
| Module | Quizzly | TriviaTap (folder `triviatap`) |
| Workspace | Quizzly | TriviaTap |
| DocTypes | `QZ Quiz`, `QZ Question`, `QZ Session`, `QZ Participant`, `QZ Answer` | `TT ...` |
| Quiz names | `QZ-0092` | `TT-0092` |
| Socket events and rooms | `qz_join`, `qz_leave`, `qz_session_<pin>` | `tt_...` |
| Redis keys, ticker job, savepoint | `qz:...`, `qz_ticker`, `qz_tick` | `tt:...`, `tt_ticker`, `tt_tick` |
| Browser storage keys | `qz_player`, `qz_muted`, `qz_hosted_session`, `quizzly-theme` | `tt_...`, `trivia-tap-theme` |
| SPA route | `/quizzly/*` | `/trivia-tap/*` |
| Logo | `quizzly-logo.svg` | `trivia-tap-logo.png` (256px) |
| Site config key | `quizzly_avatar_pack` | `trivia_tap_avatar_pack` |
| Bench folder | `apps/quizzly` | `apps/trivia_tap` |
| Dev site | `quizzly.localhost` | `trivia-tap.localhost` |
| GitHub repo | `bwhtech/quizzly` | `bwhtech/trivia_tap` |
| Specs, plan, progress, README, screenshots | old name | new name |

The route uses a hyphen because it is what players type and scan. The page file
stays `www/trivia_tap.py` and route rules map the hyphenated path onto it.

Renaming Redis keys and browser storage keys drops live games and remembered
players at the moment of the upgrade. Deploy between games.

## Existing sites

Frappe cannot migrate an app whose package is gone, so the app itself is moved
by hand once per site:

1. Point `Installed Application`, the `installed_apps` default and
   `site_config.installed_apps` at `trivia_tap`.
2. Rename Module Def `Quizzly` to `TriviaTap` (`app_name = trivia_tap`) and
   move the five DocTypes to it.
3. Drop the old `Quizzly` workspace and Desktop Icon.
4. Rename `apps/quizzly` to `apps/trivia_tap`, reinstall the editable package,
   update `sites/apps.txt`, then `bench --site <site> migrate` and `bench build`.

Migrate then runs two patches that do the rest with quiz data kept:

- `rename_qz_doctypes` (pre model sync): `frappe.rename_doc` on each DocType,
  which renames the tables and every link to them.
- `rename_qz_quiz_names` (post model sync): `QZ-0092` becomes `TT-0092`, links
  follow. The quiz counter is shared, so new quizzes continue the sequence.

## Tracer bullet

1. Rename the package and hooks, move the site, migrate. **Feedback: desk opens
   the TriviaTap workspace and the tests pass.**
2. Swap the logo and route in the SPA. **Feedback: `/trivia-tap/join` shows the
   new name, the host bar and QR code show the new logo.**
3. Rename the DocTypes and events through patches. **Feedback: the old quizzes
   open in the editor under `TT-` names and a full game plays.**
4. Retake the README screenshots from a real game.
