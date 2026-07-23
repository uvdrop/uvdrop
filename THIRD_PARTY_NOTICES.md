# Third-party notices（第三者ライセンス）

uvdrop 本体は **MIT**（リポジトリ直下の `LICENSE`）です。  
この文書は、**配布物に同梱・埋め込まれる第三者コンポーネント**と、ビルド時のみ使うツールの扱いをまとめたものです。

コンプライアンスの原則:

1. **ランタイムで同梱するもの** → ライセンス全文（または義務を満たす NOTICE）を配布物に含める  
2. **ビルドマシンだけのツール** → ソースツリーに義務の範囲で記載し、利用者向けバイナリに不要なら同梱しない  
3. **依存を増やしたら** → この文書と `third_party/` を更新する（PR チェックリスト）

---

## 配布物ごとの含めもの

| コンポーネント | Python ソース | Inno Setup.exe | MSIX (Store) |
|----------------|---------------|----------------|--------------|
| uvdrop (MIT) | ✅ ソース | ✅ 埋め込み | ✅ 埋め込み |
| `uv.exe` (Apache-2.0 OR MIT) | △ PATH 利用時は別途 | ✅ `tools/uv.exe` + ライセンス文 | ✅ 同左 |
| CPython / Tcl/Tk（PyInstaller 経由） | OS/Python 側 | ✅ `_internal` に含まれる | ✅ 同左 |
| PyInstaller bootloader | — | ✅ バイナリに含まれる | ✅ 同左 |

フルテキストは `third_party/` 配下、およびバイナリ配布時はインストール先の `third_party\` / `LICENSE` を参照。

---

## 1. uvdrop（本ソフトウェア）

- License: **MIT**
- File: [`LICENSE`](./LICENSE)

---

## 2. uv（Astral）— 同梱バイナリ

uvdrop の Windows インストーラ / MSIX は、公式リリースの **`uv.exe` を同梱**します。

- Upstream: https://github.com/astral-sh/uv  
- Policy: https://docs.astral.sh/uv/reference/policies/license/  
- License: **Apache License 2.0 OR MIT**（利用側が選択可能）  
- Vendored texts:  
  - [`third_party/uv/LICENSE-APACHE`](./third_party/uv/LICENSE-APACHE)  
  - [`third_party/uv/LICENSE-MIT`](./third_party/uv/LICENSE-MIT)

### 再配布時の実務

- MIT を選ぶ場合: 著作権表示と MIT 本文を同梱（上記 `LICENSE-MIT`）  
- Apache-2.0 を選ぶ場合: Apache 本文を同梱し、NOTICE があれば帰属も残す  
- uvdrop では **両方の全文を `third_party/uv/` に同梱**し、利用者がどちらの条件でも確認できるようにしています  
- `uv.exe` は多数の Rust crate を静的リンクします。上流が提供するライセンス表記に加え、厳密な SBOM が必要な組織向けには、同梱する uv のタグを固定し、必要なら `cargo license` 等で追加レポートを取ることを推奨します（現状は上流 dual-license + 全文同梱）

### バージョン固定

ビルド時に取得した uv の版は、可能なら Release ノートに記載します。  
取得スクリプト: `installer/fetch-uv.ps1`

---

## 3. Python ランタイム依存（アプリ本体）

`pyproject.toml` の `dependencies = []` です。

- **PyPI ランタイム依存なし**（標準ライブラリのみ: `tkinter`, `urllib`, `json`, `tomllib`, `subprocess`, …）  
- 開発任意: `pytest`（テストのみ・配布バイナリに含めない）

---

## 4. PyInstaller（バイナリ梱包時）

Inno / MSIX の payload 作成に使用。

- Upstream: https://pyinstaller.org / https://github.com/pyinstaller/pyinstaller  
- License: **GPL-2.0-or-later with Bootloader exception**（一般的なアプリ同梱は例外により実務上問題になりにくいが、文言は公式を確認）  
- 参考: https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt  

配布物には PyInstaller の bootloader と、収集された **CPython / Tcl/Tk** 等が含まれます。

- CPython: PSF License — https://docs.python.org/3/license.html  
- Tcl/Tk: Tcl/Tk License — https://www.tcl-lang.org/software/tcltk/license.html  

要約メモ: [`third_party/pyinstaller/README.md`](./third_party/pyinstaller/README.md)

---

## 5. Inno Setup（ビルドツール）

Setup.exe を作るための **ビルドマシン上のツール**です。利用者への uvdrop 配布物に Inno 本体は含まれません。

- https://jrsoftware.org/isinfo.php  
- Inno Setup のライセンスに従いインストール・利用すること

---

## 6. Windows SDK / MakeAppx（MSIX ビルド）

MSIX 作成時に使う Microsoft ツール。配布物には通常含まれません。

---

## メンテ用チェックリスト（依存を足すとき）

- [ ] `pyproject.toml` の license / dependencies を更新  
- [ ] この `THIRD_PARTY_NOTICES.md` に行を追加  
- [ ] 必要なら `third_party/<name>/` に全文を vendoring  
- [ ] `installer/build.ps1` が `third_party` を payload にコピーすることを確認  
- [ ] Inno `.iss` / MSIX にライセンスファイルが入ることを確認  
- [ ] GUI の「ライセンス」から辿れることを確認  

---

## 免責

本ドキュメントは開発者向けの運用メモです。法的助言ではありません。組織の法務・OSS ポリシーに合わせて追加の SBOM / 監査を行ってください。
