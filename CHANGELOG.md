# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- ショートカットの内蔵アイコンを自由な2トーン配色に対応
- ショートカット画像へ Windows クリップボードのスクリーンショットを Ctrl+V で貼り付け
- 実行前確認画面で、起動ごとにコンソール窓の表示 / 非表示を選択
- **共有カタログ**（`uvdrop-catalog.json`）: 名前・概要・起動コマンド・置き場を正本とし、
  複数カタログを設定登録 → 一覧からワンクリック起動（フォルダ自動走査なし、ガードは維持）
- JSON を返すカタログ **HTTP(S) API エンドポイント**の登録
  （`.json` 接尾辞は不要、プロキシ設定を利用して取得）
- Python 本体の **サポート切れ / 切れまで1年以内** 警告（`python-versions.json` の `eol`）
- 想定ユース向けシナリオサンプル + `scripts/bench_samples.py`
  （並列実行、venv 作成〜起動〜削除、グラフィカルな HTML 分析レポート、作業データの完全破棄）
- `docs/CATALOG.md` / `docs/PYTHON_SUPPORT.md` / `docs/BENCHMARK.md` と `examples/uvdrop-catalog.example.json`

### Changed

- 設定画面の全タブを縦スクロール対応にし、小さい画面でも全項目を操作可能に
- 実行前のパッケージ一覧が推移依存を含むことを明記
- 設定に「カタログ」タブを追加

### Planned

- CI that builds Setup.exe / MSIX on tagged releases
- Richer xlsx column mapping (Python versions sheet)
- Partner Center 提出用アイコン差し替え・Publisher CN 固定

## [0.9.1] — 2026-07-26

### Added

