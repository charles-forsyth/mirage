"""Tutorial slides: render exact terminal/code screens as images (no AI, no cost).

Image models garble text, so any shot that must show real commands or config is drawn
here with Pillow instead of generated. Plans mark these shots as "screen" with a "code"
block (and optional "title").
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG = (13, 17, 23)
PANEL = (22, 27, 34)
BAR = (33, 38, 45)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (88, 166, 255)
GREEN = (126, 231, 135)
YELLOW = (255, 214, 102)
COMMENT = (110, 118, 129)


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _line_color(line: str) -> tuple[int, int, int]:
    s = line.lstrip()
    if s.startswith("#") or s.startswith("//"):
        return COMMENT
    if s.startswith("$ "):
        return GREEN
    if s.startswith('"') or ":" in s.split(" ")[0]:
        return TEXT
    return TEXT


def render_screen(
    code: str, title: str, out_png: Path, aspect: str = "16:9", subtitle: str = ""
) -> Path:
    """Draw a terminal/editor window with `code`, sized for the video frame, at 2x for crisp scaling."""
    w, h = (1920, 1080) if aspect == "16:9" else (1080, 1920)
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    margin = 70 if aspect == "16:9" else 50

    # Title
    ty = margin - 10
    if title:
        d.text(
            (margin, ty),
            title,
            font=_font(SANS_BOLD, 54 if aspect == "16:9" else 50),
            fill=TEXT,
        )
        ty += 78
    if subtitle:
        d.text((margin, ty), subtitle, font=_font(MONO, 30), fill=ACCENT)
        ty += 52

    # Window
    top = ty + 20
    box = (margin, top, w - margin, h - margin - (40 if aspect == "16:9" else 260))
    d.rounded_rectangle(box, radius=18, fill=PANEL)
    d.rounded_rectangle((box[0], box[1], box[2], box[1] + 54), radius=18, fill=BAR)
    d.rectangle((box[0], box[1] + 36, box[2], box[1] + 54), fill=BAR)
    for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = box[0] + 34 + k * 34
        d.ellipse((cx - 10, box[1] + 17, cx + 10, box[1] + 37), fill=c)

    # Fit code to the window: pick the largest font size that fits width and height.
    inner_w = box[2] - box[0] - 80
    inner_h = box[3] - box[1] - 54 - 60
    lines = code.rstrip("\n").split("\n")
    size = 40
    wrapped: list[str] = lines
    while size > 16:
        f = _font(MONO, size)
        char_w = f.getlength("M")
        max_chars = max(10, int(inner_w // char_w))
        wrapped = []
        for ln in lines:
            wrapped += textwrap.wrap(
                ln, max_chars, subsequent_indent="    ", drop_whitespace=False
            ) or [""]
        if len(wrapped) * size * 1.45 <= inner_h:
            break
        size -= 2
    f = _font(MONO, size)
    y = box[1] + 54 + 32
    for ln in wrapped:
        d.text((box[0] + 40, y), ln, font=f, fill=_line_color(ln))
        y += int(size * 1.45)

    img.save(out_png)
    return out_png
