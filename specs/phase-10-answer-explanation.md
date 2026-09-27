# Phase 10: Answer explanation screen

## Goal

Between the buzzer and the scoreboard, the room gets one screen that says **why**
that answer is right. Text, an optional image, or both. Off by default, on per
quiz.

## Tracer bullet

1. `explanation` + `explanation_image` on `TT Question`, `show_explanation` on
   `TT Quiz`. **Feedback: the fields save and come back.**
2. New `explanation` phase in the engine between `question` and `stats`.
   **Feedback: the host screen shows the explanation, then the distribution.**
3. Player phone shows its own verdict with the explanation under it.

## State machine

```
get_ready -> question -> [explanation] -> stats -> get_ready(next) | podium
get_ready -> question -> stats -> [explanation] -> get_ready(next) | podium
```

Which of the two is a quiz setting, `explanation_position`, defaulting to
before. Before keeps the teaching beat away from the scoreboard scramble; after
lets the room see the split first and then hear why.

`close_question` still settles everything at the buzzer: scoring, streaks,
distribution, top 5. Only the *publish* moves. When the quiz explains answers and
the question has something to say, the scoreboard payload is parked in Redis
state as `closed_payload` and an `explanation` event goes out instead. The
explanation step then publishes the parked payload unchanged.

Parking it beats recomputing: scores are already written, and a second pass over
participants would be pure duplication.

The phase is skipped entirely when `show_explanation` is off or the question has
neither text nor image, so a half-authored quiz never stalls on a blank screen.

## Timing

The quiz's `explanation_time_limit` (default 10s) with auto-advance on,
`ADVANCE_WAIT_CAP` with it off, the same rule the stats phase already follows.
`EXPLANATION_SECONDS` is only the fallback for a quiz that never set one.

With auto-advance off the host clicks **Show results**, then **Next question**:
two beats, both host-driven.

The host buttons name the next screen rather than a fixed one, so the payloads
carry `before_stats` on the explanation and `explanation_next` on the stats.

## Reconnect

`get_host_state` and the player `get_state` both return the stored explanation
payload while the phase is live, so a reload lands back on the explanation
screen rather than skipping it.

## Authoring

One toggle on the quiz (`Explanations on/off`), a before/after button and a
seconds field beside it, and,
when it is on, a text box plus an image uploader per question. The per-question
fields hide with the toggle rather than being deleted, so flipping it off and
back on loses nothing.

## Out of scope

- Per-question control over whether the screen shows (the text being empty is
  the control).
- Rich text or links in the explanation. Plain text on a projector.
