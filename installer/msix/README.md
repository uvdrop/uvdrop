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

## Partner Center の流れ（概要）

1. https://storedeveloper.microsoft.com で個人アカウント（無料フロー）  
2. アプリ名を予約  
3. パッケージにこの `.msix` をアップロード  
4. ストア掲載情報・年齢レーティング・審査  

詳細コンセプトは [docs/DISTRIBUTION.md](../../docs/DISTRIBUTION.md)。

## マニフェストメモ

- `runFullTrust` … `uv.exe` 子プロセス・AppData・ネットのため  
- Publisher は Partner Center の発行元に合わせて後で差し替え（今は開発用プレースホルダ）
