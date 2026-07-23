# 配布の3本柱（Python / Inno / MSIX）

uvdrop の **アプリ本体コードは1つ**です。違うのは「包み方」だけです。

```text
                 src/uvdrop/  （共通コード）
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   [1] Python        [2] Inno         [3] MSIX
   ソース/ wheel     Setup.exe        Store 提出用
   開発者向け         GitHub Releases   Microsoft Store
```

| ルート | 誰向け | 署名 | 更新 |
|--------|--------|------|------|
| **Python** | 開発者・ソースから動かす人 | 不要 | `git pull` |
| **Inno Setup.exe** | Store 外・社内・オフライン | 任意（Authenticode） | Releases で差し替え |
| **MSIX (Store)** | 一般ユーザー | **Store が再署名（証明書代不要）** | Store が配信 |

詳細ビルド手順:

- Inno: [installer/PACKAGING.md](../installer/PACKAGING.md)
- MSIX: [installer/msix/README.md](../installer/msix/README.md)
- ライセンス: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)

---

## コードは兼用できるか？

**はい。ランタイムの Python コードはそのまま兼用**です。

- GUI / CLI / `uv` 呼び出し / ポリシー / 一時実行 … すべて `src/uvdrop/`
- 配布物ごとに **エントリや同梱物だけが変わる**

| 配布 | 実行の実体 | 同梱するもの |
|------|------------|--------------|
| Python | `python -m uvdrop` | なし（PATH の `uv` 可） |
| Inno | PyInstaller の `uvdrop.exe` | `_internal/` + `tools/uv.exe` + ライセンス文 |
| MSIX | 同じ `uvdrop.exe` ツリーをパッケージ化 | 同上 + `AppxManifest.xml` |

つまり流れはだいたい:

```text
共通コード
  →（任意）PyInstaller onedir = dist/uvdrop/
  → Inno が Setup.exe にまとめる
  → 同じ dist/uvdrop/ を MakeAppx で .msix にする
```

Store 向けだけ **マニフェスト（能力・アイデンティティ）** と審査用メタデータが追加で必要です。アプリの業務ロジックをフォークする必要はありません。

### 例外・注意（MSIX）

- Store の MSIX は **フル信頼（`runFullTrust`）** 前提で設計する（子プロセスで `uv.exe`、AppData 書き込み、ネット通信のため）
- インストール先パスが変わるので、`paths.py` の「frozen 時は exe 隣の `tools/uv.exe`」が効く（既に対応済み）
- 審査で「何をするアプリか」を説明する必要あり

---

## ビルド早見

### 1) Python（開発・ソース配布）

```powershell
git clone https://github.com/uvdrop/uvdrop.git
cd uvdrop
python -m uvdrop
# または
pip install -e .
uvdrop
```

成果物: リポジトリそのもの /（将来）PyPI wheel

### 2) Inno Setup.exe

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

成果物: `installer/output/uvdrop-<ver>-setup.exe`  
→ GitHub Releases に添付

### 3) MSIX（Store）

```powershell
# 先に payload（dist\uvdrop）を用意
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

成果物: `installer/msix/output/uvdrop-<ver>.msix`  
→ Partner Center にアップロード（**提出用は署名しなくてよい。Store が再署名**）  
ローカル検証用だけ自己署名が必要（`build-msix.ps1 -SignLocal`）

---

## コンプライアンス方針

- アプリ本体: **MIT**（`LICENSE`）
- ランタイム PyPI 依存: **なし**（標準ライブラリのみ）
- 同梱 `uv.exe`: **Apache-2.0 OR MIT**（Astral）→ ライセンス文を配布物に同梱
- ビルド専用（PyInstaller 等）: ソース配布には含めないが、バイナリ配布物に埋め込まれるランタイムは THIRD_PARTY に記載

詳細とチェックリストは [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。
