# Windows 配布ガイド（Inno Setup 入門付き）

この文書は **Inno Setup を初めて使う人**向けに、uvdrop の Setup.exe を作って GitHub Releases に載せるまでの手順です。

配布全体（Python / Inno / MSIX）の関係は先に [docs/DISTRIBUTION.md](../docs/DISTRIBUTION.md) を読むと分かりやすいです。  
第三者ライセンスは [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

想定成果物:

```text
installer/output/uvdrop-0.3.0-setup.exe
```

利用者はこれを実行すると「アプリと機能」に **uvdrop** が登録されます。  
素の PyInstaller `.exe` を直配布するより、AV ヒューリスティックに拾われにくいことが多いです（さらに **Authenticode 署名**があると安定します）。

---

## 全体像

```text
[ソース]
   │  installer/fetch-uv.ps1   … 公式 uv.exe を同梱用に取得
   │  PyInstaller (uvdrop.spec) … dist\uvdrop\ にアプリ本体
   ▼
[Inno Setup / ISCC]
   │  installer/uvdrop.iss
   ▼
Setup.exe  →  (任意) sign.ps1 で署名  →  GitHub Release
```

スクリプト一発:

```powershell
cd D:\path\to\uvdrop
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

成功すると `installer\output\uvdrop-<version>-setup.exe` ができます。

---

## 1. 必要なもの

| ツール | 用途 | 入れ方 |
|--------|------|--------|
| Python 3.11+ | 開発・PyInstaller | 既存で OK |
| **Inno Setup 6** | Setup.exe を作る本命 | 下記 |
| uv.exe（公式） | ランチャー同梱 | `fetch-uv.ps1` が自動取得可（推奨 0.11.6+。版の話は [docs/UV_RUNTIME.md](../docs/UV_RUNTIME.md)） |
| （任意）Windows SDK | `signtool` で署名 | Visual Studio / Build Tools |
| （任意）コード署名証明書 | Authenticode | プライベート CA または購入 |

### Inno Setup のインストール（初めての人向け）

**A. winget（おすすめ）**

```powershell
winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
```

**B. 公式インストーラ**

1. https://jrsoftware.org/isinfo.php を開く  
2. **Download Inno Setup**（Inno Setup 6）  
3. インストール（日本語 UI あり）  
4. コンパイラ本体はだいたい次の場所:

```text
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

GUI で開くなら **Inno Setup Compiler** を起動し、`installer\uvdrop.iss` を File → Open。

> `build.ps1` は `ISCC.exe` を自動検索します。見つからない場合は終了コード 2 で止まり、payload（`dist\uvdrop\`）までは作ってあります。

---

## 2. 初回ビルド（最短）

```powershell
# リポジトリルートで
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

やっていること:

1. `src\uvdrop\version.py` の版を `uvdrop.iss` に同期  
2. `uv.exe` が無ければ GitHub Releases から取得  
3. `pip install pyinstaller` + `PyInstaller uvdrop.spec`  
4. `ISCC.exe installer\uvdrop.iss` で Setup.exe 生成  

### Inno だけ後からやる場合

```powershell
# payload のみ
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno

# Inno 導入後、再実行（または GUI で Build）
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1
```

### GUI で .iss をビルドする（勉強用）

1. **Inno Setup Compiler** を起動  
2. `installer\uvdrop.iss` を開く  
3. メニュー **Build → Compile**（または Ctrl+F9）  
4. 下のログに `Successful compile` が出れば成功  
5. 出力: `installer\output\uvdrop-<ver>-setup.exe`

`.iss` のざっくり意味:

| セクション | 意味 |
|------------|------|
| `[Setup]` | アプリ名・版・インストール先・Apps & Features 用 AppId |
| `[Files]` | どのファイルをどこへコピーするか |
| `[Icons]` | スタートメニュー / デスクトップ |
| `[Run]` | インストール直後に起動するか |
| `[Languages]` | ウィザードの言語 |

`AppId` は **一度決めたら変えない**こと（変えると別アプリ扱い・二重インストールになります）。

---

## 3. インストール結果の確認

1. `uvdrop-*-setup.exe` を実行  
2. 既定では `%LOCALAPPDATA%\Programs\uvdrop\` に入る（管理者不要）  
3. 「設定 → アプリ」に **uvdrop** が出る  
4. 起動してヘッダーの版番号を確認  
5. ステータス行に `uv: ...\tools\uv.exe` と出るか確認  

アンインストールも「アプリと機能」からできます。

---

## 4. 署名（あると本命）

署名なしでも配布はできますが、SmartScreen / AV ではまだ警告が出ることがあります。

```powershell
# 証明書の Thumbprint を調べる
Get-ChildItem Cert:\CurrentUser\My |
  Where-Object { $_.HasPrivateKey } |
  Format-Table Thumbprint, Subject

$env:SIGN_CERT_THUMBPRINT = "（拇印）"
powershell -ExecutionPolicy Bypass -File .\installer\sign.ps1 `
  -Path .\installer\output\uvdrop-0.3.0-setup.exe
```

`build.ps1 -Sign` でも、ビルド直後に同じ処理を呼べます。

必要なもの:

- コード署名証明書（`.pfx` をインポート済み、またはスマートカード）  
- `signtool.exe`（Windows SDK）

限定した相手にだけ配るなら、**プライベート CA で発行したコード署名証明書**を利用者 PC に信頼させる運用でも十分です。

---

## 5. GitHub Releases への載せ方

1. `version.py` / `CHANGELOG.md` / Pages の版を揃える（コミット・タグ）  
2. Setup.exe をビルド（できれば署名）  
3. GitHub → **Releases → Draft a new release**  
4. Tag: `v0.3.0`（既存タグでも可）  
5. タイトル例: `uvdrop 0.3.0`  
6. 本文に `CHANGELOG.md` の該当節を貼る  
7. Assets に `uvdrop-0.3.0-setup.exe` を添付  
8. Publish  

サイト（Pages）のダウンロード導線は Releases を指すようにしてあります。

CLI がある場合:

```powershell
gh release create v0.3.0 .\installer\output\uvdrop-0.3.0-setup.exe `
  --title "uvdrop 0.3.0" `
  --notes-file CHANGELOG.md
```

---

## 6. トラブルシュート

| 症状 | 確認 |
|------|------|
| `ISCC.exe not found` | Inno Setup 6 を入れる。パスは上文参照 |
| PyInstaller で tkinter エラー | Python が Embeddable 版でないか。通常の python.org / Store 版を推奨 |
| 起動後 `uv.exe not found` | `resources\tools\windows-x64\uv.exe` があるか。`fetch-uv.ps1` 再実行 |
| AV が Setup を落とす | 署名、または AV 側の許可登録。単体 exe 直配布は避ける |
| 版が古い | `src\uvdrop\version.py` を上げてから `build.ps1`（.iss は自動同期） |

---

## 7. 版の上げ方（メンテ手順）

1. `src/uvdrop/version.py` を変更（例 `0.3.0` → `0.3.1`）  
2. `pyproject.toml` の `version` も同じに  
3. `CHANGELOG.md` に節を追加  
4. `docs/index.html` の表示版を更新  
5. `build.ps1`（.iss は自動同期）  
6. タグ `vX.Y.Z` を push → Release に Setup.exe  

---

## 8. Smart App Control / 「署名がない」でブロックされるとき

Windows 11 の **スマート アプリ コントロール (SAC)** や、厳しい環境のアプリケーション制御は、**未署名の exe を CreateProcess エラー（例: 4551）で止めます。**

Inno で入れた構成だと、少なくとも次が対象になり得ます。

| ファイル | なぜブロックされうるか |
|----------|------------------------|
| `uvdrop.exe` | PyInstaller 製で、配布者が Authenticode 署名していない |
| `tools\uv.exe` | 公式ビルドでも環境によっては「信頼不足」と判定されることがある |

### 開発者本人が試すとき（いちばん手軽）

インストーラ版を使わず、ソースから:

```powershell
cd path\to\uvdrop
python -m uvdrop
```

（通常の python.org 製 Python は署名付きのため、SAC 下でも動きやすいです。）

### 利用者向けの本命ルート

| 配布 | SAC / 信頼 |
|------|------------|
| **Microsoft Store + MSIX** | Store がパッケージを再署名 → **証明書を自分で買わなくても**一般利用者向けに最も通りやすい |
| **GitHub Releases + Setup.exe** | **Authenticode 署名が実質必須**（`uvdrop.exe` と、同梱するなら `uv.exe` も署名推奨） |

署名手順は上文「4. 署名」および `installer/sign.ps1`。  
証明書が無い段階では、**Store 提出を先に進める**か、**テストは `python -m uvdrop`** が現実的です。

### SAC をオフにする？

自分の検証 PC だけ、一時的に無効化して試す人はいます。ただし:

- 組織ポリシーや家庭の「推奨構成」では推奨しない  
- SAC は一度 Enforcement になると、**簡単には元に戻せない**場合がある  

利用者向け案内に「SAC を切ってください」と書くのは避け、**Store 版または署名付き Setup** を案内してください。

---

## 参考リンク

- Inno Setup: https://jrsoftware.org/isinfo.php  
- Inno ドキュメント: https://jrsoftware.org/ishelp/  
- uv releases: https://github.com/astral-sh/uv/releases  
- uvdrop Releases: https://github.com/uvdrop/uvdrop/releases  
- サイト: https://uvdrop.github.io/uvdrop/
