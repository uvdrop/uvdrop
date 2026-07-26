"""Read a Windows clipboard bitmap and encode it as PNG (stdlib only)."""

from __future__ import annotations

import os
import struct
import zlib

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_BI_RGB = 0
_BI_BITFIELDS = 3
_CF_DIB = 8
_CF_DIBV5 = 17


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _rgba_png(width: int, height: int, rows: list[bytes]) -> bytes:
    raw = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        _PNG_MAGIC
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def dib_to_png(dib: bytes) -> bytes:
    """Convert an uncompressed 24/32-bit CF_DIB or CF_DIBV5 payload to PNG."""
    if len(dib) < 40:
        raise ValueError("クリップボードの画像データが短すぎます")
    header_size, width, signed_height, planes, bpp, compression = struct.unpack_from(
        "<IiiHHI", dib, 0
    )
    if header_size < 40 or header_size > len(dib):
        raise ValueError("クリップボード画像のヘッダーが不正です")
    if width <= 0 or signed_height == 0 or planes != 1:
        raise ValueError("クリップボード画像のサイズが不正です")
    if bpp not in (24, 32) or compression not in (_BI_RGB, _BI_BITFIELDS):
        raise ValueError("貼り付けできる画像は24/32ビットのスクリーンショットです")

    height = abs(signed_height)
    top_down = signed_height < 0
    # BITMAPINFOHEADER stores three masks after the 40-byte header for
    # BI_BITFIELDS. V4/V5 headers include masks inside their declared size.
    pixel_offset = header_size + (12 if header_size == 40 and compression == _BI_BITFIELDS else 0)
    stride = ((width * bpp + 31) // 32) * 4
    required = pixel_offset + stride * height
    if required > len(dib):
        raise ValueError("クリップボード画像のピクセルデータが不足しています")

    rows: list[bytes] = []
    for out_y in range(height):
        source_y = out_y if top_down else height - 1 - out_y
        offset = pixel_offset + source_y * stride
        row = bytearray()
        for x in range(width):
            pos = offset + x * (bpp // 8)
            blue, green, red = dib[pos : pos + 3]
            alpha = dib[pos + 3] if bpp == 32 else 255
            # CF_DIB screenshots commonly leave alpha at zero despite being
            # fully opaque. Treat zero as opaque so pasted images stay visible.
            if alpha == 0:
                alpha = 255
            row.extend((red, green, blue, alpha))
        rows.append(bytes(row))
    return _rgba_png(width, height, rows)


def clipboard_png() -> bytes:
    """Return a clipboard screenshot as PNG, or raise ValueError."""
    if os.name != "nt":
        raise ValueError("画像の貼り付けは Windows で利用できます")

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.restype = ctypes.c_size_t

    if not user32.OpenClipboard(None):
        raise ValueError("クリップボードを開けませんでした")
    try:
        handle = None
        for fmt in (_CF_DIBV5, _CF_DIB):
            handle = user32.GetClipboardData(fmt)
            if handle:
                break
        if not handle:
            raise ValueError("クリップボードに画像がありません")
        size = kernel32.GlobalSize(handle)
        pointer = kernel32.GlobalLock(handle)
        if not pointer or not size:
            raise ValueError("クリップボード画像を読み取れませんでした")
        try:
            dib = ctypes.string_at(pointer, size)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
    return dib_to_png(dib)
