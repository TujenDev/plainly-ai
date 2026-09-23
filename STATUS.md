# Plainly — status

The short version, kept current at the end of every session. The public record is
`public/changes.html`; how the site is built and deployed is `README.md`. MyDash reads this
file, and ticking a box there edits it here. (It sits outside `public/`, so it never ships.)

Seeded 22 Sep 2026 from the repo and `changes.html` — correct anything that's off.

## State
Live at plainlyai.org, deployed and pushed through `deploy.sh` on 23 Sep 2026, so main, GitHub
and the live site all match. Three deploys that day: the 15 Sep Astra / Gemini 3.8 Flash change
with the 23 Sep monthly check, run early (Opus 5.5 replaced Opus 5, and GPT-6 Sol and Luna
replaced GPT-5.6 Sol and Terra); Getting better results, re-read early because Opus 5 went
legacy (every quote still word for word, last verified now 23 Sep); and a fix to the date line
on Sources, which counted rows re-read on 1 Sep when no row said 1 Sep any more. Nothing is
waiting on Shawn; the only thing ahead is the scheduled monthly check. The daily price watch runs from Windows Task Scheduler ("Plainly price watch", 09:15
with hourly catch-up, log at `%LOCALAPPDATA%\plainlyai\pricewatch.log`). The monthly Model
facts and home page checks run as the Claude scheduled task `plainly-monthly-check`, on the
11th at 10:00, while the app is open. The quarterly concepts/guides and Start here checks
run as `plainly-quarterly-check` at 14:00 on 11 Feb/May/Aug/Nov, on top of that day's
monthly branch. X post drafts are written to `PROMO.md` (gitignored) daily at 08:10 by
`plainly-daily-x-drafts`, for MyDash's promo panel. Posting them is Shawn's, and nothing posts
them for him; MyDash nudges after 7 days without a post, so it isn't a Blocked item. The procedures are in README.md,
MONTHLY-CHECK.md and QUARTERLY-CHECK.md. Next monthly checks are due 11 Oct 2026, and the
quarterly ones 11 Nov.

## Next up
- [ ] 11 Oct: the scheduled monthly check prepares a `monthly-check-2026-10-11` branch. Review it, flip its "Committed, not yet published" lines, merge, and deploy through `deploy.sh`. Its first run may pause for tool approvals, which stick once given. Keep the app open that morning
- [ ] Watch Haiku 4.5 in that check: Anthropic gives its retirement as not sooner than 15 Oct 2026
- [ ] 11 Nov: the first scheduled quarterly check. It stops if that day's monthly check hasn't finished, so check it ran. Getting better results was already re-read on 23 Sep because Opus 5 went legacy, and its Opus 5 caveat still held word for word; it gets re-read with the rest regardless
- [ ] Anthropic's models overview answers with a 307 (temporary) redirect to `/docs/en/models/overview`. Every link still works; move them over if it turns permanent

## Live bugs
(none)

## Blocked on Shawn
(none)
