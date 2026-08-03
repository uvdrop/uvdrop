"""OCR engines — pip-installable only (no system Tesseract / HuggingFace repos)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from PIL import Image


@dataclass
class OcrBox:
    x: int
    y: int
    w: int
    h: int
    text: str = ""
    confidence: float | None = None


@dataclass
class OcrResult:
    engine_id: str
    label: str
    text: str
    elapsed_sec: float
    boxes: list[OcrBox] = field(default_factory=list)
    error: str | None = None


@dataclass
class EngineSpec:
    engine_id: str
    label: str
    available: bool
    note: str = ""


@lru_cache(maxsize=1)
def discover_engines() -> tuple[EngineSpec, ...]:
    """Only engines that install via pip and run without extra system setup."""
    return (
        _probe("rapidocr", "RapidOCR (ONNX / pip)", _import_rapidocr),
        _probe("easyocr", "EasyOCR（初回モデルDL・やや重い）", _import_easyocr),
    )


def _probe(engine_id: str, label: str, importer) -> EngineSpec:  # noqa: ANN001
    try:
        importer()
        return EngineSpec(engine_id, label, True)
    except Exception as exc:  # noqa: BLE001
        return EngineSpec(engine_id, label, False, str(exc))


def run_engine(engine_id: str, image: Image.Image) -> OcrResult:
    runners = {
        "rapidocr": _run_rapidocr,
        "easyocr": _run_easyocr,
    }
    label = engine_id
    available = True
    note = ""
    for spec in discover_engines():
        if spec.engine_id == engine_id:
            label = spec.label
            available = spec.available
            note = spec.note
            break
    if not available:
        return OcrResult(engine_id, label, "", 0.0, error=note or "利用不可")
    runner = runners.get(engine_id)
    if runner is None:
        return OcrResult(engine_id, label, "", 0.0, error="未知のエンジン")
    t0 = time.perf_counter()
    try:
        text, boxes = runner(image)
        return OcrResult(engine_id, label, text, time.perf_counter() - t0, boxes=boxes)
    except Exception as exc:  # noqa: BLE001
        return OcrResult(engine_id, label, "", time.perf_counter() - t0, error=str(exc))


def _import_rapidocr() -> None:
    from rapidocr_onnxruntime import RapidOCR  # noqa: F401


def _import_easyocr() -> None:
    import easyocr  # noqa: F401


_rapid: object | None = None
_easyocr_reader = None


def _run_rapidocr(image: Image.Image) -> tuple[str, list[OcrBox]]:
    global _rapid
    from rapidocr_onnxruntime import RapidOCR

    if _rapid is None:
        _rapid = RapidOCR()
    arr = np.array(image.convert("RGB"))
    result, _elapse = _rapid(arr)  # type: ignore[operator]
    lines: list[str] = []
    boxes: list[OcrBox] = []
    for item in result or []:
        # [box, text, score]
        if not item or len(item) < 2:
            continue
        pts, txt = item[0], item[1]
        conf = float(item[2]) if len(item) > 2 else None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        lines.append(str(txt))
        boxes.append(OcrBox(x=x, y=y, w=w, h=h, text=str(txt), confidence=conf))
    return "\n".join(lines), boxes


def _run_easyocr(image: Image.Image) -> tuple[str, list[OcrBox]]:
    global _easyocr_reader
    import easyocr

    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["ja", "en"], gpu=False)
    arr = np.array(image.convert("RGB"))
    rows = _easyocr_reader.readtext(arr)
    lines: list[str] = []
    boxes: list[OcrBox] = []
    for bbox, txt, conf in rows:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        lines.append(txt)
        boxes.append(OcrBox(x=x, y=y, w=w, h=h, text=txt, confidence=float(conf)))
    return "\n".join(lines), boxes
