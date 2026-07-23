# MSIX（Microsoft Store 向け）

同じ `dist/uvdrop/` payload（Inno と共通）を **MSIX** に包みます。  
アプリコードの分岐は不要です。

## 前提

- Windows 10/11
- 先に payload をビルド:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
```

- Store 提出用 `.msix` は **提出時に Microsoft が再署名**するため、提出パッケージに CA 証明書は不要  
  （ローカルインストール検証だけ自己署名が必要 → `-SignLocal`）

## ビルド

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
# ローカルで Install して試すとき
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1 -SignLocal
```

成果物: `installer/msix/output/uvdrop-<ver>.msix`

## Partner Center

Identity values for this app are in [IDENTITY.md](./IDENTITY.md) and `AppxManifest.xml`.

After packaging, in the app’s submission:

1. **Packages** → upload `installer/msix/output/uvdrop-<ver>.msix`（提出用は未署名で可）
2. Store listing（説明・スクショ）
3. Age ratings / properties
4. **Submit for certification**
