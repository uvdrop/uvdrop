"""Windows clipboard DIB conversion (platform-independent byte fixtures)."""

from __future__ import annotations

import struct

import pytest

from uvdrop.appicon import _png_dimensions
from uvdrop.clipboard_image import dib_to_png


def _dib24(width: int, height: int) -> bytes:
    stride = ((width * 24 + 31) // 32) * 4
    header = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        24,
        0,
        stride * height,
        0,
        0,
        0,
        0,
    )
    # Bottom-up BGR rows, padded to stride.
    row = (b"\x00\x00\xff" * width).ljust(stride, b"\x00")
    return header + row * height


def test_dib24_converts_to_png() -> None:
    png = dib_to_png(_dib24(3, 2))
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert _png_dimensions(png) == (3, 2)


@pytest.mark.parametrize("payload", [b"", b"\x00" * 39])
def test_short_dib_is_rejected(payload: bytes) -> None:
    with pytest.raises(ValueError):
        dib_to_png(payload)
