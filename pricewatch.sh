#!/bin/sh
# Wrapper for the launchd agent. See com.plainlyai.pricewatch.plist.
#
# prices.py prints and exits non-zero when something moved or could not be
# verified. Run from a schedule, that output goes nowhere anybody looks, which
# would make the watcher the quiet failure it was written to prevent. So this
# appends every run to a log and raises a macOS notification when a run is not
# clean.
#
# It also refuses to cry wolf. If the machine simply has no network, every
# source fails to fetch and prices.py correctly reports UNVERIFIED across the
# board. Alarming about that would train you to dismiss the notification, which
# costs more than the missed run. A connectivity probe comes first, and an
# offline run is logged and skipped rather than announced.

REPO="/Users/varga/Developer/plainly-ai"
LOG="$HOME/Library/Logs/plainlyai-pricewatch.log"
PYTHON="/usr/bin/python3"

cd "$REPO" || { echo "pricewatch: $REPO is gone" >> "$LOG"; exit 1; }

stamp() { date '+%Y-%m-%d %H:%M:%S %z'; }

# Reachability, not a fetch: one vendor host, short timeout, no page parsed.
if ! /usr/bin/curl -sS -o /dev/null --max-time 10 https://platform.claude.com/ 2>/dev/null; then
  printf '=== %s\noffline, skipped\n\n' "$(stamp)" >> "$LOG"
  exit 0
fi

out=$("$PYTHON" prices.py 2>&1)
status=$?

printf '=== %s\n%s\nexit %s\n\n' "$(stamp)" "$out" "$status" >> "$LOG"

if [ "$status" -ne 0 ]; then
  summary=$(printf '%s' "$out" | grep -E 'figures checked' | head -1)
  [ -n "$summary" ] || summary="prices.py exited $status"
  /usr/bin/osascript -e "display notification \"${summary}\" with title \"Plainly: Model facts needs a look\" sound name \"Submarine\"" >/dev/null 2>&1
fi

exit 0
