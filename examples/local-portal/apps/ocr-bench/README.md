# OCR Bench

複数 OCR エンジンの結果と所要時間を比較する Tkinter ツールです。  
画像上の検出ボックスをクリックすると、その範囲の文字を強調表示します。

## エンジン

| ID | 説明 | 入れ方 |
|---|---|---|
| tesseract | TesseractOCR via pytesseract | 既定依存 + **OS に Tesseract 本体** |
| pyocr | PyOCR（Tesseract backend） | 同上 |
| easyocr | EasyOCR（いわゆる SimpleOCR 系） | 既定依存（初回モデル DL） |
| paddleocr | PaddleOCR 2.x CPU | `uv sync --extra paddle` |
| baberu | Baberu OCR（HF ONNX。吹き出し向け） | `uv sync --extra baberu`（初回に HF から取得） |
| manga_ocr | manga-ocr | `uv sync --extra manga` |

> **baberuOCR** は PyPI パッケージではなく [genshiai-daichi/baberu-ocr](https://huggingface.co/genshiai-daichi/baberu-ocr) です。  
> 吹き出し切り出し前提の認識モデルなので、**文字が小さい全ページより、テキスト付近のクロップ**の方が向いています（ボックスは返しません）。

## システム要件

- **Tesseract**: [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) 等 + `jpn` / `eng`
- **PaddleOCR**: 重い。Python 3.11+ では `paddleocr>=2.7,<3` を推奨（2.5 系は古い Python 向け）
- オフライン PC では EasyOCR / Baberu / Paddle の初回 DL に失敗します

## 使い方

1. 画像を開く  
2. 実行するエンジンにチェック  
3. 「選択エンジンを実行」→ 右側タブにテキスト、左側に色付きボックス  
4. ボックスをクリック → その文字をステータスに表示
