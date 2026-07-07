#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "day-sharpness-config.json"


def read_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def item_index(config: dict) -> dict[str, dict]:
    return {item["id"]: item for item in config["items"]}


def asset_path(config: dict, item: dict) -> Path:
    return ROOT / config["assetBase"] / item["file"]


def item_for(config: dict, group: dict, focal: str, side: str) -> dict | None:
    items = item_index(config)
    if side == "left":
        camera_id = group.get("leftCameraId", "l10")
        return next(
            (
                item
                for item in config["items"]
                if item.get("cameraId") == camera_id and str(item.get("focal")) == str(focal)
            ),
            None,
        )

    override = group.get("rightItemIds", {}).get(str(focal))
    if override:
        return items.get(override)
    camera_id = group.get("rightCameraId")
    if not camera_id:
        return None
    return next(
        (
            item
            for item in config["items"]
            if item.get("cameraId") == camera_id and str(item.get("focal")) == str(focal)
        ),
        None,
    )


def crop_with_anchor(path: Path, anchor: list[int], base_width: int, pane: tuple[int, int], zoom: float):
    image = Image.open(path).convert("RGB")
    normalized_scale = base_width / image.width
    effective_zoom = zoom * normalized_scale
    pane_w, pane_h = pane
    crop_w = pane_w / effective_zoom
    crop_h = pane_h / effective_zoom
    cx, cy = anchor
    left = round(cx - crop_w / 2)
    top = round(cy - crop_h / 2)
    right = round(left + crop_w)
    bottom = round(top + crop_h)
    canvas = Image.new("RGB", (right - left, bottom - top), (16, 16, 16))
    box = (max(0, left), max(0, top), min(image.width, right), min(image.height, bottom))
    if box[2] > box[0] and box[3] > box[1]:
        canvas.paste(image.crop(box), (max(0, -left), max(0, -top)))
    return canvas.resize(pane, Image.Resampling.NEAREST), normalized_scale


