#!/usr/bin/env bash
# Ramp a live quiz through increasing player counts, one full game per stage,
# writing a JSON report per stage. Stops at the first stage that degrades, so a
# broken run does not burn the whole ramp.
#
# Self-hosting (preferred, no host clicking):
#   QZ_QUIZ="General Knowledge" QZ_API_KEY=... QZ_API_SECRET=... scripts/loadtest_ramp.sh
#
# Manual host (you drive the host screen, script prompts for each stage's pin):
#   scripts/loadtest_ramp.sh
set -uo pipefail

ORIGIN="${QZ_ORIGIN:-https://gajendra.fsn.frappe.cloud}"
STAGES="${QZ_STAGES:-100 250 500 1000}"
OUT_DIR="${QZ_OUT_DIR:-./loadtest-reports}"
COOLDOWN="${QZ_COOLDOWN:-60}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OUT_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
echo "ramp $stamp  origin=$ORIGIN  stages=[$STAGES]  reports=$OUT_DIR"

for players in $STAGES; do
	echo
	echo "════ stage: $players players ════"

	# the generator only creates its own session in hosted mode; otherwise the
	# host makes one and we need its pin before any bot can join
	if [ -z "${QZ_QUIZ:-}" ]; then
		read -rp "  open a fresh lobby on the host screen, then enter its pin: " QZ_PIN
		export QZ_PIN
	fi

	report="$OUT_DIR/${stamp}-${players}.json"
	QZ_PLAYERS="$players" QZ_OUT="$report" QZ_NAME_PREFIX="bot" \
		node "$SCRIPT_DIR/loadtest_live.mjs"
	status=$?

	if [ "$status" -ne 0 ]; then
		echo "  stage $players exited $status — stopping the ramp here"
		exit "$status"
	fi

	# a stage that lost players or dropped answers makes every larger stage
	# unreadable, so the ramp stops rather than piling failure on failure
	if node -e '
		const r = require(process.argv[1]);
		const lost = r.sockets < r.players;
		const dropped = r.questions.some((q) => Object.keys(q.errors).length);
		const undelivered = r.questions.some((q) => {
			const [got, want] = q.delivered.split("/").map(Number);
			return got < want;
		});
		process.exit(lost || dropped || undelivered ? 1 : 0);
	' "$(cd "$(dirname "$report")" && pwd)/$(basename "$report")"; then
		echo "  stage $players clean"
	else
		echo "  stage $players degraded — see $report. Stopping."
		exit 1
	fi

	echo "  cooling down ${COOLDOWN}s"
	sleep "$COOLDOWN"
done

echo
echo "ramp complete, reports in $OUT_DIR"
