# Distribution: three paths (Python / Inno / MSIX)

uvdrop has **one application codebase**. Only the packaging differs.

```text
                 src/uvdrop/  (shared code)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   [1] Python        [2] Inno         [3] MSIX
   source / wheel    Setup.exe        Store submission
   for developers    GitHub Releases  Microsoft Store
```

| Path | Who | Signing | Updates |
|------|-----|---------|---------|
| **Python** | Developers / run from source | Not required | `git pull` |
| **Inno Setup.exe** | Offline / outside the Store | Optional (Authenticode) | Replace on Releases |
| **MSIX (Store)** | General users | **Store re-signs (no cert fee)** | Store delivers |

Build details:

- Inno: [installer/PACKAGING.md](../installer/PACKAGING.md)
- MSIX: [installer/msix/README.md](../installer/msix/README.md)
- Licenses: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)

---

## Japanese

### コードは兼用できるか？

**はい。ランタイムの Python コードはそのまま兼用**です。

- 画面 / コマンドライン / `uv` の呼び出し / 許可・禁止リスト / 一時実行 … すべて `src/uvdrop/`
- 配布物ごとに **起動の入り口や同梱物だけが変わる**

| 配布 | 実行の実体 | 同梱するもの |
|------|------------|--------------|
| Python | `python -m uvdrop` | なし（PATH の `uv` 可） |
| Inno | PyInstaller の `uvdrop.exe` | `_internal/` + `tools/uv.exe` + ライセンス文 |
| MSIX | 同じ `uvdrop.exe` ツリーをパッケージ化 | 同上 + `AppxManifest.xml` |

流れのイメージ:

```text
共通コード
  →（任意）PyInstaller onedir = dist/uvdrop/
  → Inno が Setup.exe にまとめる
  → 同じ dist/uvdrop/ を MakeAppx で .msix にする
```

Store 向けだけ **マニフェスト（能力・アイデンティティ）** と掲載用の説明が追加で必要です。業務ロジックをフォークする必要はありません。

#### MSIX の注意

- Store の MSIX は **フル信頼（`runFullTrust`）** 前提（子プロセスで `uv.exe`、AppData への書き込み、ネット通信のため）
- インストール先が変わるので、frozen 時は exe 隣の `tools/uv.exe` を使う（対応済み）
- 審査では「何をするアプリか」を平易に説明する必要がある

### ビルド早見

#### 1) Python（開発・ソース）

```powershell
git clone https://github.com/uvdrop/uvdrop.git
cd uvdrop
python -m uvdrop
# または
pip install -e .
uvdrop
```

#### 2) Inno Setup.exe

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

成果物: `installer/output/uvdrop-<ver>-setup.exe` → GitHub Releases に添付

#### 3) MSIX（Store）

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

成果物: `installer/msix/output/uvdrop-<ver>.msix`  
→ Partner Center にアップロード（**提出用は署名しなくてよい。Store が再署名**）  
ローカル検証だけ自己署名が必要（`build-msix.ps1 -SignLocal`）

### コンプライアンス方針

- アプリ本体: **MIT**（`LICENSE`）
- ランタイム PyPI 依存: **なし**（標準ライブラリのみ）
- 同梱 `uv.exe`: **Apache-2.0 OR MIT**（Astral）→ ライセンス文を配布物に同梱
- ビルド専用（PyInstaller 等）: 詳細は [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)

---

## English

### Can the same code be reused?

**Yes. The runtime Python code is shared as-is.**

- GUI / CLI / calling `uv` / allow & block lists / temporary runs — all live in `src/uvdrop/`
- Only the **entry point and bundled files** change per distribution

| Distribution | What runs | What is bundled |
|--------------|-----------|-----------------|
| Python | `python -m uvdrop` | Nothing extra (`uv` on PATH is fine) |
| Inno | PyInstaller `uvdrop.exe` | `_internal/` + `tools/uv.exe` + license texts |
| MSIX | Same `uvdrop.exe` tree packaged | Same + `AppxManifest.xml` |

