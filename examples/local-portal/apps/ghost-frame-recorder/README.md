# Ghost Frame Recorder

半透明の枠で画面領域を選び、その矩形を録画する PySide6 アプリです。

## 機能

- 背景は透明、枠線と左上ドラッグゾーンのみ（録画中は枠を隠して焼き込み防止）
- `Ctrl+Shift+R` 録画開始/停止、`Ctrl+Shift+H` 枠表示切替、`Esc` 停止
- マイクは並行 WAV 録音。`imageio-ffmpeg` が使えれば `_mux.mp4` に結合
- 録画一覧ドック: 名前変更・削除・フォルダを開く・名前を付けて保存
- 連続で何度でも録画可能

## 保存先

`%USERPROFILE%\Videos\GhostFrameRecorder`（なければ `./recordings`）

## 注意

- オーバーレイ中心はクリックスルーではありません。操作の妨げになる場合は枠を非表示にしてください。
- MP4 は OpenCV `mp4v` コーデック。再生環境によっては別プレイヤーが必要な場合があります。
