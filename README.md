# uvdrop



小規模組織向けの **アプリポータル**です。  

`pyproject.toml` のあるフォルダ（uv で動く構成）をカタログに載せれば、利用者が uvdrop から自由に選んで実行できます。



フォルダ / ZIP を渡すと、同梱または PATH の `uv` で専用 `.env` を用意し、`uv sync` → `uv run` で起動します。  

押しどころは次のとおりです。



- **カタログ起点のポータル** — フォルダ自動走査なし。管理者が載せたアプリだけが一覧に出る

- **実行前の確認** — 依存ツリー全体を見てから venv を作る（`uv lock --no-build`）

- **許可 / 禁止パッケージと Python 版** — 組織ポリシーとサポート期限のチェック



- サイト: https://uvdrop.github.io/uvdrop/

- リポジトリ: https://github.com/uvdrop/uvdrop

- リリースノート: [CHANGELOG.md](./CHANGELOG.md)

- 現在のバージョン: **0.10.0**（GUI ヘッダーにも表示）

- セキュリティ / 脅威モデル: [SECURITY.md](./SECURITY.md)

- 開発への参加: [CONTRIBUTING.md](./CONTRIBUTING.md)

- アプリ構成の説明: [docs/APP_FORMAT.md](./docs/APP_FORMAT.md)

- 共有カタログ: [docs/CATALOG.md](./docs/CATALOG.md)

- ローカル配布デモ: [examples/local-portal/](./examples/local-portal/)（Win11 の普通のフォルダで試せる）

- 同梱 uv の版と差し替え: [docs/UV_RUNTIME.md](./docs/UV_RUNTIME.md)

- Python サポート期限: [docs/PYTHON_SUPPORT.md](./docs/PYTHON_SUPPORT.md)

- シナリオ計測: [docs/BENCHMARK.md](./docs/BENCHMARK.md)

- アンインストール手順: [docs/UNINSTALL.md](./docs/UNINSTALL.md)

- 配布3本柱: [docs/DISTRIBUTION.md](./docs/DISTRIBUTION.md)（Python / Inno / MSIX）

- Store / Partner Center 手順: [docs/STORE_PARTNER_CENTER.md](./docs/STORE_PARTNER_CENTER.md)

- Windows Inno 手順: [installer/PACKAGING.md](./installer/PACKAGING.md)

- 第三者ライセンス: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)



## 速度の目安（実測の感覚）



計測はマシン・回線・ウイルス対策・**uv グローバルキャッシュの有無**で大きく変わります。  

詳細と再現手順は [docs/BENCHMARK.md](./docs/BENCHMARK.md)。



| 状況 | 体感の目安 |

|---|---|

| 依存なし（stdlib） | 数秒以内（準備〜起動） |

| 軽い Web / データ系（Flask, pandas など）・**キャッシュ暖機後** | だいたい数秒〜十数秒で venv 同期〜起動 |

| 同じスタックの**初回（コールド）** | 依存ダウンロードが支配的。light 帯でも数分〜十数分になり得る |

| Qt / sklearn / 大きめ wheel | 暖機後は速いことが多い。初回は通信と展開次第でさらに長い |

| torch / TF などの heavy | 初回は数十分規模を想定 |



「今くらい速い」＝だいたい **一度入れたパッケージが uv キャッシュに残っている状態**です。  

新しい PC や空の `UV_CACHE_DIR` では初回だけ遅く見えます。venv を「冬眠」してもグローバルキャッシュは残るので、再構築は暖機に近い速さになりやすいです。



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

- 同梱または PATH 上の `uv.exe`（推奨 **0.11.6+**。差し替えは [docs/UV_RUNTIME.md](./docs/UV_RUNTIME.md)）



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



同梱 uv が無いときは:



```powershell

powershell -ExecutionPolicy Bypass -File .\installer\fetch-uv.ps1

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


