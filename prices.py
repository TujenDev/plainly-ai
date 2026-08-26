"""The price watcher: does Model facts still match the vendors' own pages?

    python prices.py

`check.py` checks structure and `feed.py` derives the feed. This one checks the
only thing on the site that can be wrong about money. It fetches the seven
primary sources listed in MONTHLY-CHECK.md, pulls out the figures that
`public/model-facts.html` claims, and reports every difference.

Why it exists: on 26 August 2026 the monthly check found GPT-5.6 Sol listed at
$5/$30 when OpenAI had moved it to $4/$20. That table was checked and correct on
14 August, so it had been wrong for up to twelve days, because the check runs
monthly. A page that can be wrong about a price for a month is not doing the one
job it exists for. Run this daily and the window is a day.

Three rules it is built around, all of them from mistakes this site has already
made and logged:

1. **It never edits anything.** It prints. Deciding what to do about a change is
   a human job: a new model on a vendor page is a selection decision, not a row,
   and MONTHLY-CHECK.md is explicit that figures are never filled in
   automatically.

2. **It fails loud, never quiet.** If a figure cannot be located — the vendor
   restructured the page, the URL moved, the fetch failed — it reports
   UNVERIFIED and exits non-zero. It must never report "unchanged" because it
   could not look. A watcher that goes quietly blind is worse than no watcher,
   and is exactly the false freshness signal this site warns readers about.

3. **It watches the words as well as the numbers.** The 11 August correction was
   a caveat going stale while its figure stayed right: a price marked
   introductory that had quietly become permanent. So the notes that qualify the
   figures are watched too.

Exit codes: 0 all clear, 1 something changed or could not be verified.
"""
import re
import sys
import html
import urllib.request
from urllib.error import URLError, HTTPError
import pathlib

ROOT = pathlib.Path(__file__).parent / "public"
UA = "Mozilla/5.0 (compatible; plainlyai-price-watch/1.0; +https://plainlyai.org)"
TIMEOUT = 30

SRC = {
    "anthropic_models": "https://platform.claude.com/docs/en/about-claude/models/overview.md",
    "anthropic_pricing": "https://platform.claude.com/docs/en/about-claude/pricing.md",
    "openai_pricing": "https://developers.openai.com/api/docs/pricing",
    "openai_models": "https://developers.openai.com/api/docs/models",
    "google_pricing": "https://ai.google.dev/gemini-api/docs/pricing",
    "google_flash": "https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash",
    "meta_pricing": "https://dev.meta.ai/docs/pricing-rate-limits.md",
}

findings = []          # (verdict, subject, detail)
OK, CHANGED, UNVERIFIED = "unchanged", "CHANGED", "UNVERIFIED"


def note(verdict, subject, detail=""):
    findings.append((verdict, subject, detail))


def fetch(key):
    """Return the page as plain text, or None. None always means unverified."""
    req = urllib.request.Request(SRC[key], headers={"User-Agent": UA})
    try:
        raw = urllib.request.urlopen(req, timeout=TIMEOUT).read().decode("utf-8", "replace")
    except (URLError, HTTPError, TimeoutError, OSError) as e:
        note(UNVERIFIED, key, f"fetch failed: {e}")
        return None
    if SRC[key].endswith(".md"):
        return raw
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


# ---------------------------------------------------------------- the claims

def tokens(s):
    """'1.05M', '200k', '1,048,576', '128K tokens' -> int, or None."""
    s = s.replace(",", "").strip()
    m = re.match(r"([\d.]+)\s*([MmKk])?", s)
    if not m:
        return None
    n = float(m.group(1))
    suffix = (m.group(2) or "").lower()
    return int(n * {"m": 1_000_000, "k": 1_000, "": 1}[suffix])


def claims():
    """Read what model-facts.html asserts. Derived, never duplicated."""
    s = (ROOT / "model-facts.html").read_text(encoding="utf-8")
    rows = {}
    for tr in re.findall(r"<tr>(.*?)(?=<tr>|</tbody>)", s, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) == 8 and cells[0].startswith("Claude"):
            rows[cells[0]] = dict(zip(
                ("model", "api_id", "context", "max_output", "input", "output",
                 "reliable_cutoff", "training_cutoff"), cells))
        elif len(cells) == 7:
            rows[cells[1]] = dict(zip(
                ("vendor", "model", "api_id", "context", "max_output", "input",
                 "output"), cells))
    return rows


# ---------------------------------------------------------------- comparing

