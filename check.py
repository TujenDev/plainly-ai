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

Exits non-zero if anything fails, so it can gate a deploy later if that is ever
wanted.
"""
import re, sys, pathlib
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).parent / "public"
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
    import xml.etree.ElementTree as ET
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
        lids = re.findall(r'<h3 id="([^"]+)">', log[1]) if len(log) == 2 else []
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

# 7. the nav is identical everywhere. It is hand-edited across 23 files.
navs = Counter()
for name, s in src.items():
    m = re.search(r'<nav class="site-nav".*?</nav>', s, re.S)
    if m:
        navs[re.sub(r'\s+', ' ', re.sub(r' aria-current="page"', '', m.group(0)))] += 1
if len(navs) > 1:
    note("nav drift", f"{len(navs)} different navs across pages")

print(f"{len(pages)} pages, {links} links, {anchors} anchors")
if problems:
    print(f"\n{len(problems)} problem(s):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("clean")
