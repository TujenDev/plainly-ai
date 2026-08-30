"""Generate public/model-facts.json from the tables on public/model-facts.html.

    python modelfacts.py

Same arrangement as feed.py: the HTML is the source, the machine-readable file
is derived, and check.py fails if the two have drifted. The page a reader sees
and the file a scraper reads cannot disagree, because only one of them is
written by hand.

Why it exists. `prices.py` had its own parser for these tables, and that parser
was the site's worst outage: it discarded rows it could not read and still
printed that Model facts matched every vendor page. Patching it left two
parsers for one table, either of which could go quietly blind. There is now one
parser, in this file, and it fails loudly rather than skipping anything —
prices.py reads the JSON.

To be clear about what that does and does not fix: reading the table is still
done by a regex over hand-edited HTML, and that can still go wrong. What
changed is that it can only go wrong in one place, and check 13 compares this
file against the table on every run, so a parse that silently loses a row shows
up as a structural failure rather than as a clean price report.

Three things this file will not do:

1. **It never invents a figure.** A cell the site has left visibly blank under
   rule 4 becomes `null` in the JSON *and* an entry in `unverified` carrying the
   reason. `null` on its own reads as "unknown"; these are not unknown, they are
   figures the vendor does not publish, and the difference is the whole point of
   flagging them on the page.

2. **The numbers it emits are the numbers on the page, normalised.**
   `data-tokens="64000"` is what "64k" means, not a claim that the vendor's
   exact limit is 64,000 — Google's is 65,536 and the page says so in its notes.
   The attribute exists so a reader of the JSON does not have to parse "1.05M";
   it never asserts anything the visible cell does not.

3. **It writes no dates of its own.** `verified` is read off the page's own
   stamp, which is the only place that date is allowed to live.
"""
import json
import re
import html
import pathlib

ROOT = pathlib.Path(__file__).parent / "public"
SITE = "https://plainlyai.org"
SOURCE = f"{SITE}/model-facts"

TBODY = re.compile(r"<tbody\b[^>]*>(.*?)</tbody>", re.S)
ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<(t[dh])\b([^>]*)>(.*?)</\1>", re.S)

CLAUDE_COLS = ("model", "api_id", "context", "max_output",
               "input_usd_per_mtok", "output_usd_per_mtok",
               "reliable_cutoff", "training_cutoff")
OTHER_COLS = ("vendor", "model", "api_id", "context", "max_output",
              "input_usd_per_mtok", "output_usd_per_mtok")
NUMERIC = {"context": "data-tokens", "max_output": "data-tokens",
           "input_usd_per_mtok": "data-usd-per-mtok",
           "output_usd_per_mtok": "data-usd-per-mtok"}


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", fragment))).strip()


def attr(tag_attrs, name):
    m = re.search(name + r'="([^"]*)"', tag_attrs)
    return html.unescape(m.group(1)) if m else None


def models(src):
    """Every row in every tbody, or an exception. Never a partial list."""
    out = []
    for body in TBODY.findall(src):
        for tr in ROW.findall(body):
            cells = CELL.findall(tr)
            if len(cells) == 8:
                cols, rec = CLAUDE_COLS, {"vendor": "Anthropic"}
            elif len(cells) == 7:
                cols, rec = OTHER_COLS, {}
            else:
                raise SystemExit(
                    f"modelfacts.py: a row has {len(cells)} cells, expected 7 or 8 — "
                    f"{text(tr)[:70]!r}. The table changed shape; fix this parser "
                    f"rather than letting a row go unpublished.")
            unverified = {}
            for col, (_tag, attrs, inner) in zip(cols, cells):
                shown = text(inner)
                data_attr = NUMERIC.get(col)
                if data_attr is None:
                    rec[col] = shown
                    continue
                reason = attr(attrs, "data-unverified")
                if reason is not None:
                    rec[col] = None
                    unverified[col] = {"shown": shown, "reason": reason}
                    continue
                raw = attr(attrs, data_attr)
                if raw is None:
                    raise SystemExit(
                        f"modelfacts.py: {rec.get('model', '?')} has no {data_attr} on "
                        f"its {col} cell and it is not flagged unverified. Every "
                        f"figure must be machine-readable or explicitly blank.")
                rec[col] = int(raw) if data_attr == "data-tokens" else float(raw)
            rec["unverified"] = unverified
            out.append(rec)
    return out


def build(src):
    stamp = re.search(r'Last verified <time datetime="(\d{4}-\d{2}-\d{2})"', src)
    if not stamp:
        raise SystemExit("modelfacts.py: no last-verified stamp on model-facts.html")
    rows = models(src)
    return {
        "$comment": (
            "Derived from " + SOURCE + " by modelfacts.py. Do not edit: the page is "
            "the source and this file is regenerated from it. Token counts are the "
            "figures printed on the page normalised to integers, not a claim about a "
            "vendor's exact limit; where a vendor publishes an exact figure the page "
            "says so in its notes. A null figure is never 'unknown' — see unverified."),
        "source": SOURCE,
        "verified": stamp.group(1),
        "units": {
            "context": "tokens",
            "max_output": "tokens",
            "input_usd_per_mtok": "USD per million input tokens",
            "output_usd_per_mtok": "USD per million output tokens",
        },
        "rights": ("Free to quote. If you reproduce a figure from here, carry its "
                   "verified date with it."),
        "models": rows,
    }


def dump(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    src = (ROOT / "model-facts.html").read_text(encoding="utf-8")
    data = build(src)
    if not data["models"]:
        raise SystemExit("modelfacts.py: no rows parsed, refusing to write an empty file")
    (ROOT / "model-facts.json").write_text(dump(data), encoding="utf-8")
    flagged = sum(len(m["unverified"]) for m in data["models"])
    print(f"model-facts.json: {len(data['models'])} models, {flagged} figures "
          f"flagged unverified, verified {data['verified']}")
