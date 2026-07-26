"""Find an app's own image and turn it into a shortcut icon.

Windows shortcuts need an .ico. Since Vista an .ico may simply wrap a PNG, so a
PNG found inside the app can be reused without any imaging dependency.
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

SEARCH_DIRS = (
    ".",
    "assets",
    "asset",
    "icons",
    "icon",
    "images",
    "image",
    "img",
    "static",
    "resources",
    "res",
    "media",
)

PREFERRED_STEMS = ("icon", "appicon", "app", "logo", "thumb", "thumbnail", "favicon", "cover")

SUPPORTED_EXTS = (".ico", ".png")

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_MAX_ICON_BYTES = 4 * 1024 * 1024


def find_icon_candidates(workspace: Path, *, limit: int = 12) -> list[Path]:
    """Images that look like an app icon, best guess first."""
    workspace = workspace.resolve()
    seen: set[Path] = set()
    found: list[Path] = []
    for rel in SEARCH_DIRS:
        base = workspace if rel == "." else workspace / rel
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            if path in seen or path.stat().st_size > _MAX_ICON_BYTES:
                continue
            seen.add(path)
            found.append(path)

    def rank(path: Path) -> tuple[int, int, int, str]:
        stem = path.stem.lower()
        named = 0 if any(s in stem for s in PREFERRED_STEMS) else 1
        ico_first = 0 if path.suffix.lower() == ".ico" else 1
        depth = len(path.relative_to(workspace).parts)
        return (named, ico_first, depth, stem)

    found.sort(key=rank)
    return found[:limit]


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(_PNG_MAGIC) or len(data) < 24:
        raise ValueError("PNG ファイルとして読み取れません")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if not width or not height:
        raise ValueError("PNG のサイズが不正です")
    return width, height


def png_to_ico(png: bytes) -> bytes:
    """Wrap PNG bytes in a single-image ICO container (Vista+)."""
    width, height = _png_dimensions(png)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        0 if width >= 256 else width,
        0 if height >= 256 else height,
        0,
        0,
        1,
        32,
        len(png),
        len(header) + 16,
    )
    return header + entry + png


def ensure_ico(source: Path, dest_dir: Path, name: str) -> Path:
    """Copy or convert `source` into `<dest_dir>/<name>.ico`."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name}.ico"
    suffix = source.suffix.lower()
    if suffix == ".ico":
        if source.resolve() != dest.resolve():
            shutil.copyfile(source, dest)
        return dest
    if suffix == ".png":
        dest.write_bytes(png_to_ico(source.read_bytes()))
        return dest
    raise ValueError(f"アイコンに使えない形式です: {source.suffix}（.ico / .png のみ）")
