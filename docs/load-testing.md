# Live Quiz Load Test

Drives N guests at `submit_answer` over HTTP, one salvo per question, and reports
latency percentiles for the concurrency-critical path (`mark_answered` + Answer
insert + batch scoring at close).

Scripts:

- `loadtest.sh` — one-command runner. Arms the game, drives the ticker on the real
  worker, runs the driver, prints the matrix, deletes the test session. Player count
  is the first argument.
- `loadtest_setup.py` — runs in frappe context. Mints participants directly (skips
  the single-IP join throttle, an artifact of driving from one host) and arms the
  game. Reads player count from `TT_LOADTEST_PLAYERS` (default 100).
- `loadtest.py` — the HTTP driver. Reads `/tmp/trivia_tap_loadtest.json`, polls state,
  fires one submit salvo per question, prints the latency matrix.

## Quick start

```bash
# apps/trivia_tap/scripts/loadtest.sh <players> [origin] [site]
apps/trivia_tap/scripts/loadtest.sh 1000
apps/trivia_tap/scripts/loadtest.sh 1000 https://quiz.example.com quiz.example.com
```

Site defaults to `sites/currentsite.txt`, origin to `https://<site>`. The rest of
this doc explains the pieces the script wires together, plus how to tune the web
tier so the numbers are real.

## Prerequisites

- Quiz seeded. `loadtest_setup.py` looks up `General Knowledge` (run
  `scripts/seed_demo.py` first if missing).
- Web tier must be gunicorn, not `bench serve` (see below).
- **Do not point it at a site with live players** — it writes real sessions,
  participants, and answers, and saturates the web tier. Use a staging clone or a
  dedicated load-test site, off-peak.

## Why not `bench serve`

`bench serve` is the werkzeug dev server: single process, cannot accept ~1000
concurrent sockets. It resets connections under load (`ConnectionError`), so the
numbers reflect the dev server, not the app. Always load test against gunicorn.

## Option A — gunicorn only (local, real serving path)

No nginx, no supervisor, no root. Good enough to get true app numbers on a dev box.

Size the pool under MariaDB `max_connections` — each active thread holds one DB
connection. Check it:

```bash
bench --site <site> mariadb -e "SHOW VARIABLES LIKE 'max_connections'"
```

Keep `workers * threads` a bit below that value. Default dev is 60, so 8x6=48:

```bash
env/bin/gunicorn --chdir sites -b 127.0.0.1:8001 \
  -w 8 --threads 6 -k gthread -t 120 --backlog 4096 \
  frappe.app:application
```

- `-k gthread` — threaded workers, no extra dep (gevent not required).
- `--backlog 4096` — excess connections queue instead of being reset.
- Frappe resolves the site from the `Host` header, so hitting `trivia-tap.localhost:8001`
  serves the same site.

To push past 48 concurrent DB handlers, raise the DB cap (needs MariaDB root):

```bash
sudo mysql -e "SET GLOBAL max_connections=250"   # runtime only, resets on restart
```

then size gunicorn e.g. `-w 8 --threads 25` (200 handlers, under 250).

## Option B — full production (real environment)

Closest to how it actually runs. Sets up gunicorn + nginx + supervisor.

```bash
sudo bench setup production <user>
```

This generates:

- gunicorn workers (tune in `common_site_config.json` → `gunicorn_workers`, or the
  supervisor conf). Production default is `2 * cpu + 1`.
- nginx as reverse proxy + static/socketio routing.
- supervisor to keep web, workers, scheduler, and socketio alive.

Tuning for a real load test:

1. **DB connections.** Set MariaDB `max_connections` in `my.cnf` above
   `gunicorn_workers * threads + socketio + workers + headroom`. Persist it, then
   restart MariaDB.
2. **Gunicorn.** Set `gunicorn_workers` in `common_site_config.json`, then
   `sudo supervisorctl restart all` (or `bench restart`).
3. **Ticker — run it in the foreground, do NOT enqueue it.** In normal gameplay
   starting a session enqueues `run_ticker` on the `long` RQ queue. For load testing,
   `loadtest_setup.py` arms the game with low-level calls and `loadtest.sh` drives the
   ticker as a foreground loop instead:

   ```bash
   echo 'from trivia_tap import engine; engine.run_ticker()' | bench --site <site> console &
   ```

   Do not rely on the enqueued path here: under a large arm the single dev worker may
   not schedule the job before the `get_ready` state's TTL expires, and the game dies
   with zero answers. The foreground loop advances deterministically and exits once
   the active-sessions set is cleared. The setup script already sets `auto_advance = 1`.
4. **socketio.** Live push (answer counts, phase changes) goes over socketio. Under
   1000 clients, watch the node process; scale with `bench setup socketio` /
   multiple socketio processes behind nginx if it saturates.

## Running manually

`loadtest.sh` does all of this. Run the steps by hand only when debugging one stage:

```bash
# 1. arm the game (creates session + participants, writes /tmp/trivia_tap_loadtest.json)
TT_LOADTEST_PLAYERS=1000 bench --site <site> console < scripts/loadtest_setup.py

# 2. start the ticker. local: foreground loop. production: enqueue on the long worker (see Option B step 3)
echo 'from trivia_tap import engine; engine.run_ticker()' | bench --site <site> console &

# 3. run the driver
TT_LOADTEST_ORIGIN="https://quiz.example.com" env/bin/python scripts/loadtest.py
```

## Reading the output

```
┌────┬───────────┬─────┬─────┬─────┬─────┐
│ Q  │ ok/total  │ p50 │ p95 │ p99 │ max │
├────┼───────────┼─────┼─────┼─────┼─────┤
│ Q1 │ 1000/1000 │ 137 │ 229 │ 290 │ 373 │
├────┼───────────┼─────┼─────┼─────┼─────┤
│ Q5 │ 1000/1000 │ 231 │ 437 │ 511 │ 682 │
└────┴───────────┴─────┴─────┴─────┴─────┘

=== overall ===
questions driven: 5  submits: 5000  ok: 5000
latency ms  p50=193 p95=363 p99=459 max=682 mean=206
errors: -
```

- `ok/total` per question — anything less than total means dropped submits.
- `ConnectionError` — web tier too small (workers/backlog) or OS socket limits.
- `500` — check `Error Log` in Desk; app-level failure under load.
- `1064/pool` style DB errors — `max_connections` too low for the pool size.

## Cleanup

`loadtest.sh` clears the active set and deletes the test session (answers +
participants + session) automatically. For the manual path, do it yourself:

```bash
# stop the ticker (clears active set so run_ticker's loop exits), then delete test data
bench --site <site> console <<'PY'
import frappe
frappe.cache.delete("tt:active_sessions")
s = "<session-name>"   # from the "armed session=..." line
frappe.db.delete("TT Answer", {"session": s})
frappe.db.delete("TT Participant", {"session": s})
frappe.delete_doc("TT Session", s, force=True, ignore_permissions=True)
frappe.db.commit()
PY
```
