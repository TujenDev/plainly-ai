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


print(f"{len(pages)} pages, {links} links, {anchors} anchors")
if problems:
    print(f"\n{len(problems)} problem(s):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("clean")
