"""Built-in shortcut thumbnail themes (stdlib PNG, no Pillow).

Icons are solid accent-color tiles with bold white glyphs so they stay
recognizable on a crowded Windows desktop at ~32–48 px.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


@dataclass(frozen=True)
class IconTheme:
    id: str
    label: str


THEMES: tuple[IconTheme, ...] = (
    IconTheme("office", "OA"),
    IconTheme("chart", "Chart"),
    IconTheme("tool", "Tool"),
    IconTheme("lab", "Lab"),
    IconTheme("bolt", "Bolt"),
    IconTheme("box", "Box"),
    IconTheme("nodes", "Nodes"),
    IconTheme("rocket", "Rocket"),
)

PALETTE: tuple[tuple[str, str], ...] = (
    ("#2f7d62", "フォレスト"),
    ("#3b6ea5", "ブルー"),
    ("#c47b2b", "アンバー"),
    ("#8b4d6b", "ローズ"),
    ("#4a5568", "スレート"),
    ("#2c7a7b", "ティール"),
)


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def _hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _blend(fg: tuple[int, int, int], bg: tuple[int, int, int], a: float) -> tuple[int, int, int]:
    return tuple(int(f * a + b * (1 - a)) for f, b in zip(fg, bg, strict=True))  # type: ignore[return-value]


def _encode_png(pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend((r, g, b, a))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def _blank(size: int, bg: tuple[int, int, int]) -> list[list[tuple[int, int, int, int]]]:
    return [[(*bg, 255) for _ in range(size)] for _ in range(size)]


def _fill(
    px: list[list[tuple[int, int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
    alpha: int = 255,
) -> None:
    h, w = len(px), len(px[0])
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            px[y][x] = (*color, alpha)


def _circle(
    px: list[list[tuple[int, int, int, int]]],
    cx: int,
    cy: int,
    radius: int,
    color: tuple[int, int, int],
    *,
    ring: int | None = None,
) -> None:
    h, w = len(px), len(px[0])
    r2 = radius * radius
    inner = (radius - ring) ** 2 if ring else None
    for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d <= r2 and (inner is None or d >= inner):
                px[y][x] = (*color, 255)


def _poly(
    px: list[list[tuple[int, int, int, int]]],
    points: list[tuple[int, int]],
    color: tuple[int, int, int],
) -> None:
    """Filled polygon via horizontal scanlines."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    min_y = max(0, min(ys))
    max_y = min(len(px) - 1, max(ys))
    n = len(points)
    for y in range(min_y, max_y + 1):
        xs: list[float] = []
        for i in range(n):
            ax, ay = points[i]
            bx, by = points[(i + 1) % n]
            if ay == by:
                continue
            if (ay <= y < by) or (by <= y < ay):
                t = (y - ay) / (by - ay)
                xs.append(ax + t * (bx - ax))
        if len(xs) < 2:
            continue
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            _fill(px, int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, color)


def _round_corners(
    px: list[list[tuple[int, int, int, int]]],
    radius: int,
    outside: tuple[int, int, int],
) -> None:
    """Cut square corners so the tile reads as a rounded app icon."""
    h = len(px)
    w = len(px[0]) if h else 0
    r2 = radius * radius
    corners = (
        (radius, radius),
        (w - 1 - radius, radius),
        (radius, h - 1 - radius),
        (w - 1 - radius, h - 1 - radius),
    )
    for cx, cy in corners:
        for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
                in_tl = x <= cx and y <= cy and cx == radius and cy == radius
                in_tr = x >= cx and y <= cy and cx == w - 1 - radius and cy == radius
                in_bl = x <= cx and y >= cy and cx == radius and cy == h - 1 - radius
                in_br = x >= cx and y >= cy and cx == w - 1 - radius and cy == h - 1 - radius
                if not (in_tl or in_tr or in_bl or in_br):
                    continue
                if (x - cx) ** 2 + (y - cy) ** 2 > r2:
                    px[y][x] = (*outside, 255)


