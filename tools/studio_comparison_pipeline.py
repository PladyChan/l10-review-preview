#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "studio-comparison-config.json"


@dataclass(frozen=True)
class Camera:
    id: str
    name: str
    focal: str
    prefix: str
    source_dir: Path | None = None
    source_pattern: str = "{prefix}_{iso}*.jpg"


def read_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rel_to_tools(path: str | Path) -> Path:
    return ROOT / Path(path)


def camera_from(raw: dict, group: dict) -> Camera:
    source_dir = raw.get("sourceDir") or group.get("sourceDir")
    return Camera(
        id=raw["id"],
        name=raw["name"],
        focal=raw.get("focal", ""),
        prefix=raw["prefix"],
        source_dir=Path(source_dir).expanduser() if source_dir else None,
        source_pattern=raw.get("sourcePattern") or group.get("sourcePattern") or "{prefix}_{iso}*.jpg",
    )


def asset_path(config: dict, group_id: str, iso: str, camera: Camera) -> Path:
    return rel_to_tools(config["assetBase"]) / group_id / iso / f"{camera.prefix}_{iso}.jpg"


def find_source(camera: Camera, iso: str) -> Path | None:
    if not camera.source_dir:
        return None
    pattern = camera.source_pattern.format(prefix=camera.prefix, iso=iso, camera=camera.id)
    candidates = sorted(camera.source_dir.glob(pattern))
    return candidates[0] if candidates else None


