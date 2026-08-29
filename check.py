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
ids = {n: re.findall(r'\sid="([^"]+)"', s) for n, s in src.items()}


def resolve(href):
    """Map a root-relative URL to a page key the way Cloudflare Pages serves it."""
    p = href.split("#")[0].strip("/")
    if p == "":
        return "index"
    return p if p in pages else (p + "/index" if p + "/index" in pages else p)


# 1. every root-relative link resolves, and its fragment exists on the target
links = 0
for name, s in src.items():
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
        log = src["changes"].split('<h2 id="the-log">', 1)
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
            note("feed", "could not find the log on changes.html")
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
    home = re.search(r"<main.*?</main>", src["index"], re.S)
    home = home.group(0) if home else ""
    if not listed:
        note("guides", "the guide list on guides.html is empty")
    for g in listed:
        if not re.search(r'href="/' + re.escape(g) + r'["#]', home):
            note("unreachable guide", f"{g} is listed on Guides but not linked from the "
                                      f"home page, which is why Guides is not in the nav")


print(f"{len(pages)} pages, {links} links, {anchors} anchors")
if problems:
    print(f"\n{len(problems)} problem(s):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("clean")