- `SECURITY.md`（脅威モデル・安全機構・報告方法を三言語で）、`CONTRIBUTING.md`、
  `docs/UNINSTALL.md`（アンインストール後の `%LOCALAPPDATA%\uvdrop\` 残置と削除手順）
- i18n の網羅テスト（全キーに ja / en / zh が揃うこと、プレースホルダ一致）と
  依存解決 `--no-build`・block 時の解決失敗拒否のテスト

### Changed

- 確認前の依存解決を `uv lock --no-build` に変更。メタデータ取得のために
  パッケージのビルドバックエンド（＝任意コード）を実行しない
- 許可リストが「未許可はブロック」設定で、依存ツリー全体を確認できなかった場合は
  未確認の推移的依存を入れないよう **起動を中止**（保守的な既定）
- UI・エラー・ヘルプ・確認画面・ポリシー通知・バージョン規則ガイドを完全に三言語化
  （安全に関わる文言が言語に関わらず正しく表示される）
- インストーラの版数を実バージョンに同期（`installer/uvdrop.iss` / MSIX マニフェスト）

## [0.9.0] — 2026-07-26

### Added

- インストール前に `uv lock` で依存関係を解決し、あわせて入るパッケージも含めて許可 / NG リストと照合
- 設定「毎回確認する」「許可リスト未設定のとき」が実際の起動フローに反映される
- ZIP 展開時のパストラバーサル（Zip Slip）防御
- 表示言語: 日本語 / English / 中文（OS 自動検出 + 設定で切替）
- GitHub Pages・配布 / Store 文書の三言語化
- Windows CI（pytest）

### Changed

- 設定「起動時にコンソール窓を出す（デバッグ用）」— オフがデフォルトで黒い窓を隠す
- CLI 新規起動は確認が必要な場合に拒否（`UVDROP_ASSUME_YES=1` で上書き可）。ショートカット再起動は block のみ再評価

## [0.8.0] — 2026-07-26

### Added

- 「バージョンの書き方」ガイド（`*` の意味、ドット区切り、位ごとの判定、使える記号）を
  許可 / NG リストと確認画面から開けるように
- バージョン規則の検証: 読み取れない行は赤字表示、保存前に確認。`~=` `===` `==1.*` `v1.2` などを説明付きで指摘
- PyPI のバージョン表記（rc / post / dev / ローカル版 / エポック）で正確に判定できない場合、
  実行前の確認画面に「判定できない項目」として通知
- アプリ一覧に「最終起動」「起動回数」列。見出しクリックで並び替え、名前・場所での絞り込み
- 使用状況ウィンドウ: 日ごと / 週ごと / 月ごとの起動回数を棒グラフ表示（アプリ別・全体）
- 起動履歴を `usage.json` に日別で記録（アプリ削除時に併せて削除）

### Changed

- 実行確認・設定ダイアログを小さめにし、入りきらない分はスクロール。保存ボタンは常に下に固定
- 許可 / NG リスト: 複数行選択・全選択、大量貼り付け時の行自動追加
- メインの「サンプルで試す」をカードから「1. 起動する」横のリンクに縮小

## [0.7.0] — 2026-07-26

### Added

- 許可リストを表形式（パッケージ名 + バージョン規則）に変更。`*` / `1.*` / `>=1.0,<2` などに対応
- NGリスト（ヒットで常に block）
- Excel / CSV 取り込み（A列=名前、B列=バージョン）。URL だけでなくローカルパスも可
- 許可リスト / NGリストを表計算ライクなグリッドに刷新。行番号・A/B 列見出し・セル単位編集、
  Tab で右セル / Enter で下行、Ctrl+V で Excel からの範囲貼り付け、Ctrl+C でコピー
- ショートカット: アイコンプレビュー、OA/計測/ツール/実験のサンプルサムネ、色パレット

### Changed

- 「xlsx URL」表記を「Excel / CSV」に分かりやすく変更
- settings.json の allowlist.packages を `{name, version}` 配列に（旧カンマ区切りも読み込み可）

## [0.6.0] — 2026-07-26


### Added

- 確認画面で起動コマンドを指定できるように（候補から選択、引数つきの直接入力も可）。選んだコマンドは登録され、再起動・ショートカットでも使われる
- 起動成功後に「ショートカットを作りますか？」を提案（未作成のときだけ）。仕組みの説明も表示
- ショートカットのアイコン選択。アプリ内の `.ico` / `.png`（`assets` / `icons` などを探索）またはファイル指定
- `appicon` モジュール: PNG を ICO コンテナへ包む変換（追加依存なし）

### Changed

- 起動エントリの自動推定は「最初の候補」を初期値にするだけになり、実行前に必ず確認できる

## [0.5.0] — 2026-07-26

### Added

- 実行前の確認ダイアログ: インストールされるパッケージ一覧、許可リスト外の強調、未設定時の注意
- 設定に「実行前の確認」タブ（毎回確認 / 許可リスト未設定時の扱い / requirements 変換の許可）
- `requirements.txt` → 最小 `pyproject.toml` の簡易変換（`-e .`・`--index-url`・直接 URL は除外し、注意を表示）
- 起動エントリが見つからない場合の事前警告

### Changed

- 起動前の「一時 / 保持」選択を廃止。常に一覧へ残し、不要になったら削除する
- GUI を最大化で起動し、フォントを Yu Gothic UI 基調に変更（配色も低コントラストへ）
- 「社内」表現を一般的な言い方へ統一

## [0.4.1] — 2026-07-26

### Removed

- OSV.dev 連携（設定・ポリシー・`osv_check` モジュール）。許可リストと Python 版チェックに集約

## [0.4.0] — 2026-07-24

### Changed

- GUI を導線優先に再設計（大きな3カード、番号付きステップ、空状態案内）
- ログは既定非表示（出力時に自動表示）
- 設定をタブ分割し、長文ヘルプは「？」に退避
- サンプル保存でフォルダ/ZIP を Yes/No ではなくラジオで選択

## [0.3.6] — 2026-07-24


### Fixed

- 初回シードの `allowlist.json`（httpx 等入り）が常時適用され、手動許可リストの検証が効かない問題
- ポリシー結果ダイアログに許可リストの適用状況（照合件数）を表示

## [0.3.5] — 2026-07-24

### Added

- Settings: manual allowlist（カンマ区切り直接入力、`settings.json` に永続化、xlsx/JSON とマージ）

## [0.3.4] — 2026-07-24

### Fixed

- Desktop shortcut relaunch: set `PYTHONPATH` for source runs, log failures, pause on error
- Packaged builds use `--relaunch <key>`

### Added

- Sample 1 (Tk / no PyPI deps) and Sample 2 (`httpx` install + ping UI)
- Settings: 「OSV 接続・検知テスト」button

## [0.3.3] — 2026-07-24

### Added

- uv priority clarified（同梱 > PATH）+ status bar shows source and `uv --version`
- Proxy settings (HTTP/HTTPS/NO_PROXY) applied to uv / OSV / xlsx
- Policy check always shows a dialog（問題なしでも表示）before venv sync
- Sample app is a small Tk welcome UI（no rich / no nora folder）
- Optional `uvdrop.manifest.json`（legacy `nora/` still accepted silently）

### Changed

- Help / format docs: remove advertised nora paths; document apps/envs locations and temp cleanup
- Version bump to 0.3.3

## [0.3.2] — 2026-07-24

### Added

- First-run help: 構成説明ダイアログ、ヘルプ、サンプルアプリ書き出し（フォルダ/ZIP）
- Hover tooltips + settings explanations for OSV.dev and xlsx allowlist format
- `docs/APP_FORMAT.md`（期待するフォルダ構成）

### Changed

- Main window layout clarified（はじめての方へ / 起動 / 一覧）
- Version bump to 0.3.2

## [0.3.1] — 2026-07-23

### Added

- Three-track distribution guide: `docs/DISTRIBUTION.md` (Python / Inno / MSIX)
- `THIRD_PARTY_NOTICES.md` + vendored `third_party/uv` license texts
- MSIX scaffold: `installer/msix/` (`AppxManifest.xml`, `build-msix.ps1`)
- GUI「ライセンス」ボタン（NOTICE / LICENSE を開く）
- Packaging copies LICENSE + `third_party/` into binary payload

### Changed

- Version bump to 0.3.1

## [0.3.0] — 2026-07-23

### Added

- End-to-end Windows packaging scripts: `fetch-uv.ps1`, `build.ps1`, `sign.ps1`
- PyInstaller `uvdrop.spec` (onedir) for Inno payload
- Beginner-oriented Inno Setup guide: `installer/PACKAGING.md`
- Installed layout looks for `{app}\tools\uv.exe`

### Changed

- Version bump to 0.3.0; `.iss` version synced by `build.ps1`

## [0.2.0] — 2026-07-22

### Added

- Temporary run cleans up workspace / venv / dotenv after the process exits
- Startup GC for leftover temp apps
- Optional OSV.dev malicious-package check (`settings.json` → `osv.enabled`)
- Optional allowlist sync from a remote `.xlsx` URL
- GitHub Pages site (`docs/`) covering features, usage, and operations
- Inno Setup installer skeleton (`installer/uvdrop.iss`)
- Version shown prominently in the GUI title and header
- `CHANGELOG.md` and centralized `version.py`

### Changed

- Bump package version to 0.2.0

## [0.1.0] — 2026-07-22

### Added

- Initial offline uv launcher (Tk GUI + CLI)
- Folder / ZIP import → dedicated `.env` → `uv sync` / `uv run`
- Keep vs temp mode (temp cleanup landed in 0.2.0)
- Desktop shortcut creation (Windows)
- Local JSON policies for package allowlist and Python versions
- MIT license, example policies, basic tests

[Unreleased]: https://github.com/uvdrop/uvdrop/compare/v0.9.1...HEAD
[0.9.1]: https://github.com/uvdrop/uvdrop/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/uvdrop/uvdrop/compare/v0.8.0...v0.9.0
[0.3.1]: https://github.com/uvdrop/uvdrop/releases/tag/v0.3.1
[0.3.0]: https://github.com/uvdrop/uvdrop/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/uvdrop/uvdrop/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/uvdrop/uvdrop/releases/tag/v0.1.0
