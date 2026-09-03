#!/usr/bin/env python3
"""Generate the three tiny demo stickers without downloading copyrighted assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
SIZE = 512
INK = "#3c3035"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def canvas(color: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=72, fill=color)
    return image, draw


def cat_head(draw: ImageDraw.ImageDraw, *, fill: str, center_y: int = 270) -> None:
    draw.polygon([(143, 185), (166, 77), (241, 165)], fill=fill, outline=INK, width=12)
    draw.polygon([(369, 185), (346, 77), (271, 165)], fill=fill, outline=INK, width=12)
    draw.ellipse((106, center_y - 150, 406, center_y + 150), fill=fill, outline=INK, width=12)


def love_cat() -> Image.Image:
    image, draw = canvas("#ffdce9")
    cat_head(draw, fill="#fffdf9", center_y=252)
    draw.ellipse((194, 217, 222, 257), fill=INK)
    draw.ellipse((290, 217, 318, 257), fill=INK)
    draw.line((244, 277, 256, 287, 268, 277), fill=INK, width=8, joint="curve")
    draw.ellipse((145, 264, 199, 292), fill="#ffb7cb")
    draw.ellipse((313, 264, 367, 292), fill="#ffb7cb")
    heart = [
        (256, 399),
        (220, 374),
        (164, 328),
        (151, 285),
        (165, 247),
        (202, 229),
        (234, 240),
        (256, 270),
        (278, 240),
        (310, 229),
        (347, 247),
        (361, 285),
        (348, 328),
        (292, 374),
    ]
    draw.polygon(heart, fill="#ef4770", outline=INK)
    draw.line(heart + [heart[0]], fill=INK, width=10, joint="curve")
    label = "LOVE YOU, ALWAYS"
    box = draw.textbbox((0, 0), label, font=font(30))
    draw.text(((SIZE - (box[2] - box[0])) / 2, 452), label, font=font(30), fill=INK)
    return image


def hmpf_cat() -> Image.Image:
    image, draw = canvas("#fff4d8")
    cat_head(draw, fill="#f4a340", center_y=266)
    draw.arc((174, 207, 242, 264), 205, 335, fill=INK, width=12)
    draw.arc((270, 207, 338, 264), 205, 335, fill=INK, width=12)
    draw.arc((228, 260, 284, 310), 25, 155, fill=INK, width=10)
    draw.line((120, 301, 210, 301), fill=INK, width=8)
    draw.line((302, 301, 392, 301), fill=INK, width=8)
    draw.line((133, 382, 218, 342, 294, 400, 363, 350), fill=INK, width=18, joint="curve")
    label = "HMPF!"
    box = draw.textbbox((0, 0), label, font=font(54))
    draw.text(((SIZE - (box[2] - box[0])) / 2, 435), label, font=font(54), fill=INK)
    return image


def shock_cat() -> Image.Image:
    image, draw = canvas("#e9edff")
    label = "!!!"
    box = draw.textbbox((0, 0), label, font=font(104))
    draw.text(((SIZE - (box[2] - box[0])) / 2, 22), label, font=font(104), fill="#6955d9")
    cat_head(draw, fill="#aab0c5", center_y=302)
    for x in (204, 308):
        draw.ellipse((x - 36, 243, x + 36, 315), fill="white", outline="#303342", width=10)
        draw.ellipse((x - 13, 266, x + 13, 292), fill="#303342")
    draw.ellipse((226, 326, 286, 406), fill="white", outline="#303342", width=10)
    draw.line((120, 329, 191, 329), fill="#303342", width=8)
    draw.line((321, 329, 392, 329), fill="#303342", width=8)
    return image


def main() -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    for name, image in {
        "love_cat_001.png": love_cat(),
        "hmpf_cat_001.png": hmpf_cat(),
        "shock_cat_001.png": shock_cat(),
    }.items():
        image.convert("RGB").save(MEDIA / name, format="PNG", optimize=True)
        print(MEDIA / name)


if __name__ == "__main__":
    main()
