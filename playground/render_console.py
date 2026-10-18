import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\consola.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]
FONT_SIZE = 20
PADDING = 24
BG = (12, 12, 12)
FG = (204, 204, 204)
GREEN = (78, 201, 176)


def load_font():
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, FONT_SIZE)
    return ImageFont.load_default()


def main():
    raw = open("playground/console_raw.txt", "r", encoding="utf-8").read()
    lines = []
    for line in raw.splitlines():
        lines.append(line.split("\r")[-1].rstrip())
    lines = [line for line in lines if line.strip()]

    font = load_font()
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    widths = [draw.textlength(line, font=font) for line in lines]
    width = int(max(widths)) + 2 * PADDING
    height = FONT_SIZE * 3 // 2 * len(lines) + 2 * PADDING

    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    y = PADDING
    for line in lines:
        color = GREEN if line.startswith("Successfully") else FG
        draw.text((PADDING, y), line, font=font, fill=color)
        y += FONT_SIZE * 3 // 2

    image.save("console_output.png")
    print(f"wrote console_output.png with {len(lines)} lines")


if __name__ == "__main__":
    main()
