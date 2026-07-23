# uvdrop

実務向けのオフライン **uv ランチャー**です。

フォルダ（または ZIP）を渡すと、同梱 / PATH の `uv` で専用 `.env` を用意し、`uv sync` → `uv run` でアプリを起動します。

- サイト: https://uvdrop.github.io/uvdrop/
- リポジトリ: https://github.com/uvdrop/uvdrop
- リリースノート: [CHANGELOG.md](./CHANGELOG.md)
- 現在のバージョン: **0.3.0**（GUI ヘッダーにも表示）
- Windows 配布手順: [installer/PACKAGING.md](./installer/PACKAGING.md)

## できること

- 対象フォルダ / ZIP の選択と起動
- アプリ専用 `.env` の作成・再利用
- **一時実行**（終了後にワークスペース / venv / .env を削除）と **保持**
- 保持アプリのデスクトップショートカット
- 許可パッケージ・許可 Python バージョンのローカル JSON ポリシー
- 任意: 許可リストの **xlsx URL** 同期
- 任意: **OSV.dev** による `MAL-*` チェック

ポータル（カタログ配信）や Gitea 連携は含めません。

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

`%LOCALAPPDATA%\uvdrop\` 配下（apps / envs / dotenv / policies / settings.json）。詳細は [サイトの運営セクション](https://uvdrop.github.io/uvdrop/#ops)。

## インストーラ

素の PyInstaller exe 直配布は避け、**Inno Setup の Setup.exe**（Apps & Features 登録）を配布します。

```powershell
winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

詳細・署名・Releases 手順: [installer/PACKAGING.md](./installer/PACKAGING.md)  
成果物: `installer/output/uvdrop-<version>-setup.exe`

## ライセンス

MIT
