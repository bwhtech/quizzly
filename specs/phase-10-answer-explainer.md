# Phase 10: Answer explainer

Teach the answer, not just reveal it. After a question closes, the reveal screen carries an optional explanation and an optional explainer image authored on the question.

## Goal

A host can write "why" behind an answer, plus a supporting picture (diagram, map, photo, meme), and every screen shows it during the reveal. Zero engine phase changes: scoring, timing contracts, and the state machine stay as they are.

## Tracer bullet

1. Two fields on `QZ Question`: `explanation`, `explanation_image`. **Feedback: a saved quiz round-trips the text and image in the editor.**
2. Both fields ride the `question_closed` broadcast. **Feedback: host big screen shows the explainer card under the options.**
3. Player result screen shows the same card, reconnect paths carry it.

## Where it renders: the existing reveal, not a new slide

The reveal (`stats` phase) *is* the slide after the question. It already holds the correct-answer highlight, the distribution bars, and the top 5, and the host already controls how long it stays up. Putting the explainer there costs two fields and two template blocks.

A separate `explain` phase (its own state machine step, its own payload, its own reconnect mapping, its own timing knob on both screens) buys a bigger picture and nothing else. Deferred until someone asks for a full-screen teaching slide.

## Model

`QZ Question` (child, istable) gains two fields, placed after `image`:

| field | type | notes |
|---|---|---|
| explanation | Small Text | Optional. Plain text, no rich text: it renders on a TV at 10 feet, formatting is noise. |
| explanation_image | Attach Image | Optional. Separate from `image`, which is the question's own picture and is already on screen during the question. |

No new DocType, no quiz-level setting. A question either has an explainer or it does not.

## Payloads

**`question_payload` must stay clean.** Neither field may appear in the `question` event or in `get_state`'s question dict, for the same reason `correct_option` never does: an explanation is a giveaway ("the treaty was signed in 1919, so...") and the payload reaches every guest device while the clock runs.

`question_closed` (engine `close_question`) gains:

```python
"explanation": question.explanation or None,
"explanation_image": question.explanation_image or None,
```

Reconnect paths, both already question-row aware:

- `get_host_state` — in the `closed` branch, alongside `correct_option`.
- `get_result` — returned with the player's own outcome, so a player who reloads during the reveal sees the same explainer the broadcast carried.

`None` rather than `""` so the client can `v-if` on one truthiness check.

## Screens

**Host (`Host.vue`, `phase === 'closed'`)** — explainer card between the answer options and the distribution bars, so the eye goes correct answer → why → how everyone did. Image capped like the question image (`max-h-[22vh]` / `sm:max-h-[40vh]`) so a tall portrait upload cannot push the leaderboard off screen. Card is skipped entirely when both fields are empty, which is the common case and must not leave a gap.

**Player (`Play.vue`, `phase === 'result'`)** — same content under the rank/score line, above the top-5 list. Text at reading size, image constrained to the card width. This is the screen a player actually studies, so the explainer matters more here than on the TV.

**Editor (`QuizEditor.vue`)** — per question, below the existing image row: an `explanation` textarea (placeholder "Why is this the answer? (optional)") and an explainer image uploader reusing the current `FileUploader` block. Both new fields go into `QUESTION_FIELDS`, otherwise `save()` silently drops them.

## Timing

Manual advance needs nothing: the host reads the room and hits Next.

Auto-advance currently holds the reveal for `STATS_SECONDS = 5`, which is too short to read a paragraph. `close_question` uses a longer hold when the question has an explanation:

```python
EXPLAIN_STATS_SECONDS = 12
```

One constant, chosen by the question's own content, no per-quiz setting.

## Tests

`tests/test_engine.py`:

- `question_payload` and the live `question` event contain neither `explanation` nor `explanation_image`, extending the existing "no giveaway in an open-question payload" assertion.
- `question_closed` carries both fields when set, and `None` for a question with neither.
- Auto-advance reveal window is `EXPLAIN_STATS_SECONDS` for a question with an explanation and `STATS_SECONDS` for one without.

`tests/test_api.py`:

- `get_host_state` during `closed` returns both fields.
- `get_result` returns both fields.

`tests/test_authoring.py`:

- A quiz saved with `explanation` + `explanation_image` reads back with both intact after a reorder (the rebuilt-rows path in `save()`).

## Exit criteria

- Full game in a real browser, host screen + two players: a question with an explainer shows text and image on all three screens during the reveal, and a question without one shows the reveal exactly as it looks today.
- Nothing in any pre-close network payload contains the explanation text (checked on the wire, not just in tests).
- Auto-advance holds long enough to read the explainer, then moves on by itself.
- Host reloads mid-reveal and the explainer is still there.

## Out of scope

- A dedicated full-screen explainer slide with its own engine phase.
- Rich text, links, video, or per-option explanations ("why C is wrong").
- Explainers on the podium or in any post-game recap.
