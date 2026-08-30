"""The structural check, run after any page is added or substantially changed.

The site promises this publicly on /changes: "Whenever a page is added or
substantially changed, no date attached. A new page can make an old page wrong
without touching a single fact." That commitment was being kept by remembering
to grep, which is the same as not keeping it. This makes it one command.

    python check.py

It checks structure, not truth. It cannot tell you a price is stale; that is the
monthly check in MONTHLY-CHECK.md. What it catches is the rot this site keeps
generating for itself: a link that stopped resolving, a page that became
unreachable, an id that got duplicated, a heading permalink that broke.

It also checks that every page still carries what every page here is supposed to
carry — a last-verified stamp, a canonical matching the URL it is served at, one
h1, the shared nav, a skip link, an entry in the sitemap. Those are the rules the
README states, and until 28 August 2026 nothing enforced any of them: a page
could lose its stamp or its nav entirely and this script still printed clean.

Exits non-zero if anything fails, so it can gate a deploy later if that is ever
wanted.
"""
import re, sys, pathlib
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).parent / "public"
SITE = "https://plainlyai.org"
problems = []


def note(kind, detail):
    problems.append(f"{kind}: {detail}")


pages = {}
for f in ROOT.rglob("*.html"):
    rel = f.relative_to(ROOT).as_posix()[:-5]
    if rel.endswith("/index"):
        rel = rel[:-6]
    pages[rel or "index"] = f

src = {n: f.read_text(encoding="utf-8") for n, f in pages.items()}

# L9. Several checks below index straight into these by name. A page renamed or
# deleted made this file raise a KeyError, which is the worst way for a checker
# to fail: it stops at the first one, every check after it never runs, and the
# output looks like a broken script rather than a broken site. Name the pages the
# checks depend on, report the missing one, and let the rest of the run continue
# against what is there.
REQUIRED = ("index", "changes", "guides", "model-facts")
for _req in REQUIRED:
    if _req not in src:
        problems.append(f"missing page: {_req}.html is gone or renamed, and checks "
                        f"below depend on it by name")
src = {**{r: "" for r in REQUIRED}, **src}
ids = {n: re.findall(r'\sid="([^"]+)"', s) for n, s in src.items()}


def resolve(href):
    """Map a root-relative URL to a page key the way Cloudflare Pages serves it."""
    p = href.split("#")[0].strip("/")
    if p == "":
        return "index"
    return p if p in pages else (p + "/index" if p + "/index" in pages else p)


# 1. every root-relative link resolves, and its fragment exists on the target
#
#    L10. This only ever looked at hrefs starting with "/". Every other internal
#    form — "../concepts/tokens", "tokens.html", "./guides" — was not checked and
#    not reported, so the first relative link anybody wrote would have been the
#    one link on the site nothing was watching. The site's convention is that
#    internal links are root-relative and extensionless, because that is how Pages
#    serves them without a redirect hop; anything else is now a finding rather
#    than a blind spot. External http(s), mailto: and #fragments are handled
#    elsewhere or deliberately not followed.
RELATIVE = re.compile(r'href="(?!https?:|mailto:|#|/)([^"]+)"')
links = 0
for name, s in src.items():
    for href in RELATIVE.findall(s):
        note("relative link", f"{name} -> {href} (internal links are root-relative "
                              f"and extensionless here, so this is unchecked by the "
                              f"link check below)")
    for href in re.findall(r'href="(/[^"]*)"', s):
        links += 1
        target, _, frag = href.partition("#")
        key = resolve(target)
        if key not in pages:
            if not (ROOT / target.lstrip("/")).exists():   # static assets
                note("broken link", f"{name} -> {href}")
            continue
        if frag and frag not in ids[key]:
            note("broken fragment", f"{name} -> {href}")

# 2. same-page anchors resolve
anchors = 0
for name, s in src.items():
    for frag in re.findall(r'href="#([^"]+)"', s):
        anchors += 1
        if frag not in ids[name]:
            note("broken anchor", f"{name} -> #{frag}")

# 3. no duplicate ids on a page
for name, lst in ids.items():
    for dup, n in Counter(lst).items():
        if n > 1:
            note("duplicate id", f"{name} #{dup} x{n}")

# 4. note-titles stay unique site-wide. Repeated box headings were a real
#    finding once: five pages closed with the same one.
titles = Counter()
for s in src.values():
    titles.update(re.findall(r'<p class="note-title">([^<]*)', s))
for t, n in titles.items():
    if n > 1:
        note("repeated note-title", f'"{t}" on {n} pages')

