#!/bin/sh
# The deploy, with the ritual built in instead of remembered.
#
#     ./deploy.sh              run every guard, deploy, verify, push
#     ./deploy.sh --dry-run    run every guard and stop before deploying
#
# Why this exists. On 29 August 2026 a deploy went out with a log entry still
# reading "Committed, not yet published" — the site publishing a false statement
# about itself, on the one page whose whole job is being the honest record.
#
# check.py cannot catch that. Before a deploy the sentence is *true*, and there
# is no way to tell the honest case from the stale one by reading the file. The
# only thing that can tell them apart is the act of deploying, which is why the
# guard has to live here and not in the structural check.
#
# The order below is the order, and it is not arbitrary: every guard runs and
# must pass BEFORE anything reaches the network, because a deploy cannot be
# taken back — a wrong page is served the moment it uploads, and pulling it
# means another deploy. Everything after the upload is verification of what was
# actually served, not of what was in the working tree.
#
# What this will not do: edit a page. Flipping "Committed, not yet published" to
# "All of it is live." is a change to the words of the log, and prices.py's
# first rule holds here too — a script does not write the site's sentences. So
# this refuses and tells you, rather than fixing it for you and publishing
# something you never read.

set -eu

cd "$(dirname "$0")"

DRY_RUN=no
[ "${1:-}" = "--dry-run" ] && DRY_RUN=yes

PYTHON=python3
SITE="https://plainlyai.org"
LOG_SRC="public/changes.html"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\nREFUSING TO DEPLOY: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- guard 1
# The failure this file exists for.
say "1. No entry may still claim to be unpublished"
if [ ! -f "$LOG_SRC" ]; then
  fail "$LOG_SRC is missing — this guard cannot see the log it is guarding."
fi
stale=$(grep -c "not yet published" "$LOG_SRC" || true)
if [ "$stale" -ne 0 ]; then
  grep -n "not yet published" "$LOG_SRC" >&2 || true
  if [ "$stale" -eq 1 ]; then which="one log entry above still says"
  else which="$stale log entries above still say"; fi
  fail "$which
  'Committed, not yet published'. Deploying now would publish that claim while
  making it false. Flip the wording first — replace EVERY occurrence, not the
  first one; that is the exact mistake this guard was written after."
fi
echo "   clean: no entry claims to be unpublished"

# ---------------------------------------------------------------- guard 2
# Derived files current, and everything check.py covers. Run the generators
# first: if either rewrites its output, the tree was stale and guard 3 says so.
say "2. Regenerate the derived files"
$PYTHON feed.py
$PYTHON modelfacts.py

say "3. Structural check"
$PYTHON check.py

# ---------------------------------------------------------------- guard 3
# What gets uploaded must be what is committed. Without this, a deploy can
# serve a working-tree edit that exists on no branch and in no history, and the
# only record of what the site said would be the site itself.
say "4. Working tree must be clean"
if [ -n "$(git status --porcelain)" ]; then
  git status --short >&2
  fail "the working tree has uncommitted changes (listed above). Commit them
  first, so what is served is what is in the history. If the generators above
  are what changed, that means they had not been re-run since the last edit."
fi
echo "   clean: HEAD is $(git rev-parse --short HEAD)"

if [ "$DRY_RUN" = yes ]; then
  say "--dry-run: every guard passed, stopping before the deploy"
  exit 0
fi

# ---------------------------------------------------------------- deploy
say "5. Deploy"
npx wrangler pages deploy public --project-name plainlyai --branch main

# ---------------------------------------------------------------- verify
# Against what is actually being served, not against the files on disk. The
# whole failure was a mismatch between the two.
say "6. Verify what was served"
i=0
while [ "$i" -lt 10 ]; do
  live=$(curl -fsS "$SITE/changes" 2>/dev/null || true)
  [ -n "$live" ] && break
  i=$((i + 1))
  sleep 3
done
[ -n "$live" ] && echo "   fetched $SITE/changes" \
  || fail "could not fetch $SITE/changes after the deploy. The upload may have
  succeeded — check the site by hand before deploying again."

live_stale=$(printf '%s' "$live" | grep -c "not yet published" || true)
[ "$live_stale" -eq 0 ] \
  && echo "   live: no entry claims to be unpublished" \
  || fail "the LIVE page still claims to be unpublished in $live_stale place(s).
  This is the failure itself, now in production.
  Fix the wording and deploy again immediately."

for path in "/model-facts.json" "/feed.xml"; do
  code=$(curl -o /dev/null -s -w '%{http_code}' "$SITE$path")
  [ "$code" = 200 ] && echo "   live: $path $code" || fail "$SITE$path returned $code"
done

# The derived data file must agree with the page it was derived from, on the
# server. check.py proves that about the working tree; this proves it about
# what a reader and a scraper actually get.
say "7. Live JSON still matches the live table"
curl -fsS "$SITE/model-facts" -o /tmp/plainly-live-mf.html
curl -fsS "$SITE/model-facts.json" -o /tmp/plainly-live-mf.json
$PYTHON - <<'PY'
import modelfacts, sys
built = modelfacts.dump(modelfacts.build(open("/tmp/plainly-live-mf.html").read()))
live = open("/tmp/plainly-live-mf.json").read()
if built != live:
    sys.exit("   the live model-facts.json does NOT match the live table")
print("   live: model-facts.json rebuilt from the live page matches byte for byte")
PY

# ---------------------------------------------------------------- push
say "8. Push"
git push origin main
say "Deployed and pushed. $SITE is serving $(git rev-parse --short HEAD)."
