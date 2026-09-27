# Phase 4a: Content (images + authoring UI)

Slice 1 of Phase 4 juice. See `phase-4-juice.md` for the umbrella.

## Goal

A host can create and edit a quiz entirely in the SPA, including a picture on any question, and play it. Removes the Desk-only authoring constraint that makes the app unusable for a real host.

## Tracer bullet

Ship the thinnest end-to-end path first, then widen:

1. `image` Attach Image field on `TT Question` + question payload carries `image_url` + player and host question views render it. Author the image in Desk for this step. **Feedback: an image shows up mid-game on both screens.**
2. `/host/quizzes` list + `/host/quizzes/new` create form that saves a quiz with one question through a whitelisted API. **Feedback: a quiz authored in the SPA is playable.**
3. Widen the form: edit, delete, reorder, per-question time limit and multiplier, upload image from the form.

## Data model

`TT Question` gains:

- `image` — Attach Image, optional.

No other schema change. Images ride on the standard `File` doctype and are served from `/files/...`.

## APIs

Authoring is CRUD on one doctype, which the framework already exposes, so the editor uses `frappe.client.*` and TriviaTap adds one endpoint:

- `list_quizzes()` (`trivia_tap/api.py`) — `name`, `title` and a question count per quiz. The count is the only part `frappe.client.get_list` cannot return without an aggregate whose result key is the raw SQL expression.
- Read: `frappe.client.get("TT Quiz", name)`, which returns the child rows in `idx` order, image included.
- Save: `frappe.client.insert` for a new quiz, `frappe.client.save` for an existing one. `get_doc(dict).save()` replaces the child table with whatever it is given, so sending the whole list in display order makes reorder and delete a plain save.
- Delete: `frappe.client.delete`.

An app-level wrapper around each of those was written first and then deleted. It re-implemented what the framework does, and it enforced ownership by hand when `if_owner` on `TT Quiz` already does exactly that. It was not even a smaller attack surface: `frappe.client.save` is whitelisted for every logged-in user whether or not this app calls it.

Two rules the client has to respect on the standard path, both verified in the browser and pinned by a test:

- Send the loaded doc back as it came. Frappe refuses a save that drops `creation` or `owner`, and rejects a stale `modified`, which is the concurrent-edit protection the hand-written `save_quiz` silently lacked.
- Rebuild the question rows without `name` or `idx`. Frappe keeps an `idx` it is given, so rows carrying their old one would ignore the reorder.

Image upload reuses the framework's `/api/method/upload_file` through frappe-ui's `FileUploader`, and the returned `file_url` is stored on the question row. No custom upload endpoint. The file is not attached to the parent quiz, because a brand new quiz has no name yet when the host picks the picture.

## Validation

In the `TT Quiz` controller, so nothing on any path can write a quiz the engine cannot play:

- At least one question.
- Each question: non-empty text, all four options non-empty, `correct_option` in 1..4.

In the editor, because a time limit is an authoring taste rather than an integrity rule:

- `time_limit` clamped to 5..120 seconds, native `min`/`max` on the input, falling back to the quiz default when unset.

The range is deliberately not in the controller. The engine plays any window correctly, and the test suite uses 1 to 2 second questions to keep runs fast; a controller-level range broke 26 existing tests to buy nothing. The worst a hand-crafted request achieves is a host boring their own players.

## Question payload change

`publish_question` adds `image_url` (null when absent). Everything else stays byte-identical, so a quiz with no images produces the exact payload v1 produced.

## Screens

- `/host/quizzes` — list, create button, edit and delete per row.
- `/host/quizzes/:name` — question-by-question editor: text, image picker with preview and remove, four option inputs, correct-option radio, time limit, multiplier. Add, delete, and reorder questions. Reorder is a pair of up/down buttons, not drag: a drag library is a dependency, and a quiz is a handful of rows. Revisit when a host writes 30-question quizzes and starts moving a row across a screenful.
- Existing `/host` quiz picker links out to the editor when the host has no quizzes yet.

Image display rules: contained, max 40% of the question area's height on the host screen, above the options on the player screen. Never letterboxed or cropped, never pushing options below the fold on a phone.

## Tests

Only what this app adds to the standard path is worth a test:

- A reorder sent through `frappe.client.save` lands in `tabTT Question` `idx` order.
- The controller rejects zero questions, a blank option, and `correct_option` out of range.
- `list_quizzes` returns the question count.
- Deleting a quiz a session references raises `LinkExistsError`.
- A question with an image produces `image_url` in the published payload; one without produces `null`.

## Exit criteria

- Host creates a quiz in the SPA with an image on one question, starts a session on it, plays it to podium with a real player, never touching Desk.
- A pre-existing image-free quiz plays with byte-identical payloads to v1.
