# Phase 1: Content + Session Shell

## Goal

All DocTypes exist, a host can create a session, and the lobby works end-to-end: join via PIN/QR, names appear live on the host screen, kick and lock work.

## DocTypes

### TT Quiz (the content)

Authored in Desk by hosts. `autoname: format:TT-{####}`.

| field | type | notes |
|---|---|---|
| title | Data, reqd | |
| description | Small Text | |
| default_time_limit | Int, default 20 | seconds per question |
| questions | Table -> TT Question | |

### TT Question (child, istable)

| field | type | notes |
|---|---|---|
| question_text | Small Text, reqd | |
| option_1..option_4 | Data, reqd | canonical order, server-side only |
| correct_option | Select 1\n2\n3\n4, reqd | NEVER serialized to players until close |
| time_limit | Int | blank = quiz default |
| points_multiplier | Select 0\n1\n2, default 1 | 0 = fun question, 2 = double |

Child rows have stable `name` (row id); answers reference it.

### TT Session (one running game)

`autoname: hash`.

| field | type | notes |
|---|---|---|
| quiz | Link TT Quiz, reqd | |
| host | Link User, reqd | set server-side to session creator |
| game_pin | Data, unique | 6 digits, generated, reused pins avoided while active |
| status | Select Lobby\nActive\nEnded\nCancelled | |
| lobby_locked | Check | |
| auto_advance | Check, default 1 | else host advances |
| randomize_answer_order | Check, default 1 | per-participant display shuffle |
| current_question | Int, default -1 | index into quiz questions |
| started_at / ended_at | Datetime | |

### TT Participant

`autoname: hash`.

| field | type | notes |
|---|---|---|
| session | Link TT Session, reqd | |
| nickname | Data, reqd | unique per session (validated in controller) |
| token_hash | Data | sha256 of participant_token; raw token never stored |
| score | Int, default 0 | |
| streak | Int, default 0 | current correct streak |
| rank | Int | final rank, set at end |
| kicked | Check | kicked tokens rejected on all APIs |
| joined_at | Datetime | |

### TT Answer

`autoname: hash`.

| field | type | notes |
|---|---|---|
| session | Link TT Session, reqd | |
| participant | Link TT Participant, reqd | |
| question_row | Data, reqd | child row name of TT Question |
| selected_option | Select 1\n2\n3\n4 | |
| is_correct | Check | computed server-side |
| response_ms | Int | server receive time minus question opened_at |
| points | Int | computed server-side |

Composite unique constraint (participant, question_row) via `on_doctype_update()`:

```python
# tt_answer.py
def on_doctype_update():
    frappe.db.add_unique("TT Answer", ["participant", "question_row"])
```

Duplicate submits die at the DB level regardless of race conditions.

## Permissions

- TT Quiz, TT Session: role Quiz Host (create/write own), System Manager all. `if_owner` for hosts.
- TT Participant, TT Answer: no direct role access for anyone but System Manager. All reads/writes go through whitelisted APIs. Guests never touch the REST resource API.
- correct_option: exists only in TT Question, which guests can never read. Question delivery API builds the payload explicitly, field never included.

## APIs

Host APIs (login + Quiz Host role, host must own session):

| endpoint | does |
|---|---|
| `create_session` | from quiz, generate PIN |
| `lock_lobby` / `unlock_lobby` | |
| `kick_participant` | sets kicked, publishes `kicked` targeted payload |

Guest APIs (`allow_guest=True`, rate-limited via `frappe.rate_limiter`):

| endpoint | args | does |
|---|---|---|
| `join_session` | pin, nickname | validate lobby open + not locked, nickname clean/unique, create participant, return token + session snapshot |
| `leave_session` | pin, token | mark left, lobby update |

Token: 32-byte random, returned once to the client, only sha256 stored server-side. Client keeps it in localStorage.

## Lobby flow

1. Host (logged-in Desk user with Quiz Host role) creates TT Session from a quiz. PIN generated, status Lobby.
2. Player: GET join page, enters PIN + nickname (or QR link `/join?pin=XXXXXX` prefills PIN). `join_session` validates PIN, lobby open, nickname unique + clean, creates TT Participant, returns `participant_token`. Lobby update published on `tt_session_{pin}`.
3. Host can lock lobby and kick players. Kicked tokens rejected on all APIs.

Quiz authoring stays in Frappe Desk (free CRUD UI on TT Quiz).

## Exit criteria

- Host creates quiz in Desk, creates session, sees giant PIN.
- Player joins via PIN and via QR link, name pops onto host screen live.
- Wrong PIN, locked lobby, and duplicate nickname all rejected.
- Kick works; kicked token rejected afterwards.
