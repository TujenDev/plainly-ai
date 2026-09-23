# Plainly — status

The short version, kept current at the end of every session. The public record is
`public/changes.html`; how the site is built and deployed is `README.md`. MyDash reads this
file, and ticking a box there edits it here. (It sits outside `public/`, so it never ships.)

Seeded 22 Sep 2026 from the repo and `changes.html` — correct anything that's off.

## State
Live at plainlyai.org. Last monthly model-facts check 15 Sep 2026 (four days late); the next
model-facts and home-page checks are both due 11 Oct 2026, the quarterly ones 11 Nov. The GPT-6
Astra / Gemini 3.8 Flash update is committed on `add-astra-gemini38-2026-09-15` but not merged
or deployed — its log entry still says "Committed, not yet published".

## Next up
- [ ] Merge `add-astra-gemini38-2026-09-15` and deploy it with `deploy.sh`, so the live model-facts page catches up
- [ ] Merge or close `fix-deploy-tmp-2026-09-15` (the post-deploy check fix)
- [ ] Monthly model-facts check and home-page check — due 11 Oct 2026
- [ ] Quarterly concepts/guides and start-here resource checks — due 11 Nov 2026

## Live bugs
(none)

## Blocked on Shawn
- [ ] Say go on merging and deploying the Astra / Gemini 3.8 Flash branch — deploys go through `deploy.sh` only
- [ ] Commit the `.gitignore` secrets block (uncommitted since 16 Sep) — `deploy.sh` refuses to deploy a dirty tree
- [ ] Check the daily price watcher still runs somewhere — it was a macOS launchd agent, nothing schedules it on this Windows PC, and the site says it runs daily
- [ ] Post the X drafts once the daily task starts writing `PROMO.md`
