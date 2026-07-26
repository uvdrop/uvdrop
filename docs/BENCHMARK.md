# Sample scenario bench

Realistic **import-smoke** apps under `samples/scenarios/` exercise
`prepare_launch` → `uv sync` (venv) → `uv run` → discard, with timing reports.

They are **not** full products: each `main.py` imports the stack (or runs a tiny
fit) and prints `uvdrop-sample-ok`.

## Generate

```powershell
python samples/generate_samples.py
```

Catalog: `samples/uvdrop-catalog.json` (register in Settings → Catalogs).

## Run bench

```powershell
# baseline / CI-friendly (3 samples in parallel by default)
python scripts/bench_samples.py --tier light --workers 3

# also Qt / LightGBM / FAISS / Streamlit / …
python scripts/bench_samples.py --tier light,medium --workers 3

# large wheels (torch / TF / YOLO / PaddleOCR / …) — expect long sync
python scripts/bench_samples.py --tier heavy --timeout 600 --workers 2

# one-off
python scripts/bench_samples.py --ids stdlib-hello,flask-app,sklearn-basic
```

Reports: standalone `reports/bench/bench-*.html` + raw `.json`
(also `latest.html` / `latest.json`). The HTML report includes:

- phase-stacked timing bars with tooltips
- tier/search filters and sorting
- success/failure, wall time, parallel speedup, median and P90 sync time
- slowest-sample diagnosis and per-sample logs

Columns: `prepare_s` (copy/policy), `sync_s` (**venv / uv sync**), `run_s`,
`cleanup_s`, `total_s`.

Each run uses a fresh temporary `LOCALAPPDATA`. Every copied app, venv, dotenv
file, and run-local uv cache is removed in a `finally` block, including failed
samples. Only HTML/JSON reports remain. Parallel jobs use unique app keys and
share only the disposable uv cache for that run.

If `sync_s` is huge, check network, proxy (`Settings → Proxy`), PyPI mirror, and AV scanning of `%LOCALAPPDATA%\uvdrop\envs`.

**Warm vs cold cache:** the machine-wide uv cache (`UV_CACHE_DIR`, usually under the user profile) survives between disposable bench runs. A PC that already downloaded PySide6 / sklearn once will look much faster than a brand-new machine. For a first-PC estimate, run with an empty cache:

```powershell
$env:UV_CACHE_DIR = "$env:TEMP\uvdrop-cold-cache"
New-Item -ItemType Directory -Force $env:UV_CACHE_DIR | Out-Null
python scripts/bench_samples.py --tier light --workers 3
```

**PyQt5 on Windows:** current `PyQt5-Qt5` releases on PyPI often omit `win_amd64` wheels. The sample pins `PyQt5-Qt5==5.15.2` (last Windows build). Prefer PySide6 when possible.

## Tiers

| Tier | Intent |
|---|---|
| `light` | Fast feedback (stdlib, pandas/matplotlib, flask/fastapi, sklearn, opencv, pywin32, …) |
| `medium` | Minutes (PySide6/PyQt5, LightGBM, FAISS, Streamlit/Gradio/Django, ONNX, librosa, …) |
| `heavy` | Large downloads (torch, tensorflow, transformers, diffusers, ultralytics, paddleocr, …) |

## Japanese

想定ユース（CSV/XLSX/計測ファイル、Qt リアルタイム、各種 ML、COM/GUI 自動化、音声・カメラ、OCR/YOLO、ONNX/TFLite、Web、生成 AI、RAG）を **依存インストール〜起動成功** で測るための土台です。計測結果は uv の強みの説明や、「遅い＝通信／プロキシ／ウイルス対策を疑え」の判断材料になります。
