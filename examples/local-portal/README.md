# Local portal sample (Win11)

小規模組織向けの **アプリポータル**を、自分の PC の普通のフォルダだけで試すセットです。  
UNC 共有も社内 HTTP も不要です。

```text
examples/local-portal/
  uvdrop-catalog.json     … カタログ（正本）
  serve-catalog.ps1       … 任意: HTTP エンドポイント動作確認
  apps/
    hello-stdlib/         … 依存なし CLI
    tk-counter/           … Tkinter GUI（標準ライブラリ）
    flask-health/         … Flask の極小ヘルスチェック
    csv-report/           … pandas + openpyxl（表計算っぽい）
    pillow-thumb/         … Pillow（画像系）
    meet-av-check/        … カメラ・マイク確認（Tkinter + OpenCV + sounddevice）
    ghost-frame-recorder/ … 画面領域録画オーバーレイ（PySide6 + mss）
    supertonic-reader/    … Supertonic 読み上げ（初回 ~400MB DL）
    ocr-bench/            … 複数 OCR エンジン比較
```

### 追加ツール（実用サンプル）

| アプリ | 用途 | 主な依存 |
|---|---|---|
| **Meet AV Check** | 会議前にカメラ映像・マイク音量を確認 | opencv-python-headless, sounddevice, pillow |
| **Ghost Frame Recorder** | 半透明枠で任意矩形を画面録画（マイク同時） | PySide6, mss, opencv, imageio-ffmpeg |
| **Supertonic Reader** | 原稿の TTS 読み上げ・WAV 出力 | supertonic（初回モデル DL） |
| **OCR Bench** | 画像 OCR を複数エンジンで比較 | pytesseract, easyocr 等（Tesseract 本体は別途） |

PaddleOCR / Baberu OCR / manga-ocr は `ocr-bench` の optional extras です。

```powershell
cd examples\local-portal\apps\ocr-bench
uv sync --extra paddle
uv sync --extra baberu
uv sync --extra manga
```

詳細は各 `apps/*/README.md` を参照してください。

## 1. ファイルカタログ（いちばん簡単）

1. uvdrop を起動  
2. **設定 → カタログ** で次を追加（この `uvdrop-catalog.json` のフルパス）:

   ```text
   D:\...\uvdrop\examples\local-portal\uvdrop-catalog.json
   ```

3. メインの **カタログから開く** → 好きなアプリを選ぶ  
4. 実行前確認（パッケージ一覧・許可 / 禁止）→ 起動

`apps[].path` はカタログ相対なので、フォルダごと別ドライブにコピーしても動きます。

## 2. HTTP エンドポイント（ローカル擬似）

UNC や本番 API が無いときでも、カタログ取得だけ HTTP で試せます。

```powershell
cd examples\local-portal
powershell -ExecutionPolicy Bypass -File .\serve-catalog.ps1
```

表示された URL（例: `http://127.0.0.1:8765/uvdrop-catalog.json`）を  
設定 → カタログに登録します。

- レスポンス JSON の `base` は、このポータルフォルダの絶対パスに書き換えて配信します  
- アプリ本体のパス解決は `base` + 相対 `path`  
- 認証付き社内 API の再現までは対象外（トークン入力は未実装）

## できないこと / 別途必要なこと

| 項目 | ローカルでできる？ |
|---|---|
| カタログ JSON + 相対フォルダ起動 | はい |
| 許可 / 禁止・Python 版チェック | はい（設定で） |
| HTTP カタログ取得 | はい（`serve-catalog.ps1`） |
| UNC `\\server\share\...` | 実共有が必要 |
| 本番の社内 Web API 連携 | 実エンドポイントが必要 |

計測用の重いサンプル群は `samples/`（`docs/BENCHMARK.md`）を使ってください。こちらは **配布・カタログ体験用の軽量パック**です。
