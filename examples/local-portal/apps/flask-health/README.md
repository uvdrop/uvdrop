# Flask health

小さな Flask サーバを起動し、ブラウザで確認するポータル用サンプルです。

## 使い方

1. uvdrop から起動（カタログの command は `main.py --port {port}`）
2. 空きポートが自動割当され、制御ウィンドウに URL が表示される
3. 「ブラウザで開く」または自動でブラウザが開く
4. `/health` で JSON `{"status":"ok",...}`
5. 制御ウィンドウを閉じるとサーバ停止

ポートは `--port` 引数、または環境変数 `UVDROP_PORT` / `PORT` を読みます。
stdout には `UVDROP_URL=http://127.0.0.1:…/` も出ます。
