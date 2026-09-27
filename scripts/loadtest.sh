#!/usr/bin/env bash
# End-to-end live-quiz load test. Runs from the bench host (production or dev).
# Arms a session with N bot participants, drives the shared ticker on the real
# worker, fires one submit salvo per question, prints a latency matrix, cleans up.
#
#   apps/trivia_tap/scripts/loadtest.sh <players> [origin] [site]
#
#   players   number of bot participants (required)
#   origin    URL the driver hits (default https://<site>)
#   site      frappe site (default: sites/currentsite.txt)
#
# Examples:
#   apps/trivia_tap/scripts/loadtest.sh 1000
#   apps/trivia_tap/scripts/loadtest.sh 1000 https://quiz.example.com quiz.example.com
set -euo pipefail

PLAYERS="${1:?usage: loadtest.sh <players> [origin] [site]}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$BENCH_DIR"

SITE="${3:-$(cat sites/currentsite.txt)}"
ORIGIN="${2:-https://$SITE}"
STATE_FILE="/tmp/trivia_tap_loadtest.json"

echo "bench=$BENCH_DIR site=$SITE origin=$ORIGIN players=$PLAYERS"
echo

echo "==> arming session ($PLAYERS participants)"
TT_LOADTEST_PLAYERS="$PLAYERS" bench --site "$SITE" console < apps/trivia_tap/scripts/loadtest_setup.py \
	| grep "armed session" || { echo "setup failed (is 'General Knowledge' seeded?)"; exit 1; }

# Drive the ticker in the foreground, not via the RQ worker. loadtest_setup.py arms
# the game with low-level calls, and the dev bench's single worker will not schedule
# the shared ticker before the get_ready state's TTL expires under a large arm. A
# foreground loop advances the game deterministically. It exits on its own once the
# active-sessions set is cleared in cleanup.
echo "==> starting ticker (foreground)"
echo 'from trivia_tap import engine; engine.run_ticker()' | bench --site "$SITE" console > /dev/null 2>&1 &
TICKER_PID=$!

echo "==> driving submits"
TT_LOADTEST_ORIGIN="$ORIGIN" env/bin/python apps/trivia_tap/scripts/loadtest.py
rc=$?

echo
echo "==> cleanup"
SESSION="$(env/bin/python -c "import json; print(json.load(open('$STATE_FILE'))['session'])")"
kill "$TICKER_PID" 2>/dev/null || true
bench --site "$SITE" console <<PY > /dev/null
import frappe
frappe.cache.delete("tt:active_sessions")
s = "$SESSION"
frappe.db.delete("TT Answer", {"session": s})
frappe.db.delete("TT Participant", {"session": s})
frappe.delete_doc("TT Session", s, force=True, ignore_permissions=True)
frappe.db.commit()
print("removed test session", s)
PY
echo "done (session $SESSION removed)"

exit $rc
