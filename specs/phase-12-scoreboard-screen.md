# Phase 12: Scoreboard screen

## Goal

Split the one screen that ends a question into two. First the room sees **what
everyone answered**. Then, on its own screen, it sees **who moved**: the points
land on the rows and the rows climb or fall to their new places.

Today both live on the stats screen: the distribution bars, the top five and the
streak callouts share it, so the points arrive as a list that is already sorted.
Nobody sees the overtake happen.

## Tracer bullet

1. New `scoreboard` phase in the engine after the stats screen, carrying every
   player's new score, the points they just won, and the rank they held before.
   **Feedback: the event lands in the room with both ranks.**
2. Host screen renders the standings, animates them, and the host advances from
   there. **Feedback: the room watches a player overtake another.**
3. Reload lands back on the settled standings, no replay.

## State machine

```
question -> [explanation] -> stats -> scoreboard -> get_ready(next)
question -> stats -> [explanation] -> scoreboard -> get_ready(next)
question(last) -> [explanation] -> stats -> podium
```

The standings are the last beat before the next question, whichever order the
explanation is set to. On the last question there is nothing to stand on but the
podium, so the scoreboard is skipped.

`close_question` still settles everything at the buzzer. It now also builds the
standings and parks them in Redis state, where every phase between the buzzer and
the standings hands them on untouched.

## Payload

```json
{
  "type": "scoreboard",
  "q_index": 0,
  "total": 5,
  "standings": [
    {"nickname": "bob", "avatar": 4, "score": 954, "gained": 954, "rank": 1, "previous_rank": 2}
  ],
  "streaks": [{"nickname": "bob", "avatar": 4, "streak": 3}]
}
```

Top five only, the same slice the stats screen used to show. Ties break on join
time, the way the podium ranks them, so the before and after orders agree.

The streak callouts move here from the stats screen: a streak is a scoreboard
story, not an answer-split one.

## Screen

- Rows open in the order the room already knows (previous ranks), each showing the
  score it had before the question.
- After a beat the points count up on every row at once and the rows move to their
  new places. Row identity is kept, so the move is a real move, not a repaint.
- The rank number reads as the row's place while the list is still in its old
  order, and switches to the true rank once the rows land. A player who dropped
  out of the top five would otherwise leave a gap in the numbering.
- Leader takes an accent border once settled.
- `Next question` on the screen; auto-advance holds it for `SCOREBOARD_SECONDS`.

## Reconnect

`get_host_state` returns the parked standings for the `scoreboard` phase and the
screen paints them settled: a reload mid-animation is not a reason to replay it.

The player phone keeps its own result screen through the standings; it already
shows the player's own points, rank and the top five.

## Exit criteria

- A room of six plays a question and sees the split, then the overtake.
- Host reload during the standings comes back to the same standings.
- The last question goes straight to the podium.
