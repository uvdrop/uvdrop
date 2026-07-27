# Meet AV Check

リモート会議前にカメラ映像とマイク音量を確認する Tkinter アプリです。

## 依存

- OpenCV (headless) — カメラ列挙・プレビュー
- sounddevice — マイクリスト・レベルメータ・短時間録音/再生
- Pillow — プレビュー表示

## 使い方

1. カメラ/マイクをドロップダウンで選択
2. プレビューと RMS メータで状態を確認
3. 「2秒録音して再生」で自分の声を確認

Windows では DirectShow (`CAP_DSHOW`) でカメラを開きます。
