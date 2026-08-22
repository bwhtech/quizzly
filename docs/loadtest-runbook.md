# 1000-player load run — runbook

Everything below is staged and ready. On "go" it runs top to bottom.

Target: `https://gajendra.fsn.frappe.cloud` (private FC bench).
Generator: 1–2 DoppioBoxes on `test-01` (Hetzner FSN, same region as the target,
so measured latency is server time rather than network).

## 0. Prerequisites (one-time, before "go")

- [ ] `join_session` rate limit lifted on the target — **and a reminder set to restore it**
- [ ] global `frappe.conf.rate_limit` checked: `grep -i rate_limit sites/<site>/site_config.json sites/common_site_config.json`
      (site-wide, not per-IP — if set, a 1000-wide salvo trips it and every bot gets a bare 429)
- [ ] a quiz with **8+ questions** seeded, so the ramp has enough salvos to show a trend
- [ ] devbox slugs agreed and provisioned
- [ ] host API key + secret issued (optional — without it you drive the host screen)

## 1. Bootstrap the generator box

```bash
git clone https://github.com/bwhtech/quizzly && cd quizzly
npm i --no-save undici socket.io-client
ulimit -n 8192          # each bot holds a websocket + an http connection
```

## 2. Pre-flight

```bash
QZ_ORIGIN=https://gajendra.fsn.frappe.cloud QZ_PIN=<lobby pin> \
  scripts/loadtest_preflight.sh 1000
```

Checks clock skew (a snapshot-cloned microVM fails every TLS handshake with
"certificate is not yet valid", which reads exactly like a dead target), node
version, `ulimit -n`, deps, then runs a 2-bot smoke and cleans it up.
**Do not ramp until this is clean.**

## 3. Ramp

Self-hosting — the generator creates each session, seats the bots, starts the
game and plays to the podium, no clicking:

```bash
QZ_QUIZ="General Knowledge" QZ_API_KEY=... QZ_API_SECRET=... \
  scripts/loadtest_ramp.sh
```

Manual host — you open a fresh lobby per stage, the script asks for the pin:

```bash
scripts/loadtest_ramp.sh
```

Stages default to `100 250 500 1000` (`QZ_STAGES` to change), 60s cooldown
between them, one JSON report per stage in `./loadtest-reports/`. The ramp
**stops at the first degraded stage** rather than piling failure on failure.

Splitting across two boxes: run 500 on each with `QZ_STAGES=500` against the
same pin. If two-box 500+500 beats one-box 1000, the generator was the
bottleneck, not the server.

## 4. Watch, server-side

The client numbers say *when* it broke; these say *what* broke.

- gunicorn worker saturation and request queue depth
- the socket.io node process — CPU and RSS during the podium burst
- MariaDB slow log, and lock waits on `QZ Answer` inserts
- RQ: whether the shared ticker stays on schedule or drifts

## 5. Pass / fail, decided before the run

| Measure | Threshold at 1000 | Why |
|---|---|---|
| players seated / sockets live | 100% | anything less and the rest is unreadable |
| question delivery skew p99 | **< 500 ms** | scoring is `(1 - (response_ms/window_ms)/2) * 1000`; on a 20s window 500ms costs ~12 of 1000 points, 2s costs ~50 — 500ms is the edge of fair |
| `submit_answer` p99 | < 1000 ms | beyond this the countdown on screen is lying |
| dropped answers | 0 | excludes legitimate "Already answered" |
| podium delivered | 100%, p99 < 2s | see the prediction below |
| HTTP 429 | 0 | any means a limiter is still in the path |

## 6. The prediction to confirm or kill

`engine.py:403` broadcasts the podium carrying the **full leaderboard** to the
whole room. At 1000 players that is ~80KB × 1000 sockets ≈ **80MB pushed from a
single node process in one burst**, immediately followed by 1000 `get_state`
calls that each return the same leaderboard again over HTTP.

My bet is the first failure is here, not in the submit salvo the existing
`scripts/loadtest.py` measures. The generator reports podium payload size,
fan-out total and delivery skew specifically to settle this. If confirmed, the
fix is small: broadcast top-N only, and let players fetch their own placement.

## 7. Abort

Stop if the target starts serving 5xx to real traffic, or FC's proxy begins
rate-limiting site-wide. `ctrl-c` on the ramp; sessions in flight can be ended
from the host screen.

## 8. Cleanup

```bash
# dry run first
echo 'exec(open("apps/quizzly/scripts/loadtest_cleanup.py").read())' | bench --site <site> console
# then
QZ_CLEANUP_APPLY=1 bash -c 'echo "exec(open(\"apps/quizzly/scripts/loadtest_cleanup.py\").read())" | bench --site <site> console'
```

Deletes bot participants and their answers, and drops only sessions where
*every* player was synthetic. Then: **restore the `join_session` rate limit.**
