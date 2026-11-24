#!/usr/bin/env python3
"""Make the example profile's art: abstract 'photos', a logo and client logos.
Everything is drawn here, so the example carries no stock photo or third-party mark.
Run from the repo root: python3 tools/make_example_assets.py"""
import math, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "skills", "profile-studio", "templates", "example")
FONT = os.path.join(ROOT, "skills", "profile-studio", "assets", "fonts", "Poppins-Bold.ttf")
FONT_R = os.path.join(ROOT, "skills", "profile-studio", "assets", "fonts", "Poppins-Medium.ttf")

SCENES = {  # name: (base colour A, base colour B, accent, motif)
    "city.jpg": ((10, 40, 60), (30, 90, 110), (120, 220, 160), "towers"),
    "team.jpg": ((20, 50, 70), (60, 110, 120), (240, 200, 120), "bokeh"),
    "desk.jpg": ((15, 35, 45), (50, 80, 90), (110, 200, 240), "grid"),
    "growth.jpg": ((12, 45, 40), (40, 110, 80), (160, 240, 120), "chart"),
    "audit.jpg": ((18, 30, 50), (60, 70, 110), (150, 180, 255), "lines"),
    "people.jpg": ((30, 45, 60), (90, 110, 120), (255, 210, 150), "bokeh"),
    "network.jpg": ((10, 30, 45), (30, 70, 100), (100, 220, 255), "nodes"),
    "office.jpg": ((20, 40, 45), (70, 100, 100), (200, 240, 200), "towers"),
}

def gradient(w, h, a, b):
    im = Image.new("RGB", (w, h)); px = im.load()
    for y in range(h):
        for x in range(0, w, 1):
            t = (x / w * 0.6 + y / h * 0.4)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return im

def scene(name, a, b, acc, motif, w=1600, h=1100):
    rnd = random.Random(name)
    im = gradient(w, h, a, b); d = ImageDraw.Draw(im, "RGBA")
    if motif == "towers":
        x = 0
        while x < w:
            tw = rnd.randint(70, 180); th = rnd.randint(250, 900)
            d.rectangle([x, h - th, x + tw, h], fill=(0, 0, 0, rnd.randint(60, 130)))
            for wy in range(h - th + 20, h, 34):
                for wx in range(x + 12, x + tw - 12, 26):
                    if rnd.random() < 0.35: d.rectangle([wx, wy, wx + 10, wy + 14], fill=acc + (rnd.randint(60, 180),))
            x += tw + rnd.randint(4, 30)
    elif motif == "bokeh":
        for _ in range(60):
            r = rnd.randint(20, 140); x, y = rnd.randint(0, w), rnd.randint(0, h)
            d.ellipse([x - r, y - r, x + r, y + r], fill=acc + (rnd.randint(20, 70),))
        im = im.filter(ImageFilter.GaussianBlur(14)); d = ImageDraw.Draw(im, "RGBA")
    elif motif == "grid":
        for gx in range(0, w, 80): d.line([(gx, 0), (gx, h)], fill=acc + (40,), width=2)
        for gy in range(0, h, 80): d.line([(0, gy), (w, gy)], fill=acc + (40,), width=2)
        for _ in range(14):
            x, y = rnd.randrange(0, w, 80), rnd.randrange(0, h, 80)
            d.rectangle([x, y, x + 160, y + 80], fill=acc + (rnd.randint(40, 110),))
    elif motif == "chart":
        for i in range(16):
            bh = int(120 + i * 45 + rnd.randint(-60, 60)); x = 80 + i * 95
            d.rectangle([x, h - bh, x + 60, h], fill=acc + (90 + i * 6,))
        pts = [(80 + i * 95 + 30, h - (160 + i * 48)) for i in range(16)]
        d.line(pts, fill=(255, 255, 255, 200), width=8)
    elif motif == "lines":
        for i in range(40):
            y = rnd.randint(0, h); d.line([(0, y), (w, y + rnd.randint(-300, 300))], fill=acc + (rnd.randint(30, 90),), width=rnd.randint(2, 10))
    elif motif == "nodes":
        pts = [(rnd.randint(0, w), rnd.randint(0, h)) for _ in range(40)]
        for p in pts:
            for q in pts:
                if p < q and math.dist(p, q) < 300: d.line([p, q], fill=acc + (60,), width=2)
        for x, y in pts: d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=acc + (220,))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(os.path.join(EX, "photos", name), quality=86)

def logo(path, name, colour, w=900, h=240, ground=None):
    im = Image.new("RGBA", (w, h), ground or (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(20, h - 30), (110, 30), (200, h - 30)], fill=colour)
    d.polygon([(80, h - 30), (150, 90), (220, h - 30)], fill=tuple(max(c - 60, 0) for c in colour[:3]) + (255,))
    f = ImageFont.truetype(FONT, 92); d.text((250, h / 2 - 66), name, font=f, fill=(29, 42, 53, 255))
    im.save(path)

def client(path, text, colour, shape):
    im = Image.new("RGBA", (600, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shape == 0: d.ellipse([10, 50, 130, 170], fill=colour)
    elif shape == 1: d.rectangle([10, 50, 130, 170], fill=colour)
    else: d.polygon([(10, 170), (70, 50), (130, 170)], fill=colour)
    f = ImageFont.truetype(FONT_R, 62); d.text((150, 70), text, font=f, fill=(40, 50, 60, 255))
    im.save(path)

if __name__ == "__main__":
    os.makedirs(os.path.join(EX, "photos"), exist_ok=True); os.makedirs(os.path.join(EX, "logos"), exist_ok=True)
    for n, (a, b, acc, m) in SCENES.items(): scene(n, a, b, acc, m)
    logo(os.path.join(EX, "logo.png"), "Lumen Ridge", (67, 176, 42, 255))
    for i, (t, c) in enumerate([("Avora", (230, 90, 60, 255)), ("Kestrel", (40, 120, 200, 255)), ("Tidewell", (20, 160, 150, 255)),
                                ("Orbis", (150, 80, 200, 255)), ("Halden", (220, 160, 30, 255)), ("Marlo", (90, 90, 90, 255)),
                                ("Quillo", (200, 60, 120, 255)), ("Ferro", (60, 140, 70, 255))]):
        client(os.path.join(EX, "logos", "%s.png" % t.lower()), t, c, i % 3)
    print("example assets written to", EX)
