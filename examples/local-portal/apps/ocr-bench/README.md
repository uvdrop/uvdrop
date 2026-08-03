# OCR Bench

pip だけで入る OCR を並べて比較します（システム Tesseract / HuggingFace 専用モデルは扱いません）。

## エンジン

| ID | パッケージ | メモ |
|---|---|---|
| **RapidOCR** | `rapidocr-onnxruntime` | 既定のおすすめ。ONNX・比較的軽い |
| **EasyOCR** | `easyocr` | 日英対応。初回にモデル DL（torch 系で重い） |

## 使い方

1. 画像を開く
2. 使いたいエンジンにチェック
3. 実行 → ボックスとテキストを比較

以前の Tesseract / Paddle / Baberu / manga-ocr は、追加セットアップが必要になりやすいため外しています。
