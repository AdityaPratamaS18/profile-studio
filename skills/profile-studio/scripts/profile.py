#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
profile-studio: build a print-ready company profile (A4 PDF) from one profile.json.

    python3 profile.py doctor                     check Python packages and optional tools
    python3 profile.py new <folder> [--name X]    start a profile from the example
    python3 profile.py build <folder> [--pages 1,3-5]
    python3 profile.py check <folder>             fonts, words, overflow, contact sheet
    python3 profile.py docx <folder>              Word review copy of the words

One profile is one folder: profile.json, photos/, logo file, and build/ for output.
Every page is drawn as vector art with live, embedded text. Photos are baked to JPEG.
"""
import argparse, datetime, glob, hashlib, io, json, math, os, re, shutil, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(SKILL, "assets", "fonts")
ICONS = os.path.join(SKILL, "assets", "icons")
TEMPLATE = os.path.join(SKILL, "templates", "example")

# ------------------------------------------------------------------ doctor
REQUIRED = [("reportlab", "reportlab"), ("PIL", "pillow"), ("svglib", "svglib"), ("docx", "python-docx")]
OPTIONAL = [("pdftoppm", "contact sheets in `check`"), ("pdffonts", "font check in `check`"),
            ("pdftotext", "word check in `check`")]

def cmd_doctor(_):
    ok = True
    print("Python %s" % sys.version.split()[0])
    for mod, pkg in REQUIRED:
        try:
            __import__(mod); print("OK    %s" % pkg)
        except Exception as e:
            ok = False
            spec = pkg
            if pkg == "reportlab" and sys.version_info < (3, 10):
                spec = '"reportlab<5.1"'
            print("MISS  %s (%s)   fix: python3 -m pip install --user %s" % (pkg, str(e).splitlines()[0][:80], spec))
    for tool, why in OPTIONAL:
        found = shutil.which(tool)
        print("%s  %s (%s)%s" % ("OK  " if found else "WARN", tool, why,
              "" if found else "   fix: install poppler (macOS: brew install poppler; Debian: apt install poppler-utils)"))
    print("READY" if ok else "NOT READY: install the MISS items, then run doctor again")
    return 0 if ok else 1

# ------------------------------------------------------------------ profile loading
def load(folder):
    path = os.path.join(folder, "profile.json")
    if not os.path.exists(path):
        sys.exit("No profile.json in %s. Start one with: profile.py new %s" % (folder, folder))
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_dir"] = os.path.abspath(folder)
    return cfg

def cmd_new(a):
    if os.path.exists(os.path.join(a.folder, "profile.json")):
        sys.exit("%s already has a profile.json. Nothing changed." % a.folder)
    shutil.copytree(TEMPLATE, a.folder, dirs_exist_ok=True)
    if a.name:
        p = os.path.join(a.folder, "profile.json"); cfg = json.load(open(p, encoding="utf-8"))
        cfg["company"]["name"] = a.name
        json.dump(cfg, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("Started %s from the example. Edit profile.json, add photos to photos/, then run build." % a.folder)

# ------------------------------------------------------------------ theme
try:
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:          # `doctor` must run before the packages are installed
    HexColor = None

PW, PH = 595.2756, 841.8898   # A4 in points
ML = MR = 48
CW = PW - ML - MR
DEFAULT_BRAND = {
    "ground": "#0a1c24", "surface": "#0f2a33", "border": "#2a4d58",
    "accent": "#43b02a", "accent_light": "#5ed12f", "accent_dark": "#2f8c1d",
    "secondary": "#29a8e0", "heading": "#f2f7f5", "body": "#b8c7cc", "muted": "#8aa0a7",
    "ink": "#1d2a35", "band": "#ffffff",
}
T = {}          # theme colours for the current build

def set_theme(cfg):
    b = dict(DEFAULT_BRAND); b.update(cfg.get("brand", {}).get("colors", {}))
    for k, v in b.items():
        T[k] = HexColor(v); T[k + "_hex"] = v

_FACES = {"R": "Poppins-Regular.ttf", "L": "Poppins-Light.ttf", "M": "Poppins-Medium.ttf",
          "MI": "Poppins-MediumItalic.ttf", "S": "Poppins-SemiBold.ttf", "B": "Poppins-Bold.ttf"}
F = {}

def register_fonts():
    for k, fn in _FACES.items():
        name = "PS-" + k
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, fn))); F[k] = name

def sw(text, font, size):
    return pdfmetrics.stringWidth(text, font, size)

def wrap(text, font, size, width):
    out = []
    for p in str(text).split("\n"):
        line = ""
        for w in p.split():
            t = (line + " " + w).strip()
            if sw(t, font, size) <= width or not line:
                line = t
            else:
                out.append(line); line = w
        out.append(line)
    return out

def para(c, text, x, y, width, font=None, size=10, leading=15, color=None, align="left"):
    """Wrapped text. Returns the baseline for the next line."""
    font = font or F["R"]
    c.setFillColor(color or T["body"]); c.setFont(font, size)
    for ln in wrap(text, font, size, width):
        if align == "center":
            c.drawCentredString(x + width / 2.0, y, ln)
        else:
            c.drawString(x, y, ln)
        y -= leading
    return y

WARN = []

# ------------------------------------------------------------------ images
CACHE = None
W_PX = 1786          # page width in pixels for baked art (about 216 dpi)

def _key(*p):
    return hashlib.md5("|".join(str(x) for x in p).encode()).hexdigest()[:14]

def photo_path(cfg, name):
    """A photo from the profile's photos/ folder. A missing photo gets a labelled placeholder,
    so a profile builds before its photos arrive and the gap is easy to see."""
    from PIL import Image, ImageDraw
    if name:
        for p in (os.path.join(cfg["_dir"], "photos", name), os.path.join(cfg["_dir"], name)):
            if os.path.exists(p):
                return p
    out = os.path.join(CACHE, "placeholder-%s.jpg" % _key(name))
    if not os.path.exists(out):
        im = Image.new("RGB", (1600, 1100), T["surface_hex"]); d = ImageDraw.Draw(im)
        for i in range(0, 2800, 60):
            d.line([(i, 0), (i - 1100, 1100)], fill=T["border_hex"], width=3)
        im.save(out, quality=85)
    WARN.append("missing photo: %s (placeholder used)" % (name or "(none set)"))
    return out

def bleed(c, cfg, name, x, y, w, h, focus=(0.5, 0.5), sat=1.0, bright=1.0, fades=(), into=None):
    """Draw a photo cover-cropped to a box, with fades to a flat colour baked in.
    fades: (edge, share of that axis, opacity at the edge), edge = top/bottom/left/right."""
    from PIL import Image, ImageEnhance
    into = into or T["ground_hex"]; src = photo_path(cfg, name)
    scale = W_PX / PW
    out = os.path.join(CACHE, "bleed-%s.jpg" % _key(src, os.path.getmtime(src), w, h, focus, sat, bright, fades, into))
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB"); tar = float(w) / h; iw, ih = im.size
        if float(iw) / ih > tar:
            nw = int(ih * tar); xx = int((iw - nw) * focus[0]); im = im.crop((xx, 0, xx + nw, ih))
        else:
            nh = int(iw / tar); yy = int((ih - nh) * focus[1]); im = im.crop((0, yy, iw, yy + nh))
        Wp, Hp = max(int(w * scale), 2), max(int(h * scale), 2)
        im = im.resize((Wp, Hp), Image.LANCZOS)
        if sat != 1: im = ImageEnhance.Color(im).enhance(sat)
        if bright != 1: im = ImageEnhance.Brightness(im).enhance(bright)
        flat = Image.new("RGB", (Wp, Hp), into)
        for edge, frac, strength in fades:
            vert = edge in ("top", "bottom"); n = max(int((Hp if vert else Wp) * frac), 1)
            ramp = Image.new("L", (1, n) if vert else (n, 1)); px = ramp.load()
            for i in range(n):
                v = int(255 * strength * ((n - i) / float(n)) ** 1.4)
                if vert: px[0, i] = v
                else: px[i, 0] = v
            if edge == "bottom" or edge == "right":
                ramp = ramp.transpose(Image.FLIP_TOP_BOTTOM if vert else Image.FLIP_LEFT_RIGHT)
            ramp = ramp.resize((Wp, n) if vert else (n, Hp))
            mask = Image.new("L", (Wp, Hp), 0)
            mask.paste(ramp, (0, 0 if edge == "top" else Hp - n) if vert else (0 if edge == "left" else Wp - n, 0))
            im = Image.composite(flat, im, mask)
        im.save(out, quality=86, optimize=True)
    c.drawImage(ImageReader(out), x, y, width=w, height=h)

# ------------------------------------------------------------------ icons
_ICON_CACHE = {}

def icon(c, name, x, y, size, color=None, width=None):
    """A Lucide line icon as vector art. Unknown names fall back to 'check' with a warning."""
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import STATE_DEFAULTS
    STATE_DEFAULTS["fontName"] = F["R"]            # icons have no text; keeps unused fonts out
    color = color or T["accent_light_hex"]
    path = os.path.join(ICONS, "%s.svg" % name)
    if not os.path.exists(path):
        WARN.append("unknown icon '%s' (used 'check'); add its SVG to assets/icons" % name)
        path = os.path.join(ICONS, "check.svg")
    key = (path, color, width)
    if key not in _ICON_CACHE:
        svg = open(path, encoding="utf-8").read().replace("currentColor", color)
        if width: svg = svg.replace('stroke-width="2"', 'stroke-width="%s"' % width)
        _ICON_CACHE[key] = svg2rlg(io.StringIO(svg))
    d = _ICON_CACHE[key]; k = size / float(d.width)
    c.saveState(); c.translate(x, y); c.scale(k, k); renderPDF.draw(d, c, 0, 0); c.restoreState()

def icon_tile(c, name, x, y, s=44):
    c.saveState(); c.setFillColor(T["surface"]); c.roundRect(x, y, s, s, 6, stroke=0, fill=1)
    c.setStrokeColor(T["accent"]); c.setLineWidth(1.4); c.roundRect(x, y, s, s, 6, stroke=1, fill=0)
    c.restoreState(); icon(c, name, x + s * 0.22, y + s * 0.22, s * 0.56)

# ------------------------------------------------------------------ page furniture
STATE = {"page": 0}

def flat(c):
    c.setFillColor(T["ground"]); c.rect(0, 0, PW, PH, stroke=0, fill=1)

def head(c, cfg):
    c.setFillColor(T["heading"]); c.setFont(F["R"], 8.4)
    web = cfg["company"].get("website", "")
    c.drawString(ML, PH - 50, web)
    c.setStrokeColor(T["heading"]); c.setLineWidth(0.7)
    c.line(ML + sw(web, F["R"], 8.4) + 10, PH - 47, PW - MR - 34, PH - 47)
    c.setFillColor(T["heading"]); c.circle(PW - MR - 12, PH - 47, 12, stroke=0, fill=1)
    c.setFillColor(T["ground"]); c.setFont(F["S"], 8.6)
    c.drawCentredString(PW - MR - 12, PH - 50, "%02d" % STATE["page"])

def foot(c, cfg, color=None):
    c.setFillColor(color or T["muted"]); c.setFont(F["R"], 7.4)
    c.drawString(ML, 30, cfg["company"].get("legal_name", cfg["company"]["name"]))
    c.drawRightString(PW - MR, 30, cfg["company"].get("footer_label", "Company Profile"))

def title(c, two, y, size=34, x=ML):
    a, b = (two + [""])[:2] if isinstance(two, list) else (two, "")
    c.setFont(F["B"], size); c.setFillColor(T["heading"]); c.drawString(x, y, a.upper())
    if b:
        c.setFillColor(T["accent"]); c.drawString(x, y - size * 1.08, b.upper())
    yy = y - size * 1.08 if b else y
    wmax = max(sw(a.upper(), F["B"], size), sw(b.upper(), F["B"], size))
    c.setFillColor(T["accent_light"]); c.rect(x, yy - 11, wmax * 0.42, 2.6, stroke=0, fill=1)
    return yy

def logo(c, cfg, x, y, h):
    """The logo in its true colours. It is never inverted or recoloured."""
    p = cfg.get("brand", {}).get("logo")
    path = os.path.join(cfg["_dir"], p) if p else None
    if not path or not os.path.exists(path):
        c.setFillColor(T["ink"]); c.setFont(F["B"], 18); c.drawString(x, y + h / 2 - 6, cfg["company"]["name"])
        WARN.append("logo file not found (%s): company name drawn instead" % p); return
    img = ImageReader(path); iw, ih = img.getSize()
    c.drawImage(img, x, y, width=h * iw / float(ih), height=h, mask="auto")

BAND_H = 112

def logo_band(c, cfg, lines):
    """Full-width light band that carries the true-colour logo. A small box around a logo looks
    pasted on; a band reads as part of the layout."""
    c.setFillColor(T["band"]); c.rect(0, 0, PW, BAND_H, stroke=0, fill=1)
    c.setFillColor(T["accent"]); c.rect(0, BAND_H, PW, 3, stroke=0, fill=1)
    logo(c, cfg, ML, 25, 62)
    y = BAND_H / 2.0 + (len(lines) - 1) * 7.5 - 3
    for text, font, size, col in lines:
        c.setFillColor(col); c.setFont(font, size); c.drawRightString(PW - MR, y, text); y -= 15

def bullets(c, items, x, y, w, size=10.4, leading=15):
    for t in items:
        icon(c, "check", x - 1, y - 1.6, size * 1.05, width=3)
        y = para(c, t, x + 14, y, w - 14, size=size, leading=leading) - 3
    return y

# ------------------------------------------------------------------ pages
def p_cover(c, cfg, d):
    from PIL import Image, ImageDraw
    co = cfg["company"]; style = d.get("style", "diagonal")
    kicker = d.get("kicker", ""); t = d.get("title", [co["name"]]); sub = d.get("subtitle", "")
    if style == "photo":
        bleed(c, cfg, d.get("photo"), 0, 0, PW, PH, focus=tuple(d.get("focus", (0.5, 0.4))),
              fades=(("bottom", 0.62, 1.0), ("top", 0.22, 0.8)))
        y = 340
        if kicker:
            c.setFont(F["B"], 27); c.setFillColor(T["accent_light"]); c.drawString(ML, y, kicker)
        c.setFont(F["B"], 60); c.setFillColor(T["heading"])
        for i, ln in enumerate(t[:2]): c.drawString(ML - 3, y - 62 - i * 62, ln.upper())
        para(c, sub, ML, y - 62 * len(t[:2]) - 34, CW, size=11.4, leading=16, color=T["heading"])
    else:
        # hard-edged field cut at 45 degrees, photo in the lower-left triangle, parallel bars
        K = W_PX / PW; H_PX = int(PH * K); ss = 2
        src = photo_path(cfg, d.get("photo"))
        out = os.path.join(CACHE, "cover-%s.jpg" % _key(src, os.path.getmtime(src), d.get("face"), T["accent_hex"]))
        if not os.path.exists(out):
            im = Image.new("RGB", (W_PX, H_PX), T["ground_hex"])
            def poly(pts, fill):
                m = Image.new("L", (W_PX * ss, H_PX * ss), 0)
                ImageDraw.Draw(m).polygon([(x * K * ss, y * K * ss) for x, y in pts], fill=255)
                im.paste(Image.new("RGB", (W_PX, H_PX), fill), (0, 0), m.resize((W_PX, H_PX), Image.LANCZOS))
            def bar(x0, y0, x1, y1, th, fill):
                L = math.hypot(x1 - x0, y1 - y0); nx, ny = -(y1 - y0) / L * th / 2, (x1 - x0) / L * th / 2
                poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill)
            ph = Image.open(src).convert("RGB")
            face = d.get("face", [0.5, 0.25])          # where the face is in the photo, as shares
            show_h = 720 * K; k = show_h / ph.size[1]
            ph = ph.resize((max(int(ph.size[0] * k), 1), int(show_h)), Image.LANCZOS)
            want = (142 * K, 500 * K)
            lay = Image.new("RGB", (W_PX, H_PX), T["ground_hex"])
            lay.paste(ph, (int(want[0] - face[0] * ph.size[0]), int(want[1] - face[1] * ph.size[1])))
            m = Image.new("L", (W_PX * ss, H_PX * ss), 0)
            ImageDraw.Draw(m).polygon([(0, 300 * K * ss), (PW * K * ss, (PW + 300) * K * ss), (0, H_PX * ss)], fill=255)
            im.paste(lay, (0, 0), m.resize((W_PX, H_PX), Image.LANCZOS))
            poly([(0, 128), (128, 0), (PW, 0), (PW, 236), (283, 548), (0, 265)], T["accent_hex"])
            bar(-10, 104, 104, -10, 14, T["secondary_hex"])
            bar(PW + 10, 268, 330, 548, 13, T["secondary_hex"])
            bar(-10, 272, 250, 532, 10, T["secondary_hex"])
            bar(340, 590, 470, 720, 14, T["accent_hex"])
            bar(400, 570, 520, 690, 8, T["secondary_hex"])
            im.save(out, quality=88, optimize=True)
        c.drawImage(ImageReader(out), 0, 0, width=PW, height=PH)
        x = ML + 70; y = PH - 150
        c.setFillColor(T["ground"])
        if kicker:
            c.setFont(F["L"], 30); c.drawString(x, y, kicker.upper())
        c.setFont(F["B"], 48); c.drawString(x - 2, y - 52, t[0].upper())
        if len(t) > 1:
            c.setFont(F["L"], 44); c.drawString(x - 2, y - 102, t[1].upper())
        c.rect(x, y - 124, 44, 3, stroke=0, fill=1)
        para(c, sub.upper(), x, y - 148, 300, font=F["M"], size=9.4, leading=14, color=T["ground"])
    logo_band(c, cfg, [(co.get("legal_name", co["name"]), F["S"], 8.8, T["ink"]),
                       (co.get("tagline_line", ""), F["R"], 8.6, T["muted"]),
                       (co.get("website", ""), F["M"], 8.8, T["accent_dark"])])

def p_contents(c, cfg, d):
    flat(c); pw = 214
    bleed(c, cfg, d.get("photo"), 0, 0, pw, PH, focus=(0.42, 0.5), fades=(("right", 0.34, 1.0), ("top", 0.12, 0.8), ("bottom", 0.12, 0.8)))
    head(c, cfg); foot(c, cfg)
    x = pw + 22; w = PW - MR - x
    c.setFont(F["B"], 38); c.setFillColor(T["heading"]); c.drawString(x, PH - 118, d.get("heading", "CONTENTS").upper())
    c.setFillColor(T["accent"]); c.rect(x, PH - 138, 34, 3, stroke=0, fill=1)
    rows = d["_rows"]; y = PH - 178; step = (y - 76) / float(max(len(rows), 1))
    for name, n in rows:
        c.setStrokeColor(T["border"]); c.setLineWidth(0.7); c.line(x, y + 14, x + w, y + 14)
        c.setFillColor(T["accent_light"]); c.setFont(F["B"], 15); c.drawString(x, y - 8, "%02d" % n)
        c.setFillColor(T["heading"]); c.setFont(F["M"], 12.6); c.drawString(x + 46, y - 8, name)
        y -= step

def p_about(c, cfg, d):
    flat(c); h = 430
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, focus=tuple(d.get("focus", (0.5, 0.5))), fades=(("bottom", 0.46, 1.0), ("top", 0.2, 0.7)))
    head(c, cfg)
    y = title(c, d["title"], PH - h + 44, 38)
    y = para(c, d.get("lead", ""), ML, y - 36, CW, font=F["M"], size=14.2, leading=22, color=T["heading"]) - 36
    gap = 28; w = (CW - gap) / 2.0
    for i, t in enumerate(d.get("columns", [])[:2]):
        c.setStrokeColor(T["accent"]); c.setLineWidth(2.2); c.line(ML + i * (w + gap), y + 18, ML + i * (w + gap) + 30, y + 18)
        para(c, t, ML + i * (w + gap), y, w, size=10.6, leading=16.4)
    stats = d.get("stats", [])[:3]
    if stats:
        c.setFillColor(T["accent"]); c.rect(0, 0, PW, 104, stroke=0, fill=1)
        cw = CW / float(len(stats))
        for i, (big, small) in enumerate(stats):
            x = ML + i * cw
            c.setFillColor(T["ground"]); c.setFont(F["B"], 25); c.drawString(x, 58, big)
            c.setFont(F["M"], 9.6); c.drawString(x, 39, small)
    else:
        foot(c, cfg)

def p_leadership(c, cfg, d):
    flat(c); h = 460
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, fades=(("bottom", 0.42, 1.0), ("top", 0.22, 0.74)))
    head(c, cfg); foot(c, cfg)
    y = title(c, d["title"], PH - h + 44, 36)
    y = para(c, d.get("lead", ""), ML, y - 34, CW, font=F["M"], size=13, leading=20.4, color=T["heading"]) - 46
    people = d.get("people", [])[:3]; n = max(len(people), 1)
    gap = 26; w = (CW - gap * (n - 1)) / float(n)
    for i, p in enumerate(people):
        x = ML + i * (w + gap)
        c.setFillColor(T["accent"]); c.rect(x, y + 18, 34, 3, stroke=0, fill=1)
        c.setFillColor(T["heading"]); c.setFont(F["B"], 15.6); c.drawString(x, y, p["name"])
        c.setFillColor(T["accent_light"]); c.setFont(F["M"], 11); c.drawString(x, y - 18, p.get("role", ""))
        para(c, p.get("bio", ""), x, y - 46, w, size=11, leading=17.4)

def p_values(c, cfg, d):
    flat(c); h = 520
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, fades=(("bottom", 0.52, 1.0), ("top", 0.2, 0.8)))
    head(c, cfg); foot(c, cfg)
    y = title(c, d["title"], PH - h + 62, 32) - 40
    gap = 26; w = (CW - gap) / 2.0
    for i, (lab, t) in enumerate((("Mission", d.get("mission", "")), ("Vision", d.get("vision", "")))):
        x = ML + i * (w + gap)
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 14); c.drawString(x, y, d.get("labels", {}).get(lab, lab))
        para(c, t, x, y - 23, w, size=11, leading=17, color=T["heading"])
    vals = d.get("values", [])
    if vals:
        yv = 176; cw = CW / float(len(vals))
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 14); c.drawString(ML, yv, d.get("labels", {}).get("Values", "Values"))
        c.setStrokeColor(T["accent"]); c.setLineWidth(1.6); c.line(ML, yv - 12, PW - MR, yv - 12)
        for i, v in enumerate(vals):
            mid = ML + i * cw + cw / 2.0
            icon_tile(c, v.get("icon", "check"), mid - 22, yv - 72, 44)
            yy = yv - 92; c.setFillColor(T["heading"]); c.setFont(F["M"], 10.4)
            for ln in wrap(v["name"], F["M"], 10.4, cw - 8):
                c.drawCentredString(mid, yy, ln); yy -= 14

def p_clients(c, cfg, d):
    flat(c); head(c, cfg); foot(c, cfg)
    y = title(c, d["title"], PH - 106, 32)
    hero = d.get("hero")
    top = y - 26; yt = top
    if hero:
        h = 200; py = top - h; pw = 262
        c.setFillColor(T["surface"]); c.rect(ML, py, PW - ML, h, stroke=0, fill=1)
        bleed(c, cfg, d.get("photo"), PW - pw, py, pw, h, focus=(0.47, 0.42), sat=0.85, into=T["surface_hex"], fades=(("left", 0.5, 1.0),))
        c.setFillColor(T["accent"]); c.rect(ML, py, 5, h, stroke=0, fill=1)
        icon(c, "quote", ML + 20, top - 52, 40, width=1.6)
        para(c, hero["text"], ML + 26, top - 76, 306, font=F["M"], size=12.8, leading=18.8, color=T["heading"])
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 10); c.drawString(ML + 26, py + 28, hero.get("who", ""))
        c.setFillColor(T["body"]); c.setFont(F["R"], 9); c.drawString(ML + 26, py + 15, hero.get("what", ""))
        yt = py - 18
    quotes = d.get("quotes", [])[:4]
    gap = 14; w = (CW - gap) / 2.0; ch = 126
    for i, q in enumerate(quotes):
        x = ML + (i % 2) * (w + gap); ty = yt - (i // 2) * (ch + gap)
        c.setFillColor(T["surface"]); c.rect(x, ty - ch, w, ch, stroke=0, fill=1)
        c.setFillColor(T["accent"]); c.rect(x, ty - 2.5, w, 2.5, stroke=0, fill=1)
        end = para(c, q["text"], x + 14, ty - 24, w - 28, size=10, leading=14.6, color=T["heading"])
        if end < ty - ch + 34: WARN.append("page %d: a quote is too long for its card" % STATE["page"])
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 8.8); c.drawString(x + 14, ty - ch + 24, q.get("who", ""))
        c.setFillColor(T["body"]); c.setFont(F["R"], 8.2); c.drawString(x + 14, ty - ch + 12, q.get("what", ""))
    logos = d.get("logos", [])
    if logos:
        rows_q = (len(quotes) + 1) // 2
        ly = yt - rows_q * (ch + gap) - 12
        c.setFillColor(T["heading"]); c.setFont(F["S"], 10.5); c.drawString(ML, ly, d.get("logos_label", "Some of the businesses we work with"))
        tw, th, tg = (CW - 5 * 7) / 6.0, 50, 7
        for i, lg in enumerate(logos):
            row, col = i // 6, i % 6; in_row = min(6, len(logos) - row * 6)
            x0 = ML + (CW - (in_row * tw + (in_row - 1) * tg)) / 2.0
            x = x0 + col * (tw + tg); yy = ly - 12 - th - row * (th + tg)
            if yy < 44: WARN.append("page %d: client logos run into the footer" % STATE["page"])
            item = lg if isinstance(lg, dict) else {"file": lg}
            c.setFillColor(HexColor(item.get("ground", "#ffffff"))); c.roundRect(x, yy, tw, th, 5, stroke=0, fill=1)
            p = os.path.join(cfg["_dir"], "logos", item["file"])
            if not os.path.exists(p):
                WARN.append("missing client logo: %s" % item["file"]); continue
            img = ImageReader(p); iw, ih = img.getSize(); k = min((tw - 12.0) / iw, (th - 8.0) / ih)
            c.drawImage(img, x + (tw - iw * k) / 2, yy + (th - ih * k) / 2, width=iw * k, height=ih * k, mask="auto")

def p_services(c, cfg, d):
    flat(c); h = 250
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, sat=0.6, bright=0.85, fades=(("bottom", 0.5, 1.0), ("top", 0.3, 0.7)))
    head(c, cfg); foot(c, cfg)
    y = title(c, d["title"], PH - h + 40, 34)
    para(c, d.get("intro", ""), ML, y - 34, CW, font=F["M"], size=12.4, leading=18, color=T["heading"])
    y -= 70; lh = 15.6; tx = ML + 64
    lines = d["_lines"]
    hs = [17 + len(wrap(b, F["R"], 10.6, CW - 64)) * lh for a, b, ic in lines]
    pad = (y - 60 - sum(hs)) / float(max(len(lines), 1))
    if pad < 8: WARN.append("page %d: too many service lines for one page" % STATE["page"])
    for i, (a, b, ic) in enumerate(lines):
        c.setStrokeColor(T["border"]); c.setLineWidth(0.7); c.line(ML, y, PW - MR, y)
        ty = y - pad / 2 - 12
        icon_tile(c, ic, ML, ty - 26, 44)
        c.setFillColor(T["accent_light"]); c.setFont(F["B"], 10); c.drawString(tx, ty + 1, "%02d" % (i + 1))
        c.setFillColor(T["heading"]); c.setFont(F["B"], 13.6); c.drawString(tx + 22, ty, a)
        para(c, b, tx, ty - 19, CW - 64, size=10.6, leading=lh)
        y -= hs[i] + pad

def p_why(c, cfg, d):
    flat(c); h = 330
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, focus=tuple(d.get("focus", (0.5, 0.3))), fades=(("bottom", 0.5, 1.0), ("top", 0.24, 0.7)))
    head(c, cfg); foot(c, cfg)
    y = title(c, d["title"], PH - h + 44, 34)
    y = para(c, d.get("intro", ""), ML, y - 34, CW, font=F["M"], size=12.4, leading=18.6, color=T["heading"]) - 26
    reasons = d.get("reasons", [])[:8]; gap = 26; w = (CW - gap) / 2.0
    rh = (y - 52) / float(max((len(reasons) + 1) // 2, 1))
    for i, r in enumerate(reasons):
        x = ML + (i % 2) * (w + gap); ty = y - (i // 2) * rh
        icon_tile(c, r.get("icon", "check"), x, ty - 44, 44)
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 12.4); c.drawString(x + 58, ty - 14, r["title"])
        end = para(c, r.get("text", ""), x + 58, ty - 32, w - 58, size=10.4, leading=15.4, color=T["heading"])
        if end < ty - rh + 8: WARN.append("page %d: reason '%s' is too long" % (STATE["page"], r["title"]))

def _block_h(b, w):
    h = len(wrap(b["name"], F["S"], 13, w)) * 17 + 5
    if b.get("text"): h += len(wrap(b["text"], F["R"], 10.4, w)) * 15.6
    for t in b.get("bullets", []): h += len(wrap(t, F["R"], 10.4, w - 14)) * 15 + 3
    return h + 22

def _draw_block(c, b, x, y, w):
    c.setFillColor(T["accent_light"]); c.setFont(F["S"], 13)
    for ln in wrap(b["name"], F["S"], 13, w):
        c.drawString(x, y, ln); y -= 17
    y -= 5
    if b.get("text"): y = para(c, b["text"], x, y, w, size=10.4, leading=15.6, color=T["heading"])
    if b.get("bullets"): y = bullets(c, b["bullets"], x, y - (4 if b.get("text") else 0), w)
    return y - 22

def p_service(c, cfg, d):
    flat(c); gap = 28; w = (CW - gap) / 2.0
    hs = [38, 38] if d.get("groups") else [0, 0]
    if d.get("steps"):
        hs[0] += 30 + 34 * len(d["steps"]) + 40
    for b in d.get("blocks", []):
        col = b.get("column")
        col = col if col in (0, 1) else (0 if hs[0] <= hs[1] else 1)
        b["_col"] = col; hs[col] += _block_h(b, w)
    intro_h = (len(wrap(d.get("intro", ""), F["M"], 12, CW)) * 18.6 + 30) if d.get("intro") else 0
    need = 132 + 34 + max(hs) + intro_h + 36
    h = int(max(240, min(470, PH - need - 6)))
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, focus=tuple(d.get("focus", (0.5, 0.4))), sat=0.9, bright=0.92,
          fades=(("bottom", 0.5, 1.0), ("top", 0.26, 0.72)))
    head(c, cfg); foot(c, cfg)
    num = "%02d" % d["_n"]
    c.setFillColor(T["accent_light"]); c.setFont(F["B"], 30); c.drawRightString(PW - MR, PH - h + 42, num)
    icon_tile(c, d.get("icon", "briefcase"), PW - MR - sw(num, F["B"], 30) - 56, PH - h + 32, 44)
    y = title(c, d["title"], PH - h + 42, 30)
    if d.get("intro"):
        y = para(c, d["intro"], ML, y - 30, CW, font=F["M"], size=12, leading=18.6, color=T["heading"])
    y -= 34; xs = [ML, ML + w + gap]; ys = [y, y]
    for i, g in enumerate(d.get("groups", [])[:2]):
        c.setFillColor(T["heading"]); c.setFont(F["B"], 15); c.drawString(xs[i], ys[i], g)
        c.setStrokeColor(T["border"]); c.setLineWidth(0.7); c.line(xs[i], ys[i] - 10, xs[i] + w, ys[i] - 10)
        ys[i] -= 38
    if d.get("steps"):
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 13); c.drawString(xs[0], ys[0], d.get("steps_label", "How it works"))
        yy = ys[0] - 30
        for i, st in enumerate(d["steps"]):
            c.setFillColor(T["accent"]); c.circle(xs[0] + 12, yy + 4, 12, stroke=0, fill=1)
            c.setFillColor(T["ground"]); c.setFont(F["B"], 11); c.drawCentredString(xs[0] + 12, yy, "%d" % (i + 1))
            c.setFillColor(T["heading"]); c.setFont(F["M"], 11); c.drawString(xs[0] + 34, yy, st)
            if i < len(d["steps"]) - 1:
                c.setStrokeColor(T["accent"]); c.setLineWidth(1.2); c.line(xs[0] + 12, yy - 9, xs[0] + 12, yy - 22)
            yy -= 34
        ys[0] = yy - 18
    for b in d.get("blocks", []):
        ys[b["_col"]] = _draw_block(c, b, xs[b["_col"]], ys[b["_col"]], w)
    if d.get("who"):
        c.setFillColor(T["accent"]); c.rect(ML, 56, CW, 62, stroke=0, fill=1)
        c.setFillColor(T["ground"]); c.setFont(F["B"], 11); c.drawString(ML + 18, 96, d.get("who_label", "Who it is for"))
        para(c, d["who"], ML + 18, 80, CW - 36, font=F["M"], size=10.4, leading=14.6, color=T["ground"])
    if min(ys) < (132 if d.get("who") else 60):
        WARN.append("page %d: copy runs into the bottom bar; shorten it or split the page" % STATE["page"])

def p_team(c, cfg, d):
    flat(c); h = 330
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, sat=0.0, bright=0.85, fades=(("bottom", 0.46, 1.0), ("top", 0.24, 0.74)))
    head(c, cfg); foot(c, cfg)
    y = title(c, d["title"], PH - h + 42, 32)
    y = para(c, d.get("intro", ""), ML, y - 30, CW, font=F["M"], size=11.6, leading=18.2, color=T["heading"]) - 18
    groups = d.get("groups", [])[:4]; gap = 12; w = (CW - gap) / 2.0
    rows = [max([len(g["members"]) for g in groups[r * 2:r * 2 + 2]] + [1]) * 19 + 60 for r in range(2)]
    for i, g in enumerate(groups):
        x = ML + (i % 2) * (w + gap); r = i // 2; ty = y - sum(rows[:r]) - r * gap; ch = rows[r]
        if ty - ch < 44: WARN.append("page %d: team list runs into the footer" % STATE["page"])
        c.setFillColor(T["surface"]); c.rect(x, ty - ch, w, ch, stroke=0, fill=1)
        c.setFillColor(T["accent"]); c.rect(x, ty - 2.5, w, 2.5, stroke=0, fill=1)
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 11); c.drawString(x + 14, ty - 25, g["name"])
        yy = ty - 45
        for m in g["members"]:
            c.setFillColor(T["heading"]); c.setFont(F["R"], 10.4); c.drawString(x + 14, yy, m); yy -= 19

def p_contact(c, cfg, d):
    flat(c); h = 400
    bleed(c, cfg, d.get("photo"), 0, PH - h, PW, h, sat=0.72, bright=0.66, fades=(("bottom", 0.42, 1.0), ("top", 0.3, 0.86)))
    head(c, cfg)
    y = title(c, d["title"], PH - h + 48, 34)
    if d.get("headline"):
        c.setFillColor(T["heading"]); c.setFont(F["M"], 13); c.drawString(ML, y - 28, d["headline"])
    y -= 64
    offices = d.get("offices", [])[:3]; n = max(len(offices), 1); gap = 18; w = (CW - gap * (n - 1)) / float(n)
    for i, o in enumerate(offices):
        x = ML + i * (w + gap)
        c.setStrokeColor(T["accent"]); c.setLineWidth(2.2); c.line(x, y + 16, x + 30, y + 16)
        icon(c, "map-pin", x, y - 2, 13)
        c.setFillColor(T["accent_light"]); c.setFont(F["S"], 12.4); c.drawString(x + 18, y, o["name"])
        yy = y - 19
        for ln in o.get("lines", []):
            c.setFillColor(T["body"]); c.setFont(F["R"], 9.8); c.drawString(x, yy, ln); yy -= 14.6
    y -= 100
    c.setStrokeColor(T["border"]); c.setLineWidth(0.7); c.line(ML, y + 22, PW - MR, y + 22)
    people = d.get("people", [])[:2]; gap = 26; w = (CW - gap) / 2.0
    for i, p in enumerate(people):
        x = ML + i * (w + gap)
        c.setFillColor(T["heading"]); c.setFont(F["S"], 12.4); c.drawString(x, y, p["name"])
        c.setFillColor(T["accent_light"]); c.setFont(F["M"], 10); c.drawString(x, y - 16, p.get("role", ""))
        c.setFillColor(T["heading"]); c.setFont(F["R"], 10.4)
        if p.get("phone"): icon(c, "phone", x, y - 38.5, 11.5); c.drawString(x + 18, y - 36, p["phone"])
        if p.get("email"): icon(c, "mail", x, y - 55, 11.5); c.drawString(x + 18, y - 52, p["email"])
    lines = d.get("band_lines", [cfg["company"].get("phone", ""), cfg["company"].get("email", ""), cfg["company"].get("website", "")])
    logo_band(c, cfg, [(lines[0], F["S"], 8.8, T["ink"])] + [(t, F["R"], 8.8, T["muted"]) for t in lines[1:-1]] + [(lines[-1], F["M"], 8.8, T["accent_dark"])])

PAGE_TYPES = {"cover": p_cover, "contents": p_contents, "about": p_about, "leadership": p_leadership,
              "values": p_values, "clients": p_clients, "services": p_services, "why": p_why,
              "service": p_service, "team": p_team, "contact": p_contact}

def page_name(d):
    if d.get("contents_name"): return d["contents_name"]
    t = d.get("title", "")
    return " ".join(t).title() if isinstance(t, list) else str(t)

def prepare(cfg):
    pages = cfg["pages"]; n = 0; lines = []
    for i, d in enumerate(pages, 1):
        if d["type"] not in PAGE_TYPES:
            sys.exit("page %d: unknown type '%s'. Types: %s" % (i, d["type"], ", ".join(PAGE_TYPES)))
        if d["type"] == "service":
            n += 1; d["_n"] = n
            lines.append((page_name(d), d.get("summary", ""), d.get("icon", "briefcase")))
    for i, d in enumerate(pages, 1):
        if d["type"] == "contents":
            d["_rows"] = [(page_name(p), j) for j, p in enumerate(pages, 1) if j > i and p["type"] != "cover"]
        if d["type"] == "services":
            d["_lines"] = lines

def parse_pages(spec, total):
    if not spec: return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return [p for p in out if 1 <= p <= total]

def cmd_build(a):
    global CACHE
    cfg = load(a.folder); set_theme(cfg); register_fonts(); prepare(cfg)
    build = os.path.join(cfg["_dir"], "build"); CACHE = os.path.join(build, "_cache")
    os.makedirs(CACHE, exist_ok=True)
    nums = parse_pages(a.pages, len(cfg["pages"]))
    slug = re.sub(r"[^a-z0-9]+", "-", cfg["company"]["name"].lower()).strip("-") or "profile"
    out = os.path.join(build, "%s-profile.pdf" % slug if not a.pages else "%s-pages.pdf" % slug)
    c = rl_canvas.Canvas(out, pagesize=(PW, PH), initialFontName=F["R"])
    c.setTitle(cfg["company"]["name"] + " " + cfg["company"].get("footer_label", "Company Profile"))
    c.setAuthor(cfg["company"]["name"])
    for n in nums:
        STATE["page"] = n; PAGE_TYPES[cfg["pages"][n - 1]["type"]](c, cfg, cfg["pages"][n - 1]); c.showPage()
    c.save()
    print("built: %s (%d pages)" % (out, len(nums)))
    for w in dict.fromkeys(WARN): print("WARNING: " + w)
    return out

# ------------------------------------------------------------------ check
def _strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, list):
        for i in x: yield from _strings(i)
    elif isinstance(x, dict):
        for k, v in x.items():
            if not k.startswith("_") and k not in ("type", "photo", "icon", "style", "focus", "face", "file", "ground", "column", "logos"):
                yield from _strings(v)

def cmd_check(a):
    class A: pass
    b = A(); b.folder = a.folder; b.pages = None
    pdf = cmd_build(b); cfg = load(a.folder); problems = 0
    if shutil.which("pdffonts"):
        fonts = subprocess.run(["pdffonts", pdf], capture_output=True, text=True).stdout.splitlines()[2:]
        bad = [f for f in fonts if " no " in f.split("Identity")[0][-20:] or "Times" in f or "Helvetica" in f]
        print("fonts: %d, %s" % (len(fonts), "all embedded" if not bad else "PROBLEM: " + "; ".join(bad))); problems += bool(bad)
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout.lower()
        have = set(re.findall(r"[a-z0-9%+]+", text))
        words = set()
        for p in cfg["pages"]:
            for s in _strings(p): words |= set(re.findall(r"[a-z0-9%+]+", s.lower()))
        miss = sorted(w for w in words if w not in have and len(w) > 2)
        print("words: %d checked, %s" % (len(words), "all in the PDF" if not miss else "not found: " + ", ".join(miss[:30])))
        if re.search("[\u2013\u2014]", text): print("PROBLEM: the PDF has an en dash or em dash"); problems += 1
    if shutil.which("pdftoppm"):
        from PIL import Image
        tmp = os.path.join(cfg["_dir"], "build", "_sheet"); os.makedirs(tmp, exist_ok=True)
        for f in glob.glob(os.path.join(tmp, "*.png")): os.remove(f)
        subprocess.run(["pdftoppm", "-png", "-r", "40", pdf, os.path.join(tmp, "p")], check=True)
        ims = [Image.open(f) for f in sorted(glob.glob(os.path.join(tmp, "p-*.png")))]
        if ims:
            w, h = ims[0].size; cols = 6; rows = (len(ims) + cols - 1) // cols
            s = Image.new("RGB", (cols * (w + 6), rows * (h + 6)), "white")
            for i, im in enumerate(ims): s.paste(im, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
            sheet = os.path.join(cfg["_dir"], "build", "contact-sheet.png"); s.save(sheet)
            print("contact sheet: %s (look at every page)" % sheet)
    problems += len(set(WARN))
    print("CHECK %s" % ("PASSED" if not problems else "FOUND %d PROBLEM(S)" % problems))
    return 0 if not problems else 1

# ------------------------------------------------------------------ docx review copy
def cmd_docx(a):
    from docx import Document
    from docx.shared import Pt, RGBColor
    cfg = load(a.folder); prepare(cfg); co = cfg["company"]
    doc = Document(); st = doc.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(10.5)
    doc.add_heading("%s %s" % (co["name"], co.get("footer_label", "Company Profile")), 0)
    doc.add_paragraph("Draft %s · %s" % (cfg.get("version", "v1"), datetime.date.today().strftime("%d %B %Y")))
    doc.add_heading("About this document", 2)
    doc.add_paragraph("This is a draft of the content for the %s %s. It sets out the words for each page, "
                      "so the content can be reviewed and agreed before the final design."
                      % (co["name"], co.get("footer_label", "company profile").lower()))
    doc.add_heading("Summary of the plan", 2)
    tb = doc.add_table(rows=1, cols=2); tb.style = "Light Grid Accent 1"
    tb.rows[0].cells[0].text = "Page"; tb.rows[0].cells[1].text = "Section"
    for i, p in enumerate(cfg["pages"], 1):
        r = tb.add_row().cells; r[0].text = "%02d" % i; r[1].text = "Cover" if p["type"] == "cover" else page_name(p)
    skip = ("type", "photo", "icon", "style", "focus", "face", "file", "ground", "column", "contents_name", "logos")
    def walk(x, depth=0):
        if isinstance(x, str):
            if x.strip(): doc.add_paragraph(x, style="List Bullet" if depth > 1 else None)
        elif isinstance(x, list):
            for i in x: walk(i, depth + 1)
        elif isinstance(x, dict):
            for k, v in x.items():
                if k.startswith("_") or k in skip: continue
                if k in ("name", "title") and isinstance(v, str):
                    pp = doc.add_paragraph(); r = pp.add_run(v); r.bold = True; r.font.color.rgb = RGBColor(0x2f, 0x8c, 0x1d)
                else:
                    walk(v, depth)
    for i, p in enumerate(cfg["pages"], 1):
        doc.add_page_break(); doc.add_heading("%02d · %s" % (i, "Cover" if p["type"] == "cover" else page_name(p)), 1)
        walk({k: v for k, v in p.items() if k != "title" or p["type"] == "cover"})
    out = os.path.join(cfg["_dir"], "build", "%s-content-draft-%s.docx" % (
        re.sub(r"[^a-z0-9]+", "-", co["name"].lower()).strip("-"), cfg.get("version", "v1")))
    os.makedirs(os.path.dirname(out), exist_ok=True); doc.save(out); print("review copy: %s" % out)

def main():
    ap = argparse.ArgumentParser(prog="profile.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    p = sub.add_parser("new"); p.add_argument("folder"); p.add_argument("--name"); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("build"); p.add_argument("folder"); p.add_argument("--pages"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("check"); p.add_argument("folder"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("docx"); p.add_argument("folder"); p.set_defaults(fn=cmd_docx)
    a = ap.parse_args()
    if a.cmd != "doctor" and HexColor is None:
        sys.exit("reportlab is not installed. Run: python3 profile.py doctor")
    r = a.fn(a)
    sys.exit(r if isinstance(r, int) else 0)

if __name__ == "__main__":
    main()
