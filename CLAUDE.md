# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TriviaTap is a live multiplayer quiz application built on Frappe. Guests join a game with a PIN or QR code, no login required, and gameplay is server-authoritative. The Python backend lives in `trivia_tap/`, with portal pages served from `www/`. See `plan.md` and `specs/` for the build plan.

## IMPORTANT

- Always load and use frappe-app-dev skills.

## Guidelines for writing good code

- use /code-style skill
- Choose clean code over clever code.
- Use standard API as much as possible.
- Reuse. Write as little code as possible.
- Use Frappe UI, espresso design system for UI styling.
- Always write tests, and make sure they work.
- Build the minimum working app, then iterate towards your goals.

## Development and Testing

- use the `/agent-browser` skill to test in the browser. site: quizzly.localhost
- use Administrator/admin as credentials.
- After every bug fix or feature: Send me a Telegram Message using `tg_bot -h`, attach relevant screenshots related to the fix/feature.
- Kill all the browser session after testing.

## Planning / Spec-ing

Use Tracer bullets comes from the Pragmatic Programmer. When building systems, you want to write code that gets you feedback as quickly as possible. Tracer bullets are small slices of functionality that go through all layers of the system, allowing you to test and validate your approach early. This helps in identifying potential issues and ensures that the overall architecture is sound before investing significant time in development.

## Implementation Guidelines

- Overrides the bench-level approval rule: in this app, create branches and commit autonomously, no prior approval needed. Pushing to remotes and raising PRs still require approval.
- Create a new branch before working on a new feature/spec (branch name patterns: feat/, fix/, just like conventional commit pre-fixes)
- Reconcile the spec and log the progress in progress.md after each phase of development
- Commit after each meaningful phase
- Commit the spec before the development commits
- Use comments only when necessary to explain "why?" not "how?", how must be clear from the code itself

### Code Quality

```bash
pre-commit run --all-files    # Run all pre-commit hooks (ruff, prettier, eslint)
```

## Pull Requests

- Raise PR always against the develop branch
- Keep pull request descriptions stupid simple
- Some formats:
    - h2 Problem (1-2 sentences), h2 Solution: good for bugs, etc.