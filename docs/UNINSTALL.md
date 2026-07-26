# Uninstalling uvdrop / アンインストール / 卸载

## 日本語

uvdrop 本体（Setup.exe / MSIX / Python パッケージ）をアンインストールしても、
利用者データは自動では消えません。これは、取り込んだアプリや設定を誤って失わない
ための仕様です。

### 残るもの

`%LOCALAPPDATA%\uvdrop\` 配下：

| フォルダ / ファイル | 内容 |
| --- | --- |
| `apps\` | 取り込んだアプリのワークスペース |
| `envs\` | 各アプリの仮想環境（.venv） |
| `dotenv\` | アプリ専用の `.env` |
| `policies\` | 許可 / NG リスト・Python バージョン設定 |
| `launchers\` | デスクトップショートカットが呼ぶ `.cmd` とログ |
| `settings.json` | アプリの設定（表示言語・ガード設定など） |
| `usage.json` | 起動履歴（最終起動・回数） |

デスクトップに作成したショートカット（`.lnk`）も残ります。

### 完全に削除する

エクスプローラのアドレスバーに次を貼り付けて開き、フォルダごと削除してください。

```
%LOCALAPPDATA%\uvdrop
```

PowerShell の場合：

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\uvdrop"
```

作成済みのデスクトップショートカットは手動で削除してください。

## English

Uninstalling the uvdrop application (Setup.exe / MSIX / Python package) does
**not** remove your data automatically, so you never lose imported apps or
settings by accident.

### What remains

Under `%LOCALAPPDATA%\uvdrop\`:

| Folder / file | Contents |
| --- | --- |
| `apps\` | imported app workspaces |
| `envs\` | each app's virtual environment |
| `dotenv\` | per-app `.env` |
| `policies\` | allow / block lists, Python version rules |
| `launchers\` | the `.cmd` shortcuts call, plus their logs |
| `settings.json` | app settings (language, guard options, …) |
| `usage.json` | launch history |

Any desktop shortcuts (`.lnk`) you created also remain.

### Remove everything

Open `%LOCALAPPDATA%\uvdrop` in Explorer and delete the folder, or:

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\uvdrop"
```

Then delete any desktop shortcuts you made.

## 中文

卸载 uvdrop 程序（Setup.exe / MSIX / Python 包）**不会**自动删除你的数据，
以免误删已导入的应用或设置。

保留位置：`%LOCALAPPDATA%\uvdrop\`（`apps` / `envs` / `dotenv` / `policies` /
`launchers` / `settings.json` / `usage.json`）以及你创建的桌面快捷方式。

彻底删除：

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\uvdrop"
```

然后手动删除桌面快捷方式。
