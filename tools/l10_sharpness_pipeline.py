#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "l10-sharpness-config.json"


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel_to_tools(path: str | Path) -> Path:
    return ROOT / Path(path)


def photo_path(config: dict, photo: dict) -> Path:
    return rel_to_tools(config["assetBase"]) / photo["file"]


def check_assets(config: dict) -> None:
    missing: list[str] = []
    for photo in config["photos"] + config.get("extras", []):
        path = photo_path(config, photo)
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    if missing:
        raise SystemExit("missing sharpness assets:\n" + "\n".join(missing))
    print("l10 sharpness assets OK")


def focal_by_id(config: dict) -> dict[str, dict]:
    return {item["id"]: item for item in config["focals"]}


def aperture_by_id(config: dict) -> dict[str, dict]:
    return {item["id"]: item for item in config["apertures"]}


def crop_box(anchor: list[int], image_size: tuple[int, int], crop_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = image_size
    crop_w, crop_h = crop_size
    left = max(0, min(width - crop_w, int(anchor[0] - crop_w / 2)))
    top = max(0, min(height - crop_h, int(anchor[1] - crop_h / 2)))
    return left, top, left + crop_w, top + crop_h


def preview_filename(photo: dict, point: str) -> str:
    stem = Path(photo["file"]).stem.lower()
    return f"{stem}_{point}.jpg"


def generate_previews(config: dict) -> None:
    out_dir = rel_to_tools(config["previewBase"])
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = int(config.get("previewZoom", 2))
    preview_w, preview_h = config.get("previewSize", [720, 480])
    crop_size = (preview_w // zoom, preview_h // zoom)
    focals = focal_by_id(config)
    apertures = aperture_by_id(config)

    for photo in config["photos"]:
        src = photo_path(config, photo)
        with Image.open(src) as image:
            image = image.convert("RGB")
            anchors = focals[photo["focal"]]["anchors"]
            for point, anchor in anchors.items():
                crop = image.crop(crop_box(anchor, image.size, crop_size))
                crop = crop.resize((preview_w, preview_h), Image.Resampling.NEAREST)
                draw = ImageDraw.Draw(crop)
                label = f"{photo['focal']} {apertures[photo['aperture']]['label']} ({photo['actualAperture']}) {point} {zoom}x"
                draw.rectangle((0, 0, preview_w, 30), fill=(0, 0, 0))
                draw.text((10, 9), label, fill=(255, 255, 255))
                crop.save(out_dir / preview_filename(photo, point), quality=92)
    print("l10 sharpness previews generated")


def emit_markdown(config: dict) -> None:
    for photo in config["photos"]:
        for point in ("center", "edge"):
            path = Path(config["previewBase"]) / preview_filename(photo, point)
            print(f"![{photo['focal']} {photo['actualAperture']} {point}](tools/{path})")


def main() -> None:
    parser = argparse.ArgumentParser(description="L10 single-camera lens sharpness asset pipeline.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--generate-previews", action="store_true")
    parser.add_argument("--emit-markdown", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.check:
        check_assets(config)
    if args.generate_previews:
        generate_previews(config)
    if args.emit_markdown:
        emit_markdown(config)
    if not (args.check or args.generate_previews or args.emit_markdown):
        parser.print_help()


if __name__ == "__main__":
    main()