def draw_checker(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]):
    left, top, right, bottom = box
    size = 24
    for y in range(top, bottom, size):
        for x in range(left, right, size):
            fill = (16, 16, 16) if ((x // size) + (y // size)) % 2 else (10, 10, 10)
            draw.rectangle([x, y, min(x + size, right), min(y + size, bottom)], fill=fill)


def panel_label(item: dict | None, fallback_camera: str, focal: str) -> tuple[str, str]:
    if not item:
        return fallback_camera, f"无法拍摄 {focal}mm"
    name = item["camera"]
    meta = f"{item['label']} · {item['aperture']} · {item['iso']} · {item['pixels']}"
    return name, meta


def draw_label(
    draw: ImageDraw.ImageDraw,
    y: int,
    item: dict | None,
    fallback_camera: str,
    focal: str,
    scale: float | None,
    pane_w: int,
    pane_h: int,
    zoom: float,
    fonts: tuple[ImageFont.ImageFont, ImageFont.ImageFont],
):
    font_bold, font_small = fonts
    name, meta = panel_label(item, fallback_camera, focal)
    meta_w = draw.textlength(meta, font=font_small)
    name_w = draw.textlength(name, font=font_bold)
    box_w = min(pane_w - 24, max(480, int(name_w + meta_w + 68)))
    draw.rectangle([16, y + 14, box_w, y + 58], fill=(15, 15, 15), outline=(48, 48, 48))
    draw.text((28, y + 22), name, fill=(245, 245, 245), font=font_bold)
    draw.text((28 + int(name_w) + 22, y + 25), meta, fill=(206, 206, 206), font=font_small)
    if scale is not None:
        badge = f"{int(round(zoom * 100))}% · L10 size x {scale:.2f}"
        draw.rectangle([pane_w - 270, y + pane_h - 48, pane_w - 16, y + pane_h - 14], fill=(12, 12, 12), outline=(46, 46, 46))
        draw.text((pane_w - 256, y + pane_h - 42), badge, fill=(210, 210, 210), font=font_small)


def missing_panel(pane: tuple[int, int], camera: str, focal: str) -> Image.Image:
    pane_w, pane_h = pane
    image = Image.new("RGB", pane, (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw_checker(draw, (0, 0, pane_w, pane_h))
    font_bold = load_font(34)
    font = load_font(24)
    title = f"{camera} 无法拍摄 {focal}mm"
    subtitle = "该焦段没有可用光学或裁切素材"
    title_w = draw.textlength(title, font=font_bold)
    subtitle_w = draw.textlength(subtitle, font=font)
    draw.text(((pane_w - title_w) / 2, pane_h / 2 - 40), title, fill=(238, 238, 238), font=font_bold)
    draw.text(((pane_w - subtitle_w) / 2, pane_h / 2 + 10), subtitle, fill=(150, 150, 150), font=font)
    return image


def generate_previews(config: dict) -> list[Path]:
    out_dir = ROOT / config.get("previewDir", "day-sharpness-assets/article-previews")
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_focals = [str(focal) for focal in config.get("previewFocals", ["50", "75"])]
    preview_groups = set(config.get("previewGroups", [group["id"] for group in config["compareGroups"]]))
    pane_w, pane_h = config.get("previewPane", [880, 560])
    pane = (int(pane_w), int(pane_h))
    gap = int(config.get("previewGap", 8))
    header_h = int(config.get("previewHeader", 64))
    footer_h = int(config.get("previewFooter", 48))
    zoom = float(config.get("previewZoom", 2))
    font_bold = load_font(26)
    font = load_font(20)
    font_small = load_font(18)
    outputs: list[Path] = []

    for group in config["compareGroups"]:
        if group["id"] not in preview_groups:
            continue
        for focal in preview_focals:
            left = item_for(config, group, focal, "left")
            right = item_for(config, group, focal, "right")
            if not left:
                continue
            base_width = Image.open(asset_path(config, left)).width
            canvas_h = header_h + pane[1] * 2 + gap + footer_h
            canvas = Image.new("RGB", (pane[0], canvas_h), (5, 5, 5))
            draw = ImageDraw.Draw(canvas)
            title = f"{group['label']} · {focal}mm · R&F aligned {int(zoom * 100)}%"
            draw.text((16, 18), title, fill=(242, 242, 242), font=font_bold)

            for index, (item, fallback_camera) in enumerate(
                [(left, "L10"), (right, group.get("rightLabel") or group.get("rightCameraId", "reference").upper())]
            ):
                y = header_h + index * (pane[1] + gap)
                if item and asset_path(config, item).exists():
                    crop, scale = crop_with_anchor(asset_path(config, item), item["anchor"], base_width, pane, zoom)
                else:
                    crop = missing_panel(pane, fallback_camera, focal)
                    scale = None
                canvas.paste(crop, (0, y))
                draw.rectangle([0, y, pane[0] - 1, y + pane[1] - 1], outline=(52, 52, 52), width=2)
                draw_label(draw, y, item, fallback_camera, focal, scale, pane[0], pane[1], zoom, (font_bold, font_small))

            footer = "RAW 导出 JPG · 正文预览为 200%，每组按 R&F 标识居中并按 L10 图像宽度归一化。"
            draw.text((16, header_h + pane[1] * 2 + gap + 16), footer, fill=(160, 160, 160), font=font)
            output = out_dir / f"{group['id']}_{focal}mm.jpg"
            canvas.save(output, quality=94, subsampling=0)
            outputs.append(output)
    return outputs


def markdown_refs(config: dict) -> str:
    preview_focals = [str(focal) for focal in config.get("previewFocals", ["50", "75"])]
    preview_groups = set(config.get("previewGroups", [group["id"] for group in config["compareGroups"]]))
    out_dir = Path(config.get("previewDir", "day-sharpness-assets/article-previews"))
    rows: list[str] = []
    for group in config["compareGroups"]:
        if group["id"] not in preview_groups:
            continue
        for focal in preview_focals:
            left = item_for(config, group, focal, "left")
            right = item_for(config, group, focal, "right")
            if not left:
                continue
            right_label = right["camera"] if right else group.get("rightLabel", "参照相机")
            filename = f"{group['id']}_{focal}mm.jpg"
            path = f"tools/{out_dir / filename}"
            alt = f"L10 {focal}mm vs {right_label} {focal}mm，R&F 同尺寸 200% 像素放大"
            rows.append(f"![{alt}]({path})")
    return "\n\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate day sharpness article preview JPG files.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--generate-previews", action="store_true")
    parser.add_argument("--emit-markdown", action="store_true")
    args = parser.parse_args()

    config = read_config(args.config)
    if args.generate_previews:
        for path in generate_previews(config):
            print(f"preview {path.relative_to(ROOT)}")
    if args.emit_markdown:
        print(markdown_refs(config))
    if not args.generate_previews and not args.emit_markdown:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
