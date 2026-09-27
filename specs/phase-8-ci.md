# Phase 8: CI Parity with frappe/wiki

## Goal

TriviaTap already has `.github/workflows/ci.yml` (server tests) and
`linter.yml` (pre-commit, semgrep, pip-audit). Wiki has one more workflow we
don't: **Playwright E2E against a real bench**, plus a **commitlint** job.

That gap matters more here than it does for wiki. TriviaTap is a realtime,
multi-client game: host opens a session, guests join with a PIN over
socket.io, the server broadcasts state transitions. Every real bug in this app
so far has lived in the seam between two browsers and the server, which is
exactly the seam `bench run-tests` cannot see. The python tests in
`trivia_tap/tests/` cover the engine; nothing covers "host starts game, player
answers, score appears on both screens."

So: add UI tests, add commitlint, tighten the two existing workflows. No new
runtime dependency, no change to app code.

## Non-goals

- **No Cypress.** Playwright is what wiki settled on, it drives two browser
  contexts in one test (host + player) without hacks, and the pre-commit
  config already excludes a `cypress/` dir that doesn't exist. Drop that
  stale exclude.
- **No unit tests for the Vue frontend.** No vitest, no jsdom. The components
  are thin and the interesting behaviour is server-authoritative. If a
  component ever grows real logic, add vitest then.
- **No matrix builds.** One python, one node, one mariadb. TriviaTap ships to
  one bench, not to the world.
- **No deploy / release workflow.** Nothing to deploy yet.
- **No `.github/instructions/`.** That's wiki's Copilot config.
- **No self-hosted or cached bench image.** A cold `bench init` per run is
  ~4 minutes and costs nothing to maintain.

## Tracer bullet

1. `playwright.config.ts` + one test that loads the join page and asserts the
   PIN field renders. Green locally against `trivia-tap.localhost:8000`.
   **Feedback: the harness works before any game logic is written into it.**
2. Same test green in CI, on a bench the workflow builds from scratch.
3. Two-context test: host creates a session, player joins, both see the
   lobby.
4. Full happy path: question shown, player answers, leaderboard updates.

## What gets added

### `playwright.config.ts` (repo root)

Copy wiki's shape, it is already tuned for Frappe:

- `testDir: ./e2e/tests`, `fullyParallel: false`, `workers: 1`. Frappe
  sessions and a single game PIN space do not parallelize.
- `retries: process.env.CI ? 2 : 0`, `forbidOnly: !!process.env.CI`.
- `baseURL: process.env.BASE_URL || 'http://trivia-tap.test:8000'`.
- `trace: 'on-first-retry'`, `video: 'retain-on-failure'`,
  `screenshot: 'only-on-failure'`.
- Reporter: `[['github'], ['html', { open: 'never' }]]` in CI, `html` local.
- A `setup` project running `auth.setup.ts` that logs in as
  Administrator/admin and saves storage state to `e2e/.auth/user.json`
  (gitignored). The `chromium` project depends on it.

Guest players must **not** use that storage state, joining is the
no-login path and reusing an admin session would test the wrong thing.
Player contexts get created fresh inside the test via `browser.newContext()`.

### Root `package.json`

The repo has no root `package.json` today, only `frontend/package.json`.
Add a minimal one: `@playwright/test` as the single devDependency, plus
`test:e2e`, `test:e2e:ui`, `test:e2e:headed` scripts. Also add
`commitlint.config.js` (`extends: ['@commitlint/config-conventional']`) so
commitlint runs off committed config rather than an inline npx guess.

### `e2e/`

```
e2e/
  helpers/     host.ts, player.ts — create a session, join with a PIN
  tests/       auth.setup.ts, join.spec.ts, game-flow.spec.ts
  tsconfig.json
```

Helpers keep the two-context dance in one place. Selectors come from the
existing DOM where it is already unambiguous; where it isn't, add
`data-testid` rather than leaning on text that visual work will churn.