def copy_assets(config: dict) -> list[str]:
    messages: list[str] = []
    for group in config["groups"]:
        for iso in config["isos"]:
            for raw_camera in group["cameras"]:
                camera = camera_from(raw_camera, group)
                target = asset_path(config, group["id"], iso, camera)
                if target.exists():
                    messages.append(f"exists {target.relative_to(ROOT)}")
                    continue
                source = find_source(camera, iso)
                if not source:
                    messages.append(f"missing source for {group['id']} {iso} {camera.id}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                messages.append(f"copied {source} -> {target.relative_to(ROOT)}")
    return messages


def check_assets(config: dict) -> list[str]:
    problems: list[str] = []
    for group in config["groups"]:
        anchors = group.get("anchors", {})
        for raw_camera in group["cameras"]:
            camera = camera_from(raw_camera, group)
            if camera.id not in anchors.get("ifc", {}):
                problems.append(f"missing IFC anchor: {group['id']} {camera.id}")
            if camera.id not in anchors.get("corner", {}):
                problems.append(f"missing corner anchor: {group['id']} {camera.id}")
        for iso in config["isos"]:
            for raw_camera in group["cameras"]:
                camera = camera_from(raw_camera, group)
                path = asset_path(config, group["id"], iso, camera)
                if not path.exists():
                    problems.append(f"missing asset: {path.relative_to(ROOT)}")
    return problems


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


def draw_label(draw: ImageDraw.ImageDraw, y: int, name: str, focal: str, iso: str, scale: float, pane_w: int, pane_h: int, preview_zoom: float, scale_base_label: str, fonts):
    font_bold, font_small = fonts
    meta = f"{focal} · {iso.replace('ISO', 'ISO ')}"
    label_w = draw.textlength(name, font=font_bold)
    meta_w = draw.textlength(meta, font=font_small)
    box_w = min(pane_w - 24, max(360, int(label_w + meta_w + 56)))
    draw.rectangle([16, y + 14, box_w, y + 56], fill=(15, 15, 15), outline=(48, 48, 48))
    draw.text((28, y + 21), name, fill=(245, 245, 245), font=font_bold)
    draw.text((box_w - meta_w - 18, y + 25), meta, fill=(155, 155, 155), font=font_small)
    badge = f"{int(round(preview_zoom * 100))}% · {scale_base_label} size x {scale:.2f}"
    draw.rectangle([pane_w - 270, y + pane_h - 48, pane_w - 16, y + pane_h - 14], fill=(12, 12, 12), outline=(46, 46, 46))
    draw.text((pane_w - 256, y + pane_h - 42), badge, fill=(210, 210, 210), font=font_small)


def generate_previews(config: dict) -> list[Path]:
    out_dir = rel_to_tools(config["previewDir"])
    suffix = config.get("previewFileSuffix", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_isos = config.get("previewIsos") or config["isos"]
    pane_w, pane_h = config.get("previewPane", [880, 560])
    gap = int(config.get("previewGap", 8))
    header_h = int(config.get("previewHeader", 64))
    footer_h = int(config.get("previewFooter", 48))
    zoom = float(config.get("previewZoom", 2))
    scale_base_label = config.get("scaleBaseLabel") or config.get("scaleBaseCamera", "base")
    font_bold = load_font(26)
    font = load_font(20)
    font_small = load_font(18)
    outputs: list[Path] = []

    for group in config["groups"]:
        cameras = [camera_from(camera, group) for camera in group["cameras"]]
        if len(cameras) != 2:
            raise ValueError(f"Preview generator expects 2 cameras per group: {group['id']}")
        anchors = group["anchors"]["ifc"]
        for iso in preview_isos:
            base_camera = next((cam for cam in cameras if cam.id == config.get("scaleBaseCamera", "l10")), cameras[0])
            base_width = Image.open(asset_path(config, group["id"], iso, base_camera)).width
            canvas_h = header_h + pane_h * 2 + gap + footer_h
            canvas = Image.new("RGB", (pane_w, canvas_h), (5, 5, 5))
            draw = ImageDraw.Draw(canvas)
            title = group["id"].replace("_", " ") + f" · {iso.replace('ISO', 'ISO ')} · IFC aligned {int(zoom * 100)}%"
            draw.text((16, 18), title, fill=(242, 242, 242), font=font_bold)
            for index, camera in enumerate(cameras):
                y = header_h + index * (pane_h + gap)
                crop, scale = crop_with_anchor(asset_path(config, group["id"], iso, camera), anchors[camera.id], base_width, (pane_w, pane_h), zoom)
                canvas.paste(crop, (0, y))
                draw.rectangle([0, y, pane_w - 1, y + pane_h - 1], outline=(52, 52, 52), width=2)
                draw_label(draw, y, camera.name, camera.focal, iso, scale, pane_w, pane_h, zoom, scale_base_label, (font_bold, font_small))
            draw.text((16, header_h + pane_h * 2 + gap + 16), f"RAW 导出 JPG · 正文预览为 {int(zoom * 100)}%，每台机共用固定 IFC 锚点。", fill=(160, 160, 160), font=font)
            output = out_dir / f"{group['id']}_{iso}{suffix}.jpg"
            canvas.save(output, quality=94, subsampling=0)
            outputs.append(output)
    return outputs


def markdown_refs(config: dict) -> str:
    rows: list[str] = []
    preview_isos = config.get("previewIsos") or config["isos"]
    zoom = int(float(config.get("previewZoom", 2)) * 100)
    suffix = config.get("previewFileSuffix", "")
    for group in config["groups"]:
        camera_label = " vs ".join(f"{camera['name']} {camera.get('focal', '')}".strip() for camera in group["cameras"])
        for iso in preview_isos:
            filename = f"{group['id']}_{iso}{suffix}.jpg"
            path = f"tools/{Path(config['previewDir']) / filename}"
            alt = f"{camera_label}，{iso.replace('ISO', 'ISO ')}，IFC 同尺寸 {zoom}% 像素放大"
            rows.append(f"![{alt}]({path})")
    return "\n\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reusable studio comparison asset pipeline.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--copy-assets", action="store_true", help="Copy configured source files into the tool asset tree.")
    parser.add_argument("--generate-previews", action="store_true", help="Generate vertical article preview JPG files.")
    parser.add_argument("--check", action="store_true", help="Check required assets and anchors.")
    parser.add_argument("--emit-markdown", action="store_true", help="Print Markdown image references for article insertion.")
    args = parser.parse_args()

    config = read_config(args.config)
    if args.copy_assets:
        for message in copy_assets(config):
            print(message)
    if args.generate_previews:
        for path in generate_previews(config):
            print(f"preview {path.relative_to(ROOT)}")
    if args.check:
        problems = check_assets(config)
        if problems:
            for problem in problems:
                print(problem)
            return 1
        print("comparison assets OK")
    if args.emit_markdown:
        print(markdown_refs(config))
    if not any([args.copy_assets, args.generate_previews, args.check, args.emit_markdown]):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
