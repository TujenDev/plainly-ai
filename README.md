# Plainly

An independent, plain-English reference for learning AI — from *never used it* to
*building with the APIs*. No affiliate links, no advertising, nothing gated.

**Live at [plainlyai.org](https://plainlyai.org)**

## Why this exists

Almost everything that ranks for "learn AI" is an affiliate page pointing at a
course. The gap isn't more content, it's content you can trust. AI writing rots
faster than any other technical subject: a guide written eight months ago can be
confidently wrong about prices, limits, and which model to use, and it will go on
sounding authoritative while it does.

So this site is built around one promise that content farms structurally cannot
fake: **it is maintained, and it shows you when.**

## The two rules the site runs on

**1. Every page carries a "last verified" date.**
A date stamp doesn't make a page current. It makes a page's currency
*checkable*, which is the part that lets a reader decide how much to trust it.

**2. All hard numbers live on exactly one page.**
Context windows, prices, model IDs and cutoff dates live only in
`model-facts.html`. The explainers teach the concept and link out for the figure.
This means one page rots instead of nine, and it's what makes the site
maintainable by one person. A concept page that contains no numbers is still
correct in two years.

A corollary: **where a figure couldn't be verified against a primary source, it
is visibly flagged rather than filled in.** Some vendor rows on the model facts
table are deliberately blank. An empty cell is information; a plausible wrong
number is a liability — and "plausible-looking" is exactly what a language model
produces when it doesn't know.

## Structure

```
public/                 the deployable site — nothing outside this ships
  index.html            home, three level tracks
  start-here.html       placement, with verified resources per track
  model-facts.html      the single dated table of figures
  concepts/             the explainers
  guides.html           index of the guides; the guides themselves are the
                        remaining *.html at this level
  glossary.html         the defined terms
  sources.html          every primary source the site cites
  changes.html          the maintenance log, the source the feed is built from
  404.html              custom not-found page
  robots.txt            open to all crawlers, on purpose (see below)
  sitemap.xml           every page but 404, checked against the files by check.py
  _headers              security headers and cache policy
  feed.xml              Atom feed of the maintenance log, generated
  model-facts.json      the two model tables, machine-readable, generated
README.md               this file
check.py                the structural check, run after any page changes
feed.py                 regenerates public/feed.xml from the log
modelfacts.py           regenerates public/model-facts.json from the model tables
deploy.sh               the deploy: every guard, then upload, then verify, then push
prices.py               diffs Model facts against the seven vendor pages, daily
pricewatch.py           what the schedule runs: prices.py, logged, notify on trouble
pricewatch-task.ps1     registers the Windows scheduled task, run by hand (see below)
```

Static HTML and one stylesheet. No framework and no JavaScript: it loads fast,
it will still work in a decade, and there's nothing to keep updated but the
words.

There is no build step in the sense that matters — every page is committed as
the HTML that ships, and editing one is editing the file the reader gets. Two
files are generated, both derived from a page rather than maintained beside it:
`feed.xml`, which `feed.py` builds from the log on `changes.html`, and
`model-facts.json`, which `modelfacts.py` builds from the two tables on
`model-facts.html`. `check.py` fails if either has drifted from its source,
which is what makes the generation safe to rely on. **Edit the page, then run
the generator** — never the other way round.

The figures in the model tables carry `data-tokens` and `data-usd-per-mtok`
attributes so the JSON can be built without re-parsing "1.05M", and check 13
verifies each attribute against the text of its own cell. Those attributes state
the printed figure as a number and nothing more: `data-tokens="64000"` on a cell
reading 64k is not a claim that the vendor's limit is exactly 64,000. A cell
left blank under rule 3 carries `data-unverified` with the reason, and reaches
the JSON as `null` plus an entry in `unverified` — because `null` on its own
reads as "unknown", and these are not unknown.

URLs are extensionless (`/concepts/tokens`, not `/concepts/tokens.html`) because
that is how Cloudflare Pages serves the files — it redirects the `.html` form to
the clean one. Links, canonicals and the sitemap all use the clean form so no
internal link takes a redirect hop.

Run it locally the way it is actually served:

```bash
npx wrangler pages dev public
```

## Deploying

```bash
./deploy.sh              # guards, deploy, verify, push
./deploy.sh --dry-run    # guards only, stops before the deploy
```

This is a direct-upload Pages project: **a git push does not deploy.** Use the
script rather than calling `wrangler` yourself, because the guards are the point.
In order, and all of them before anything reaches the network:

1. **No log entry may still say "Committed, not yet published."** This is the
   one failure this project has actually had. `check.py` cannot catch it —
   before a deploy that sentence is true, and nothing in the file separates the
   honest case from the stale one. Only deploying can, so the guard lives here.
2. `feed.py` and `modelfacts.py` are re-run, so the derived files cannot be stale.
3. `check.py` must pass.
4. **The working tree must be clean.** What is served is then what is in the
   history — and if step 2 rewrote a derived file, this is what catches it.

After the upload it verifies against what is actually being served rather than
against the working tree: that the live log carries no unpublished claim, that
`/model-facts.json` and `/feed.xml` return 200, and that `model-facts.json`
rebuilt from the *live* page matches the *live* JSON byte for byte. Then it
pushes.

It refuses rather than fixing. Flipping "Committed, not yet published" to the
live wording is a change to the words of the log, and the rule that a script
never writes the site's sentences applies here as much as it does in `prices.py`.

## The daily price check

`prices.py` is only useful if it actually runs daily. It runs from Windows Task
Scheduler, registered by hand rather than by anything in the deploy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File pricewatch-task.ps1
Start-ScheduledTask -TaskName 'Plainly price watch'    # launch it once now
```

**The schedule belongs to a machine, not to the repo, and it has already been
lost that way once.** It used to be a launchd agent on a Mac. When work moved to
a Windows PC in September 2026, nothing replaced it, and the site went on
promising a daily check that nothing was running until 23 September. Moving to a
new machine means running `pricewatch-task.ps1` on it. The script replaces the
task rather than adding a second one, so running it again is safe.

It runs at 09:15, and it catches up. The task ticks hourly from 09:15, and
`pricewatch.py` decides whether the day's run is owed: it records the date of the
last real run and exits at once when that date is today. The effect is at most
one check a day, at 09:15 if the machine is on then and at the first tick
afterwards if it wasn't. The design dates from the Mac, whose scheduler dropped a
run missed while the machine was powered off. That is not a hypothetical: the
machine was shut down over 09:15 on 27 August 2026, and the day's check simply
never happened while the site went on promising a daily one. A run that finds days
missing since the last one says so in the log and notifies, because healing the
gap quietly would leave the log agreeing with a promise the site hadn't actually
kept. `PRICEWATCH_FORCE=1` skips the time-of-day guard, so the whole path can be
exercised now rather than tomorrow morning.

Runs append to `%LOCALAPPDATA%\plainlyai\pricewatch.log`. A run that is not clean
also raises a Windows notification, because a scheduled check whose output only
reaches a log file nobody opens is the quiet failure the script was written to
prevent. A run with no network is logged as skipped and does not notify: a
watcher that cries wolf gets dismissed, which costs more than the missed run. It
leaves the day's run owed, so the next tick tries again, and logs the skip only
once a day. It runs under `pythonw`, so the hourly tick never opens a window, and
for the same reason a crash in the wrapper itself is logged and notified rather
than lost.

It checks whatever is checked out: `prices.py` reads `public/model-facts.json`
from the working tree, so a run while a half-edited branch is checked out reports
on that branch.

To stop it:

```powershell
Unregister-ScheduledTask -TaskName 'Plainly price watch' -Confirm:$false
```

The macOS wrapper and its launchd agent were retired on 23 September 2026 and are
in the history. `pricewatch.py` still notifies on macOS, if the site ever moves
back to one.

## On crawlers

`robots.txt` welcomes everything — search crawlers, AI training crawlers, and AI
agents acting for a user, without distinction. That's deliberate. This is a free
reference with nothing to sell; being read, indexed and cited is the entire
point. If a model gives someone a better answer because it read these pages, the
site did its job. We'd rather be quoted accurately than not quoted.

One ask, unenforceable but stated plainly: **if you reproduce a fact from here,
carry the "last verified" date with it.** Facts about AI go stale fast. That's
why they're dated in the first place.

## Corrections

A stale or wrong fact here isn't a nitpick, it's a bug — the whole premise
depends on it. Open an issue. Corrections to figures are especially welcome, and
most especially if you can point at a primary source.

## Credit

Written with [Claude](https://claude.ai). The irony of an AI-assisted site whose
central subject is how much to trust AI output is not lost on anyone involved,
and is arguably the reason the verification discipline is so strict: every figure
on this site is checked against a primary source and dated, precisely because the
tool that helped write it is very good at producing confident text and
indifferent to whether it's true.
