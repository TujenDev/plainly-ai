# The monthly Model facts check

This is the procedure for the re-verification that [plainlyai.org/changes](https://plainlyai.org/changes)
promises publicly, with a date attached. It runs on the 11th of each month, as a scheduled
task on Shawn's own machine. A human can follow it just as well.

It deliberately does **not** run in a cloud sandbox. That was tried on 14 August 2026 and
the sandbox's egress proxy blocked `developers.openai.com`, `ai.google.dev` and
`dev.meta.ai` outright, by WebFetch and by raw curl alike, while allowing Anthropic's
docs. A check that can only reach one vendor of four cannot honestly be logged as this
check having run.

The promise on `/changes` reads, in effect: if the due date passes and nothing appears in
the log, the site has broken its own promise and you should discount it accordingly. This
file exists so that does not happen by accident.

## The rule that matters

**Never guess, recall, or back-compute a figure.** Every number must come from opening the
vendor's own page on the day of the check and reading it there.

- If a page will not load, say so in the report and leave that row untouched. An
  unverified cell is fine. An invented plausible-looking one is the worst thing that can
  happen to this site.
- Ignore what you think you already know about model prices, including any cached table in
  a bundled tool or skill. That data is stale by definition, and on this exact task it has
  been wrong before: in August 2026 a bundled skill's model table still showed a
  superseded Sonnet price months after the vendor had changed it. The live vendor page wins.
- If a source shows something obviously broken, cross-check a second source or leave the
  field and flag it. Do not repair it by arithmetic.

## What to check

`public/model-facts.html` is the only page on the site carrying per-model figures. That is
deliberate: one page rots instead of a hundred. Check every row and every column in its
tables against these primary sources, which are also listed with their purpose in
`public/sources.html`:

| Source | Backs |
| --- | --- |
| https://platform.claude.com/docs/en/about-claude/models/overview | Context windows, max output, prices, **both** cutoff dates, and the word/character approximations |
| https://platform.claude.com/docs/en/about-claude/pricing | Batch and caching discounts, and whether any rate is introductory |
| https://developers.openai.com/api/docs/pricing | GPT prices, and the long-context tiers the table deliberately does not reproduce |
| https://developers.openai.com/api/docs/models | Context and output limits, knowledge cutoff |
| https://ai.google.dev/gemini-api/docs/pricing | Gemini prices and tiering |
| https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash | Context and output limits, and the absence of a published cutoff |
| https://dev.meta.ai/docs/pricing-rate-limits.md | Muse pricing, the contributor tier, and the absence of a first-party Llama price |

Also confirm the API ID column still matches, including the distinction between a pinned
model ID and an alias, which the vendor documents separately.

## Traps this check has already fallen into

- **Meta does not fit the table, and that is the finding.** Llama is downloaded and run
  wherever you choose, so there is no first-party per-token price. Cells read "not
  published" on purpose. Never fill them from a reseller or an aggregator.
- **A caveat rots faster than a figure.** The site once carried a correct price with a
  warning that it was introductory and would rise on a stated date. The price stayed and
  the increase was cancelled, so the number was right and the caveat was wrong. Nothing
  about a caveat looks due for re-checking, so check the words around each figure, not
  only the figure.
- **Cross-vendor per-token comparison is weaker than it looks**, because tokenisers differ
  and the same text is a different token count per vendor. The page says so. Do not add a
  comparison, a "best value" note, or a normalised column.
- **A new model on a vendor page is not automatically a new row.** Propose it in the
  report; do not silently restructure the table.

## What to do with what you find

Whether or not anything changed:

1. Move `Last verified` on `public/model-facts.html` to today. This is one of the rare
   cases where it moves, because the sources really were re-read.
2. Update the `Last read` date on every row you actually opened in `public/sources.html`.
   Only those rows. The dates are per-document for a reason.
3. Add an entry at the top of the log in `public/changes.html`, dated today. A re-check
   that found nothing still gets an entry: a confirmation is a result, and the log is how
   the promise is kept visibly.
4. Update the "Checks that are due" block on `public/changes.html` so the Model facts line
   names the 11th of next month.

If a figure changed, correct it on `public/model-facts.html` and say so in the log entry
plainly, including what was wrong and for how long. The log records mistakes on purpose.

**Never move a `Last verified` date for a cosmetic edit** anywhere on the site. Rewording,
retitling and re-linking change nothing about whether the facts hold. That rule is the
site's whole credibility and the log explains it to readers at `/changes#dates`.

## What not to do

- **Do not deploy, even though the credentials on this machine would let you.** This check
  runs unattended on a schedule, where `npx wrangler pages deploy public --project-name
  plainlyai --branch main` would work with nobody watching. Prepare everything, commit it,
  and stop there.

  This rule is prose, and prose is the weakest kind of rule — which this project of all
  projects should admit. There is no technical lock behind it: a deny rule on the deploy
  command would work, but it would also block the deploys Shawn does want, and nothing in
  the settings can tell a scheduled run from a session with him sitting there. So the rule
  is backed by an audit trail instead, which is the same move this site makes everywhere
  else: if you cannot prevent a thing, make it visible after the fact.

  **Two things make it visible.** First, the log entry you write on `changes.html` must
  say, in the entry itself, whether the change is live or only prepared. Since 29 August
  that half is enforced rather than promised: `deploy.sh` refuses to deploy while any
  entry still reads "Committed, not yet published", so a prepared-but-not-live entry
  cannot be published as though it were live. The rule against deploying unattended is
  still prose and still yours to keep — the guard only stops the specific lie. Second,
  `npx wrangler pages deployment list --project-name plainlyai` prints every deployment
  with a timestamp and the commit it came from. Anyone, including Shawn a month later, can
  line that list up against the dates in the log and see whether a check deployed itself.
  A run that deploys and does not say so is caught by the second; a run that claims a
  correction is live when it is not is caught by the first.

- **Note the promise is only kept once it is live.** A verified change sitting in an
  unpushed commit does not keep it, and neither does one pushed to GitHub — this is a
  direct-upload Pages project, so a push does not deploy. If Shawn is not around, say so
  in the report and say it in the log entry too, rather than deploying to close the loop.
  "Corrected, not yet published" is an honest public state. Silently leaving readers on a
  wrong figure while the fix sits on disk is not.
- **Do not add affiliate links, ads, a newsletter, or a comparison table.** These used to
  point at the site's planning notes for the reasons, and those notes are gitignored and
  not in this checkout — so the record of what the site has refused on purpose was
  somewhere nobody reading this could reach it, which is no record at all. The reasons
  are here now, where the rule is:

  - **Affiliate links and ads.** The home page states in its own words that nothing here
    is an affiliate link, and the whole positioning is that this site is the one page on
    the subject with nothing to sell. Adding either does not merely change the business
    model, it makes a published sentence false.
  - **A newsletter.** The site's answer to "how do I keep up" already exists and is
    better: `/feed.xml`, which carries every log entry, costs the reader no email address,
    and cannot be used to sell anything later. A subscribe box turns a reference into a
    funnel, which is the thing the front page complains about.
  - **A comparison table, a "best value" note, or a normalised column.** Refused above
    under the Model facts rules, for a factual reason rather than a stylistic one:
    tokenisers differ between vendors, so the same text is a different number of tokens
    depending on who is counting, and a per-token comparison across vendors is therefore
    weaker than it looks. The page says so itself.
- Do not add hard figures to any page other than Model facts.

Em dashes are allowed on this project, unlike Shawn's other work. Match the surrounding
prose, which is plain, specific, and unhurried.

## The daily watcher, and what it does not do

`prices.py` fetches all seven sources below and diffs them against what
`public/model-facts.html` claims. Run it daily:

```
python prices.py
```

It exists because of what this check found on 26 August 2026: GPT-5.6 Sol had
moved from $5/$30 to $4/$20 while the table said otherwise, and the table had been
correct on 14 August. Checking monthly means being wrong for up to a month. The
watcher makes that a day. It prints and never edits, and it reports UNVERIFIED and
exits non-zero rather than reporting "unchanged" when it could not read a figure.

**It does not replace this check, and the difference matters.** The watcher can
only compare figures the table already carries. It cannot notice a model that
should be added, a pricing tier that did not exist last month, a cell that ought
to stop saying "not published", or a caveat whose wording is still present but no
longer means what it did. Those need somebody reading the page. A green run from
`prices.py` means nothing has moved under the table, not that the table is right.

## Before you finish, regenerate the derived files and run the structural check

```
python feed.py && python modelfacts.py && python check.py
```

(`deploy.sh` runs all three itself, so if you are deploying you get this for free.
Run them here anyway — you want to see a clean check before you decide anything.)

From the project root. `feed.py` rewrites `public/feed.xml` from the log you just
added to, and `modelfacts.py` rewrites `public/model-facts.json` from the two
tables on Model facts. Both are derived and never edited by hand — if you changed
a figure this month, the JSON is stale until you run it, and `prices.py` reads
the JSON, so a forgotten run means tomorrow's price watch compares against last
month's numbers. Check 13 fails on exactly that. `check.py` takes a second,
exits non-zero on failure, and covers the things that break silently: links that
stopped resolving, heading permalinks that broke, duplicated ids, pages that
became reachable only from the nav, nav drift across the pages, and a feed that
no longer matches the log. It checks structure, never truth, so it is no
substitute for anything above.

The feed matters for the same reason the log does. Someone subscribed to it is
relying on a correction reaching them, so a month where the log moves and the
feed does not is a promise quietly broken for the readers who took the site up
on it. That is why the check fails on it rather than warning.

Section permalinks matter here: **do not change an existing heading id.** They are
generated once and then frozen, and `/changes` states publicly that a section's
link will not change. Reword a heading if it helps; leave its id alone.

## Deliverable

Leave the changes committed on a branch and open a pull request if the environment permits
it. If it does not, leave them in the working tree and print the full diff.

Then report, in this order:

1. Every figure checked, with a verdict: unchanged, changed (from → to), or not verified
   and why.
2. Anything on a vendor page that the table does not yet cover.
3. What you edited, and the exact text of the changes.html entry you wrote.
4. Anything you were unsure about. Say it rather than resolving it quietly.
