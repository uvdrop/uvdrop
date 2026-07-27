"""Local portal sample — generate a tiny PNG with Pillow."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> int:
    out = Path(__file__).resolve().parent / "_thumb.png"
    img = Image.new("RGB", (128, 128), color=(32, 96, 160))
    draw = ImageDraw.Draw(img)
    draw.rectangle((24, 24, 104, 104), outline=(240, 240, 240), width=3)
    draw.text((36, 56), "uvdrop", fill=(240, 240, 240))
    img.save(out)
    print("uvdrop-portal-ok pillow-thumb", flush=True)
    print(f"size={img.size} out={out.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
