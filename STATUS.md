# Plainly — status

The short version, kept current at the end of every session. The public record is
`public/changes.html`; how the site is built and deployed is `README.md`. MyDash reads this
file, and ticking a box there edits it here. (It sits outside `public/`, so it never ships.)

Seeded 22 Sep 2026 from the repo and `changes.html` — correct anything that's off.

## State
Live at plainlyai.org, serving main as of the 15 Sep deploy (`c4d0ae0`; checked against the
live pages on 23 Sep). The monthly model-facts check ran early on 23 Sep 2026 and is committed
on `monthly-check-2026-09-23`, not merged or deployed. That branch also carries the 15 Sep
Astra / Gemini 3.8 Flash change and everything on main. Both of those log entries still say
"Committed, not yet published". main is 4 commits ahead of origin (the `.gitignore` block,
this file, and the deploy fix); `deploy.sh` pushes them. The next model-facts and home-page
checks are both due 11 Oct 2026, and the quarterly ones 11 Nov.

## Next up
- [ ] Deploy `monthly-check-2026-09-23`: flip both "Committed, not yet published" lines to the live wording, merge into main, run `deploy.sh --dry-run`, then `deploy.sh`
- [ ] Monthly model-facts and home-page checks, due 11 Oct 2026. Anthropic gives Haiku 4.5's retirement as not sooner than 15 Oct 2026, so look at that row closely
- [ ] Quarterly concepts/guides and start-here checks, due 11 Nov 2026. Getting better results quotes a Claude Opus 5 caveat fetched 12 Aug, and Opus 5 is now a legacy model, so re-read Anthropic's prompting best practices then
- [ ] Anthropic's models overview now answers with a 307 (temporary) redirect to `/docs/en/models/overview`. Every link still works; move them over if it turns permanent

## Live bugs
- Live Model facts lists Claude Opus 5, GPT-5.6 Sol and GPT-5.6 Terra as current models. Their vendors moved on after 15 Sep. Fixed on `monthly-check-2026-09-23`, not deployed
- Live Model facts' context-figures note says Google's 1,048,576 and OpenAI's 1.05M are the same number. OpenAI's pages give 1,050,000. Fixed on the same branch, not deployed
- The daily price check lapsed for part of September when the Mac went, and `/changes` doesn't say so yet. It has been scheduled on this PC since 23 Sep (Task Scheduler, "Plainly price watch", via `pricewatch.py`), and the lapse is written up in the 23 Sep log entry on the branch, not deployed

## Blocked on Shawn
- [ ] Say go on deploying `monthly-check-2026-09-23`, which includes the Astra / Gemini 3.8 Flash change. Deploys go through `deploy.sh` only
- [ ] Nothing schedules the monthly check on this PC either. MONTHLY-CHECK.md says it runs "as a scheduled task on Shawn's own machine", and this PC has no Claude scheduled tasks at all. Say whether to set one up for the 11th
- [ ] Post the X drafts once the daily task starts writing `PROMO.md`. That daily task isn't scheduled on this PC either
