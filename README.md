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
  404.html              custom not-found page
  robots.txt            open to all crawlers, on purpose (see below)
  sitemap.xml           all nine pages
  _headers              security headers and cache policy
  feed.xml              Atom feed of the maintenance log, generated
README.md               this file
check.py                the structural check, run after any page changes
feed.py                 regenerates public/feed.xml from the log
```

Static HTML and one stylesheet. No framework and no JavaScript: it loads fast,
it will still work in a decade, and there's nothing to keep updated but the
words.

There is no build step in the sense that matters — every page is committed as
the HTML that ships, and editing one is editing the file the reader gets. The
one generated file is `feed.xml`, which `feed.py` derives from the log on
`changes.html` so the two cannot drift apart. `check.py` fails if it has, which
is what makes the generation safe to rely on.

URLs are extensionless (`/concepts/tokens`, not `/concepts/tokens.html`) because
that is how Cloudflare Pages serves the files — it redirects the `.html` form to
the clean one. Links, canonicals and the sitemap all use the clean form so no
internal link takes a redirect hop.

Run it locally the way it is actually served:

```bash
npx wrangler pages dev public
```

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