# 5. nothing is reachable only from the nav and footer. This is the failure
#    that created the Guides page: three pages had quietly become unreachable.
inbound = defaultdict(set)
for name, s in src.items():
    blocks = {
        "content": re.search(r"<main.*?</main>", s, re.S),
        "chrome": None,
    }
    chrome = "".join(
        m.group(0) for m in
        [re.search(r'<nav class="site-nav".*?</nav>', s, re.S),
         re.search(r"<footer.*?</footer>", s, re.S)] if m
    )
    for label, blk in (("content", blocks["content"].group(0) if blocks["content"] else ""),
                       ("chrome", chrome)):
        for href in re.findall(r'href="(/[^"]*)"', blk):
            key = resolve(href)
            if key in pages and key != name:
                inbound[key].add(label)
for name in pages:
    if name in ("404", "index"):
        continue                                   # the wordmark links home
    if "content" not in inbound.get(name, set()):
        note("content-orphan", f"{name} reachable only from nav/footer")

# 6. the feed still matches the log. feed.py derives one from the other, so the
#    only way they diverge is a log entry added without regenerating. This is
#    the check that makes that a build failure instead of a silent lie.
feed_path = ROOT / "feed.xml"
if not feed_path.exists():
    note("missing feed", "public/feed.xml — run python feed.py")
else:
    NS = {"a": "http://www.w3.org/2005/Atom"}
    try:
        feed = ET.parse(feed_path).getroot()
    except ET.ParseError as e:
        note("unparseable feed", str(e))
        feed = None
    if feed is not None:
        fids = [e.findtext("a:id", "", NS).partition("#")[2]
                for e in feed.findall("a:entry", NS)]
        # L13. Discovered rather than named, exactly as feed.py does it, so a
        # year-based split of the log adds an archive page and edits neither
        # program. The two used to reach for changes.html by name, which made
        # splitting the log a change to two pieces of tooling as well as the page.
        # Order matters: the live log leads, archives follow newest-first. Sorting
        # the names is wrong — "changes-2026" sorts before "changes" — and this
        # check is what caught that when the split was rehearsed.
        LOG_MARKER = '<h2 id="the-log">'
        _archives = sorted((n for n in src
                            if n.startswith("changes-") and LOG_MARKER in src[n]),
                           reverse=True)
        _order = ([n for n in ("changes",) if LOG_MARKER in src.get(n, "")] + _archives)
        log_bodies = [src[n].split(LOG_MARKER, 1)[1] for n in _order]
        log = ["", "".join(log_bodies)] if log_bodies else [""]
        # Match id wherever it sits in the tag. This check and feed.py used to
        # share a pattern that required id to come first, so a heading written
        # with any other attribute order was invisible to both: feed.py skipped
        # the entry and this check confirmed the short feed was correct. Two
        # checks that fail together are one check.
        lids = re.findall(r'<h3\b[^>]*\bid="([^"]+)"', log[1]) if len(log) == 2 else []
        if len(log) == 2:
            headings = len(re.findall(r"<h3\b", log[1]))
            if headings != len(lids):
                note("log", f"{headings} entry headings but {len(lids)} carry an id "
                            "— feed.py cannot link the ones without")
        if not lids:
            note("feed", "no page carries a log section")
        elif fids != lids:
            missing = [i for i in lids if i not in fids]
            extra = [i for i in fids if i not in lids]
            detail = f"{len(lids)} log entries, {len(fids)} feed entries"
            if missing:
                detail += f"; not in the feed: {', '.join(missing[:3])}"
            if extra:
                detail += f"; not in the log: {', '.join(extra[:3])}"
            note("stale feed", detail + " — run python feed.py")

# 7. the nav is identical everywhere, and every page has one. It is hand-edited
#    across every page. Counting variants could not see a page that lost its nav
#    altogether: a page with no nav was simply not counted, so len(navs) stayed 1
#    and the check passed. It degraded as pages lost navs, which is backwards.
navs = defaultdict(list)
for name, s in src.items():
    m = re.search(r'<nav class="site-nav".*?</nav>', s, re.S)
    if not m:
        note("no site nav", name)
        continue
    navs[re.sub(r'\s+', ' ', re.sub(r' aria-current="page"', '', m.group(0)))].append(name)
if len(navs) > 1:
    majority = max(navs.values(), key=len)
    for names in navs.values():
        if names is not majority:
            note("nav drift", f"{', '.join(sorted(names))} "
                              f"differs from the nav on the other {len(majority)} pages")


