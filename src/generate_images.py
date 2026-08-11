#!/usr/bin/env python3
"""Generate a four-slide Instagram carousel from an approved CSV row."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1350
MARGIN = 78

INK = "#111111"
OFF_WHITE = "#FFFDF5"
LIME = "#D9FF57"
CORAL = "#FF6B61"
LAVENDER = "#CDBDFF"
YELLOW = "#FFD84D"
BLUE = "#4D7CFE"
MUTED = "#5B5B5B"

REQUIRED_FIELDS = (
    "id",
    "publish_date",
    "japanese",
    "english",
    "explanation",
    "example_ja",
    "example_en",
    "alternatives",
    "quiz",
    "caption",
    "status",
)

REGULAR_FONT_CANDIDATES = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/ee89e7987a76cc8cfdff36c96bd7bc77655b343e.asset/AssetData/YuGothic-Medium.otf",
    "/System/Library/AssetsV2/PreinstalledAssetsV2/InstallWithOs/com_apple_MobileAsset_Font7/11ead4dd9f3a3503b4ced2546782dd8bc31871c9.asset/AssetData/YuGothic-Medium.otf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)

BOLD_FONT_CANDIDATES = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/b7a6a6575a699e801915b73b9e1e75c74a3404ce.asset/AssetData/YuGothic-Bold.otf",
    "/System/Library/AssetsV2/PreinstalledAssetsV2/InstallWithOs/com_apple_MobileAsset_Font7/0703ece025f7511095fc290b30bc2d3d28d509a9.asset/AssetData/YuGothic-Bold.otf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
)


def find_font(env_name: str, candidates: tuple[str, ...]) -> str:
    override = os.getenv(env_name)
    candidates_to_check: Iterable[str] = (override,) + candidates if override else candidates
    for candidate in candidates_to_check:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        f"Japanese font not found. Set {env_name} to a Japanese-compatible .ttf/.ttc/.otf file."
    )


REGULAR_FONT_PATH = find_font("INSTAGRAM_FONT", REGULAR_FONT_CANDIDATES)
BOLD_FONT_PATH = find_font("INSTAGRAM_FONT_BOLD", BOLD_FONT_CANDIDATES)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD_FONT_PATH if bold else REGULAR_FONT_PATH, size=size)


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont) -> float:
    box = draw.textbbox((0, 0), text, font=text_font)
    return box[2] - box[0]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and text_width(draw, candidate, text_font) > max_width:
                lines.append(current.rstrip())
                current = char.lstrip()
            else:
                current = candidate
        lines.append(current.rstrip())
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    spacing: int = 18,
    max_lines: int | None = None,
) -> int:
    lines = wrap_text(draw, text, text_font, max_width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("。.!? ") + "…"
    x, y = xy
    line_height = text_font.size + spacing
    for line in lines:
        draw.text((x, y), line, font=text_font, fill=fill)
        y += line_height
    return y


def base_slide(post_id: str, page: int, background: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((58, 58, 476, 128), radius=35, fill=INK)
    draw.text((91, 75), "英語1000本ノック", font=font(28, bold=True), fill=OFF_WHITE)
    draw.ellipse((WIDTH - 155, 50, WIDTH - 61, 144), fill=OFF_WHITE, outline=INK, width=4)
    page_font = font(24, bold=True)
    page_text = f"{page}/4"
    page_w = text_width(draw, page_text, page_font)
    draw.text((WIDTH - 108 - page_w / 2, 82), page_text, font=page_font, fill=INK)
    draw.text((MARGIN, HEIGHT - 83), f"KNOCK #{post_id}  •  SWIPE →", font=font(24, bold=True), fill=INK)
    return image, draw


def slide_one(row: dict[str, str]) -> Image.Image:
    image, draw = base_slide(row["id"], 1, LIME)
    draw.ellipse((820, 164, 1040, 384), fill=CORAL, outline=INK, width=5)
    draw.line((850, 210, 1004, 336), fill=INK, width=8)
    draw.line((1004, 210, 850, 336), fill=INK, width=8)
    draw.rounded_rectangle((MARGIN, 190, 388, 252), radius=28, fill=OFF_WHITE, outline=INK, width=4)
    draw.text((112, 202), "今日のひとこと", font=font(28, bold=True), fill=INK)
    jp_font = font(104 if len(row["japanese"]) <= 10 else 76, bold=True)
    draw_wrapped(draw, (MARGIN, 326), row["japanese"], jp_font, INK, 820, spacing=10, max_lines=3)
    draw.rounded_rectangle((48, 594, WIDTH - 48, 1115), radius=54, fill=INK)
    draw.text((MARGIN, 647), "NATURAL ENGLISH", font=font(27, bold=True), fill=LIME)
    en_font = font(76 if len(row["english"]) <= 28 else 61, bold=True)
    draw_wrapped(
        draw,
        (MARGIN, 730),
        row["english"],
        en_font,
        OFF_WHITE,
        WIDTH - 2 * MARGIN,
        spacing=16,
        max_lines=4,
    )
    draw.rounded_rectangle((704, 1052, 982, 1161), radius=52, fill=CORAL, outline=INK, width=4)
    draw.text((761, 1080), "SAVE IT!", font=font(31, bold=True), fill=INK)
    return image


def slide_two(row: dict[str, str]) -> Image.Image:
    image, draw = base_slide(row["id"], 2, CORAL)
    draw.text((MARGIN, 200), "このニュアンス、", font=font(51, bold=True), fill=INK)
    draw.text((MARGIN, 267), "知ってる？", font=font(82, bold=True), fill=INK)
    draw.line((74, 365, 570, 365), fill=OFF_WHITE, width=18)
    draw.rounded_rectangle((58, 420, WIDTH - 58, 970), radius=52, fill=OFF_WHITE, outline=INK, width=5)
    draw_wrapped(
        draw,
        (MARGIN + 28, 487),
        row["explanation"],
        font(45, bold=True),
        INK,
        WIDTH - 2 * MARGIN - 56,
        spacing=23,
        max_lines=7,
    )
    draw.rounded_rectangle((58, 1018, WIDTH - 58, 1190), radius=38, fill=INK)
    draw.text((91, 1046), "POINT", font=font(26, bold=True), fill=LIME)
    draw_wrapped(draw, (91, 1094), "場面と気持ちに合う英語を選ぼう。", font(34, bold=True), OFF_WHITE, 865, spacing=10, max_lines=2)
    return image


def slide_three(row: dict[str, str]) -> Image.Image:
    image, draw = base_slide(row["id"], 3, LAVENDER)
    draw.text((MARGIN, 205), "リアル会話で", font=font(48, bold=True), fill=INK)
    draw.text((MARGIN, 265), "KNOCK! KNOCK!", font=font(73, bold=True), fill=INK)
    draw.ellipse((840, 188, 1016, 364), fill=YELLOW, outline=INK, width=5)
    draw.text((890, 235), "×3", font=font(46, bold=True), fill=INK)
    draw.rounded_rectangle((58, 420, 910, 704), radius=48, fill=OFF_WHITE, outline=INK, width=5)
    draw.rounded_rectangle((82, 386, 244, 446), radius=26, fill=INK)
    draw.text((126, 397), "日本語", font=font(25, bold=True), fill=OFF_WHITE)
    draw_wrapped(
        draw,
        (MARGIN + 24, 492),
        row["example_ja"],
        font(42, bold=True),
        INK,
        760,
        spacing=20,
        max_lines=4,
    )
    draw.polygon(((852, 704), (918, 704), (884, 770)), fill=OFF_WHITE, outline=INK)
    draw.rounded_rectangle((170, 800, WIDTH - 58, 1124), radius=48, fill=INK)
    draw.rounded_rectangle((790, 766, 976, 830), radius=28, fill=YELLOW, outline=INK, width=4)
    draw.text((827, 778), "ENGLISH", font=font(25, bold=True), fill=INK)
    draw_wrapped(
        draw,
        (218, 868),
        row["example_en"],
        font(39, bold=True),
        OFF_WHITE,
        744,
        spacing=18,
        max_lines=5,
    )
    draw.polygon(((170, 1038), (170, 1124), (110, 1124)), fill=INK)
    return image


def slide_four(row: dict[str, str]) -> Image.Image:
    image, draw = base_slide(row["id"], 4, YELLOW)
    draw.text((MARGIN, 190), "TRY IT!", font=font(92, bold=True), fill=INK)
    draw.rounded_rectangle((650, 184, 1008, 292), radius=50, fill=LIME, outline=INK, width=5)
    draw.text((715, 211), "MINI QUIZ", font=font(31, bold=True), fill=INK)
    draw_wrapped(draw, (MARGIN, 338), row["quiz"], font(50, bold=True), INK, WIDTH - 2 * MARGIN, spacing=18, max_lines=4)
    draw.line((80, 585, 1000, 585), fill=INK, width=6)
    draw.text((MARGIN, 626), "ALSO SAY", font=font(28, bold=True), fill=BLUE)
    draw.rounded_rectangle((58, 680, WIDTH - 58, 1055), radius=48, fill=OFF_WHITE, outline=INK, width=5)
    draw_wrapped(
        draw,
        (MARGIN + 25, 750),
        row["alternatives"].replace(" / ", "\n"),
        font(46, bold=True),
        INK,
        WIDTH - 2 * MARGIN - 50,
        spacing=22,
        max_lines=4,
    )
    draw.rounded_rectangle((58, 1090, WIDTH - 58, 1210), radius=58, fill=CORAL, outline=INK, width=5)
    draw.text((154, 1121), "保存して、あとで答え合わせ ✓", font=font(31, bold=True), fill=INK)
    return image


def read_post(csv_path: Path, post_id: str | None) -> dict[str, str]:
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
        rows = [dict(row) for row in reader]

    malformed = [row.get("id", "?") for row in rows if row.get(None)]
    if malformed:
        raise ValueError(
            "CSV has extra columns in posts: "
            + ", ".join(malformed)
            + ". Put fields containing commas inside double quotes."
        )

    if post_id:
        rows = [row for row in rows if row["id"] == post_id]
    else:
        rows = [row for row in rows if row["status"].strip().lower() == "approved"]

    if not rows:
        target = post_id or "an approved post"
        raise ValueError(f"Could not find {target} in {csv_path}")

    row = rows[0]
    empty = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
    if empty:
        raise ValueError(f"Post {row.get('id', '?')} has empty fields: {', '.join(empty)}")
    return row


def generate(row: dict[str, str], output_root: Path) -> list[Path]:
    destination = output_root / row["id"]
    destination.mkdir(parents=True, exist_ok=True)
    slides = (slide_one(row), slide_two(row), slide_three(row), slide_four(row))
    paths: list[Path] = []
    for index, slide in enumerate(slides, start=1):
        path = destination / f"{index:02d}.jpg"
        slide.save(path, "JPEG", quality=92, optimize=True, progressive=True)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("data/posts.csv"))
    parser.add_argument("--post-id")
    parser.add_argument("--output-dir", type=Path, default=Path("generated"))
    args = parser.parse_args()

    row = read_post(args.csv, args.post_id)
    paths = generate(row, args.output_dir)
    print(f"Generated post {row['id']} using {REGULAR_FONT_PATH} / {BOLD_FONT_PATH}")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
