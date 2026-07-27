# Bundled uv runtime

uvdrop は公式の `uv.exe` を同梱して起動します（なければ PATH）。  
**uvdrop のアプリ版（例: 0.10.0）と、同梱 `uv.exe` の版は別物**です。

ステータスバーに `[同梱|PATH] uv x.y.z` と出ます。迷ったらそこを見てください。

## いまの想定

| 項目 | 内容 |
|---|---|
| 同梱の置き場 | `resources/tools/windows-x64/uv.exe`（Installer では `tools/uv.exe`） |
| 推奨レンジ | **0.11.6 以上**（RECORD 関連の修正を含む 0.11 系） |
| 開発ツリーでの実測例 | **0.11.31**（`uv audit` コマンドあり） |

「uv が 0.6.0」に見える場合は、だいたい次のどちらかです。

1. **uvdrop 自体の古いリリース番号**（CHANGELOG の 0.6.x）と混同している  
2. 古い Setup.exe を入れたまま、同梱 `uv.exe` を更新していない  

## `uv audit` / マルウェアチェックについて

Astral の新しい監査機能（`uv audit`、任意の `UV_MALWARE_CHECK=1`）は **uv 0.11 系のプレビュー**です。  
同梱が 0.11.x ならコマンドは使えます。uvdrop GUI から自動で `uv audit` を回す導線はまだありません（実行前ガードは従来どおり許可 / 禁止リストと依存ツリー確認）。

将来 GUI 連携する場合も、**同梱 uv を上げるだけ**で機能面は追従しやすい構成です。

## 差し替え手順（開発ツリー）

```powershell
cd D:\path\to\uvdrop

# 最新
powershell -ExecutionPolicy Bypass -File .\installer\fetch-uv.ps1

# 版を固定したいとき
powershell -ExecutionPolicy Bypass -File .\installer\fetch-uv.ps1 -Version 0.11.31

.\resources\tools\windows-x64\uv.exe -V
```

`resources/tools/**/uv.exe` は `.gitignore` 対象です。CI / リリースビルドでは `installer/build.ps1` が必要に応じて取得します。

## 差し替え手順（インストール済み PC）

1. インストール先の `tools\uv.exe`（または同梱パス）を、上記で取得した公式バイナリで上書き  
2. uvdrop を再起動し、ステータスバーの版を確認  
3. 組織ポリシーで「同梱 uv の版を固定」する場合は、Setup 再配布時に `fetch-uv.ps1 -Version …` でピン留め

PATH 上の別 `uv` より **同梱が優先**されます。意図せず古い PATH を使っている場合は、同梱を入れ直すかインストール構成を確認してください。

## リリース運用の目安

- セキュリティ修正や `uv audit` 改善を取り込みたい → `fetch-uv.ps1` で更新 → Setup / MSIX を再ビルド  
- 利用者への案内は「ステータスバーの uv 版」と本ドキュメントへのリンクで足りることが多いです