# 8. the invariants every page carries. These are the site's own rules, and
#    nothing checked them: a page could lose its last-verified stamp, its skip
#    link, its lang attribute or its <main> and this still printed clean.
#    <main> is the worst of those, because check 5 reads content links out of it
#    — a page without one contributes no inbound links, so removing it does not
#    just go unnoticed, it weakens the orphan check for every page it links to.
def canonical_url(name):
    """The URL Cloudflare Pages serves this page at. Directory indexes keep
    their trailing slash; /concepts/ and /concepts are not the same canonical."""
    if name == "index":
        return f"{SITE}/"
    return f"{SITE}/{name}/" if pages[name].name == "index.html" else f"{SITE}/{name}"


for name, s in src.items():
    if "<html lang=" not in s:
        note("no lang attribute", name)
    if s.count("<main") != 1:
        note("main", f"{name} has {s.count('<main')} <main> elements, expected 1")
    # Added with M4. Every page's body is one <article> inside <main>, so a
    # crawler and a screen reader can both tell the page's own content from the
    # nav and footer that surround it. It is one line of markup and nothing
    # visual depends on it, which is exactly the kind of thing that gets
    # dropped from the next new page without this.
    if s.count("<article") != 1:
        note("article", f"{name} has {s.count('<article')} <article> elements, expected 1")
    if 'class="skip-link"' not in s:
        note("no skip link", name)
    h1s = len(re.findall(r"<h1[ >]", s))
    if h1s != 1:
        note("h1", f"{name} has {h1s} <h1> elements, expected 1")
    if name == "404":
        continue                      # deliberately carries no dates and no canonical
    if 'class="stamp"' not in s:
        note("no last-verified stamp", name)
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', s)
    if not canon:
        note("no canonical", name)
    elif canon.group(1) != canonical_url(name):
        note("wrong canonical", f"{name} -> {canon.group(1)}, "
                                f"expected {canonical_url(name)}")
    og = re.search(r'<meta property="og:url" content="([^"]+)"', s)
    if not og:
        note("no og:url", name)
    elif canon and og.group(1) != canon.group(1):
        note("og:url != canonical", f"{name} -> {og.group(1)}")


# 9. the sitemap lists every page and nothing else. It is hand-edited, and a
#    page missing from it is a page search engines stop indexing, with no
#    symptom anywhere on the site. This drifts quietly: the README described the
#    sitemap as covering "all nine pages" long after it covered twenty-six.
sitemap_path = ROOT / "sitemap.xml"
if not sitemap_path.exists():
    note("missing sitemap", "public/sitemap.xml")
else:
    SM = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    try:
        urls = ET.parse(sitemap_path).getroot().findall("s:url", SM)
    except ET.ParseError as e:
        note("unparseable sitemap", str(e))
        urls = []
    listed = {u.findtext("s:loc", "", SM).replace(f"{SITE}/", "").rstrip("/") or "index"
              for u in urls}
    expected = {n for n in pages if n != "404"}
    for n in sorted(expected - listed):
        note("missing from sitemap", n)
    for n in sorted(listed - expected):
        note("sitemap lists a page that does not exist", n)


# 10. the structured data agrees with the page it sits on. The last-verified
#     date is now written twice — once for the reader in the stamp, once for a
#     crawler in JSON-LD — and robots.txt asks every crawler to carry that date
#     with any fact it takes. Two copies of a date is exactly the arrangement
#     this site refuses everywhere else, so it is allowed here only because this
#     check makes them impossible to disagree. If that ever becomes untrue,
#     delete the JSON-LD rather than letting it drift.
import json

STAMP = re.compile(r'<p class="stamp"[^>]*>(.*?)</p>', re.S)
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

for name, s in src.items():
    blocks = LD.findall(s)
    if name == "404":
        if blocks:
            note("json-ld", "404 carries structured data; it is not indexed")
        continue
    if len(blocks) != 1:
        note("json-ld", f"{name} has {len(blocks)} ld+json blocks, expected 1")
        continue
    try:
        data = json.loads(blocks[0])
    except json.JSONDecodeError as e:
        note("json-ld", f"{name} does not parse: {e}")
        continue
    node = data.get("@graph", [data])[0]
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', s)
    if canon and node.get("url") != canon.group(1):
        note("json-ld url", f"{name} -> {node.get('url')}, canonical is {canon.group(1)}")
    st = STAMP.search(s)
    if not st:
        continue
    for label, field in (("Published", "datePublished"),
                         ("Last (?:verified|updated)", "dateModified")):
        m = re.search(label + r' <time datetime="([^"]+)"', st.group(1))
        if not m:
            if field == "dateModified":
                note("stamp", f"{name} has no machine-readable last-verified date")
            continue
        if node.get(field) != m.group(1):
            note("json-ld date", f"{name} {field}={node.get(field)} "
                                 f"but the stamp says {m.group(1)}")


