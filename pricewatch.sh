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
#
# Catch-up. The agent's calendar trigger is 09:15, but launchd only re-runs a
# job missed while the machine was asleep; one missed while it was powered off
# is dropped without a trace. That is not hypothetical — it happened on
# 27 August 2026, and nothing anywhere said so. So the agent also ticks hourly
# and this script decides whether the day's run is owed: it keeps the date of
# the last real run and exits silently until that date is not today. The effect
# is at most one check a day, at 09:15 if the machine is up then and at the
# first opportunity after that if it wasn't.
#
# And it says when it slipped. Healing a gap quietly would leave the site
# claiming a daily check while the log showed otherwise to nobody. A run that
# finds days missing since the last one says so in the log and notifies.

REPO="/Users/varga/Developer/plainly-ai"
LOG="$HOME/Library/Logs/plainlyai-pricewatch.log"
RAN="$HOME/Library/Logs/plainlyai-pricewatch.lastrun"
OFF="$HOME/Library/Logs/plainlyai-pricewatch.lastoffline"
PYTHON="/usr/bin/python3"

cd "$REPO" || { echo "pricewatch: $REPO is gone" >> "$LOG"; exit 1; }

stamp() { date '+%Y-%m-%d %H:%M:%S %z'; }

today=$(date '+%Y-%m-%d')
prev=$(cat "$RAN" 2>/dev/null)

# Already checked today. Every hourly tick after the day's run lands here.
[ "$prev" = "$today" ] && exit 0

# Before the nominal time, leave it to the calendar trigger. The hourly tick is
# here to catch up on a day that was missed, not to move the check earlier.
# PRICEWATCH_FORCE=1 skips this guard, so the whole path can be exercised at any
# hour instead of by waiting until tomorrow morning to find out it is broken.
if [ -z "$PRICEWATCH_FORCE" ]; then
  h=$(date '+%H'); m=$(date '+%M')
  h=$(( ${h#0} + 0 )); m=$(( ${m#0} + 0 ))
  [ "$h" -lt 9 ] && exit 0
  [ "$h" -eq 9 ] && [ "$m" -lt 15 ] && exit 0
fi

# Reachability, not a fetch: one vendor host, short timeout, no page parsed.
# No network means the day's run is still owed, so the stamp is not written and
# the next tick tries again — but the log only says so once a day.
if ! /usr/bin/curl -sS -o /dev/null --max-time 10 https://platform.claude.com/ 2>/dev/null; then
  if [ "$(cat "$OFF" 2>/dev/null)" != "$today" ]; then
    printf '=== %s\noffline, skipped\n\n' "$(stamp)" >> "$LOG"
    printf '%s\n' "$today" > "$OFF"
  fi
  exit 0
fi

# Days skipped since the last real run. Absent on a first run, which is not a gap.
gap=""
if [ -n "$prev" ]; then
  prev_s=$(date -j -f '%Y-%m-%d' "$prev" '+%s' 2>/dev/null)
  today_s=$(date -j -f '%Y-%m-%d' "$today" '+%s' 2>/dev/null)
  if [ -n "$prev_s" ] && [ -n "$today_s" ]; then
    days=$(( (today_s - prev_s) / 86400 ))
    [ "$days" -ge 2 ] && gap="missed $((days - 1)) scheduled run(s): last ran $prev"
  fi
fi

out=$("$PYTHON" prices.py 2>&1)
status=$?

if [ -n "$gap" ]; then
  printf '=== %s\n%s\n%s\nexit %s\n\n' "$(stamp)" "$gap" "$out" "$status" >> "$LOG"
else
  printf '=== %s\n%s\nexit %s\n\n' "$(stamp)" "$out" "$status" >> "$LOG"
fi

printf '%s\n' "$today" > "$RAN"

if [ "$status" -ne 0 ]; then
  summary=$(printf '%s' "$out" | grep -E 'figures checked' | head -1)
  [ -n "$summary" ] || summary="prices.py exited $status"
  /usr/bin/osascript -e "display notification \"${summary}\" with title \"Plainly: Model facts needs a look\" sound name \"Submarine\"" >/dev/null 2>&1
elif [ -n "$gap" ]; then
  /usr/bin/osascript -e "display notification \"${gap}\" with title \"Plainly: the price watcher slipped\" sound name \"Submarine\"" >/dev/null 2>&1
fi

exit 0
