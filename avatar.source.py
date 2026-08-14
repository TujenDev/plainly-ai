"""Profile avatar for the Plainly X account.

The mark is the site's own device: a rubber stamp reading LAST VERIFIED with the
date field left blank. Same argument as the og-image, which says it outright:
every page carries the date it was checked, a picture can't, so this one doesn't.

Two variants. A is a solid accent disc with the stamp reversed out of it, which
is the one that survives being shown at 48px in a timeline. B is the paper-and-
amber stamp from the og-image, truer to the device but lower contrast at size.

Rendered at 4x and downsampled, because PIL has no antialiasing on shapes.
Regenerate with:  python avatar.source.py
"""
from PIL import Image, ImageDraw, ImageFont
import math, pathlib

OUT = pathlib.Path(__file__).parent
S = 800          # final size
SS = 4           # supersample factor
N = S * SS

BOLD = "C:/Windows/Fonts/arialbd.ttf"

PALETTE = {
    "a": {  # solid accent, reversed
        "bg":    (11, 110, 99),      # --accent  #0b6e63
        "ink":   (252, 252, 250),    # --paper   #fcfcfa
        "ring":  (252, 252, 250, 150),
        "name":  "avatar-teal",
    },
    "b": {  # the og-image stamp, on paper
        "bg":    (253, 243, 228),    # --flag-soft #fdf3e4
        "ink":   (154, 91, 18),      # --flag      #9a5b12
        "ring":  (154, 91, 18, 165),
        "name":  "avatar-stamp",
    },
}

TOP_TEXT = "LAST VERIFIED"
BOTTOM_TEXT = "PLAINLYAI.ORG"


def arc(img, text, radius, font, fill, tracking=0.0, bottom=False):
    """Text on an arc, each glyph rotated to stand on the circle.

    A glyph's position on the ring and its own rotation have to be set
    independently, which is the whole difficulty. Rotating a finished top arc by
    180 degrees does not give you a bottom arc: it puts the glyphs upside down
    AND reverses the reading order. So the bottom is built separately, drawn at
    six o'clock the right way up and swept the other way round, which leaves the
    letters with their tops toward the centre. That is what makes the bottom of
    a seal read normally instead of standing on its head.
    """
    c = N // 2
    probe = ImageDraw.Draw(img)
    widths = [probe.textlength(ch, font=font) + tracking for ch in text]
    span = sum(widths) / radius                  # radians the string occupies

    # Bottom text hangs inward from its baseline, top text stands outward from
    # it, so the bottom baseline is pushed out by one cap height to keep both
    # strings inside the same band between the rings.
    bb = font.getbbox("H")
    r = radius + (bb[3] - bb[1]) if bottom else radius

    a = span / 2 if bottom else -span / 2
    for ch, w in zip(text, widths):
        step = w / r
        mid = a - step / 2 if bottom else a + step / 2
        glyph = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text(
            (c, c + r) if bottom else (c, c - r),
            ch, font=font, fill=fill, anchor="ms",
        )
        # negative because PIL rotates counter-clockwise
        img.alpha_composite(glyph.rotate(-math.degrees(mid),
                                         resample=Image.BICUBIC, center=(c, c)))
        a += -step if bottom else step


def build(key):
    p = PALETTE[key]
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = N // 2

    # full-bleed disc: X crops to a circle, so no corners to lose
    d.ellipse([0, 0, N - 1, N - 1], fill=p["bg"] + (255,))

    # the two stamp rules
    for r, w in ((int(0.470 * N), int(0.0075 * N)), (int(0.362 * N), int(0.0075 * N))):
        d.ellipse([c - r, c - r, c + r, c + r], outline=p["ring"], width=w)

    rf = ImageFont.truetype(BOLD, int(0.056 * N))
    rr = int(0.385 * N)
    arc(img, TOP_TEXT, rr, rf, p["ring"], tracking=0.010 * N)
    arc(img, BOTTOM_TEXT, rr, rf, p["ring"], tracking=0.010 * N, bottom=True)

    # dots closing the ring at 3 and 9, where the two strings meet
    dot = int(0.011 * N)
    for dx in (-1, 1):
        x = c + dx * rr
        d.ellipse([x - dot, c - dot, x + dot, c + dot], fill=p["ring"])

    # the P, optically centred on the disc rather than on its own baseline
    f = ImageFont.truetype(BOLD, int(0.375 * N))
    bb = d.textbbox((0, 0), "P", font=f)
    d.text((c - (bb[0] + bb[2]) / 2, c - (bb[1] + bb[3]) / 2 - int(0.045 * N)),
           "P", font=f, fill=p["ink"] + (255,))

    # the date field, left blank. The whole point of the mark.
    y = c + int(0.170 * N)
    d.line([c - int(0.125 * N), y, c + int(0.125 * N), y],
           fill=p["ink"] + (235,), width=int(0.0125 * N))

    out = img.resize((S, S), Image.LANCZOS)
    path = OUT / f"{p['name']}.png"
    out.convert("RGB").save(path, "PNG", optimize=True)

    # 48px is roughly what a timeline shows; check it still reads
    out.resize((48, 48), Image.LANCZOS).convert("RGB").save(
        OUT / f"{p['name']}-48px.png", "PNG")
    return path


for k in PALETTE:
    print("wrote", build(k))
