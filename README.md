# uvdrop

実務向けのオフライン **uv ランチャー**です。

フォルダ（または ZIP）を渡すと、同梱 / PATH の `uv` で専用 `.env` を用意し、`uv sync` → `uv run` でアプリを起動します。

- サイト: https://uvdrop.github.io/uvdrop/
- リポジトリ: https://github.com/uvdrop/uvdrop
- リリースノート: [CHANGELOG.md](./CHANGELOG.md)
- 現在のバージョン: **0.9.1**（GUI ヘッダーにも表示）
- セキュリティ / 脅威モデル: [SECURITY.md](./SECURITY.md)
- 開発への参加: [CONTRIBUTING.md](./CONTRIBUTING.md)
- アプリ構成の説明: [docs/APP_FORMAT.md](./docs/APP_FORMAT.md)
- 共有カタログ: [docs/CATALOG.md](./docs/CATALOG.md)
- Python サポート期限: [docs/PYTHON_SUPPORT.md](./docs/PYTHON_SUPPORT.md)
- シナリオ計測: [docs/BENCHMARK.md](./docs/BENCHMARK.md)
- アンインストール手順: [docs/UNINSTALL.md](./docs/UNINSTALL.md)
- 配布3本柱: [docs/DISTRIBUTION.md](./docs/DISTRIBUTION.md)（Python / Inno / MSIX）
- Store / Partner Center 手順: [docs/STORE_PARTNER_CENTER.md](./docs/STORE_PARTNER_CENTER.md)
- Windows Inno 手順: [installer/PACKAGING.md](./installer/PACKAGING.md)
- 第三者ライセンス: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)

## できること

- 対象フォルダ / ZIP の選択と起動
- **実行前に、起動コマンドとインストールされるパッケージを確認**（仮想環境を作る前。`uv lock --no-build` で解決した全体を照合。確認前にビルド＝任意コードは実行しない）
- 許可リストが「未許可はブロック」設定で依存ツリー全体を確認できないときは、安全のため起動を中止
- 起動コマンドは候補から選ぶか、引数つきで直接入力（`main.py --debug` など）
- 起動後にデスクトップショートカットを提案（8種のアイコン、自由な2トーン配色、
  アプリ内画像・ファイル選択・スクリーンショットの Ctrl+V 貼り付けをプレビュー）
- **共有カタログ**（`uvdrop-catalog.json`）を複数登録し、名前・概要・起動コマンド・置き場から
  ワンクリックで取り込み → 実行前ガード → 起動（フォルダ自動走査はしない）
- `pyproject.toml` が無い場合は `requirements.txt` からの簡易変換（任意・注意付き）
- アプリ専用 `.env` の作成・再利用
- 取り込んだアプリの再起動・デスクトップショートカット・削除
- アプリ一覧を残したまま venv だけを手動で「冬眠」。既定OFFの設定を有効にすれば、
  指定日数使っていない venv を起動時に冬眠（uv グローバルキャッシュは保持）
- アプリ一覧の「最終起動」「起動回数」表示、並び替え・絞り込み、使用状況グラフ（日 / 週 / 月）
- 許可 / NG パッケージ（表計算ライクなグリッド・バージョン規則）と許可 Python バージョン
- 許可 / NG リストは Excel からそのまま Ctrl+V で貼り付け可（Ctrl+C でコピー）
- バージョン規則は書き方ガイド付き。読み取れない規則や PyPI 固有の表記は実行前に通知
- 表示言語: 日本語 / English / 中文（OS 言語を自動検出、設定で切替可）
- 起動時のコンソール窓はデフォルトで非表示（設定の既定値と実行前確認で表示を選択可）
- 任意: Excel / CSV（A列=名前、B列=バージョン）からの取り込み
- 共有カタログはファイルまたは HTTP API エンドポイントで配信（Git / PAT 連携はまだ含めません）

## 動作要件

- Windows x64（当面）
- Python 3.11+（開発時）
- 同梱または PATH 上の `uv.exe`

## 開発の起動

```powershell
git clone https://github.com/uvdrop/uvdrop.git
cd uvdrop
python -m uvdrop
```

```powershell
python -m uvdrop --version
python -m uvdrop --cli path\to\app
python -m uvdrop --cli path\to\app.zip --temp
```

## データ配置

`%LOCALAPPDATA%\uvdrop\` 配下（apps / envs / dotenv / policies / settings.json / usage.json）。詳細は [サイトの運営セクション](https://uvdrop.github.io/uvdrop/#ops)。

アンインストールしてもこのフォルダは残ります（取り込んだアプリ・設定を誤って失わないため）。完全削除の手順は [docs/UNINSTALL.md](./docs/UNINSTALL.md)。

## インストーラ

配布は **Python / Inno Setup.exe / MSIX(Store)** の3本です（コード共通）。概要は [docs/DISTRIBUTION.md](./docs/DISTRIBUTION.md)。

```powershell
winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

MSIX:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

詳細: [installer/PACKAGING.md](./installer/PACKAGING.md) / [installer/msix/README.md](./installer/msix/README.md)  
成果物例: `installer/output/uvdrop-<version>-setup.exe`

## ライセンス

MIT
