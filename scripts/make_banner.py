#!/usr/bin/env python3
"""
README banner + logo mark for the Argus repo.

The mark is an eye with target rings: a silver eye, a crimson iris, a dark
ring and a red pupil. Argus was the hundred-eyed watchman; the rings say the
eye is *scanning* rather than merely watching. It is drawn low-poly, as flat
shaded facets, to match the other project marks on gurutechnology.services.

PNG rather than SVG on purpose: GitHub sanitises SVG in markdown, and text in
an SVG depends on fonts the reader may not have. A PNG renders identically
everywhere. Everything is drawn at SS x supersample and downsampled with LANCZOS,
because GitHub serves the file at the reader's column width and a 1x render
looks soft on a HiDPI screen.

Usage:
    python3 scripts/make_banner.py            # writes docs/assets/{argus-banner,argus-logo}.png
"""
import os
import xml.etree.ElementTree as ET
import sys
from PIL import Image, ImageDraw, ImageFont

SS = 4                                   # supersample factor
GROUND        = (13, 13, 15)             # near-black page ground
TEXT          = (242, 240, 238)
MUTED         = (139, 134, 128)
ACCENT        = (200, 16, 46)            # the repo's red

FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]
FONT_PREFS = {
    "bold":    ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "NotoSans-Bold.ttf"],
    "regular": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf"],
    "mono":    ["DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"],
}


def font(kind, size):
    for name in FONT_PREFS[kind]:
        for root in FONT_DIRS:
            for dirpath, _, files in os.walk(root):
                if name in files:
                    return ImageFont.truetype(os.path.join(dirpath, name), size)
    return ImageFont.load_default()


# ---- the low-poly mark ------------------------------------------------------
# The mark is docs/assets/argus-mark.svg, the same file gurutechnology.services
# shows: flat shaded polygons in a 64-unit box. draw_mark reads those polygons
# and scales them to pixels, so these PNGs cannot drift from the site's mark.
MARK_SVG = os.path.join(os.path.dirname(__file__), "..", "docs", "assets", "argus-mark.svg")


def _mark_polygons():
    """[(rgb, [(x, y), ...]), ...] from MARK_SVG, in drawing order."""
    polys = []
    for el in ET.parse(MARK_SVG).iter("{http://www.w3.org/2000/svg}polygon"):
        nums = [float(v) for v in el.get("points").replace(",", " ").split()]
        fill = el.get("fill").lstrip("#")
        polys.append((tuple(int(fill[i:i + 2], 16) for i in (0, 2, 4)), list(zip(nums[::2], nums[1::2]))))
    if not polys:
        raise SystemExit(f"no polygons found in {MARK_SVG}")
    return polys


def draw_mark(d, cx, cy, size):
    """Draw the mark centred on (cx, cy), its longer side `size` pixels.

    Each polygon is outlined in its own colour, so no seam shows between
    neighbours after the LANCZOS downsample.
    """
    polys = _mark_polygons()
    xs = [x for _, pts in polys for x, _ in pts]
    ys = [y for _, pts in polys for _, y in pts]
    s = size / max(max(xs) - min(xs), max(ys) - min(ys))
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for rgb, pts in polys:
        d.polygon([(cx + (x - mx) * s, cy + (y - my) * s) for x, y in pts], fill=rgb, outline=rgb)


def make_logo(path, size=512):
    """Square mark on a transparent ground, for a favicon, avatar or docs header.

    The faceted mark is filled, so one drawing reads on light and dark pages.
    The -dark file is kept under its old name for anything that links to it.
    """
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_mark(d, s / 2, s / 2, s * 0.90)
    img.resize((size, size), Image.LANCZOS).save(path)
    return path


def fit(d, text, kind, size, maxw):
    """Largest font <= size whose rendered width fits maxw."""
    while size > 8:
        f = font(kind, size)
        if d.textlength(text, font=f) <= maxw:
            return f
        size = int(size * 0.94)
    return font(kind, 8)


def make_banner(path, W=1280, H=320):
    w, h = W * SS, H * SS
    img = Image.new("RGB", (w, h), GROUND)
    d = ImageDraw.Draw(img)

    d.rectangle([0, h - 4 * SS, w, h], fill=ACCENT)

    PAD = w * 0.055
    r = h * 0.180
    cx, cy = PAD + r * 1.72, h * 0.47
    draw_mark(d, cx, cy, r * 3.44)

    x = cx + r * 2.45
    avail = w - x - PAD                       # hard right bound; nothing may exceed it

    tagline = "Open-source database of surveillance equipment identifiers"
    facts   = "45,809 identifiers   \u00b7   261 manufacturers   \u00b7   98 sources   \u00b7   full provenance"

    f_word = fit(d, "ARGUS", "bold",    int(h * 0.255), avail)
    f_sub  = fit(d, tagline, "regular", int(h * 0.085), avail)
    f_mono = fit(d, facts,   "mono",    int(h * 0.062), avail)

    d.text((x, h * 0.335), "ARGUS", font=f_word, fill=TEXT, anchor="lm")
    d.text((x, h * 0.625), tagline, font=f_sub,  fill=MUTED, anchor="lm")
    d.text((x, h * 0.795), facts,   font=f_mono, fill=(102, 98, 94), anchor="lm")

    img.resize((W, H), Image.LANCZOS).save(path)
    return path


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
    os.makedirs(out, exist_ok=True)
    b = make_banner(os.path.join(out, "argus-banner.png"))
    l = make_logo(os.path.join(out, "argus-logo.png"))
    make_logo(os.path.join(out, "argus-logo-dark.png"))
    for px in (128, 64, 32):
        make_logo(os.path.join(out, f"argus-logo-{px}.png"), size=px)
    import glob
    for f in sorted(glob.glob(os.path.join(out, "argus-*.png"))):
        print(f"  {os.path.relpath(f)}  {os.path.getsize(f):,} bytes")
