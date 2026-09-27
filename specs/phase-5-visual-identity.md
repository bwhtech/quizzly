# Phase 5: Visual identity

Everything up to Phase 4 shipped on borrowed shapes: red/blue/yellow/green
triangle, diamond, circle, square, on frappe-ui's default light chrome. It
worked, and it was Kahoot's design. This phase gives TriviaTap a look of its own
without touching the engine: no scoring, timing, or payload contract changes.

## Goal

A host can put the projector screen in front of a room and nobody thinks they
are looking at a clone.

## Direction: night sky

The room is dark, the screen is the light source, and the game is about the
seconds running out.

### Tokens

Defined in `frontend/tailwind.config.js`, used as Tailwind classes everywhere.

| Token    | Hex       | Role                                    |
| -------- | --------- | --------------------------------------- |
| `night`  | `#16111F` | Page ground                             |
| `dusk`   | `#241C31` | Raised surfaces, inputs, chart tracks   |
| `haze`   | `#3A2F4D` | Hairlines, pill borders                 |
| `paper`  | `#F4F0FA` | Text on the ground                      |
| `ember`  | `#FF5A36` | Answer 1, primary action, urgency       |
| `lagoon` | `#17B0BE` | Answer 2, correct                       |
| `gold`   | `#FFC43D` | Answer 3, scores, read-time countdown   |
| `orchid` | `#9B6BFF` | Answer 4                                |

The four answer inks differ in hue *and* lightness, so they stay separable for
colourblind players and on a washed-out projector. Answer tiles always carry
`night` text: every ink is bright enough that dark text is the higher-contrast
choice.

### Answer marks

Bolt, spark, moon, hex, in `SHAPES` (`frontend/src/game.js`). Same job as the
shapes they replace: let a player call out an answer across a room without
reading it. `svgFill` stays a spelled-out literal because Tailwind only
generates class names it can see.

### Type

- **Bricolage Grotesque** (600/800) — display: headings, answer labels, nicknames.
- **Instrument Sans** (400/500/600) — body and UI.
- **Martian Mono** (500/700) — anything numeric or machine-ish: game PIN, timers, scores, ranks, eyebrows.

Loaded from Google Fonts in `frontend/index.html`, with system fallbacks.

### Signature: the drain

Time drains out of a ring, not along a bar. `components/DrainRing.vue` is one
conic-gradient arc with a radial mask and the seconds parked in the middle; it
pulses under 5 seconds. The same component runs at 56px in the player header,
96px on the host question screen, and 140px during read time, so the shape of
"time left" is identical on the phone in your hand and the screen on the wall.

## Layout

- **Join** — one column on `night`: display lockup, mono PIN field, nickname with suggestion pills, avatar grid, ember submit.
- **Player question** — full-bleed 2x2 tiles filling the viewport below a slim question strip. Glyph top-left, label bottom-left, thumb reaches any corner.
- **Host lobby** — PIN in Martian Mono at `8xl` beside a `paper` QR card, player chips below, controls as quiet pills so the game owns the screen.
- **Host read time** — its own centred screen: question at `6xl` with a gold ring. Previously a bare left-aligned line with no countdown.
- **Host reveal** — answer tiles dim except the correct one; distribution bars sit in `dusk` tracks aligned to the answer grid, so an empty bar still reads as a bar.

Host controls share `.ctl` / `.ctl-go` in `frontend/src/index.css` rather than
frappe-ui `Button`, which only ships a light theme.

## Quality floor

- Visible keyboard focus: one gold `:focus-visible` outline for every control, since everything sits on the same dark ground.
- `prefers-reduced-motion` collapses the ring pulse, podium rise, and bar growth.
- Responsive down to 390px.

## Light theme

Shipped. The plan written here was to promote all eight tokens to custom
properties and re-derive the answer inks for a light ground. Building it showed
that was the wrong split: the four inks are the brand. A player learns "red is
top-left" once, and a tile that changes hue with the room breaks the one thing
the whole colour scheme exists to do. They do not theme at all.

What themes is the ground and what sits on it:

- `night`, `dusk`, `haze`, `paper` — ground, elevated surface, border, body text.
- `alert`, `accent`, `ok` — the ember, gold and lagoon hues used as *text* on the
  ground, which has to hold 4.5:1 and so darkens where the fill below it cannot.
  This is the split the original plan missed: one token cannot be both a vivid
  tile and legible small text on white.
- `ember`, `lagoon`, `gold`, `orchid`, `sunk`, `card` — fixed. The answer inks,
  the ink they carry, and the QR quiet zone.

`prefers-color-scheme` picks the default; a Theme control on the host bar and in
the lobby row overrides it in both directions and persists in `localStorage`.
The OS preference alone was not enough: the case this exists for is a bright
room, and the laptop driving the projector is usually still set to dark.

## Avatar picker as a scroll strip

Shipped. `Join.vue` renders the roster as one horizontal `overflow-x: auto` row
with `snap-x`, capped at `max-w-sm` on desktop so it stays a strip rather than
stretching across the column. It bleeds past the page gutter on a phone: the
faces cut off at both edges are the only thing that says it scrolls.

The opening pick is random, so it lands anywhere in the roster. The selected
button scrolls itself into view on mount, otherwise the strip opens on the first
face and nothing looks chosen.

A search field past ~60 avatars is still worth having, but nothing needs it yet.

## Deferred

Nothing.

## Non-goals

- No engine, API, or realtime changes. This phase is CSS, markup, and one new component.
- No illustration or motion beyond the drain ring. One signature, kept alone.
