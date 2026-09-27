# Phase 13: Rename to TriviaTap

## Goal

The app is now **TriviaTap**, with a new logo: a white question mark with eyes on
a green rounded square. Every place a player, a host, or a developer meets the
name or the logo shows the new one.

## What changes

| Thing | Before | After |
|---|---|---|
| App name (package, `app_name`, pyproject) | `quizzly` | `trivia_tap` |
| App title | Quizzly | TriviaTap |
| Module | Quizzly | TriviaTap |
| Workspace | Quizzly | TriviaTap |
| SPA route | `/quizzly/*` | `/trivia-tap/*` |
| Logo | `quizzly-logo.svg` | `trivia-tap-logo.png` (512px) |
| Site config key | `quizzly_avatar_pack` | `trivia_tap_avatar_pack` |
| Bench folder | `apps/quizzly` | `apps/trivia_tap` |

The route uses a hyphen because it is what players type and scan. The page file
stays `www/trivia_tap.py` and route rules map the hyphenated path onto it.

## Not changing

- The `QZ` DocType prefix and the `qz_` socket events. Renaming DocTypes moves
  tables for no user-facing gain.
- Past specs and progress entries. They are history.
- The GitHub repository name. That is the owner's call.

## Existing sites

Frappe cannot migrate an app whose package is gone, so an installed site is
moved by hand once, with quiz data kept:

1. Point `Installed Application`, the `installed_apps` default and
   `site_config.installed_apps` at `trivia_tap`.
2. Rename Module Def `Quizzly` to `TriviaTap` (`app_name = trivia_tap`) and
   move the five DocTypes to it.
3. Drop the old `Quizzly` workspace. Migrate syncs the new one.
4. Rename `apps/quizzly` to `apps/trivia_tap`, reinstall the editable package,
   update `sites/apps.txt`, then `bench --site <site> migrate` and `bench build`.

## Tracer bullet

1. Rename the package and hooks, move the site, migrate. **Feedback: desk opens
   the TriviaTap workspace and the tests pass.**
2. Swap the logo and route in the SPA. **Feedback: `/trivia-tap/join` shows the
   new name, the host bar and QR code show the new logo.**
