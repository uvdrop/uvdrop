"""Icon discovery and PNG → ICO wrapping."""

from __future__ import annotations

import struct
import zlib

import pytest

from uvdrop.appicon import ensure_ico, find_icon_candidates, png_to_ico


def _png(width: int = 32, height: int = 32) -> bytes:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\xff\x00\x00\xff" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(
        b"IEND", b""
    )


def test_png_to_ico_header(tmp_path) -> None:
    data = png_to_ico(_png(48, 48))
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind, count) == (0, 1, 1)
    width, height = data[6], data[7]
    assert (width, height) == (48, 48)
    offset = struct.unpack("<I", data[18:22])[0]
    assert data[offset:].startswith(b"\x89PNG")


def test_png_to_ico_marks_large_images_as_256(tmp_path) -> None:
    data = png_to_ico(_png(512, 512))
    assert (data[6], data[7]) == (0, 0)


def test_ensure_ico_converts_png(tmp_path) -> None:
    src = tmp_path / "logo.png"
    src.write_bytes(_png())
    out = ensure_ico(src, tmp_path / "out", "myapp")
    assert out == tmp_path / "out" / "myapp.ico"
    assert out.read_bytes()[:4] == b"\x00\x00\x01\x00"


def test_ensure_ico_rejects_other_formats(tmp_path) -> None:
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"nope")
    with pytest.raises(ValueError):
        ensure_ico(src, tmp_path / "out", "myapp")


def test_find_candidates_prefers_named_and_shallow(tmp_path) -> None:
    ws = tmp_path / "ws"
    (ws / "assets").mkdir(parents=True)
    (ws / "screenshot.png").write_bytes(_png())
    (ws / "assets" / "icon.png").write_bytes(_png())
    (ws / "logo.ico").write_bytes(png_to_ico(_png()))

    found = find_icon_candidates(ws)
    assert found[0].name == "logo.ico"
    assert [p.name for p in found[:2]] == ["logo.ico", "icon.png"]
    assert (ws / "screenshot.png") in found
