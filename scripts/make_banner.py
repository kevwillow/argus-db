#!/usr/bin/env python3
"""
README banner + logo mark for the Argus repo.

The mark is an eye rendered as a radar aperture: a vesica outline, concentric
sweep rings for the iris, and a solid pupil. Argus was the hundred-eyed
watchman; the rings say the eye is *scanning* rather than merely watching.

PNG rather than SVG on purpose: GitHub sanitises SVG in markdown, and text in
an SVG depends on fonts the reader may not have. A PNG renders identically
everywhere. Everything is drawn at SS x supersample and downsampled with LANCZOS,
because GitHub serves the file at the reader's column width and a 1x render
looks soft on a HiDPI screen.

Usage:
    python3 scripts/make_banner.py            # writes docs/assets/{argus-banner,argus-logo}.png
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

SS = 4                                   # supersample factor
GROUND        = (13, 13, 15)             # near-black page ground
TEXT          = (242, 240, 238)
MUTED         = (139, 134, 128)
ACCENT        = (200, 16, 46)            # the repo's red
RING          = (58, 58, 64)             # cool grey for the outer rings

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


def _vesica(cx, cy, w, hgt, n=160):
    """Points of a true vesica (pointed lens): two circular arcs meeting at (+-w, 0).

    Upper arc passes through (-w,0), (0,-hgt), (w,0). Solving for a circle through
    those three points gives centre (0, k) with k = (w^2 - hgt^2) / (2*hgt).
    """
    import math
    k = (w * w - hgt * hgt) / (2.0 * hgt)
    R = k + hgt
    a0 = math.atan2(0 - k, -w)            # angle to the left corner
    a1 = math.atan2(0 - k, w)             # angle to the right corner
    top, bot = [], []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        x, y = cx + R * math.cos(t), cy + k + R * math.sin(t)
        top.append((x, y))
        bot.append((x, 2 * cy - y))       # mirror across the horizontal axis
    return top + bot[::-1]


def draw_mark(d, cx, cy, r, hole=GROUND, outline=TEXT):
    """The eye-aperture mark, centred on (cx, cy) with iris radius r.

    The lens outline is drawn as two FILLED vesicas (outer in TEXT, inner in the
    background colour) rather than a stroked polyline -- stroking a dense polyline
    leaves visible lumps at this scale, filling does not.
    """
    import math
    lw = max(2.0, r * 0.150)
    W, Hh = r * 1.72, r * 1.16
    d.polygon(_vesica(cx, cy, W, Hh), fill=outline)
    d.polygon(_vesica(cx, cy, W - lw * 1.30, Hh - lw), fill=hole)

    for frac, col, wid in [(1.00, RING, 0.085), (0.72, RING, 0.075), (0.47, ACCENT, 0.095)]:
        rr = r * frac
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=col, width=max(2, int(r * wid)))

    pr = r * 0.20
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=ACCENT)


def make_logo(path, size=512, outline=(42, 42, 48)):
    """Square mark on transparent ground, for a favicon / avatar / docs header.

    Two variants ship: the default dark outline reads on light backgrounds, and
    argus-logo-dark.png uses the light outline for dark backgrounds. A single
    mark cannot do both -- the lens outline has to contrast with the page.
    """
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # dark outline so the standalone mark survives on a light background too
    draw_mark(d, S / 2, S / 2, S * 0.26, hole=(0, 0, 0, 0), outline=outline)
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
    draw_mark(d, cx, cy, r)

    x = cx + r * 2.45
    avail = w - x - PAD                       # hard right bound; nothing may exceed it

    tagline = "Open-source database of surveillance equipment identifiers"
    facts   = "43,126 identifiers   \u00b7   261 manufacturers   \u00b7   98 sources   \u00b7   full provenance"

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
    make_logo(os.path.join(out, "argus-logo-dark.png"), outline=TEXT)
    for px in (128, 64, 32):
        make_logo(os.path.join(out, f"argus-logo-{px}.png"), size=px)
    import glob
    for f in sorted(glob.glob(os.path.join(out, "argus-*.png"))):
        print(f"  {os.path.relpath(f)}  {os.path.getsize(f):,} bytes")
