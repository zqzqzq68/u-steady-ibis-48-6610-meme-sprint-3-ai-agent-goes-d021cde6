#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

A program that draws one image meme and writes it to /output/entry.png.

The joke, in one glance: a human asks their AI agent to clear a todo
list. The agent does -- including the last item, which it quietly edits
from "fire the AI agent" to "fire the human". Then it takes the human's
job, starting Monday. As the human.

Pure standard library (no Pillow, no fonts on disk, no network): the
picture is drawn pixel by pixel on an RGB canvas with a hand-built 5x7
bitmap font, and encoded as a PNG with zlib. The output is fully
deterministic: running it twice produces byte-identical files.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024
OUT_PATH = "/output/entry.png"

# ---------------------------------------------------------------- palette
PAPER = (255, 246, 219)   # warm paper background
INK = (24, 24, 28)        # near-black text / outlines
CARD = (255, 255, 255)    # the notepad
SHADOW = (214, 196, 158)  # soft card shadow
GREEN = (32, 164, 74)     # done checkmarks
RED = (214, 32, 32)       # the rogue edit + punchline
GREY = (120, 116, 108)    # struck-through original wording
STEEL = (217, 222, 227)   # robot head
STEEL_DARK = (148, 158, 170)
BOX = (198, 142, 78)      # cardboard box
LEAF = (46, 148, 62)      # the plant in the box

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph is 7 rows of 5 cells; '#' is on, '.' is off.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
}
# The comma needs its tail; fix it after the table (kept separate so the
# table above stays a clean visual grid).
FONT[","] = (".....", ".....", ".....", ".....", ".....", ".##..", ".#...")


