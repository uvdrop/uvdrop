# Supertonic Reader

`supertonic` パッケージを使った Tkinter 読み上げツールです。

## 機能

- 原稿エディタ、`.txt` / `.md` 読み込み
- 声 M1–M5 / F1–F5、速度・間（silence_duration）、言語
- 再生 / 停止 / WAV 書き出し
- 初回 Play でモデル自動ダウンロード（約 400MB）

## 注意

- 初回はネットワークとディスク容量が必要です。
- 合成はバックグラウンドスレッド、再生は sounddevice です。
