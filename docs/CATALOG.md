# Shared catalog (file or HTTP API endpoint)

Catalog files are the **source of truth** for team-shared apps.  
uvdrop does **not** auto-scan folders. It only lists apps declared in registered catalog files.

日本語 / English / 中文 — same schema.

---

## Japanese

### 考え方

- 管理者がカタログ JSON を書く（名前・概要・起動コマンド・置き場のパス）
- 利用者は uvdrop の設定にカタログファイル、またはカタログAPIのエンドポイントを登録する（複数可＝部署ごとなど）
- 一覧から選ぶ → そのとき初めて `path` にアクセス → 必要ファイルを検証 → **既存の実行前ガードはそのまま** → 起動

「カタログにあるから安全」にはしません。許可リスト / 禁止リスト / 依存ツリー確認は通常どおり動きます。

### ファイル例

```json
{
  "version": 1,
  "catalog": "経理チーム 共有アプリ",
  "apps": [
    {
      "id": "monthly-report",
      "name": "月次レポート",
      "summary": "売上を集計して PDF を出します",
      "path": "\\\\fileserver\\apps\\report-tool",
      "command": "main.py"
    },
    {
      "name": "画像リサイズ",
      "summary": "フォルダ内の画像を一括縮小",
      "path": "resize.zip",
      "command": "run.py --input ./in"
    }
  ]
}
```

| フィールド | 必須 | 意味 |
|---|---|---|
| `version` | 任意 | スキーマ版（現状 `1`） |
| `catalog` | 任意 | カタログの表示名 |
| `apps` | 必須 | アプリの配列 |
| `apps[].name` | 必須 | 一覧に出す名前 |
| `apps[].path` | 必須 | フォルダまたは `.zip` の場所（絶対 / UNC / カタログ相対） |
| `apps[].summary` | 任意 | 短い説明 |
| `apps[].command` | 任意 | 実行前確認の起動コマンドに事前入力。`{port}` を含めると起動時に空きポートへ置換 |
| `apps[].id` | 任意 | 取り込みキー用の安定 ID |
| `base` | HTTP+相対 path 時に推奨 | 相対 `path` の基準（絶対 / UNC） |

### `{port}` プレースホルダ

Web 系アプリでポート衝突を避けるとき、起動コマンドに `{port}`（大文字小文字不問）を書けます。

```json
"command": "main.py --port {port}"
```

uvdrop は起動直前に空き TCP ポート（既定は 8000 付近から走査）を選び、

1. コマンド内の `{port}` を数字に置換して実行  
2. あわせて環境変数 `UVDROP_PORT` と `PORT` を子プロセスへ渡す  

テンプレート（`{port}` 付き）はレジストリに残るので、再起動のたびに別ポートを取れます。  
アプリ側は `--port` を読むか、`os.environ["PORT"]` を読んでください。

例:

```text
main.py --port {port}
-m uvicorn app:app --host 127.0.0.1 --port {port}
-m streamlit run app.py --server.port {port}
```

### 運用

1. 共有ドライブなどにアプリ本体（フォルダ or ZIP）を置く  
2. 同じ場所（または別場所）に `uvdrop-catalog.json` を置く  
   **または** 同じ JSON 形をレスポンス本文として返す HTTPS API エンドポイントを用意する  
3. 利用者の uvdrop → 設定 → カタログ に **ファイルパス** または **URL** を追加して保存  
4. メイン画面の「カタログから開く」で一覧 → 実行  
   起動中はメイン画面に **進行状況バナー**（例: `2/4 実行前の確認…`）が出ます。  
   カタログ窓は閉じず、複数アプリを同時に起動できます。

HTTP 側は静的な `.json` URL でも、`GET https://portal.example/api/catalogs/team-a` のような
API エンドポイントでも構いません。URL の末尾に `.json` は不要です。認証が不要、または
ネットワーク側で認証済みのエンドポイントを想定しています（現状、トークン入力機能はありません）。
レスポンスの `Content-Type` は `application/json` 推奨です。

HTTP カタログで相対 `path` を使う場合は、レスポンスに `base`（共有ルートなど）を書いてください。  
フォルダの自動走査はしません。カタログが正本です。

### ローカルで試す（UNC / 本番 API なし）

Win11 の任意フォルダだけで配布テストするパック: [`examples/local-portal/`](../examples/local-portal/)。

1. `uvdrop-catalog.json` を設定 → カタログに登録（相対 path で `apps/` 配下を起動）  
2. HTTP だけ試したいときは同フォルダの `serve-catalog.ps1`（`base` を絶対パスに書き換えて配信）

### 起動の所要時間について

初回は依存のダウンロードで数分かかることがあります。進行状況が見えないと失敗したように見えるため、
uvdrop はメイン画面にオレンジ枠の進行状況を出します（並列起動にも対応）。

---

## English

### Idea

- Admins write a catalog JSON (name, summary, start command, path)
- Users register catalog file paths or catalog API endpoints in Settings (multiple allowed)
- Pick an app → then access `path` → validate required files → **existing launch guards unchanged** → run
- While launching, the main window shows a progress banner (e.g. `2/4`). Multiple catalog launches can run in parallel.

Being listed in a catalog does **not** bypass allow / block lists or the review dialog.

### Fields

See the JSON example above. `path` may be absolute, UNC (`\\server\share\...`), or relative to the catalog file (or `base` for HTTP catalogs). Register either a local file path or any `https://…` API endpoint returning this schema; a `.json` suffix is not required. `command` pre-fills the review dialog only.

### `{port}` placeholder

Put `{port}` in `command` (e.g. `main.py --port {port}`). At launch, uvdrop picks a free TCP port, substitutes it into the command, and sets `PORT` / `UVDROP_PORT` on the child process. The template with `{port}` is kept in the registry so relaunches get a fresh port.

---

## 中文

### 思路

- 管理员编写目录 JSON（名称、简介、启动命令、路径）
- 用户在设置中注册一个或多个目录文件路径
- 选择应用 → 再访问 `path` → 校验必需文件 → **既有启动防护不变** → 运行

目录中的条目**不会**绕过许可/禁止列表或运行前确认。
