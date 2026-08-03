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
    flask-health/         … Flask 常駐サーバ（URL 表示・ブラウザ確認）
    csv-report/           … pandas + openpyxl（表計算っぽい）
    pillow-thumb/         … Pillow（画像系）
    meet-av-check/        … カメラ・マイク確認（Tkinter + OpenCV + sounddevice）
    ghost-frame-recorder/ … 画面領域録画オーバーレイ（PySide6 + mss）
    supertonic-reader/    … Supertonic 読み上げ（初回 ~400MB DL）
    ocr-bench/            … 複数 OCR エンジン比較
    diff-shot/            … Before/After 差分（見た目重視）
    clip-factory/         … クリップボード画像工場
    praise-card/          … ありがとうカード生成（空気づくり）
    rename-preview/       … プレビュー付き一括リネーム
    size-map/             … フォルダ容量ツリーマップ
    qr-flip/              … QRパラパラ近接転写
    outlook-draft/        … Outlook COM 下書き
    one-min-retro/        … 1分 Keep/Problem/Try
```

### 追加ツール（実用サンプル）

| アプリ | 用途 | 主な依存 |
|---|---|---|
| **Meet AV Check** | 会議前にカメラ映像・マイク音量を確認 | opencv-python-headless, sounddevice, pillow |
| **Ghost Frame Recorder** | 半透明枠で任意矩形を画面録画（マイク同時） | PySide6, mss, opencv, imageio-ffmpeg |
| **Supertonic Reader** | 原稿の TTS 読み上げ・WAV 出力 | supertonic（初回モデル DL） |
| **OCR Bench** | RapidOCR + EasyOCR 比較（pip のみ） | rapidocr-onnxruntime, easyocr |
| **Flask health** | Flask サーバ常駐＋ブラウザ用 URL | flask |
| **Diff Shot** | Before/After 差分ヒートマップ | PySide6, Pillow, numpy |
| **Clip Factory** | クリップボード画像のトリム／幅そろえ | PySide6, Pillow |
| **Praise Card** | 貼れる讃めカード生成 | PySide6, Pillow |
| **Rename Preview** | 一括リネームを表で確認してから実行 | PySide6 |
| **Size Map** | フォルダ容量を色つき地図で可視化 | PySide6 |
| **QR Flip** | QRパラパラで近傍テキスト転写 | PySide6, qrcode, OpenCV |
| **Outlook Draft** | Outlook 下書きを COM で開く | PySide6, pywin32 |
| **1-min Retro** | Keep/Problem/Try 一枚絵 | PySide6, Pillow |

見た目の引きと、**全画面＋STEP＋次の操作STATUS**で迷子にならない体験を優先しています。

各アプリには `ui_shell.py`（最大化・ステップ文言）が同梱されます（uvdrop 取り込み後も単体で動くため）。

第一陣（資料・日常）＋第二陣（地図／ワンダー／COM／空気）＋入口サンプルを同一 UX 規約で揃えています。

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
