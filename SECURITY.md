# Security Policy / セキュリティポリシー / 安全策略

uvdrop is a launcher that builds a virtual environment with `uv` and runs a
Python app you point it at. It is a convenience and *guard-rail* tool — it is
**not** a sandbox. Please read the threat model below before relying on it.

---

## 日本語

### 位置づけ（できること・できないこと）

- uvdrop は「実行前に中身を確認してから起動する」ための道具です。
- 起動したアプリは **あなたのユーザー権限で普通に動きます**（ファイル操作・ネットワーク等）。
  uvdrop はサンドボックスやコンテナではありません。**最終的な実行判断は利用者の責任**です。
- 信頼できない配布元のアプリは、内容を確認できないなら起動しないでください。

### 安全のための仕組み

1. **実行前レビュー**：仮想環境を作る前に、起動コマンドとインストール予定の
   パッケージ一覧を表示します。
2. **依存ツリーの事前解決（ビルドなし）**：確認画面を出す前に
   `uv lock --no-build` で依存関係を解決します。`--no-build` を付けているため、
   メタデータ取得のために**パッケージのビルドバックエンド（＝任意コード）を実行しません**。
   sdist しか無い等で解決できない場合は「直接指定のみ確認」に切り替え、
   その旨を確認画面で通知します。
3. **許可 / NG リスト**：パッケージ名＋バージョン規則で許可・ブロックを設定できます。
   NG リストに一致したものは常にブロックします。
4. **保守的な既定動作**：許可リストが「未許可はブロック」設定のとき、
   依存ツリー全体を確認できなかった場合は、未確認の推移的依存を入れないよう
   **起動を中止**します。
5. **ZIP Slip 対策**：ZIP 展開時にパス・トラバーサル（`../` など）を拒否します。
6. **コンソール窓**：既定では非表示。デバッグ時のみ設定で表示できます。

### 注意すべき挙動（重要）

- **ショートカットからの起動は確認画面を出しません。** 一度確認して作成した
  ショートカットは、前回と同じ環境・起動コマンドで即実行します
  （NG リスト該当だけは毎回ブロック）。信頼できるアプリにだけ作成してください。
- **`uv sync`（実際のインストール）は確認後に実行されます。** このとき
  sdist のビルドが走ることがあり、その中でコードが実行され得ます。
  確認画面はあくまで「何が入るか」を見るためのもので、ビルド内容の安全性までは保証しません。
- **アンインストールしても `%LOCALAPPDATA%\uvdrop\` は残ります。** 取り込んだ
  アプリ・仮想環境・`.env`・設定・ログが含まれます。完全に消すには手動で
  フォルダを削除してください（[UNINSTALL.md](./docs/UNINSTALL.md) 参照）。
- **許可リストの URL に `http://` を使うと改ざんの恐れがあります。** できる限り
  `https://` かローカルパスを使ってください。

### 脆弱性の報告

セキュリティ上の問題を見つけた場合は、公開の Issue ではなく、
GitHub の **Security Advisories**（Report a vulnerability）からお知らせください。
できるだけ以下を含めてください。

- 再現手順（対象アプリ / 設定 / OS バージョン）
- 期待される挙動と実際の挙動
- 影響範囲の見立て

対応方針の初回返信は原則 **7 日以内** を目安とします。

---

## English

### What uvdrop is (and is not)

- uvdrop helps you **review before you run**.
- Launched apps run **with your normal user privileges** (files, network, …).
  uvdrop is **not** a sandbox or container. The final decision to run is yours.
- Do not launch apps from untrusted sources if you cannot review their contents.

### Safety mechanisms

1. **Pre-run review** of the start command and the packages to be installed,
   shown *before* the environment is created.
2. **Dependency resolution without building.** Before the review dialog, uvdrop
   runs `uv lock --no-build`, so **no package build backend (arbitrary code) is
   executed** just to read metadata. If resolution is not possible (e.g. an
   sdist-only package), it falls back to checking declared packages only and
   says so in the dialog.
3. **Allow / block lists** by package name + version rule. Block-list hits are
   always blocked.
4. **Conservative default:** when the allow list is set to *block* anything not
   allowed and the full tree could not be verified, uvdrop **refuses to launch**
   rather than install an unverified transitive tree.
5. **Zip-slip protection:** path traversal (`../`, absolute paths) is rejected
   during ZIP extraction.
6. **Console window** is hidden by default; enable it only for debugging.

### Important behaviors

- **Shortcuts skip the review dialog.** Once created (after one review), a
  shortcut re-runs with the same environment and command immediately (only
  block-list hits still stop it). Create them only for apps you trust.
- **`uv sync` (the real install) runs after confirmation.** It may build sdists,
  which can execute code. The review dialog shows *what* will be installed, not a
  guarantee about the safety of build scripts.
- **Uninstalling leaves `%LOCALAPPDATA%\uvdrop\` in place** (apps, envs, `.env`,
  settings, logs). Delete the folder manually to remove everything (see
  [docs/UNINSTALL.md](./docs/UNINSTALL.md)).
- **An `http://` allow-list URL can be tampered with.** Prefer `https://` or a
  local path.

### Reporting a vulnerability

Please report security issues privately via GitHub **Security Advisories**
(Report a vulnerability), not a public issue. Include reproduction steps, the
expected vs. actual behavior, and your impact assessment. We aim to reply within
**7 days**.

---

## 中文（简要）

uvdrop 是一个“先确认再运行”的启动器，**不是沙箱**。启动的应用以你的普通用户权限运行。
主要安全机制：运行前预览、`uv lock --no-build`（不执行构建即解析依赖）、许可/禁止列表、
禁止列表命中即阻止、block 模式下无法核实完整依赖树时中止运行、ZIP 解压防路径穿越、
默认隐藏控制台。

注意：**快捷方式启动会跳过确认界面**；`uv sync` 实际安装在确认之后进行，可能构建 sdist；
**卸载后 `%LOCALAPPDATA%\uvdrop\` 仍会保留**；许可列表 URL 请尽量用 `https://` 或本地路径。

请通过 GitHub **Security Advisories** 私下报告安全问题。