Typical flow:

```text
shared code
  → (optional) PyInstaller onedir = dist/uvdrop/
  → Inno wraps it as Setup.exe
  → same dist/uvdrop/ becomes .msix via MakeAppx
```

Store builds only need an extra **manifest (capabilities / identity)** and listing metadata. You do not fork business logic.

#### MSIX notes

- Store MSIX is designed for **full trust (`runFullTrust`)** (child `uv.exe`, AppData writes, network)
- Install path changes; frozen builds already prefer `tools/uv.exe` next to the exe
- Reviewers may ask for a plain explanation of what the app does

### Quick build

#### 1) Python (dev / source)

```powershell
git clone https://github.com/uvdrop/uvdrop.git
cd uvdrop
python -m uvdrop
# or
pip install -e .
uvdrop
```

#### 2) Inno Setup.exe

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

Output: `installer/output/uvdrop-<ver>-setup.exe` → attach on GitHub Releases

#### 3) MSIX (Store)

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

Output: `installer/msix/output/uvdrop-<ver>.msix`  
→ Upload to Partner Center (**no signing needed for Store submission; Store re-signs**)  
Self-sign only for local sideload tests (`build-msix.ps1 -SignLocal`)

### Compliance stance

- App: **MIT** (`LICENSE`)
- Runtime PyPI deps: **none** (stdlib only)
- Bundled `uv.exe`: **Apache-2.0 OR MIT** (Astral) → include license texts
- Build-only tools (PyInstaller, etc.): see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)

---

## 中文

### 代码能否共用？

**可以。运行时的 Python 代码原样共用。**

- 界面 / 命令行 / 调用 `uv` / 许可与禁止列表 / 临时运行 … 全部在 `src/uvdrop/`
- 各分发方式只改变 **入口与随附文件**

| 分发 | 实际运行 | 随附内容 |
|------|----------|----------|
| Python | `python -m uvdrop` | 无（可用 PATH 中的 `uv`） |
| Inno | PyInstaller 的 `uvdrop.exe` | `_internal/` + `tools/uv.exe` + 许可文本 |
| MSIX | 将同一 `uvdrop.exe` 树打包 | 同上 + `AppxManifest.xml` |

大致流程：

```text
共用代码
  →（可选）PyInstaller onedir = dist/uvdrop/
  → Inno 打成 Setup.exe
  → 同一 dist/uvdrop/ 用 MakeAppx 做成 .msix
```

仅 Store 版本需要额外的 **清单（能力 / 标识）** 与上架说明。无需分叉业务逻辑。

#### MSIX 注意

- Store 的 MSIX 按 **完全信任（`runFullTrust`）** 设计（子进程运行 `uv.exe`、写入 AppData、网络通信）
- 安装路径会变化；frozen 时已优先使用 exe 旁的 `tools/uv.exe`
- 审核时需用通俗语言说明应用做什么

### 快速构建

#### 1) Python（开发 / 源码）

```powershell
git clone https://github.com/uvdrop/uvdrop.git
cd uvdrop
python -m uvdrop
# 或
pip install -e .
uvdrop
```

#### 2) Inno Setup.exe

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

产物: `installer/output/uvdrop-<ver>-setup.exe` → 附到 GitHub Releases

#### 3) MSIX（Store）

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

产物: `installer/msix/output/uvdrop-<ver>.msix`  
→ 上传到 Partner Center（**提交用无需签名，Store 会重新签名**）  
仅本地侧载验证需要自签名（`build-msix.ps1 -SignLocal`）

### 合规方针

- 应用本体: **MIT**（`LICENSE`）
- 运行时 PyPI 依赖: **无**（仅标准库）
- 随附 `uv.exe`: **Apache-2.0 OR MIT**（Astral）→ 在分发物中附上许可文本
- 仅构建用工具（PyInstaller 等）: 见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)
