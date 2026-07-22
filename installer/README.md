# uvdrop installer

Windows 向けは **Inno Setup の Setup.exe** を配布する想定です（素の PyInstaller 単体 exe は AV に拾われやすいため）。

## 手順（概要）

1. [uv releases](https://github.com/astral-sh/uv/releases) から `uv.exe` を取得し `resources/tools/windows-x64/uv.exe` に配置
2. `installer/build.ps1` で PyInstaller onedir ビルド
3. Inno Setup 6 で `uvdrop.iss` をコンパイル → `installer/output/uvdrop-*-setup.exe`
4. 可能なら Authenticode 署名
5. GitHub Releases にアップロード

```powershell
# from repo root
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
# then open uvdrop.iss in Inno Setup and Build
```

Apps & Features に「uvdrop」として載るよう `AppId` / Uninstall 情報を `.iss` に定義済みです。