### `.github/workflows/ui-tests.yml`

Wiki's file with the names swapped, and with the parts our `ci.yml` already
proved unnecessary removed:

- Triggers: `push` to `develop`, `pull_request`, `workflow_dispatch`.
  Concurrency group cancels in-progress.
- Services: redis-cache 13000, redis-queue 11000, mariadb **11.8** (match
  our `ci.yml`, not wiki's 10.6).
- `echo "127.0.0.1 trivia_tap.test" | sudo tee -a /etc/hosts`.
- Caches: pip, yarn, and `~/.cache/ms-playwright`.
- Bench setup, `bench get-app trivia_tap $GITHUB_WORKSPACE`, new site
  `trivia_tap.test`, install, build.
- Skip the `SET GLOBAL character_set_server` lines wiki runs. MariaDB 11.8
  is utf8mb4 by default, and our `ci.yml` has been green without them.
- `set-config allow_tests true` and `set-config host_name
  "http://trivia-tap.test:8000"`.
- Comment out `watch:` and `schedule:` in the Procfile, `bench start &`,
  then poll `curl` until the site answers (60s timeout).
  **Keep `socketio:` running.** Wiki does not care about it; we do, the whole
  game rides on it.
- `npx playwright install --with-deps chromium`, then `npx playwright test`
  with `BASE_URL`, `FRAPPE_USER`, `FRAPPE_PASSWORD` in env.
- Always upload `playwright-report/`, upload `test-results/` on failure,
  and dump `bench_start.log` + `logs/*.log` on failure.
- `timeout-minutes: 60`.

### `linter.yml`: add the commitlint job

Wiki's `commit-lint` job verbatim: checkout with `fetch-depth: 200`, node,
`npx commitlint --from <base.sha> --to <head.sha>`. The app already follows
conventional commits by convention; this makes it a gate.

## What gets changed

**Done (2026-07-20)**, the three fixes that needed no new dependency:

- **`ci.yml`**: `paths-ignore` for `**.js`, `**.vue`, `**.css`, `**.ts` on
  both `push` and `pull_request`, so frontend-only changes don't spin up a
  bench for python tests that cannot have changed. Concurrency group was
  `develop-trivia-tap-${{ github.event.number }}`, which is empty on `push` and
  so collapsed every push to one key, each cancelling the last. Now
  `${{ github.event.number || github.ref }}`, as wiki's ui-tests does.
- **`.pre-commit-config.yaml`**: dropped the `cypress/.*` exclude from the
  eslint hook. No such directory ever existed here.

Not verified locally: `paths-ignore` only demonstrates itself on a real PR.

**Still pending**, blocked on the e2e work above:

- **`.pre-commit-config.yaml`**: `e2e/.*` scope. Playwright specs are TS and
  the eslint hook here is JS-only, so they are likely simply out of scope and
  nothing more is needed. Confirm once the files exist.
- **`.gitignore`**: `e2e/.auth/`, `playwright-report/`, `test-results/`,
  `node_modules/` at root.

## Risks

- **Flake.** A realtime game E2E is the flakiest kind of test there is. Every
  wait must be on an assertion (`expect(locator).toBeVisible()`), never a
  fixed `sleep`. Question timers are the sharp edge: a test that races a
  30-second countdown will fail on a slow runner. Prefer sessions authored
  with generous per-question time, or a test-only way to shorten it.
- **socketio in CI.** If guest sockets misbehave under `bench start` in CI,
  that is a real finding, not a test problem. `scripts/check_guest_socket.cjs`
  already exists for exactly this and can be the first thing the workflow
  runs on failure.

## Done when

- `yarn test:e2e` green locally against `trivia-tap.localhost:8000`.
- All three workflows green on a PR into `develop`.
- A deliberately broken selector makes `ui-tests` red, with a screenshot in
  the uploaded artifact.