def cmp_money(subject, claimed, live):
    if live is None:
        return note(UNVERIFIED, subject, "figure not found on the vendor page")
    c = claimed.replace("$", "").strip()
    l = str(live).replace("$", "").strip()
    if abs(float(c) - float(l)) < 0.0001:
        note(OK, subject, f"${c}")
    else:
        note(CHANGED, subject, f"${c} -> ${l}")


def cmp_tokens(subject, claimed, live):
    """5% tolerance, because k and M are written two ways here.

    The site rounds: it prints 64k where Google publishes 65,536, and 1.05M
    where Google publishes 1,048,576. Those are the same limits in binary and
    decimal, and the widest such gap is 1024 against 1000 compounded twice,
    just under 5%. Context and output limits move by doubling, halving or an
    order of magnitude, never by a few percent, so this absorbs the notation
    and nothing else. Prices are compared exactly; only limits get this.
    """
    if live is None:
        return note(UNVERIFIED, subject, "limit not found on the vendor page")
    c, l = tokens(claimed), tokens(str(live))
    if c is None or l is None:
        return note(UNVERIFIED, subject, f"could not parse {claimed!r} / {live!r}")
    if abs(c - l) <= max(c, l) * 0.05:
        note(OK, subject, claimed)
    else:
        note(CHANGED, subject, f"{claimed} ({c:,}) -> {l:,}")


def cmp_text(subject, claimed, live):
    if live is None:
        return note(UNVERIFIED, subject, "value not found on the vendor page")
    if claimed.lower().replace(" ", "") == str(live).lower().replace(" ", ""):
        note(OK, subject, claimed)
    else:
        note(CHANGED, subject, f"{claimed} -> {live}")


def phrase(subject, text, needle, why):
    """Watch a caveat, not a figure. A caveat rots faster than a number."""
    if text is None:
        return note(UNVERIFIED, subject, "page not fetched")
    if needle.lower() in text.lower():
        note(OK, subject, why)
    else:
        note(CHANGED, subject, f"the wording behind {why!r} is gone: {needle!r}")


# ---------------------------------------------------------------- the probes

def anthropic(C):
    """Anthropic publishes one markdown table, one column per model."""
    txt = fetch("anthropic_models")
    if txt is not None:
        cols = {}
        for line in txt.splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            label = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cells[0]).strip()
            cols[label.lower()] = cells[1:]
        header = cols.get("feature", [])
        idx = {re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h).strip(): i
               for i, h in enumerate(header)}

        def cell(row, model):
            r, i = cols.get(row.lower()), idx.get(model)
            return r[i] if r and i is not None and i < len(r) else None

        for model, claim in C.items():
            if not model.startswith("Claude"):
                continue
            if model not in idx:
                note(UNVERIFIED, f"{model}", "model no longer on the vendor's table")
                continue
            cmp_tokens(f"{model} context", claim["context"], cell("Context window", model))
            cmp_tokens(f"{model} max output", claim["max_output"], cell("Max output", model))
            cmp_text(f"{model} reliable cutoff", claim["reliable_cutoff"],
                     cell("Reliable knowledge cutoff", model))
            cmp_text(f"{model} training cutoff", claim["training_cutoff"],
                     cell("Training data cutoff", model))
            cmp_text(f"{model} API ID", claim["api_id"], (cell("Claude API ID", model) or "").strip("`"))
            price = cell("Pricing", model) or ""
            m = re.search(r"\$([\d.]+)\s*/\s*input MTok,\s*\$([\d.]+)\s*/\s*output MTok", price, re.I)
            if m:
                cmp_money(f"{model} input", claim["input"], m.group(1))
                cmp_money(f"{model} output", claim["output"], m.group(2))
            else:
                note(UNVERIFIED, f"{model} price", "pricing cell did not parse")

    pricing = fetch("anthropic_pricing")
    phrase("Sonnet 5 introductory-rate note", pricing,
           "is now the standard price", "the $2/$10 rate being permanent")


