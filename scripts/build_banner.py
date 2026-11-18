"""Generate the profile banner: a pixel-art sakura scene, day and night.

    python scripts/build_banner.py

Pure Python, no dependencies. The scene is painted on a 300x105 pixel grid, then
written as SVG rects (one path per colour, horizontal runs merged) and shown at
4x with crisp edges. Petals, stars and water glints animate in CSS with
steps() so they move on the pixel grid; prefers-reduced-motion freezes them.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
W, H = 300, 105
SCALE = 4
HORIZON = 80
BANK = 95

RGB = tuple[int, int, int]

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def hx(c: str) -> RGB:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def dither(x: int, y: int, f: float) -> bool:
    return f > (BAYER[y % 4][x % 4] + 0.5) / 16


# ── noise ──────────────────────────────────────────────────────────────────


def _hash(x: int, y: int, seed: int) -> float:
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF


def noise(x: float, y: float, seed: int = 0) -> float:
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a, b = _hash(xi, yi, seed), _hash(xi + 1, yi, seed)
    c, d = _hash(xi, yi + 1, seed), _hash(xi + 1, yi + 1, seed)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm(x: float, y: float, seed: int = 0, octaves: int = 3) -> float:
    s, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        s += amp * noise(x * 2**o, y * 2**o, seed + o * 17)
        norm += amp
        amp *= 0.5
    return s / norm


# ── themes ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Theme:
    name: str
    sky: tuple[str, ...]  # zenith → horizon
    fuji: str
    fuji_shade: str
    snow: str
    snow_shade: str
    far: str
    far_top: str
    mid: str
    pagoda: str
    pagoda_roof: str
    window: str | None
    water: str
    glint: str
    ground: str
    grass: str
    grass_dark: str
    bark: str
    bark_hi: str
    bark_dark: str
    bloom: tuple[str, str, str, str, str]  # highlight → deep outline
    lantern: str
    lantern_dark: str
    lantern_light: str | None
    moon: str | None
    moon_shade: str | None
    star: str | None
    cloud: str | None
    cloud_shade: str | None
    title: tuple[str, str]
    outline: str
    subtitle: str


NIGHT = Theme(
    name="dark",
    sky=("#0a0c22", "#11163a", "#1b2150", "#2a2a66", "#3f3478", "#5d3f86", "#874c8d", "#b0608f"),
    fuji="#2c3064",
    fuji_shade="#232653",
    snow="#c6cbeb",
    snow_shade="#8f96cc",
    far="#1c2048",
    far_top="#171a3c",
    mid="#121530",
    pagoda="#0d0f26",
    pagoda_roof="#090a1c",
    window="#ffcc66",
    water="#151a40",
    glint="#a9a6e8",
    ground="#0e1426",
    grass="#1a2a3a",
    grass_dark="#0a0f1d",
    bark="#2a1d33",
    bark_hi="#44304d",
    bark_dark="#160f1e",
    bloom=("#ffd9ea", "#f6a9c9", "#de7fad", "#a4558f", "#5a2c62"),
    lantern="#3a3a52",
    lantern_dark="#22223a",
    lantern_light="#ffcc66",
    moon="#fff1cc",
    moon_shade="#e3cf98",
    star="#f4f0ff",
    cloud=None,
    cloud_shade=None,
    title=("#fff6ec", "#ffc7dc"),
    outline="#0a0c22",
    subtitle="#ffc7dc",
)

DAY = Theme(
    name="light",
    sky=("#3f7cc9", "#4f8bd2", "#649cda", "#7daee2", "#9bc1e9", "#bcd5ef", "#dce4f1", "#f6e3ea"),
    fuji="#7189bd",
    fuji_shade="#5f75a8",
    snow="#f6f8fd",
    snow_shade="#cbd6ee",
    far="#6b9a96",
    far_top="#5b8a86",
    mid="#4f7d63",
    pagoda="#b9473c",
    pagoda_roof="#3d3546",
    window=None,
    water="#6f9fd6",
    glint="#ffffff",
    ground="#4f7d3c",
    grass="#78a84e",
    grass_dark="#3a6230",
    bark="#5a3a30",
    bark_hi="#7d5444",
    bark_dark="#3a241f",
    bloom=("#fff0f5", "#ffc6da", "#f99bbc", "#df6f9b", "#a84a7a"),
    lantern="#a7a39c",
    lantern_dark="#76736e",
    lantern_light=None,
    moon=None,
    moon_shade=None,
    star=None,
    cloud="#ffffff",
    cloud_shade="#dbe6f5",
    title=("#ffffff", "#ffe2ec"),
    outline="#2b2347",
    subtitle="#2b2347",
)


# ── font ───────────────────────────────────────────────────────────────────

GLYPHS = {
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####"],
    "c": [".....", ".....", ".###.", "#....", "#....", "#....", ".###."],
    "d": ["....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".###."],
    "f": ["..##.", ".#...", "####.", ".#...", ".#...", ".#...", ".#..."],
    "h": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "i": ["..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."],
    "t": ["..#..", "..#..", "#####", "..#..", "..#..", "..#..", "...##"],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    " ": ["....."] * 7,
}


def text_pixels(s: str, scale: int) -> list[tuple[int, int, int]]:
    """(x, y, row) for every lit pixel, row = glyph row 0..6."""
    out = []
    for i, ch in enumerate(s):
        g = GLYPHS[ch]
        for r, line in enumerate(g):
            for c, bit in enumerate(line):
                if bit == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            out.append((i * 6 * scale + c * scale + dx, r * scale + dy, r))
    return out


# ── painting ───────────────────────────────────────────────────────────────


class Canvas:
    def __init__(self) -> None:
        self.px: list[list[RGB]] = [[(0, 0, 0)] * W for _ in range(H)]

    def set(self, x: int, y: int, c: RGB) -> None:
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def get(self, x: int, y: int) -> RGB:
        return self.px[y][x]


def paint_sky(cv: Canvas, th: Theme) -> None:
    ramp = [hx(c) for c in th.sky]
    n = len(ramp) - 1
    for y in range(HORIZON):
        t = (y / (HORIZON - 1)) ** 1.15 * n
        i = min(int(t), n - 1)
        f = t - i
        for x in range(W):
            cv.set(x, y, ramp[i + 1] if dither(x, y, f) else ramp[i])


def paint_stars(cv: Canvas, th: Theme, rng: random.Random) -> list[tuple[int, int]]:
    if not th.star:
        return []
    star = hx(th.star)
    dim = mix(star, hx(th.sky[1]), 0.55)
    twinkle = []
    for _ in range(70):
        x, y = rng.randrange(W), rng.randrange(0, 52)
        cv.set(x, y, dim if rng.random() < 0.6 else star)
    for _ in range(9):
        x, y = rng.randrange(W), rng.randrange(0, 40)
        twinkle.append((x, y))
    return twinkle


def paint_moon(cv: Canvas, th: Theme) -> None:
    if not th.moon:
        return
    cx, cy, r = 150, 16, 8.5
    lit, shade = hx(th.moon), hx(th.moon_shade)
    halo = [mix(hx(th.sky[1]), lit, 0.18), mix(hx(th.sky[1]), lit, 0.09)]
    for y in range(int(cy - r - 6), int(cy + r + 7)):
        for x in range(int(cx - r - 6), int(cx + r + 7)):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                c = lit
                if math.hypot(x - cx - 3, y - cy + 2) < 2.2 or math.hypot(x - cx + 2, y - cy - 3) < 1.6 or math.hypot(x - cx + 4, y - cy + 1) < 1.1:
                    c = shade
                if (x - cx) + (y - cy) > r * 0.9:
                    c = shade
                cv.set(x, y, c)
            elif d <= r + 2.5 and dither(x, y, 0.5):
                cv.set(x, y, mix(cv.get(x, y), halo[0], 0.7))
            elif d <= r + 5 and dither(x, y, 0.25):
                cv.set(x, y, mix(cv.get(x, y), halo[1], 0.7))


def paint_clouds(cv: Canvas, th: Theme) -> None:
    if not th.cloud:
        return
    hi, sh = hx(th.cloud), hx(th.cloud_shade)
    for cx, cy, w, h in ((44, 16, 30, 7), (152, 8, 22, 5), (236, 22, 26, 6), (112, 32, 14, 4)):
        for y in range(cy - h - 4, cy + 3):
            for x in range(cx - w, cx + w):
                dx = (x - cx) / w
                lumps = 2.5 * abs(math.sin(x * 0.32 + cx)) + 1.5 * fbm(x * 0.2, 0, seed=cx)
                top = cy - h * (1 - dx * dx) ** 0.5 - lumps * (1 - dx * dx)
                if top <= y <= cy + 1:
                    under = y >= cy or (y == cy - 1 and dither(x, y, 0.5))
                    rim = y < top + 1 and dx < 0
                    cv.set(x, y, sh if under else hi if not rim else mix(hi, sh, 0.25))


def paint_fuji(cv: Canvas, th: Theme) -> None:
    peak_x, peak_y, base = 196, 34, HORIZON
    body, shade, snow, snow_s = hx(th.fuji), hx(th.fuji_shade), hx(th.snow), hx(th.snow_shade)
    for y in range(peak_y, base):
        t = (y - peak_y) / (base - peak_y)
        hw = 4 + 82 * t**1.55
        crater = y == peak_y
        snowline = peak_y + 17 + 6 * fbm(0, y * 0.2, 3)
        for x in range(int(peak_x - hw), int(peak_x + hw) + 1):
            if crater and abs(x - peak_x) < 2:
                continue
            right = x > peak_x + (y - peak_y) * 0.15
            # snow runs down the gullies in streaks, shorter on the far side
            line = snowline + 6 * fbm(x * 0.3, 0, 5) + (4 if (x // 2) % 3 == 0 else 0) - (3 if right else 0)
            if y < line:
                c = snow_s if right else snow
            else:
                c = shade if right else body
            cv.set(x, y, c)


def paint_far_hills(cv: Canvas, th: Theme) -> None:
    far, top = hx(th.far), hx(th.far_top)
    for x in range(W):
        ridge = 71 + 5 * fbm(x * 0.03, 1, 11) - 3 * math.exp(-((x - 40) / 30) ** 2)
        crown = ridge - 2 * (fbm(x * 0.5, 2, 12) > 0.55)
        for y in range(int(crown), HORIZON):
            cv.set(x, y, top if y < ridge else far)
    mid = hx(th.mid)
    for x in range(112, 196):
        h = 7 * math.sin(math.pi * (x - 112) / 84) ** 0.7
        for y in range(int(HORIZON - h), HORIZON):
            cv.set(x, y, mid)


def paint_pagoda(cv: Canvas, th: Theme) -> list[tuple[int, int]]:
    body, roof = hx(th.pagoda), hx(th.pagoda_roof)
    win = hx(th.window) if th.window else None
    cx, base = 160, 75
    lit = []
    tier_h, tiers = 3, 5
    y = base
    for k in range(tiers):
        w = 6 - k
        for yy in range(y - tier_h + 1, y + 1):
            for x in range(cx - w + 1, cx + w):
                cv.set(x, yy, body)
        if win and k < 4:
            cv.set(cx, y - 1, win)
            lit.append((cx, y - 1))
        rw = w + 3
        ry = y - tier_h
        for x in range(cx - rw, cx + rw + 1):
            cv.set(x, ry, roof)
        cv.set(cx - rw - 1, ry - 1, roof)
        cv.set(cx + rw + 1, ry - 1, roof)
        y = ry - 1
    for yy in range(y - 5, y + 1):
        cv.set(cx, yy, roof)
    return lit


def paint_water(cv: Canvas, th: Theme, rng: random.Random) -> list[tuple[int, int, int]]:
    water = hx(th.water)
    for y in range(HORIZON, BANK):
        depth = (y - HORIZON) / (BANK - HORIZON)
        sy = HORIZON - 1 - (y - HORIZON) * 2
        wob = round(math.sin(y * 1.9) * 1.2)
        for x in range(W):
            src = cv.get(min(max(x + wob, 0), W - 1), max(sy, 0))
            c = mix(src, water, 0.45 + 0.35 * depth)
            if (y - HORIZON) % 3 == 2 and dither(x, y, 0.35):
                c = mix(c, water, 0.5)
            cv.set(x, y, c)
    glints = []
    g = hx(th.glint)
    for _ in range(26):
        x, y, w = rng.randrange(0, W - 8), rng.randrange(HORIZON + 1, BANK - 1), rng.randrange(2, 7)
        for i in range(w):
            cv.set(x + i, y, mix(cv.get(x + i, y), g, 0.45))
    for _ in range(14):
        glints.append((rng.randrange(0, W - 8), rng.randrange(HORIZON + 1, BANK - 1), rng.randrange(2, 6)))
    if th.moon:  # moon path on the water
        for y in range(HORIZON + 1, BANK):
            row = y - HORIZON
            if row % 2:
                continue
            hw = 1 + row * 0.35 + 1.5 * _hash(0, y, 61)
            off = round(math.sin(y * 2.3) * 1.5)
            for x in range(round(150 + off - hw), round(150 + off + hw) + 1):
                cv.set(x, y, mix(cv.get(x, y), hx(th.moon), 0.55))
    return glints


def paint_bank(cv: Canvas, th: Theme, rng: random.Random) -> None:
    ground, grass, dark = hx(th.ground), hx(th.grass), hx(th.grass_dark)
    for x in range(W):
        top = BANK - round(1.5 * fbm(x * 0.08, 3, 21)) - (2 if x > 205 else 0) - max(0, (x - 225) // 18)
        for y in range(top, H):
            c = grass if y < top + 2 else (dark if dither(x, y, (y - top) / (H - top) * 0.9) else ground)
            cv.set(x, y, c)
        if rng.random() < 0.35:
            cv.set(x, top - 1, grass)
        if rng.random() < 0.12:
            cv.set(x, top - 1, grass)
            cv.set(x, top - 2, grass)


def disc(cv: Canvas, cx: float, cy: float, r: float, colors: tuple[RGB, RGB, RGB]) -> None:
    hi, mid, dark = colors
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx = x - cx
            if math.hypot(dx, y - cy) <= r:
                s = dx / max(r, 0.5)
                cv.set(x, y, hi if s < -0.35 else dark if s > 0.45 else mid)


def bez(p, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    u = 1 - t
    return (
        u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
        u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3,
    )


TREE = [  # (bezier, r0, r1)
    (((266, 106), (268, 88), (258, 74), (252, 58)), 6.5, 4.2),
    (((252, 60), (240, 44), (222, 34), (196, 26)), 4.0, 1.6),
    (((254, 62), (262, 46), (278, 36), (302, 30)), 3.6, 1.8),
    (((246, 52), (236, 30), (240, 18), (236, 4)), 2.6, 1.2),
    (((222, 36), (212, 44), (204, 50), (192, 52)), 1.8, 0.8),
    (((268, 42), (276, 54), (286, 60), (298, 66)), 1.8, 0.8),
    (((205, 29), (190, 20), (180, 18), (170, 16)), 1.4, 0.7),
]

CANOPY = [  # (cx, cy, rx, ry)
    (196, 22, 16, 9), (178, 18, 11, 7), (220, 18, 15, 10), (238, 8, 16, 9),
    (258, 22, 16, 11), (282, 26, 18, 10), (300, 18, 14, 12), (262, 4, 16, 7),
    (206, 44, 11, 6), (192, 50, 7, 5), (286, 56, 9, 6), (298, 64, 6, 6),
    (230, 34, 10, 6), (272, 40, 9, 6), (212, 6, 12, 6),
]


def paint_tree(cv: Canvas, th: Theme) -> set[tuple[int, int]]:
    bark = (hx(th.bark_hi), hx(th.bark), hx(th.bark_dark))
    for p, r0, r1 in TREE:
        for i in range(60):
            t = i / 59
            x, y = bez(p, t)
            disc(cv, x, y, r0 + (r1 - r0) * t, bark)
    # canopy mask
    mask: set[tuple[int, int]] = set()
    for cx, cy, rx, ry in CANOPY:
        for y in range(int(cy - ry - 3), int(cy + ry + 4)):
            for x in range(int(cx - rx - 3), int(cx + rx + 4)):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d < 0.75 + 0.6 * fbm(x * 0.22, y * 0.22, 31):
                    if 0 <= x < W and 0 <= y < H:
                        mask.add((x, y))
    hi, base, mid, shadow, deep = (hx(c) for c in th.bloom)
    for (x, y) in mask:
        # light from upper left: compare against the blob above-left
        lit = sum((x + dx, y + dy) in mask for dx, dy in ((-2, -2), (-3, -1), (-1, -3)))
        under = sum((x + dx, y + dy) in mask for dx, dy in ((2, 2), (1, 3), (3, 1)))
        n = fbm(x * 0.28, y * 0.28, 41)
        if (x + 1, y + 1) not in mask or (x, y + 1) not in mask:
            c = deep if under < 2 else shadow
        elif lit < 2:
            c = hi if n > 0.45 or dither(x, y, 0.5) else base
        elif under < 3:
            c = shadow if dither(x, y, 0.6) else mid
        else:
            c = base if n > 0.52 else mid
            if n > 0.68:
                c = hi
        cv.set(x, y, c)
    # branch tips poke through, dark knots between blossoms
    for (x, y) in mask:
        if _hash(x, y, 77) > 0.994:
            cv.set(x, y, hx(th.bark))
    return mask


def paint_lantern(cv: Canvas, th: Theme) -> None:
    stone, dark = hx(th.lantern), hx(th.lantern_dark)
    x0, base = 232, 96
    rows = [  # (y offset from base, half width)
        (0, 4), (-1, 3), (-2, 1), (-3, 1), (-4, 1), (-5, 3), (-6, 3), (-7, 3), (-8, 3), (-9, 5), (-10, 4), (-11, 2), (-12, 1),
    ]
    for dy, hw in rows:
        for x in range(x0 - hw, x0 + hw + 1):
            cv.set(x, base + dy, dark if x > x0 + hw // 2 else stone)
    light = hx(th.lantern_light) if th.lantern_light else dark
    for dy in (-6, -7):
        for dx in (-1, 0, 1):
            cv.set(x0 + dx, base + dy, light)
    if th.lantern_light:
        for y in range(base - 15, base + 3):
            for x in range(x0 - 10, x0 + 11):
                d = math.hypot(x - x0, (y - base + 6.5) * 1.2)
                if 2.5 < d < 9 and dither(x, y, 0.45 * (1 - d / 9)):
                    cv.set(x, y, mix(cv.get(x, y), light, 0.35))


def paint_fallen(cv: Canvas, th: Theme, rng: random.Random) -> None:
    cols = [hx(th.bloom[1]), hx(th.bloom[0]), hx(th.bloom[2])]
    for _ in range(90):
        x = int(rng.triangular(160, W, 270))
        y = rng.randrange(BANK, H)
        cv.set(x, y, rng.choice(cols))


def paint_title(cv: Canvas, th: Theme) -> None:
    outline, shadow = hx(th.outline), hx(th.outline)
    top, bottom = (hx(c) for c in th.title)
    for s, scale, ox, oy, fill_fn in (
        ("naterminch", 2, 16, 28, lambda r: top if r < 4 else bottom),
        ("code for coffee & tea", 1, 18, 50, None),
    ):
        pix = text_pixels(s, scale)
        lit = {(ox + x, oy + y) for x, y, _ in pix}
        if fill_fn:  # chunky outline + 1px drop shadow
            for x, y in lit:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1, 2):
                        if (x + dx, y + dy) not in lit:
                            cv.set(x + dx, y + dy, shadow if dy == 2 else outline)
            for x, y, r in pix:
                cv.set(ox + x, oy + y, fill_fn(r))
        else:
            sub = hx(th.subtitle)
            halo = hx(th.outline if th.name == "dark" else th.title[0])
            for x, y in lit:
                for dx, dy in ((1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
                    if (x + dx, y + dy) not in lit:
                        cv.set(x + dx, y + dy, halo)
            for x, y in lit:
                cv.set(x, y, sub)


# ── output ─────────────────────────────────────────────────────────────────


def runs(cv: Canvas) -> dict[RGB, list[tuple[int, int, int]]]:
    out: dict[RGB, list[tuple[int, int, int]]] = {}
    for y in range(H):
        row = cv.px[y]
        x = 0
        while x < W:
            c = row[x]
            s = x
            while x < W and row[x] == c:
                x += 1
            out.setdefault(c, []).append((s, y, x - s))
    return out


def hexc(c: RGB) -> str:
    return "#%02x%02x%02x" % c


CSS = """
.f{animation-name:fall;animation-iteration-count:infinite}
@keyframes fall{from{transform:translate(0,0)}to{transform:translate(var(--x),var(--y))}}
.tw{animation:tw 3.2s steps(1) infinite}
@keyframes tw{0%,100%{opacity:1}50%{opacity:.15}}
.gl{animation:gl 2.4s steps(1) infinite}
@keyframes gl{0%,100%{opacity:0}40%,70%{opacity:.85}}
.wn{animation:wn 4s steps(1) infinite}
@keyframes wn{0%,100%{opacity:1}48%{opacity:.55}}
@media (prefers-reduced-motion:reduce){.f,.tw,.gl,.wn{animation:none}.gl{opacity:0}}
"""


def build(th: Theme, seed: int = 9) -> str:
    rng = random.Random(seed)
    cv = Canvas()
    paint_sky(cv, th)
    twinkle = paint_stars(cv, th, rng)
    paint_moon(cv, th)
    paint_clouds(cv, th)
    paint_fuji(cv, th)
    paint_far_hills(cv, th)
    windows = paint_pagoda(cv, th)
    glints = paint_water(cv, th, rng)
    paint_bank(cv, th, rng)
    paint_lantern(cv, th)
    paint_fallen(cv, th, rng)
    mask = paint_tree(cv, th)
    paint_title(cv, th)

    body = []
    for c, rs in sorted(runs(cv).items(), key=lambda kv: -len(kv[1])):
        d = "".join(f"M{x} {y}h{w}v1h-{w}z" for x, y, w in rs)
        body.append(f'<path fill="{hexc(c)}" d="{d}"/>')

    anim = []
    if th.star:
        for x, y in twinkle:
            anim.append(f'<rect class="tw" x="{x}" y="{y}" width="1" height="1" fill="{th.star}" style="animation-delay:-{rng.uniform(0,3.2):.1f}s"/>')
            anim.append(f'<path class="tw" d="M{x-1} {y}h3v1h-3zM{x} {y-1}h1v3h-1z" fill="{th.star}" opacity=".5" style="animation-delay:-{rng.uniform(0,3.2):.1f}s"/>')
    for x, y in windows:
        anim.append(f'<rect class="wn" x="{x}" y="{y}" width="1" height="1" fill="{th.window}" style="animation-delay:-{rng.uniform(0,4):.1f}s"/>')
    for x, y, w in glints:
        anim.append(f'<rect class="gl" x="{x}" y="{y}" width="{w}" height="1" fill="{th.glint}" style="animation-delay:-{rng.uniform(0,2.4):.1f}s"/>')

    # petals fall from the canopy, drifting left with the breeze
    spawn = sorted(p for p in mask if p[1] > 10)
    petal_cols = th.bloom[:3]
    for i in range(22):
        sx, sy = rng.choice(spawn)
        dist_x = -rng.randint(70, 170)
        dist_y = rng.randint(55, 90)
        dur = rng.uniform(9, 16)
        steps = int(max(abs(dist_x), dist_y) / 1)  # one grid pixel per step
        c = rng.choice(petal_cols)
        shape = rng.choice([f"M{sx} {sy}h2v1h-2z", f"M{sx} {sy}h1v1h-1zM{sx+1} {sy+1}h1v1h-1z", f"M{sx} {sy}h1v2h-1z"])
        anim.append(
            f'<path class="f" d="{shape}" fill="{c}" style="--x:{dist_x}px;--y:{dist_y}px;'
            f'animation-timing-function:steps({steps});animation-duration:{dur:.1f}s;animation-delay:-{rng.uniform(0, dur):.1f}s"/>'
        )

    label = "naterminch: code for coffee &amp; tea. Pixel-art cherry blossoms by a lake under Mount Fuji."
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*SCALE}" height="{H*SCALE}" viewBox="0 0 {W} {H}" '
        f'shape-rendering="crispEdges" role="img" aria-label="{label}"><title>{label}</title>'
        f'<style>{CSS}</style><clipPath id="c"><rect width="{W}" height="{H}"/></clipPath>'
        f'<g clip-path="url(#c)">{"".join(body)}{"".join(anim)}</g></svg>\n'
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for th in (DAY, NIGHT):
        p = OUT / f"banner-{th.name}.svg"
        p.write_text(build(th), encoding="utf-8")
        print(f"{p.relative_to(ROOT)}  {p.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
