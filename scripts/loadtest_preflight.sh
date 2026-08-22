#!/usr/bin/env bash
# Pre-flight for a live load run. Run this on the load-generating box before the
# ramp: it catches the failures that otherwise look like the target breaking.
#
#   QZ_ORIGIN=https://site QZ_PIN=123456 scripts/loadtest_preflight.sh [players]
set -uo pipefail

ORIGIN="${QZ_ORIGIN:-https://gajendra.fsn.frappe.cloud}"
PLAYERS="${1:-1000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fails=0

check() {
	if [ "$1" = "ok" ]; then printf '  \033[32mok\033[0m   %s\n' "$2"
	else printf '  \033[31mFAIL\033[0m %s\n' "$2"; fails=$((fails + 1)); fi
}

echo "pre-flight: origin=$ORIGIN players=$PLAYERS"

# A snapshot-cloned microVM comes up with a skewed clock, and every TLS handshake
# then fails with "certificate is not yet valid" — which reads as a dead target.
remote_date="$(curl -sI "$ORIGIN" | awk 'BEGIN{IGNORECASE=1} /^date:/{sub(/^[Dd]ate: /,""); print}' | tr -d '\r')"
if [ -n "$remote_date" ]; then
	skew=$(( $(date -u +%s) - $(date -u -d "$remote_date" +%s 2>/dev/null || date -u -jf "%a, %d %b %Y %T %Z" "$remote_date" +%s) ))
	[ "${skew#-}" -lt 30 ] && check ok "clock skew ${skew}s" || check fail "clock skew ${skew}s — sync ntp before running"
else
	check fail "no Date header from $ORIGIN (target unreachable or TLS failed)"
fi

node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' 2>/dev/null \
	&& check ok "node $(node -v)" || check fail "node >= 20 required (have $(node -v 2>/dev/null || echo none))"

# every bot holds a websocket and an http connection; the default 1024 is not enough
limit="$(ulimit -n)"
[ "$limit" = "unlimited" ] || [ "$limit" -ge $((PLAYERS * 3)) ] \
	&& check ok "ulimit -n $limit" \
	|| check fail "ulimit -n $limit, need >= $((PLAYERS * 3)) — run: ulimit -n $((PLAYERS * 4))"

node -e 'import("undici");import("socket.io-client")' 2>/dev/null \
	&& check ok "deps installed" || check fail "run: npm i --no-save undici socket.io-client"

if [ -n "${QZ_PIN:-}" ]; then
	out="$(QZ_PLAYERS=2 QZ_TIMEOUT=8 QZ_LEAVE=1 QZ_NAME_PREFIX=preflight \
		node "$SCRIPT_DIR/loadtest_live.mjs" 2>&1)"
	echo "$out" | grep -q "sockets live" \
		&& check ok "2-bot smoke: $(echo "$out" | grep 'seated' | xargs)" \
		|| { check fail "2-bot smoke failed"; echo "$out" | sed 's/^/       /'; }
else
	echo "  skip QZ_PIN not set, skipping the smoke run"
fi

echo
[ "$fails" -eq 0 ] && echo "pre-flight clean" || echo "$fails check(s) failed — fix before ramping"
exit "$fails"
