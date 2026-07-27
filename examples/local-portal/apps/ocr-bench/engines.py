"""Optional OCR engine adapters with graceful import failures."""
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
    specs = [
        _probe("tesseract", "TesseractOCR (pytesseract)", _import_tesseract),
        _probe("pyocr", "PyOCR (Tesseract backend)", _import_pyocr),
        _probe("easyocr", "EasyOCR / SimpleOCR 系", _import_easyocr),
        _probe("paddleocr", "PaddleOCR 2.x (CPU)", _import_paddleocr),
        _probe("baberu", "Baberu OCR (HF ONNX)", _import_baberu),
        _probe("manga_ocr", "manga-ocr", _import_manga_ocr),
    ]
    return tuple(specs)


def _probe(engine_id: str, label: str, importer) -> EngineSpec:  # noqa: ANN001
    try:
        importer()
        return EngineSpec(engine_id, label, True)
    except Exception as exc:  # noqa: BLE001
        return EngineSpec(engine_id, label, False, str(exc))


def run_engine(engine_id: str, image: Image.Image) -> OcrResult:
    runners = {
        "tesseract": _run_tesseract,
        "pyocr": _run_pyocr,
        "easyocr": _run_easyocr,
        "paddleocr": _run_paddleocr,
        "baberu": _run_baberu,
        "manga_ocr": _run_manga_ocr,
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
        elapsed = time.perf_counter() - t0
        return OcrResult(engine_id, label, text, elapsed, boxes=boxes)
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - t0
        return OcrResult(engine_id, label, "", elapsed, error=str(exc))


def _import_tesseract() -> None:
    import pytesseract

    _ = pytesseract.get_tesseract_version()


def _import_pyocr() -> None:
    import pyocr

    tools = pyocr.get_available_tools()
    if not tools:
        raise RuntimeError("PyOCR: Tesseract バックエンドが見つかりません")


def _import_easyocr() -> None:
    import easyocr  # noqa: F401


def _import_paddleocr() -> None:
    from paddleocr import PaddleOCR  # noqa: F401


def _import_manga_ocr() -> None:
    from manga_ocr import MangaOcr  # noqa: F401


def _import_baberu() -> None:
    import huggingface_hub  # noqa: F401
    import onnxruntime  # noqa: F401

    # Availability of deps only; model is downloaded on first run.
    _ = (huggingface_hub, onnxruntime)


def _run_tesseract(image: Image.Image) -> tuple[str, list[OcrBox]]:
    import pytesseract

    text = pytesseract.image_to_string(image, lang="jpn+eng")
    data = pytesseract.image_to_data(image, lang="jpn+eng", output_type=pytesseract.Output.DICT)
    boxes: list[OcrBox] = []
    n = len(data["text"])
    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        conf = float(data["conf"][i]) if data["conf"][i] != "-1" else None
        boxes.append(
            OcrBox(
                x=int(data["left"][i]),
                y=int(data["top"][i]),
                w=int(data["width"][i]),
                h=int(data["height"][i]),
                text=word,
                confidence=conf,
            )
        )
    return text.strip(), boxes


def _run_pyocr(image: Image.Image) -> tuple[str, list[OcrBox]]:
    import pyocr
    from pyocr import builders

    tool = pyocr.get_available_tools()[0]
    text = tool.image_to_string(image, lang="jpn", builder=builders.TextBuilder())
    lines = tool.image_to_string(image, lang="jpn", builder=builders.LineBoxBuilder())
    boxes: list[OcrBox] = []
    for line in lines:
        # pyocr LineBox.box is typically ((x1,y1),(x2,y2))
        (x1, y1), (x2, y2) = line.position if hasattr(line, "position") else line.box
        boxes.append(OcrBox(x=int(x1), y=int(y1), w=int(x2 - x1), h=int(y2 - y1), text=line.content))
    return text.strip(), boxes


_easyocr_reader = None
_paddle_ocr = None
_manga_ocr = None
_baberu_ocr = None


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


def _run_paddleocr(image: Image.Image) -> tuple[str, list[OcrBox]]:
    global _paddle_ocr
    from paddleocr import PaddleOCR

    if _paddle_ocr is None:
        # 2.7 API; show_log may be ignored on newer builds.
        try:
            _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="japan", show_log=False)
        except TypeError:
            _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="japan")
    arr = np.array(image.convert("RGB"))
    result = _paddle_ocr.ocr(arr, cls=True)
    lines: list[str] = []
    boxes: list[OcrBox] = []
    for block in result or []:
        for item in block or []:
            pts, (txt, conf) = item
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x, y = int(min(xs)), int(min(ys))
            w, h = int(max(xs) - x), int(max(ys) - y)
            lines.append(txt)
            boxes.append(OcrBox(x=x, y=y, w=w, h=h, text=txt, confidence=float(conf)))
    return "\n".join(lines), boxes


def _run_manga_ocr(image: Image.Image) -> tuple[str, list[OcrBox]]:
    global _manga_ocr
    from manga_ocr import MangaOcr

    if _manga_ocr is None:
        _manga_ocr = MangaOcr()
    text = _manga_ocr(image)
    return text.strip(), []


def _run_baberu(image: Image.Image) -> tuple[str, list[OcrBox]]:
    """Baberu OCR via Hugging Face snapshot (ONNX preferred).

    Expects genshiai-daichi/baberu-ocr layout. Full-page images work as a crop of
    the whole image (Baberu is bubble-oriented — best on tight text crops).
    """
    global _baberu_ocr
    if _baberu_ocr is None:
        _baberu_ocr = _load_baberu()
    text = _baberu_ocr(image)
    # No detection boxes from the recognition-only model.
    return str(text).strip(), []


def _load_baberu():  # noqa: ANN201
    import importlib.util
    import sys
    from pathlib import Path

    from huggingface_hub import snapshot_download

    cache = Path.home() / ".cache" / "uvdrop-ocr-bench" / "baberu-ocr"
    root = Path(
        snapshot_download(
            repo_id="genshiai-daichi/baberu-ocr",
            local_dir=str(cache),
        )
    )

    # Prefer ONNX helper shipped in the model repo.
    for mod_name, file_name, cls_name, factory in (
        ("onnx_infer", "onnx_infer.py", "BaberuOnnxOCR", lambda mod, r: _make_baberu_onnx(mod, r)),
        ("inference", "inference.py", "BaberuOCR", lambda mod, r: mod.BaberuOCR(str(r))),
    ):
        path = root / file_name
        if not path.is_file():
            continue
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        spec = importlib.util.spec_from_file_location(f"uvdrop_baberu_{mod_name}", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, cls_name) or factory:
            try:
                return factory(mod, root)
            except Exception:
                continue

    raise RuntimeError(
        "Baberu OCR モデルは取得できましたが、推論エントリを初期化できませんでした。"
        f" 手動確認: {root}"
    )


def _make_baberu_onnx(mod, root):  # noqa: ANN001, ANN201
    from pathlib import Path

    root = Path(root)
    # Common layouts from the HF card / Zenn article.
    candidates = [
        ("onnx", "tokenizer"),
        (".", "tokenizer"),
        ("onnx", "."),
    ]
    last_err: Exception | None = None
    for args in candidates:
        try:
            return mod.BaberuOnnxOCR(*args)
        except TypeError:
            try:
                return mod.BaberuOnnxOCR(str(root / args[0]), str(root / args[1]))
            except Exception as exc:  # noqa: BLE001
                last_err = exc
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    if hasattr(mod, "BaberuOCR"):
        return mod.BaberuOCR(str(root))
    raise RuntimeError(f"BaberuOnnxOCR 初期化失敗: {last_err}")