def openai(C):
    """OpenAI shows Standard/Batch/Flex/Fast tabs; Standard is the first table."""
    txt = fetch("openai_models")
    if txt is not None:
        for model, claim in C.items():
            if claim.get("vendor") != "OpenAI":
                continue
            api = claim["api_id"]
            m = re.search(re.escape(api) + r"\b(.{0,320}?)Tools", txt, re.S)
            if not m:
                note(UNVERIFIED, f"{model}", f"{api} not found in the model catalogue")
                continue
            blk = m.group(1)

            def grab(pat):
                g = re.search(pat, blk, re.I)
                return g.group(1) if g else None

            cmp_money(f"{model} input", claim["input"], grab(r"Input price \$?([\d.]+)"))
            cmp_money(f"{model} output", claim["output"], grab(r"Output price \$?([\d.]+)"))
            cmp_tokens(f"{model} context", claim["context"], grab(r"Context window ([\d.,MK]+)"))
            cmp_tokens(f"{model} max output", claim["max_output"], grab(r"Max output ([\d.,MK]+)"))

    # cross-check the prices against the separate pricing page: one page can be
    # mid-update, and a figure confirmed twice is the one worth printing.
    txt = fetch("openai_pricing")
    if txt is not None:
        for model, claim in C.items():
            if claim.get("vendor") != "OpenAI":
                continue
            m = re.search(re.escape(claim["api_id"]) +
                          r"\s*\$([\d.]+)\s*\$[\d.]+\s*\$[\d.]+\s*\$([\d.]+)", txt)
            if not m:
                note(UNVERIFIED, f"{model} price (pricing page)",
                     "standard short-context row did not parse")
                continue
            cmp_money(f"{model} input (2nd source)", claim["input"], m.group(1))
            cmp_money(f"{model} output (2nd source)", claim["output"], m.group(2))


def google(C):
    claim = next((c for c in C.values() if c.get("vendor") == "Google"), None)
    if claim is None:
        return note(UNVERIFIED, "Google row", "no Google row on Model facts")
    txt = fetch("google_pricing")
    if txt is not None:
        i = txt.find("Gemini 3.6 Flash")
        blk = txt[i:i + 1200] if i >= 0 else ""
        inp = re.search(r"Input price.*?\$([\d.]+) through", blk, re.S)
        out = re.search(r"Output price.*?\$([\d.]+) through", blk, re.S)
        cmp_money("Gemini 3.6 Flash input", claim["input"], inp.group(1) if inp else None)
        cmp_money("Gemini 3.6 Flash output", claim["output"], out.group(1) if out else None)
        # the page states an expiry, and the site prints that date: watch both
        phrase("Gemini rate expiry", blk, "through December 31, 2026",
               "the current rate ending 31 Dec 2026")
        phrase("Gemini successor rate", blk, "starting January 1, 2027",
               "the increase on 1 Jan 2027")
    txt = fetch("google_flash")
    if txt is not None:
        cmp_tokens("Gemini 3.6 Flash context", claim["context"],
                   (re.search(r"Input token limit ([\d,]+)", txt) or [None, None])[1])
        cmp_tokens("Gemini 3.6 Flash max output", claim["max_output"],
                   (re.search(r"Output token limit ([\d,]+)", txt) or [None, None])[1])
        if re.search(r"knowledge cutoff", txt, re.I):
            note(CHANGED, "Gemini cutoff",
                 "a knowledge cutoff is now published; the table says none is")
        else:
            note(OK, "Gemini cutoff", "still unpublished, as the table says")


def meta(C):
    claim = next((c for c in C.values()
                  if c.get("vendor") == "Meta" and "$" in c.get("input", "")), None)
    txt = fetch("meta_pricing")
    if txt is None or claim is None:
        return note(UNVERIFIED, "Meta row", "page not fetched or no priced Meta row")
    std = txt.split("### Contributor tier")[0]
    cmp_money("Muse Spark input", claim["input"],
              (re.search(r"\|\s*Input\s*\|\s*\$([\d.]+)", std) or [None, None])[1])
    cmp_money("Muse Spark output", claim["output"],
              (re.search(r"\|\s*Output\s*\|\s*\$([\d.]+)", std) or [None, None])[1])
    phrase("Meta contributor tier", txt, "Contributor tier", "the cheaper tier the notes mention")
    if re.search(r"llama[^\n]{0,80}\$[\d.]", txt, re.I):
        note(CHANGED, "Llama first-party price",
             "Meta now appears to publish one; the table says it does not")
    else:
        note(OK, "Llama first-party price", "still not published, as the table says")


def main():
    C = claims()
    if not C:
        print("prices.py: could not read any rows from model-facts.html")
        return 1
    for probe in (anthropic, openai, google, meta):
        probe(C)

    width = max(len(s) for _, s, _ in findings)
    changed = [f for f in findings if f[0] == CHANGED]
    unver = [f for f in findings if f[0] == UNVERIFIED]
    for verdict, subject, detail in findings:
        if verdict != OK:
            print(f"  {verdict:<10} {subject:<{width}}  {detail}")
    print(f"\n{len(findings)} figures checked, {len(findings) - len(changed) - len(unver)} "
          f"unchanged, {len(changed)} changed, {len(unver)} unverified")
    if changed or unver:
        print("\nNothing has been edited. Read MONTHLY-CHECK.md, open the vendor page\n"
              "yourself, and decide. Never fill a figure in from this output alone.")
        return 1
    print("Model facts matches every vendor page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