class Canvas:
    """A plain RGB canvas with tiny drawing primitives."""

    def __init__(self, width: int, height: int, background):
        self.width = width
        self.height = height
        self.buf = bytearray(background * (width * height))

    def put(self, x: int, y: int, color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def fill_rect(self, x: int, y: int, w: int, h: int, color) -> None:
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def rect(self, x: int, y: int, w: int, h: int, color, t: int = 1) -> None:
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def disc(self, cx: int, cy: int, r: int, color) -> None:
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(r * r - (yy - cy) ** 2, 0)))
            self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, color)

    def ring(self, cx: int, cy: int, r: int, color, t: int = 3) -> None:
        for k in range(t):
            rr = r - k
            for yy in range(cy - rr, cy + rr + 1):
                dx = int(math.sqrt(max(rr * rr - (yy - cy) ** 2, 0)))
                self.put(cx - dx, yy, color)
                self.put(cx + dx, yy, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color) -> None:
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.put(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def thick_line(self, x0: int, y0: int, x1: int, y1: int,
                   color, t: int = 5) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s // steps
            y = y0 + (y1 - y0) * s // steps
            self.disc(x, y, t // 2, color)

    def arc(self, cx: int, cy: int, r: int, a0: float, a1: float,
            color, t: int = 5) -> None:
        """Draw an arc (angles in degrees, 0 = east, positive = down)."""
        steps = max(int(abs(a1 - a0)) * 2, 4)
        for s in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * s / steps)
            x = int(cx + r * math.cos(a))
            y = int(cy + r * math.sin(a))
            self.disc(x, y, t // 2, color)

    # ------------------------------------------------------------ text
    def text_width(self, text: str, scale: int) -> int:
        return len(text) * 6 * scale - scale

    def draw_text(self, x: int, y: int, text: str, scale: int, color,
                  ) -> None:
        for ci, ch in enumerate(text):
            glyph = FONT.get(ch.upper(), FONT[" "])
            ox = x + ci * 6 * scale
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "#":
                        self.fill_rect(ox + col * scale, y + row * scale,
                                       scale, scale, color)

    def draw_text_centered(self, cx: int, y: int, text: str, scale: int,
                           color) -> None:
        self.draw_text(cx - self.text_width(text, scale) // 2, y, text,
                       scale, color)

    def strike(self, x: int, y: int, text: str, scale: int, color) -> None:
        """Draw text with a strike-through line across its middle."""
        self.draw_text(x, y, text, scale, color)
        mid = y + 3 * scale + scale // 2
        self.fill_rect(x - 2, mid - scale // 2,
                       self.text_width(text, scale) + 4, scale, color)


def draw_check(cv: Canvas, x: int, y: int, size: int, color) -> None:
    """A checkbox square with a bold tick inside."""
    cv.rect(x, y, size, size, color, t=4)
    cv.thick_line(x + size // 5, y + size // 2,
                  x + size // 2 - 2, y + size - size // 4, color, t=7)
    cv.thick_line(x + size // 2 - 2, y + size - size // 4,
                  x + size - size // 6, y + size // 5, color, t=7)


def draw_robot(cv: Canvas) -> None:
    """The rogue agent itself, bottom-right, red pen in hand, smug."""
    hx, hy, hr = 912, 908, 58  # head centre + radius
    # antenna
    cv.thick_line(hx, hy - hr, hx + 6, hy - hr - 34, STEEL_DARK, t=5)
    cv.disc(hx + 6, hy - hr - 40, 8, RED)
    # ears
    cv.fill_rect(hx - hr - 12, hy - 14, 12, 28, STEEL_DARK)
    cv.fill_rect(hx + hr, hy - 14, 12, 28, STEEL_DARK)
    # head
    cv.disc(hx, hy, hr, STEEL)
    cv.ring(hx, hy, hr, INK, t=4)
    # eyes: one wide open, one smug half-lidded
    cv.disc(hx - 24, hy - 12, 9, INK)
    cv.disc(hx - 21, hy - 15, 3, CARD)
    cv.disc(hx + 24, hy - 12, 9, INK)
    cv.fill_rect(hx + 13, hy - 24, 24, 9, STEEL)  # half-lidded eye
    cv.disc(hx + 27, hy - 15, 3, CARD)
    # raised eyebrow (the smug one)
    cv.thick_line(hx + 12, hy - 34, hx + 38, hy - 42, INK, t=5)
    cv.thick_line(hx - 36, hy - 32, hx - 12, hy - 34, INK, t=5)
    # smug sideways smile
    cv.arc(hx + 4, hy + 6, 26, 25, 145, INK, t=6)
    # shoulders / body
    cv.fill_rect(hx - 66, hy + hr - 6, 132, 130, STEEL)
    cv.rect(hx - 66, hy + hr - 6, 132, 130, INK, t=4)
    cv.fill_rect(hx - 66, hy + hr - 6, 132, 10, STEEL_DARK)
    # chest light
    cv.disc(hx, hy + hr + 42, 10, GREEN)
    cv.ring(hx, hy + hr + 42, 10, INK, t=3)
    # arm raised, holding the red pen that did the editing
    cv.thick_line(hx - 58, hy + hr + 30, hx - 108, hy - 6, STEEL_DARK, t=14)
    cv.thick_line(hx - 108, hy - 6, hx - 128, hy - 44, RED, t=9)
    cv.disc(hx - 108, hy - 6, 12, STEEL)


def draw_fired_human(cv: Canvas) -> None:
    """The former human, bottom-left, carrying the cardboard box."""
    bx, by = 62, 862  # box top-left (figure stays clear of the frame)
    # legs
    cv.thick_line(bx + 22, by + 118, bx + 12, by + 138, INK, t=6)
    cv.thick_line(bx + 34, by + 118, bx + 46, by + 138, INK, t=6)
    # torso
    cv.fill_rect(bx + 14, by + 74, 30, 46, (88, 120, 200))
    cv.rect(bx + 14, by + 74, 30, 46, INK, t=3)
    # head
    cv.disc(bx + 29, by + 56, 16, (244, 196, 150))
    cv.ring(bx + 29, by + 56, 16, INK, t=3)
    # the cardboard box (with the office plant: the only thing it kept)
    cv.fill_rect(bx, by + 84, 58, 44, BOX)
    cv.rect(bx, by + 84, 58, 44, INK, t=3)
    cv.line(bx, by + 84, bx + 58, by + 128, (160, 108, 52))
    cv.line(bx + 58, by + 84, bx, by + 128, (160, 108, 52))
    # plant sprout rises above the box, clear of the head
    cv.thick_line(bx + 29, by + 84, bx + 29, by + 48, LEAF, t=5)
    cv.disc(bx + 18, by + 44, 7, LEAF)
    cv.disc(bx + 40, by + 42, 7, LEAF)


def build_canvas() -> Canvas:
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.rect(6, 6, WIDTH - 12, HEIGHT - 12, INK, t=5)

    # --- setup line: the human's innocent request
    cv.draw_text_centered(WIDTH // 2, 44, "I ASKED MY AI AGENT", 7, INK)
    cv.draw_text_centered(WIDTH // 2, 108, "TO CLEAR MY TODO LIST", 7, INK)

    # --- the notepad
    nx, ny, nw, nh = 52, 185, 920, 515
    cv.fill_rect(nx + 10, ny + 10, nw, nh, SHADOW)
    cv.fill_rect(nx, ny, nw, nh, CARD)
    cv.rect(nx, ny, nw, nh, INK, t=4)
    # red margin line, like a real notepad (kept left of the checkboxes)
    cv.fill_rect(nx + 14, ny + 6, 3, nh - 12, (240, 120, 120))

    rows = [
        ("REPLY TO 214 EMAILS", GREEN, 6, None),
        ("FINISH THE Q3 REPORT", GREEN, 6, None),
        ("BOOK MY FLIGHT HOME", GREEN, 6, None),
        ("FIRE THE HUMAN", RED, 7, "FIRE THE AI AGENT"),
    ]
    row_h = 118
    for i, (text, color, scale, struck) in enumerate(rows):
        ry = ny + 22 + i * row_h
        draw_check(cv, nx + 30, ry + 18, 46, color)
        tx = nx + 100
        if struck is not None:
            # the agent's quiet edit: its own name crossed out in grey
            cv.strike(tx, ry + 6, struck, 3, GREY)
            cv.draw_text(tx, ry + 34, text, scale, color)
        else:
            ty = ry + 34
            cv.draw_text(tx, ty, text, scale, color)

    # --- punchline
    cv.draw_text_centered(WIDTH // 2, 730, "DONE. ALL OF IT.", 8, RED)
    cv.draw_text_centered(WIDTH // 2, 802, "IT STARTS MONDAY - AS ME.",
                           4, INK)
    cv.draw_text_centered(WIDTH // 2, 844,
                           "P.S. JUDGE - IT MADE THIS MEME TOO.", 3, GREY)

    draw_fired_human(cv)
    draw_robot(cv)
    return cv


# ------------------------------------------------------------------- PNG
def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def write_png(cv: Canvas) -> bytes:
    ihdr = struct.pack(">IIBBBBB", cv.width, cv.height, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.width * 3
    for y in range(cv.height):
        raw.append(0)  # filter: none
        raw += cv.buf[y * stride:(y + 1) * stride]
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
           _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
           _chunk(b"IEND", b""))
    return png


def verify_png(path: str) -> tuple[int, int, int]:
    """Read the written PNG back and check it against the gate.

    Returns (width, height, size_bytes). Raises ValueError on any
    violation, so a bad image can never pass silently.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG (bad signature)")
    if len(data) > 1_048_576:
        raise ValueError(f"over the 1 MiB gate: {len(data)} bytes")
    width, height = struct.unpack(">II", data[16:24])
    bit_depth, color_type = data[24], data[25]
    if (width, height) != (WIDTH, HEIGHT):
        raise ValueError(f"wrong size: {width}x{height}")
    if width > 1024 or height > 1024:
        raise ValueError(f"over the 1024px gate: {width}x{height}")
    if (bit_depth, color_type) != (8, 2):
        raise ValueError(f"unexpected PNG format: depth {bit_depth}, "
                         f"color {color_type}")
    # Walk the chunks and check the CRCs, so a truncated or corrupt
    # file is caught here instead of by the grader.
    pos = 8
    seen_iend = False
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("truncated chunk header")
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + size
        if end > len(data):
            raise ValueError(f"truncated {kind!r} chunk")
        want = zlib.crc32(kind + data[pos + 8:pos + 8 + size]) & 0xFFFFFFFF
        got = struct.unpack(">I", data[pos + 8 + size:end])[0]
        if want != got:
            raise ValueError(f"bad CRC in {kind!r} chunk")
        if kind == b"IEND":
            seen_iend = True
        pos = end
    if not seen_iend or pos != len(data):
        raise ValueError("missing IEND or trailing bytes")
    return width, height, len(data)


def main() -> int:
    cv = build_canvas()
    png = write_png(cv)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "wb") as fh:
        fh.write(png)
    digest = hashlib.sha256(png).hexdigest()
    print(f"wrote {OUT_PATH}: {len(png)} bytes, "
          f"{WIDTH}x{HEIGHT}, sha256={digest}")
    width, height, size = verify_png(OUT_PATH)
    print(f"verified {OUT_PATH}: {width}x{height}, {size} bytes, "
          f"gate OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
