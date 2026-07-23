# installer/

Windows 向け **Setup.exe** を作るための一式です。

| ファイル | 役割 |
|----------|------|
| [PACKAGING.md](./PACKAGING.md) | **Inno 入門〜署名〜Release までの手順書（本命）** |
| `build.ps1` | uv 取得 → PyInstaller → Inno コンパイル |
| `fetch-uv.ps1` | 公式 `uv.exe` を `resources/tools/windows-x64/` へ |
| `sign.ps1` | Authenticode 署名（任意） |
| `uvdrop.iss` | Inno Setup スクリプト |

## 最短

```powershell
# 未導入なら
winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements

# リポジトリルートで
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

出力: `installer/output/uvdrop-<version>-setup.exe`
