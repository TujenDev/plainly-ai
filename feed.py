"""Generate public/feed.xml from the log on public/changes.html.

The feed is derived, never hand-written. That is the whole point: an entry
cannot appear in one and not the other, so the feed cannot quietly stop
matching the log it claims to publish. Run it after adding a log entry.

    python feed.py

check.py verifies that the newest feed entry still matches the newest log
entry, so a forgotten run fails the structural check rather than shipping.
"""
import html
import re
import pathlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).parent / "public"
SITE = "https://plainlyai.org"
LOG = f"{SITE}/changes"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# <h3 id="..">25 August 2026 — title<a class="anchor" ..></a></h3> then paragraphs
#
# `id` is matched wherever it sits in the tag, not only as the first attribute.
# The strict form silently skipped any entry headed `<h3 class=".." id="..">`,
# and check.py used the same strict pattern to verify this file's output — so
# the two agreed with each other while both missed the entry, and the feed
# shipped short with the structural check reporting clean.
ENTRY = re.compile(
    r'<h3\b[^>]*\bid="([^"]+)"[^>]*>(.*?)<a class="anchor".*?</h3>'
    r'(.*?)(?=<h3\b|<p class="next">|</div>)',
    re.S,
)
H3 = re.compile(r"<h3\b")
FIRST_P = re.compile(r"<p>(.*?)</p>", re.S)


def text(fragment):
    """Tag soup to plain text, entities resolved, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", fragment))).strip()


def iso(heading, inherited):
    """'25 August 2026 — ...' to '2026-08-25'.

    One entry in the log is headed 'Same day', which is how a reader parses it
    too: it takes the date of the entry above it. Anything else without a date
    is a broken heading and stops the run rather than being given a guess.
    """
    m = re.match(r"(\d{1,2}) (\w+) (\d{4})", heading)
    if not m:
        if heading.lower().startswith("same day") and inherited:
            return inherited
        raise SystemExit(f"feed.py: log entry does not start with a date: {heading[:60]!r}")
    day, month, year = m.groups()
    if month not in MONTHS:
        raise SystemExit(f"feed.py: unknown month {month!r} in {heading[:60]!r}")
    return f"{year}-{MONTHS.index(month) + 1:02d}-{int(day):02d}"


def entries():
    src = (ROOT / "changes.html").read_text(encoding="utf-8")
    log = src.split('<h2 id="the-log">', 1)
    if len(log) != 2:
        raise SystemExit("feed.py: could not find the log section on changes.html")
    out, last = [], None
    for eid, heading, body in ENTRY.findall(log[1]):
        heading = text(heading)
        last = iso(heading, last)
        first = FIRST_P.search(body)
        # The date is in the heading; the reader gets it in its own field, so the
        # title carries only the part after the em dash.
        _, _, title = heading.partition(" — ")
        out.append({
            "id": eid,
            "date": last,
            "title": title or heading,
            "summary": text(first.group(1)) if first else "",
        })
    # Every <h3> in the log is an entry. If one didn't parse, it is missing its
    # id or its anchor link, and writing a feed that is quietly one entry short
    # is worse than not writing one: a subscriber never learns of a correction.
    headings = len(H3.findall(log[1]))
    if headings != len(out):
        raise SystemExit(
            f"feed.py: {headings} log headings but {len(out)} parsed — an entry is "
            f"missing its id or its anchor link. Refusing to write a short feed."
        )
    return out


def build(items):
    updated = f"{items[0]['date']}T00:00:00Z" if items else "1970-01-01T00:00:00Z"
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "  <title>Plainly — the maintenance log</title>",
        "  <subtitle>Every correction, addition and re-check on plainlyai.org, dated. "
        "Corrections to this site, not AI news.</subtitle>",
        f'  <link rel="self" type="application/atom+xml" href="{SITE}/feed.xml"/>',
        f'  <link rel="alternate" type="text/html" href="{LOG}"/>',
        f"  <id>{LOG}</id>",
        f"  <updated>{updated}</updated>",
        "  <author><name>Plainly</name><uri>%s/about</uri></author>" % SITE,
        "  <rights>Free to quote. If you reproduce a fact from here, carry its "
        "last-verified date with it.</rights>",
    ]
    for it in items:
        parts += [
            "  <entry>",
            f"    <title>{escape(it['title'])}</title>",
            f'    <link rel="alternate" type="text/html" href="{LOG}#{it["id"]}"/>',
            f"    <id>{LOG}#{it['id']}</id>",
            f"    <updated>{it['date']}T00:00:00Z</updated>",
            f'    <summary type="text">{escape(it["summary"])}</summary>',
            "  </entry>",
        ]
    parts.append("</feed>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    items = entries()
    if not items:
        raise SystemExit("feed.py: no log entries found, refusing to write an empty feed")
    (ROOT / "feed.xml").write_text(build(items), encoding="utf-8")
    print(f"feed.xml: {len(items)} entries, newest {items[0]['date']} — {items[0]['title']}")
