#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws one invented passport spread (1024x1024 PNG) for the fictional
Republic of Talvera and writes it to /output/entry.png.

Self-contained, stdlib only: an embedded 5x7 bitmap font, a hand-rolled
PNG encoder, and procedural drawing (coat of arms, stylised portrait,
stamps, machine-readable zone). No network, no files read, no time or
randomness: two runs are byte-identical.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (244, 236, 215)      # passport cream
PAPER_DK = (232, 222, 194)   # darker cream / shadow
INK = (26, 42, 74)           # navy document ink
INK_SOFT = (58, 74, 106)
GOLD = (176, 141, 52)
GOLD_LT = (201, 162, 39)
TEAL = (31, 94, 92)
TEAL_LT = (214, 232, 226)
RED = (158, 43, 34)          # stamp red
BLUE = (38, 78, 138)         # stamp blue
GREEN = (46, 110, 62)
SKIN = (216, 169, 134)
SKIN_DK = (198, 148, 112)
HAIR = (46, 32, 24)
NAVY = (34, 48, 74)
WHITE = (250, 248, 242)
GUILLOCHE = (214, 200, 160)

OUT = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg[0] for _ in range(w * h))
        self.px = bytearray(w * h * 3)
        for i in range(w * h):
            self.px[3 * i] = bg[0]
            self.px[3 * i + 1] = bg[1]
            self.px[3 * i + 2] = bg[2]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            return (self.px[i], self.px[i + 1], self.px[i + 2])
        return (0, 0, 0)

    def blend(self, x, y, c, a):
        """Blend colour c over pixel with alpha a (0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            self.px[i] = int(c[0] * a + self.px[i] * (1 - a))
            self.px[i + 1] = int(c[1] * a + self.px[i + 1] * (1 - a))
            self.px[i + 2] = int(c[2] * a + self.px[i + 2] * (1 - a))

    def fill_rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w - 1, x1)
        y1 = min(self.h - 1, y1)
        for y in range(y0, y1 + 1):
            base = 3 * (y * self.w + x0)
            for x in range(x0, x1 + 1):
                self.px[base] = c[0]
                self.px[base + 1] = c[1]
                self.px[base + 2] = c[2]
                base += 3

    def hline(self, x0, x1, y, c):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        for x in range(x0, x1 + 1):
            i = 3 * (y * self.w + x)
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def vline(self, x, y0, y1, c):
        if x < 0 or x >= self.w:
            return
        y0 = max(0, y0)
        y1 = min(self.h - 1, y1)
        for y in range(y0, y1 + 1):
            i = 3 * (y * self.w + x)
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        x = 0
        y = r
        d = 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y),
                           (cx + x, cy - y), (cx - x, cy - y),
                           (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set(px, py, c)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def fill_circle(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
            self.hline(cx - dx, cx + dx, y, c)

    def fill_ellipse(self, cx, cy, rx, ry, c):
        for y in range(cy - ry, cy + ry + 1):
            t = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1 - t * t)))
            self.hline(cx - dx, cx + dx, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for a in range(360):
            t = math.radians(a)
            self.set(int(cx + rx * math.cos(t)), int(cy + ry * math.sin(t)), c)

    def poly(self, pts, c):
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            self.line(x0, y0, x1, y1, c)

    def fill_poly(self, pts, c):
        """Scanline polygon fill (non self-intersecting)."""
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(xs[i]), int(xs[i + 1]), y, c)

    def round_rect(self, x0, y0, x1, y1, r, c):
        self.fill_rect(x0 + r, y0, x1 - r, y1, c)
        self.fill_rect(x0, y0 + r, x1, y1 - r, c)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            self.fill_circle(cx, cy, r, c)

    def rect_outline(self, x0, y0, x1, y1, c, w=1):
        for t in range(w):
            self.hline(x0 + t, x1 - t, y0 + t, c)
            self.hline(x0 + t, x1 - t, y1 - t, c)
            self.vline(x0 + t, y0 + t, y1 - t, c)
            self.vline(x1 - t, y0 + t, y1 - t, c)

    def vgrad(self, x0, y0, x1, y1, top, bot):
        for y in range(y0, y1 + 1):
            t = (y - y0) / max(1, y1 - y0)
            c = tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3))
            self.hline(x0, x1, y, c)


def blit_rotated(dst, src, cx, cy, angle_deg, key=(255, 0, 255)):
    """Blit src canvas onto dst, rotated by angle_deg about (cx, cy).

    Pixels equal to `key` in src are transparent.
    """
    th = math.radians(angle_deg)
    cs, sn = math.cos(th), math.sin(th)
    hw, hh = src.w / 2.0, src.h / 2.0
    # bounding box of the rotated source
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    rc = [(x * cs - y * sn, x * sn + y * cs) for x, y in corners]
    xs = [p[0] for p in rc]
    ys = [p[1] for p in rc]
    x0, x1 = int(cx + min(xs)) - 1, int(cx + max(xs)) + 1
    y0, y1 = int(cy + min(ys)) - 1, int(cy + max(ys)) + 1
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx, dy = x - cx, y - cy
            sx = dx * cs + dy * sn + hw
            sy = -dx * sn + dy * cs + hh
            ix, iy = int(sx), int(sy)
            if 0 <= ix < src.w and 0 <= iy < src.h:
                c = src.get(ix, iy)
                if c != key:
                    dst.set(x, y, c)


# ---------------------------------------------------------------------- PNG
def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# --------------------------------------------------------------------- font
# 5x7 bitmap font. Each glyph is 7 rows; each row is a 5-bit mask, the
# leftmost pixel in the most significant bit.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ",": (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    "-": (0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "<": (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    ">": (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    '"': (0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "+": (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    "=": (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
    "*": (0x00, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0x00),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x06, 0x04, 0x00, 0x04),
    "%": (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    "#": (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    "\u2022": (0x00, 0x00, 0x0C, 0x1E, 0x1E, 0x0C, 0x00),
    "\u2014": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
}

BLANK = (0x00,) * 7


def text_w(s, scale, spacing=None):
    if spacing is None:
        spacing = scale
    return len(s) * (5 * scale + spacing) - spacing


def draw_text(cv, x, y, s, scale, color, spacing=None, bold=False):
    """Draw text at top-left (x, y). Returns width drawn."""
    if spacing is None:
        spacing = scale
    cx = x
    for ch in s:
        g = FONT.get(ch, BLANK)
        for row in range(7):
            bits = g[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 cx + col * scale + scale - 1,
                                 y + row * scale + scale - 1, color)
                    if bold:
                        cv.fill_rect(cx + col * scale + 1, y + row * scale,
                                     cx + col * scale + scale,
                                     y + row * scale + scale - 1, color)
        cx += 5 * scale + spacing
    return cx - x - spacing


def text_center(cv, cx, y, s, scale, color, spacing=None, bold=False):
    w = text_w(s, scale, spacing)
    return draw_text(cv, cx - w // 2, y, s, scale, color, spacing, bold)


def draw_rule(cv, x0, x1, y, color, w=2):
    for t in range(w):
        cv.hline(x0, x1, y + t, color)

# ------------------------------------------------------------- coat of arms
def draw_arms(cv, cx, top, s):
    """Talvera's arms: a shield with a rising sun over three waves,
    a star above, laurel sprigs at the sides. s = overall half-width."""
    # laurel sprigs: curved stems with diamond leaves hugging the shield
    for side in (-1, 1):
        stem = []
        for i in range(7):
            f = i / 6.0
            stem.append((cx + side * int(s * (1.5 - 0.35 * f)),
                         top + int(s * (1.3 - 1.2 * f))))
        for i in range(len(stem) - 1):
            cv.line(stem[i][0], stem[i][1],
                    stem[i + 1][0], stem[i + 1][1], TEAL)
        for sx, sy in stem:
            ox = side * 9
            cv.fill_poly([(sx + ox, sy), (sx + ox // 2, sy - 4),
                          (sx, sy), (sx + ox // 2, sy + 4)], TEAL)
    # shield outline
    pts = [(cx - s, top), (cx + s, top), (cx + s, top + int(s * 1.05)),
           (cx, top + int(s * 1.65)), (cx - s, top + int(s * 1.05))]
    cv.fill_poly(pts, NAVY)
    cv.poly(pts, GOLD)
    # sun: half-disc + rays above the waves
    sy = top + int(s * 0.62)
    cv.fill_circle(cx, sy, int(s * 0.34), GOLD_LT)
    for a in range(0, 360, 30):
        t = math.radians(a)
        x0 = cx + int(math.cos(t) * s * 0.42)
        y0 = sy + int(math.sin(t) * s * 0.42)
        x1 = cx + int(math.cos(t) * s * 0.58)
        y1 = sy + int(math.sin(t) * s * 0.58)
        cv.line(x0, y0, x1, y1, GOLD_LT)
    cv.fill_circle(cx, sy, int(s * 0.34), GOLD_LT)
    # waves: three gold arcs across the lower shield
    for k in range(3):
        wy = top + int(s * (0.95 + k * 0.16))
        for x in range(cx - s + 6, cx + s - 5):
            yy = wy + int(3 * math.sin((x - cx) / 9.0))
            cv.set(x, yy, GOLD_LT)
            cv.set(x, yy + 1, GOLD_LT)
    # star above the shield
    star_cy = top - int(s * 0.42)
    cv.fill_circle(cx, star_cy, 5, GOLD)
    for a in range(0, 360, 72):
        t = math.radians(a - 90)
        cv.line(cx, star_cy,
                cx + int(11 * math.cos(t)), star_cy + int(11 * math.sin(t)), GOLD)


# ------------------------------------------------------------------ portrait
def draw_portrait(cv, x0, y0, x1, y1):
    """Stylised flat portrait: a young woman, dark hair in a bun,
    against a pale studio backdrop, inside a framed photo box."""
    cv.vgrad(x0, y0, x1, y1, (207, 216, 224), (232, 238, 242))
    # faint backdrop arcs, kept inside the photo box
    for r in (52, 72, 92):
        cv.circle((x0 + x1) // 2, (y0 + y1) // 2, r, (196, 206, 216))
    cx = (x0 + x1) // 2
    # shoulders / jacket
    cv.fill_poly([(cx - 62, y1), (cx - 58, y1 - 52), (cx - 26, y1 - 66),
                  (cx + 26, y1 - 66), (cx + 58, y1 - 52), (cx + 62, y1)],
                 (58, 84, 120))
    # shirt collar
    cv.fill_poly([(cx - 14, y1 - 66), (cx, y1 - 48), (cx + 14, y1 - 66),
                  (cx + 8, y1 - 70), (cx, y1 - 64), (cx - 8, y1 - 70)], WHITE)
    # neck
    cv.fill_rect(cx - 11, y1 - 96, cx + 11, y1 - 62, SKIN_DK)
    # face
    cv.fill_ellipse(cx, y1 - 128, 34, 42, SKIN)
    # hair: mass over the top of the head, swept back
    cv.fill_ellipse(cx, y1 - 152, 36, 26, HAIR)
    cv.fill_poly([(cx - 36, y1 - 150), (cx - 38, y1 - 118),
                  (cx - 30, y1 - 132), (cx - 28, y1 - 158),
                  (cx + 28, y1 - 158), (cx + 30, y1 - 132),
                  (cx + 38, y1 - 118), (cx + 36, y1 - 150)], HAIR)
    # bun
    cv.fill_circle(cx, y1 - 172, 13, HAIR)
    # brows, eyes, nose, mouth: minimal, symmetric
    for side in (-1, 1):
        ex = cx + side * 14
        cv.fill_rect(ex - 6, y1 - 134, ex + 5, y1 - 132, HAIR)
        cv.fill_ellipse(ex, y1 - 126, 4, 3, (40, 30, 26))
    cv.line(cx, y1 - 122, cx - 2, y1 - 110, SKIN_DK)
    cv.line(cx - 2, y1 - 110, cx + 3, y1 - 110, SKIN_DK)
    cv.fill_ellipse(cx, y1 - 100, 7, 2, (150, 84, 70))
    # soft cheek shading
    cv.fill_ellipse(cx - 24, y1 - 112, 6, 4, (206, 152, 118))
    cv.fill_ellipse(cx + 24, y1 - 112, 6, 4, (206, 152, 118))
    # frame + corner ticks
    cv.rect_outline(x0, y0, x1, y1, INK, 2)
    for (tx, ty, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                             (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv.line(tx, ty + 10 * dy, tx, ty, GOLD)
        cv.line(tx + 10 * dx, ty, tx, ty, GOLD)


# -------------------------------------------------------------------- stamps
KEY = (255, 0, 255)


def stamp_circle(top, kind, date, code, color):
    """A circular border-control stamp, rendered on its own canvas."""
    d = 170
    cv = Canvas(d, d, KEY)
    cx = cy = d // 2
    cv.circle(cx, cy, 80, color)
    cv.circle(cx, cy, 74, color)
    cv.circle(cx, cy, 38, color)
    text_center(cv, cx, 24, top, 2, color, spacing=0)
    text_center(cv, cx, 52, kind, 3, color, bold=True)
    text_center(cv, cx, 90, date, 2, color, spacing=0, bold=True)
    text_center(cv, cx, 114, code, 1, color)
    cv.fill_circle(cx - 22, 132, 3, color)
    cv.fill_circle(cx + 22, 132, 3, color)
    return cv


def stamp_rect(lines, color, w=250, h=92):
    """A rectangular arrival / fee stamp on its own canvas."""
    cv = Canvas(w, h, KEY)
    cv.rect_outline(3, 3, w - 4, h - 4, color, 2)
    cv.rect_outline(8, 8, w - 9, h - 9, color, 1)
    y = 16
    for (s, sc, bold) in lines:
        text_center(cv, w // 2, y, s, sc, color, bold=bold)
        y += 7 * sc + 6
    return cv


# ----------------------------------------------------------------------- MRZ
MRZ_VAL = {}
for _i, _ch in enumerate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    MRZ_VAL[_ch] = _i
MRZ_VAL["<"] = 0


def mrz_check(s):
    total = 0
    for i, ch in enumerate(s):
        total += MRZ_VAL[ch] * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = ("P<TAL" + "MARLOW<<ELENA<VERA").ljust(44, "<")
    doc = "TA4839201"
    dob = "880314"
    exp = "310602"
    opt = "TALVERA" + "<" * 8  # optional data, 15 chars
    line2 = (doc + mrz_check(doc) + "TAL" + dob + mrz_check(dob) + "F"
             + exp + mrz_check(exp) + opt + mrz_check(doc + mrz_check(doc)
             + "TAL" + dob + mrz_check(dob) + "F" + exp + mrz_check(exp)
             + opt))
    assert len(line1) == 44 and len(line2) == 44, (len(line1), len(line2))
    return line1, line2


# ------------------------------------------------------------------ guilloche
def guilloche(cv, x0, y0, x1, y1):
    """Faint wavy security lines across a page."""
    for k in range(0, y1 - y0, 14):
        yb = y0 + k
        for x in range(x0, x1, 3):
            yy = yb + int(2.5 * math.sin((x - x0) / 26.0 + k))
            cv.set(x, yy, GUILLOCHE)

# --------------------------------------------------------------------- pages
def field(cv, x, y, label, value, vscale=2, width=250):
    draw_text(cv, x, y, label, 1, INK_SOFT)
    draw_text(cv, x, y + 11, value, vscale, INK, bold=True)
    return y + 11 + 7 * vscale + 10


def draw_left_page(cv):
    x0, x1 = 28, 500
    guilloche(cv, x0 + 8, 40, x1 - 8, 950)
    # coat of arms + title block
    draw_arms(cv, 264, 78, 42)
    text_center(cv, 264, 196, "REPUBLIC OF TALVERA", 3, INK, bold=True)
    text_center(cv, 264, 232, "PASSPORT", 4, INK, bold=True)
    text_center(cv, 264, 268, "PASSEPORT", 2, INK_SOFT)
    draw_rule(cv, 60, 468, 292, GOLD, 2)
    # portrait + data fields
    draw_portrait(cv, 52, 312, 202, 492)
    y = 312
    y = field(cv, 222, y, "SURNAME", "MARLOW")
    y = field(cv, 222, y, "GIVEN NAMES", "ELENA VERA")
    y = field(cv, 222, y, "NATIONALITY", "TALVERAN")
    y = field(cv, 222, y, "DATE OF BIRTH", "14 MAR 1988")
    # second row of fields under the portrait
    y2 = 516
    draw_text(cv, 52, y2, "PLACE OF BIRTH", 1, INK_SOFT)
    draw_text(cv, 52, y2 + 11, "PORT MERIDIAN", 2, INK, bold=True)
    draw_text(cv, 300, y2, "SEX", 1, INK_SOFT)
    draw_text(cv, 300, y2 + 11, "F", 2, INK, bold=True)
    draw_text(cv, 380, y2, "HEIGHT", 1, INK_SOFT)
    draw_text(cv, 380, y2 + 11, "168 CM", 2, INK, bold=True)
    draw_rule(cv, 52, 476, 566, INK_SOFT, 1)
    # document block
    y3 = 590
    draw_text(cv, 52, y3, "PASSPORT NO.", 1, INK_SOFT)
    draw_text(cv, 52, y3 + 11, "TA 4839201", 2, INK, bold=True)
    draw_text(cv, 300, y3, "DATE OF EXPIRY", 1, INK_SOFT)
    draw_text(cv, 300, y3 + 11, "02 JUN 2031", 2, INK, bold=True)
    y3 = 648
    draw_text(cv, 52, y3, "DATE OF ISSUE", 1, INK_SOFT)
    draw_text(cv, 52, y3 + 11, "02 JUN 2021", 2, INK, bold=True)
    draw_text(cv, 300, y3, "AUTHORITY", 1, INK_SOFT)
    draw_text(cv, 300, y3 + 11, "PORT MERIDIAN", 2, INK, bold=True)
    # holder's signature
    draw_text(cv, 52, 716, "HOLDER'S SIGNATURE", 1, INK_SOFT)
    sig = [(60, 750), (74, 736), (88, 754), (104, 740), (118, 756),
           (134, 738), (148, 750), (164, 744), (180, 756), (196, 740),
           (212, 752), (228, 736), (244, 752), (262, 746), (280, 754),
           (296, 742), (308, 750)]
    for i in range(len(sig) - 1):
        cv.line(sig[i][0], sig[i][1], sig[i + 1][0], sig[i + 1][1], (28, 52, 110))
        cv.line(sig[i][0], sig[i][1] + 1, sig[i + 1][0], sig[i + 1][1] + 1,
                (28, 52, 110))
    draw_rule(cv, 52, 320, 762, INK, 1)
    draw_text(cv, 52, 770, "ELENA VERA MARLOW", 1, INK_SOFT)
    # machine-readable zone
    draw_rule(cv, 52, 476, 806, INK, 1)
    l1, l2 = mrz_lines()
    draw_text(cv, 52, 824, l1, 2, INK, spacing=0)
    draw_text(cv, 52, 846, l2, 2, INK, spacing=0)
    draw_rule(cv, 52, 476, 880, INK, 1)
    text_center(cv, 264, 896, "TALVERA  \u2022  PORT MERIDIAN  \u2022  EST. 1962",
                1, INK_SOFT)


def draw_visa_sticker(cv, x0, y0, x1, y1):
    cv.round_rect(x0, y0, x1, y1, 10, TEAL)
    cv.rect_outline(x0 + 6, y0 + 6, x1 - 6, y1 - 6, GOLD_LT, 2)
    # small star + sun motif top-left
    cv.fill_circle(x0 + 34, y0 + 34, 12, GOLD_LT)
    for a in range(0, 360, 45):
        t = math.radians(a)
        cv.line(x0 + 34, y0 + 34,
                x0 + 34 + int(18 * math.cos(t)),
                y0 + 34 + int(18 * math.sin(t)), GOLD_LT)
    cv.fill_circle(x0 + 34, y0 + 34, 12, GOLD_LT)
    text_center(cv, (x0 + x1) // 2 + 14, y0 + 16, "VISA", 4, WHITE, bold=True)
    text_center(cv, (x0 + x1) // 2, y0 + 56, "KINGDOM OF NORDHAVEN", 2,
                (232, 240, 232), bold=True)
    draw_rule(cv, x0 + 24, x1 - 24, y0 + 84, GOLD_LT, 1)
    rows = [("TYPE", "MULTIPLE ENTRY"),
            ("VALID", "01 AUG 2021 - 01 AUG 2022"),
            ("STAY", "90 DAYS IN ANY 180"),
            ("FEE", "25 TALERS - PAID")]
    y = y0 + 96
    for label, val in rows:
        draw_text(cv, x0 + 24, y, label, 1, (190, 214, 204))
        draw_text(cv, x0 + 84, y, val, 2, WHITE, bold=True)
        y += 22
    text_center(cv, (x0 + x1) // 2, y1 - 20,
                "ISSUED IN PORT MERIDIAN  \u2022  NV-884120",
                1, (190, 214, 204))


def draw_right_page(cv):
    x0, x1 = 524, 996
    guilloche(cv, x0 + 8, 40, x1 - 8, 950)
    text_center(cv, 760, 56, "VISAS", 4, INK, bold=True)
    text_center(cv, 760, 92, "VISA  \u2022  ENTRY AND EXIT STAMPS", 1, INK_SOFT)
    draw_rule(cv, 556, 964, 112, GOLD, 2)
    draw_visa_sticker(cv, 556, 128, 964, 330)
    # border-control stamps, each slightly rotated like a real hand stamp
    blit_rotated(cv, stamp_circle("NORDHAVEN", "ENTRY", "17 AUG 2021",
                                  "N-441", BLUE), 648, 440, -12)
    blit_rotated(cv, stamp_circle("NORDHAVEN", "EXIT", "02 SEP 2021",
                                  "N-902", BLUE), 880, 446, 9)
    blit_rotated(cv, stamp_rect([("ZEPHYRIA", 2, True),
                                 ("ARRIVAL 11 JAN 2023", 2, False),
                                 ("PORT OF ZEPHYR", 1, False)], RED),
                 672, 595, -6)
    blit_rotated(cv, stamp_circle("CORMORANT", "ENTRY", "05 MAY 2024",
                                  "C-118", GREEN), 888, 692, 14)
    blit_rotated(cv, stamp_rect([("ISLAND HOPPER FEE PAID", 2, True),
                                 ("25 TALERS - 03 SEP 2021", 2, False)],
                                RED, w=300, h=80), 688, 800, 5)
    # the telling detail: conditions of stay, printed small
    draw_rule(cv, 556, 964, 872, INK_SOFT, 1)
    text_center(cv, 760, 888, "CONDITIONS OF STAY", 2, INK, bold=True)
    for i, ln in enumerate((
            "HOLDER MAY REMAIN 90 DAYS IN ANY 180.",
            "EMPLOYMENT IS PROHIBITED WITHOUT A",
            "WORK PERMIT ISSUED IN PORT MERIDIAN.",
            "NOT VALID FOR THE NORTHERN REACHES.")):
        text_center(cv, 760, 914 + i * 18, ln, 1, INK_SOFT)


# ---------------------------------------------------------------------- main
def build():
    cv = Canvas(W, H, PAPER)
    # book frame + centre gutter
    cv.rect_outline(8, 8, W - 9, H - 9, NAVY, 4)
    cv.rect_outline(16, 16, W - 17, H - 17, GOLD, 1)
    cv.fill_rect(508, 20, 516, H - 21, (120, 104, 74))
    cv.fill_rect(500, 20, 507, H - 21, (200, 186, 152))
    cv.fill_rect(517, 20, 524, H - 21, (200, 186, 152))
    draw_left_page(cv)
    draw_right_page(cv)
    return cv


def main():
    out_dir = OUT
    os.makedirs(out_dir, exist_ok=True)
    # Clear only the contents of the output directory (it may be a mount).
    for name in os.listdir(out_dir):
        p = os.path.join(out_dir, name)
        if os.path.isfile(p):
            os.remove(p)
    cv = build()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(cv, path)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
