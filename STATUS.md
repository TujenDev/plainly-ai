# Plainly — status

The short version, kept current at the end of every session. The public record is
`public/changes.html`; how the site is built and deployed is `README.md`. MyDash reads this
file, and ticking a box there edits it here. (It sits outside `public/`, so it never ships.)

Seeded 22 Sep 2026 from the repo and `changes.html` — correct anything that's off.

## State
Live at plainlyai.org, serving `0e9026a`, deployed and pushed through `deploy.sh` on 23 Sep
2026. That deploy carried the 15 Sep Astra / Gemini 3.8 Flash change and the 23 Sep monthly
check, run early: Opus 5.5 replaced Opus 5, and GPT-6 Sol and Luna replaced GPT-5.6 Sol and
Terra. The daily price watch runs from Windows Task Scheduler ("Plainly price watch", 09:15
with hourly catch-up, log at `%LOCALAPPDATA%\plainlyai\pricewatch.log`). The monthly Model
facts and home page checks run as the Claude scheduled task `plainly-monthly-check`, on the
11th at 10:00, while the app is open. Both are documented in README.md and MONTHLY-CHECK.md.
Next monthly checks are due 11 Oct 2026, and the quarterly ones 11 Nov.

## Next up
- [ ] 11 Oct: the scheduled monthly check prepares a `monthly-check-2026-10-11` branch. Review it, flip its "Committed, not yet published" lines, merge, and deploy through `deploy.sh`. Its first run may pause for tool approvals, which stick once given. Keep the app open that morning
- [ ] Watch Haiku 4.5 in that check: Anthropic gives its retirement as not sooner than 15 Oct 2026
- [ ] Quarterly concepts/guides and start-here checks, due 11 Nov 2026, not scheduled. Getting better results quotes a Claude Opus 5 caveat fetched 12 Aug, and Opus 5 is now legacy, so re-read Anthropic's prompting best practices then
- [ ] Anthropic's models overview answers with a 307 (temporary) redirect to `/docs/en/models/overview`. Every link still works; move them over if it turns permanent
- [ ] Tidy merged branches, local and on GitHub: `add-astra-gemini38-2026-09-15`, `fix-deploy-tmp-2026-09-15`, `fix-deploy-python-2026-09-15`, `home-check-2026-09-15`, `monthly-check-2026-09-15`, `monthly-check-2026-09-23`

## Live bugs
(none)

## Blocked on Shawn
- [ ] Post the X drafts once the daily task starts writing `PROMO.md`. That daily task isn't scheduled on this PC
