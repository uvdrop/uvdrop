# uvdrop が受け付けるアプリ構成 / App layout / 应用结构

## Japanese

フォルダまたは ZIP を渡すと、中身を `%LOCALAPPDATA%\uvdrop\apps\` に取り込み、  
仮想環境を `%LOCALAPPDATA%\uvdrop\envs\` に作ってから起動します。

**実行前の確認**では、あなたが直接書いたパッケージ名だけでなく、**あわせて入るパッケージ**（依存関係の全体）も一覧で見られます。許可リスト / 禁止リスト（版のルール付き）と照合します。

### uv の優先順位

1. **同梱 `uv.exe`（最優先）** — `tools/uv.exe` または `resources/tools/windows-x64/uv.exe`
2. 無いときだけ **PATH** の `uv`

### 必須

1. **`pyproject.toml`**（ルート、または直下1階層）
2. **起動エントリ** — `main.py` / `app.py` / `run.py`、または `uvdrop.manifest.json`、または `[project.scripts]`

### 推奨

```text
my-app/
  pyproject.toml
  main.py
  README.md                 # 任意
  uvdrop.manifest.json      # 任意
```

`pyproject.toml` が無い場合は、`requirements.txt` からの簡易変換を試せることがあります（動かないこともあります）。

### 保持と削除

取り込んだアプリは一覧に残ります。不要になったら画面から削除できます（作業フォルダ・仮想環境・専用の設定・使用履歴も一緒に消えます）。

### サンプル

GUI の「サンプルで試す」などから、最小プロジェクトを書き出せます。

---

## English

Pass a folder or ZIP. uvdrop copies it under `%LOCALAPPDATA%\uvdrop\apps\`,  
creates a virtual environment under `%LOCALAPPDATA%\uvdrop\envs\`, then starts the app.

**Review before running** shows not only the packages you named, but also **packages that come along** (the full resolved set). They are checked against the allow list / block list (with version rules).

### uv preference

1. **Bundled `uv.exe` (first)** — `tools/uv.exe` or `resources/tools/windows-x64/uv.exe`
2. Otherwise **`uv` on PATH**

### Required

1. **`pyproject.toml`** (at the root, or one level down)
2. **Launch entry** — `main.py` / `app.py` / `run.py`, or `uvdrop.manifest.json`, or `[project.scripts]`

### Recommended layout

```text
my-app/
  pyproject.toml
  main.py
  README.md                 # optional
  uvdrop.manifest.json      # optional
```

If there is no `pyproject.toml`, a simple conversion from `requirements.txt` may be tried (it does not always work).

### Keeping and deleting

Imported apps stay in the list. Delete them from the UI when finished (workspace, environment, dedicated settings, and usage history go away together).

### Sample

The GUI can write out a minimal sample project.

---

## 中文

放入文件夹或 ZIP 后，内容会复制到 `%LOCALAPPDATA%\uvdrop\apps\`，  
并在 `%LOCALAPPDATA%\uvdrop\envs\` 创建虚拟环境后再启动。

**运行前确认**不仅显示你直接写明的软件包，还会列出**一并安装的软件包**（完整依赖集合），并与许可列表 / 禁止列表（含版本规则）对照。

### uv 的优先级

1. **随附 `uv.exe`（优先）** — `tools/uv.exe` 或 `resources/tools/windows-x64/uv.exe`
2. 没有时才用 PATH 中的 **`uv`**

### 必需

1. **`pyproject.toml`**（根目录，或下一级）
2. **启动入口** — `main.py` / `app.py` / `run.py`，或 `uvdrop.manifest.json`，或 `[project.scripts]`

### 推荐结构

```text
my-app/
  pyproject.toml
  main.py
  README.md                 # 可选
  uvdrop.manifest.json      # 可选
```

若没有 `pyproject.toml`，可尝试从 `requirements.txt` 简易转换（不一定总能成功）。

### 保留与删除

导入的应用会留在列表中。不需要时从界面删除即可（工作目录、虚拟环境、专用配置与使用历史一并清除）。

### 示例

可从 GUI 写出最小示例项目。