# 11. Rule 2: model names and prices belong on Model facts and nowhere else.
#     This is the rule the whole maintenance model rests on — one page rots
#     instead of nine — and until now nothing enforced it. It was found broken by
#     reading, not by tooling: Getting better results named a current model well
#     outside the two-page exemption Model facts grants at line 95.
#
#     The names are derived from the table rather than listed here, so this check
#     cannot fall out of step with the thing it is checking. Every exemption is
#     written down with the reason it was granted, and an exemption that stops
#     being needed is reported too — an allowlist nobody prunes quietly turns
#     into permission for anything.
#
#     What it does NOT catch, stated so nobody trusts it further than it goes:
#     word counts, context sizes written out in prose, and dates. Those cannot be
#     told apart from ordinary numbers without more false alarms than findings.
RULE2_ALLOWED = {
    "changes": "the log quotes figures that were wrong, on purpose; every entry is dated",
    "concepts/tokens": "the arithmetic exemption Model facts grants at line 95, and the "
                       "sentence points back at the table by name",
    "getting-better-results": "quotes a dated vendor caveat naming a model, with the fetch "
                              "date in the sentence and the staleness as the lesson",
    "sources": "names which document each figure came from; the figures stay on Model facts",
}

mf = src.get("model-facts", "")
model_names = set()
for body in re.findall(r"<tbody\b[^>]*>(.*?)</tbody>", mf, re.S):
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", body, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) == 8:
            model_names.add(cells[0])
        elif len(cells) == 7:
            model_names.add(cells[1])
model_names = {n for n in model_names if len(n) > 4 and "/" not in n}

if not model_names:
    note("rule 2", "no model names could be read from model-facts.html")
else:
    used = set()
    for name, s in src.items():
        if name == "model-facts":
            continue
        m = re.search(r"<main.*?</main>", s, re.S)
        if not m:
            continue
        body = re.sub(r"<[^>]+>", " ", m.group(0))
        found = sorted(n for n in model_names if n in body)
        prices = re.findall(r"\$\d", body)
        if not (found or prices):
            continue
        if name in RULE2_ALLOWED:
            used.add(name)
            continue
        what = []
        if found:
            what.append("names " + ", ".join(found))
        if prices:
            what.append(f"carries {len(prices)} price figure(s)")
        note("rule 2", f"{name} {' and '.join(what)} — these live on Model facts, or the "
                       f"exemption needs writing into RULE2_ALLOWED with its reason")
    for name in sorted(set(RULE2_ALLOWED) - used):
        if name in src:
            note("stale exemption", f"{name} is allowlisted for rule 2 but no longer needs "
                                    f"it — remove it from RULE2_ALLOWED")


# 12. every guide is reachable from the home page's own content.
#     This is not a style rule, it is the condition a decision rests on. Guides
#     was taken out of the nav on 14 August "once all three were reachable from
#     the homepage directly". Two guides were added on 26 August and not linked
#     there, so the reason quietly stopped being true and the nav stayed as it
#     was on the strength of it. Nothing noticed for three days.
#
#     The list is read from the Guides page rather than written here, so adding
#     a guide adds it to this check automatically. If this ever fails, the
#     honest options are to link the guide from the home page or to put Guides
#     back in the nav — not to delete the check.
guide_list = re.search(r'<ul class="concept-list">(.*?)</ul>', src.get("guides", ""), re.S)
if not guide_list:
    note("guides", "could not read the guide list from guides.html")
else:
    listed = [h.strip("/") for h in re.findall(r'href="(/[^"#]+)"', guide_list.group(1))]
    home = re.search(r"<main.*?</main>", src.get("index", ""), re.S)
    home = home.group(0) if home else ""
    if not listed:
        note("guides", "the guide list on guides.html is empty")
    for g in listed:
        if not re.search(r'href="/' + re.escape(g) + r'["#]', home):
            note("unreachable guide", f"{g} is listed on Guides but not linked from the "
                                      f"home page, which is why Guides is not in the nav")


# 13. model-facts.json still matches the table it is derived from, and the
#     machine-readable attributes still match the figures a reader sees.
#
#     Two copies of a price is exactly the arrangement this site refuses
#     everywhere else. It is allowed here for the same reason the JSON-LD dates
#     are: this check makes them impossible to disagree. If that ever stops being
#     true, delete the attributes rather than letting them drift — a scraper
#     reading data-usd-per-mtok="4" off a cell that now reads $5 is worse served
#     than one that had to parse the text.
#
#     The first half catches a table edited without re-running modelfacts.py.
#     The second catches a cell whose visible figure was changed while its
#     attribute was not, which the first half cannot see: the generator would
#     faithfully publish the stale attribute and both files would agree.
try:
    import modelfacts