def render_theme_png(
    theme_id: str,
    accent: str = "#2f7d62",
    accent2: str | None = None,
    *,
    size: int = 128,
) -> bytes:
    """Return PNG bytes for a built-in two-tone theme.

    Drawing coordinates are authored for a 128px canvas and scaled to `size`.
    ``accent`` colors the tile; ``accent2`` colors the glyph. When omitted the
    glyph stays white for backward compatibility and maximum contrast.
    """
    accent_rgb = _hex_rgb(accent)
    glyph_rgb = _hex_rgb(accent2) if accent2 else (255, 255, 255)
    # Solid tile — high contrast against any desktop wallpaper
    deep = _blend(accent_rgb, (10, 14, 12), 0.35)
    mid = accent_rgb
    light = _blend(accent_rgb, (255, 255, 255), 0.55)
    white = glyph_rgb
    soft = _blend(glyph_rgb, accent_rgb, 0.72)

    # Outside of rounded corners: near-white so preview cards stay clean
    outside = (244, 247, 245)
    px = _blank(size, mid)

    def s(v: int) -> int:
        return max(1, int(round(v * size / 128)))

    def fill(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        _fill(px, s(x0), s(y0), s(x1), s(y1), color)

    def circle(cx: int, cy: int, radius: int, color: tuple[int, int, int], *, ring: int | None = None) -> None:
        _circle(px, s(cx), s(cy), s(radius), color, ring=None if ring is None else max(1, s(ring)))

    def poly(points: list[tuple[int, int]], color: tuple[int, int, int]) -> None:
        _poly(px, [(s(x), s(y)) for x, y in points], color)

    # Soft top highlight strip for a bit of depth
    fill(0, 0, 128, 10, light)

    if theme_id == "office":
        # Document with folded corner + thick text lines
        fill(30, 18, 98, 112, white)
        poly([(78, 18), (98, 18), (98, 38)], soft)
        fill(78, 18, 98, 38, mid)
        for y in (48, 62, 76, 90):
            fill(42, y, 86, y + 7, mid)

    elif theme_id == "chart":
        # Bold ascending bars + trend arrow
        for i, h in enumerate((28, 44, 58, 78)):
            x0 = 22 + i * 24
            fill(x0, 108 - h, x0 + 16, 108, white)
        poly([(24, 40), (64, 28), (100, 48), (100, 58), (64, 38), (24, 50)], white)
        fill(92, 36, 108, 52, white)

    elif theme_id == "tool":
        # Bold gear: outer ring + hub + 8 thick spokes
        circle(64, 64, 40, white)
        circle(64, 64, 24, mid)
        circle(64, 64, 12, white)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            fill(64 + dx * 28 - 5, 64 + dy * 28 - 5, 64 + dx * 28 + 5, 64 + dy * 28 + 5, white)

    elif theme_id == "lab":
        # Flask: neck + triangular body + bubble
        fill(56, 16, 72, 42, white)
        poly([(40, 108), (88, 108), (72, 42), (56, 42)], white)
        fill(44, 78, 84, 108, soft)
        circle(74, 88, 7, white)

    elif theme_id == "bolt":
        # Classic lightning bolt — one continuous silhouette
        poly(
            [
                (74, 12),
                (42, 64),
                (58, 64),
                (38, 116),
                (86, 54),
                (70, 54),
            ],
            white,
        )

    elif theme_id == "box":
        # Isometric package cube
        top = [(64, 22), (104, 44), (64, 66), (24, 44)]
        left = [(24, 44), (64, 66), (64, 108), (24, 86)]
        right = [(64, 66), (104, 44), (104, 86), (64, 108)]
        poly(top, white)
        poly(left, soft)
        poly(right, light)
        # seam
        fill(62, 66, 66, 108, deep)

    elif theme_id == "nodes":
        # Three hubs + thick links (reads as "connected apps")
        circle(36, 40, 16, white)
        circle(92, 40, 16, white)
        circle(64, 92, 18, white)
        # thick links
        poly([(40, 48), (56, 84), (48, 88), (32, 52)], white)
        poly([(88, 48), (72, 84), (80, 88), (96, 52)], white)
        poly([(48, 40), (80, 40), (80, 48), (48, 48)], white)
        # centers
        circle(36, 40, 6, mid)
        circle(92, 40, 6, mid)
        circle(64, 92, 7, mid)

    elif theme_id == "rocket":
        # Nose + body + fins + flame — unmistakable at small size
        poly([(64, 10), (86, 48), (42, 48)], white)
        fill(46, 46, 82, 92, white)
        poly([(46, 78), (46, 100), (24, 108), (46, 88)], white)
        poly([(82, 78), (82, 100), (104, 108), (82, 88)], white)
        circle(64, 62, 9, mid)
        # flame
        poly([(54, 92), (74, 92), (64, 118)], light)
        poly([(58, 92), (70, 92), (64, 108)], white)

    else:
        circle(64, 64, 36, white)

    # Small identity mark: white "drop" dot in corner (uvdrop-ish)
    circle(108, 20, 7, white)
    circle(108, 20, 3, mid)

    _round_corners(px, s(18), outside)
    return _encode_png(px)
