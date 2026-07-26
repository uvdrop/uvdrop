"""Generate scenario sample apps under samples/scenarios/ + catalog JSON.

Each sample is a minimal pyproject + main.py that imports the stack and exits.
Goal: exercise ``uv sync`` → ``uv run`` end-to-end, not full product demos.

  python samples/generate_samples.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = ROOT / "scenarios"

# tier: light (CI-friendly), medium (minutes), heavy (large wheels / GPU stacks)
SPECS: list[dict] = [
    # --- data / viz ---
    {
        "id": "csv-xlsx-matplotlib",
        "tier": "light",
        "name": "CSV/XLSX → matplotlib",
        "summary": "pandas + openpyxl + matplotlib (Agg)",
        "deps": ["pandas>=2.0", "openpyxl>=3.1", "matplotlib>=3.8"],
        "imports": ["pandas", "openpyxl", "matplotlib"],
        "extra": "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n",
    },
    {
        "id": "plotly-dashboard",
        "tier": "light",
        "name": "Plotly chart",
        "summary": "plotly figure build (no browser)",
        "deps": ["plotly>=5.18", "pandas>=2.0"],
        "imports": ["plotly", "pandas"],
        "extra": "import plotly.express as px\n",
    },
    {
        "id": "unv-df4-mdf-hint",
        "tier": "medium",
        "name": "Measurement file hint (ASAM)",
        "summary": "asammdf for MDF; UNV/DF4 often need vendor SDKs — import smoke only",
        "deps": ["asammdf>=7.4", "numpy>=1.26"],
        "imports": ["asammdf", "numpy"],
    },
    # --- GUI realtime ---
    {
        "id": "pyside6-import",
        "tier": "medium",
        "name": "PySide6 import",
        "summary": "Qt binding smoke (no window)",
        "deps": ["PySide6>=6.6"],
        "imports": ["PySide6"],
        "extra": "from PySide6 import QtCore\n",
    },
    {
        "id": "pyqt5-import",
        "tier": "medium",
        "name": "PyQt5 import",
        "summary": "Qt5 binding smoke (no window). Pins PyQt5-Qt5==5.15.2 — newer Qt5 wheels dropped win_amd64 on PyPI",
        "deps": ["PyQt5>=5.15", "PyQt5-Qt5==5.15.2"],
        "imports": ["PyQt5"],
        "extra": "from PyQt5 import QtCore\n",
    },
    # --- classic ML ---
    {
        "id": "sklearn-basic",
        "tier": "light",
        "name": "scikit-learn",
        "summary": "fit a tiny model",
        "deps": ["scikit-learn>=1.4", "numpy>=1.26"],
        "imports": ["sklearn", "numpy"],
        "extra": (
            "from sklearn.linear_model import LogisticRegression\n"
            "import numpy as np\n"
            "X = np.array([[0.0], [1.0], [2.0], [3.0]])\n"
            "y = np.array([0, 0, 1, 1])\n"
            "LogisticRegression().fit(X, y)\n"
        ),
    },
    {
        "id": "lightgbm-basic",
        "tier": "medium",
        "name": "LightGBM",
        "summary": "tiny booster fit",
        "deps": ["lightgbm>=4.0", "numpy>=1.26", "scikit-learn>=1.4"],
        "imports": ["lightgbm", "numpy"],
        "extra": (
            "import lightgbm as lgb\n"
            "import numpy as np\n"
            "X = np.random.randn(40, 3)\n"
            "y = (X[:, 0] > 0).astype(int)\n"
            "lgb.LGBMClassifier(n_estimators=5, verbose=-1).fit(X, y)\n"
        ),
    },
    {
        "id": "timeseries-statsmodels",
        "tier": "medium",
        "name": "Time series (statsmodels)",
        "summary": "statsmodels import + tiny ARIMA-ready series",
        "deps": ["statsmodels>=0.14", "pandas>=2.0", "numpy>=1.26"],
        "imports": ["statsmodels", "pandas"],
    },
    # --- deep learning ---
    {
        "id": "torch-cpu",
        "tier": "heavy",
        "name": "PyTorch CPU",
        "summary": "torch tensor op (CPU wheel)",
        "deps": ["torch"],
        "imports": ["torch"],
        "extra": "import torch\nx = torch.ones(2, 2); _ = x @ x\n",
    },
    {
        "id": "tensorflow-cpu",
        "tier": "heavy",
        "name": "TensorFlow",
        "summary": "tf constant (large download)",
        "deps": ["tensorflow"],
        "imports": ["tensorflow"],
        "extra": "import tensorflow as tf\n_ = tf.constant(1)\n",
    },
    {
        "id": "transformers-tiny",
        "tier": "heavy",
        "name": "Transformers",
        "summary": "import transformers (no model download)",
        "deps": ["transformers>=4.40", "torch"],
        "imports": ["transformers", "torch"],
    },
    {
        "id": "diffusers-import",
        "tier": "heavy",
        "name": "Diffusers",
        "summary": "import diffusers (no pipeline download)",
        "deps": ["diffusers>=0.27", "torch"],
        "imports": ["diffusers", "torch"],
    },
    # --- vision / OCR / edge ---
    {
        "id": "opencv-pillow",
        "tier": "light",
        "name": "OpenCV + Pillow",
        "summary": "image array smoke",
        "deps": ["opencv-python-headless>=4.8", "Pillow>=10.0", "numpy>=1.26"],
        "imports": ["cv2", "PIL", "numpy"],
        "extra": (
            "import cv2\nimport numpy as np\nfrom PIL import Image\n"
            "img = np.zeros((8, 8, 3), dtype=np.uint8)\n"
            "_ = Image.fromarray(img)\n_ = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)\n"
        ),
    },
    {
        "id": "onnxruntime",
        "tier": "medium",
        "name": "ONNX Runtime",
        "summary": "onnxruntime import",
        "deps": ["onnxruntime>=1.16"],
        "imports": ["onnxruntime"],
    },
    {
        "id": "tflite-runtime-hint",
        "tier": "medium",
        "name": "TFLite-ish (ai-edge-litert)",
        "summary": "Prefer ai-edge-litert where tflite-runtime is unavailable",
        "deps": ["ai-edge-litert"],
        "imports": [],
        "extra": (
            "try:\n"
            "    import ai_edge_litert  # noqa: F401\n"
            "except ImportError:\n"
            "    import importlib\n"
            "    importlib.import_module('ai_edge_litert')\n"
        ),
    },
    {
        "id": "ultralytics-yolo",
        "tier": "heavy",
        "name": "Ultralytics YOLO",
        "summary": "import ultralytics (no weights download)",
        "deps": ["ultralytics"],
        "imports": ["ultralytics"],
    },
    {
        "id": "paddleocr-import",
        "tier": "heavy",
        "name": "PaddleOCR",
        "summary": "import paddleocr (large)",
        "deps": ["paddleocr", "paddlepaddle"],
        "imports": ["paddleocr"],
    },
    # --- Windows automation ---
    {
        "id": "pywin32-com",
        "tier": "light",
        "name": "pywin32 COM",
        "summary": "win32com import (Windows)",
        "deps": ["pywin32>=306"],
        "imports": ["win32com"],
        "extra": "import win32com.client  # noqa: F401\n",
        "platforms": ["win32"],
    },
    {
        "id": "pyautogui-import",
        "tier": "medium",
        "name": "PyAutoGUI",
        "summary": "import only (no input injection)",
        "deps": ["pyautogui>=0.9"],
        "imports": ["pyautogui"],
    },
    # --- audio / camera (import only) ---
    {
        "id": "audio-librosa",
        "tier": "medium",
        "name": "Audio (librosa)",
        "summary": "librosa import",
        "deps": ["librosa>=0.10", "numpy>=1.26"],
        "imports": ["librosa", "numpy"],
    },
    {
        "id": "camera-opencv",
        "tier": "light",
        "name": "Camera stack (OpenCV)",
        "summary": "VideoCapture API available — does not open a device",
        "deps": ["opencv-python-headless>=4.8"],
        "imports": ["cv2"],
        "extra": "import cv2\nassert hasattr(cv2, 'VideoCapture')\n",
    },
    # --- web apps (import / ASGI app object only) ---
    {
        "id": "flask-app",
        "tier": "light",
        "name": "Flask",
        "summary": "create Flask app object, no server",
        "deps": ["flask>=3.0"],
        "imports": ["flask"],
        "extra": "from flask import Flask\napp = Flask(__name__)\n",
    },
    {
        "id": "fastapi-app",
        "tier": "light",
        "name": "FastAPI",
        "summary": "create FastAPI app object, no server",
        "deps": ["fastapi>=0.110"],
        "imports": ["fastapi"],
        "extra": "from fastapi import FastAPI\napp = FastAPI()\n",
    },
    {
        "id": "bottle-app",
        "tier": "light",
        "name": "Bottle",
        "summary": "import bottle",
        "deps": ["bottle>=0.12"],
        "imports": ["bottle"],
    },
    {
        "id": "django-setup",
        "tier": "medium",
        "name": "Django",
        "summary": "django.setup with minimal settings",
        "deps": ["django>=5.0"],
        "imports": ["django"],
        "extra": (
            "import django\n"
            "from django.conf import settings\n"
            "if not settings.configured:\n"
            "    settings.configure(DEBUG=True, SECRET_KEY='uvdrop-bench', USE_TZ=True)\n"
            "    django.setup()\n"
        ),
    },
    {
        "id": "streamlit-import",
        "tier": "medium",
        "name": "Streamlit",
        "summary": "import streamlit (no server)",
        "deps": ["streamlit>=1.30"],
        "imports": ["streamlit"],
    },
    {
        "id": "gradio-import",
        "tier": "medium",
        "name": "Gradio",
        "summary": "import gradio (no server)",
        "deps": ["gradio>=4.0"],
        "imports": ["gradio"],
    },
    # --- RAG ---
    {
        "id": "faiss-cpu",
        "tier": "medium",
        "name": "FAISS CPU",
        "summary": "tiny index add/search",
        "deps": ["faiss-cpu", "numpy>=1.26"],
        "imports": ["faiss", "numpy"],
        "extra": (
            "import faiss\nimport numpy as np\n"
            "xb = np.random.random((16, 8)).astype('float32')\n"
            "index = faiss.IndexFlatL2(8)\n"
            "index.add(xb)\n"
            "_ = index.search(xb[:1], 3)\n"
        ),
    },
    # --- always-on control ---
    {
        "id": "stdlib-hello",
        "tier": "light",
        "name": "Stdlib hello",
        "summary": "no third-party deps (baseline timing)",
        "deps": [],
        "imports": [],
        "extra": "print('hello from stdlib sample')\n",
    },
]


def _pyproject(spec: dict) -> str:
    deps = ",\n".join(f'    "{d}"' for d in spec["deps"])
    if deps:
        deps = "\n" + deps + ",\n"
    return (
        f'[project]\n'
        f'name = "uvdrop-sample-{spec["id"]}"\n'
        f'version = "0.0.1"\n'
        f'description = "{spec["summary"]}"\n'
        f'requires-python = ">=3.11"\n'
        f"dependencies = [{deps}]\n"
        f"\n"
        f"[tool.uv]\n"
        f"package = false\n"
    )


def _main_py(spec: dict) -> str:
    extra = spec.get("extra") or ""
    imports = "\n".join(f"import {m}  # noqa: F401" for m in spec.get("imports") or [])
    body_parts = [p for p in (imports, extra) if p]
    body = "\n".join(body_parts)
    if body:
        body = "\n    " + body.replace("\n", "\n    ") + "\n"
    return (
        '"""uvdrop scenario sample — import / tiny smoke, then exit."""\n'
        "from __future__ import annotations\n"
        "\n"
        "\n"
        "def main() -> int:\n"
        f"{body}"
        "    print(\"uvdrop-sample-ok\", flush=True)\n"
        "    return 0\n"
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    raise SystemExit(main())\n"
    )


def generate() -> Path:
    SCENARIOS.mkdir(parents=True, exist_ok=True)
    apps: list[dict] = []
    for spec in SPECS:
        dest = SCENARIOS / spec["id"]
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "pyproject.toml").write_text(_pyproject(spec), encoding="utf-8")
        (dest / "main.py").write_text(_main_py(spec), encoding="utf-8")
        meta = {
            "id": spec["id"],
            "tier": spec["tier"],
            "name": spec["name"],
            "summary": spec["summary"],
            "platforms": spec.get("platforms") or ["any"],
        }
        (dest / "sample.meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        apps.append(            {
                "id": spec["id"],
                "name": spec["name"],
                "summary": f"[{spec['tier']}] {spec['summary']}",
                "path": f"scenarios/{spec['id']}",
                "command": "main.py",
                "tier": spec["tier"],
            }
        )

    catalog = {
        "version": 1,
        "catalog": "uvdrop scenario samples",
        "base": str(ROOT),
        "apps": [
            {
                "id": a["id"],
                "name": a["name"],
                "summary": a["summary"],
                "path": a["path"],
                "command": a["command"],
            }
            for a in apps
        ],
    }
    cat_path = ROOT / "uvdrop-catalog.json"
    cat_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    index = {"samples": [{k: s[k] for k in ("id", "tier", "name", "summary")} | {"platforms": s.get("platforms") or ["any"]} for s in SPECS]}
    (ROOT / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"generated {len(SPECS)} samples → {SCENARIOS}")
    print(f"catalog → {cat_path}")
    return cat_path


if __name__ == "__main__":
    generate()