except Exception as e:                        # pragma: no cover - import guard
    note("model-facts.json", f"modelfacts.py could not be imported: {e}")
else:
    mf_src = src.get("model-facts", "")
    json_path = ROOT / "model-facts.json"
    if not json_path.exists():
        note("model-facts.json", "is missing — run modelfacts.py")
    else:
        try:
            expected = modelfacts.dump(modelfacts.build(mf_src))
        except SystemExit as e:
            expected = None
            note("model-facts.json", f"cannot be generated from the table: {e}")
        if expected is not None and json_path.read_text(encoding="utf-8") != expected:
            note("model-facts.json",
                 "does not match the table on model-facts.html — run modelfacts.py")

    # the attributes against the text of their own cells
    def as_tokens(t):
        m = re.fullmatch(r"([\d.]+)\s*([MmKk]?)", t.strip())
        if not m:
            return None
        return int(float(m.group(1)) * {"m": 1_000_000, "k": 1_000, "": 1}[m.group(2).lower()])

    cells = re.findall(r"<t[dh]\b([^>]*)>(.*?)</t[dh]>", mf_src, re.S)
    checked = 0
    for attrs, inner in cells:
        shown = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", inner)).strip()
        tok = re.search(r'data-tokens="([^"]*)"', attrs)
        usd = re.search(r'data-usd-per-mtok="([^"]*)"', attrs)
        if tok:
            checked += 1
            if as_tokens(shown) != int(tok.group(1)):
                note("model-facts attribute",
                     f'data-tokens="{tok.group(1)}" but the cell reads {shown!r}')
        if usd:
            checked += 1
            try:
                same = abs(float(shown.replace("$", "")) - float(usd.group(1))) < 1e-9
            except ValueError:
                same = False
            if not same:
                note("model-facts attribute",
                     f'data-usd-per-mtok="{usd.group(1)}" but the cell reads {shown!r}')
        if 'class="unverified"' in attrs and "data-unverified" not in attrs:
            note("model-facts attribute",
                 f"a cell flagged unverified carries no reason: {shown!r}")
    if checked == 0:
        note("model-facts attribute",
             "no data-tokens or data-usd-per-mtok attributes found — the figures "
             "are no longer machine-readable, or this check has gone blind")


# 14. the log is not yet too big to serve in one piece.
#     L13. changes.html grows monotonically and never shrinks: 94% of that page is
#     the log, and a reader who wants the newest entry downloads all of it. The
#     split into per-year archives is not due yet — every entry so far is from one
#     year, so splitting today would produce an empty archive — but "not yet" is
#     the kind of judgement that survives long past the point it stopped being
#     true. This is the trigger, written down, so the decision happens on a number
#     rather than on somebody noticing.
#
#     feed.py and check 6 both discover log pages by their marker, so the split
#     needs no tooling change at all. Rehearsed on 30 August by actually splitting
#     the log and running both: the feed came out complete and in the right order
#     with nothing edited. What the rehearsal showed the archive page does need,
#     all of it ordinary page work that the checks above will name for you:
#       - keep <h2 id="the-log"> and every entry id byte-for-byte, or permalinks die
#       - its own canonical, og:url and JSON-LD url (checks 8 and 10)
#       - an entry in sitemap.xml (check 9)
#       - a link from changes.html body text, not just the nav (check 5)
#       - a note-title that is not a copy of the one on changes.html (check 4)
#     Then run feed.py. The rehearsal also caught a bug in this very mechanism:
#     "changes-2026.html" sorts before "changes.html", so ordering log pages by
#     filename put the oldest entries at the top of the feed. Both files now name
#     the live log first and take archives in reverse.
LOG_LIMIT = 200_000
_log_page = pages.get("changes")
if _log_page:
    _size = _log_page.stat().st_size
    if _size > LOG_LIMIT:
        note("log size",
             f"changes.html is {_size:,} bytes, over the {LOG_LIMIT:,} trigger. "
             f"Split the older entries into public/changes-YYYY.html — the tooling "
             f"finds log pages by their marker, so nothing else needs changing.")


print(f"{len(pages)} pages, {links} links, {anchors} anchors")
if problems:
    print(f"\n{len(problems)} problem(s):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("clean")
