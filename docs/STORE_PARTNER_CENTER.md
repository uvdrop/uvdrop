# Microsoft Store に uvdrop を出すまで（Partner Center 手順メモ）

Qiita 等への転載を想定した手順メモです。  
uvdrop は **Python / Inno Setup.exe / MSIX(Store)** の3配布のうち、Store 向けが MSIX です。

- アプリ本体コードは共通（包み方だけ違う）→ [DISTRIBUTION.md](./DISTRIBUTION.md)
- パッケージ ID 控え → [../installer/msix/IDENTITY.md](../installer/msix/IDENTITY.md)
- 第三者ライセンス → [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)

---

## 結論だけ先に

| 疑問 | 答え |
|------|------|
| 登録・本人確認は自分がやる？ | **はい。代行不可**（身分証＋セルフィー等） |
| 申請（提出・審査）に費用はかかる？ | **個人の新フローなら登録料ゼロ。提出ごと課金も通常なし**（有料アプリの売上配分は別） |
| 製品 ID は今しか見えない？ | **いいえ。Partner Center に残り続ける**（公開前でもアプリ詳細から再確認可） |
| Qiita は HTML？ MD？ | **Markdown**（Qiita は MD。リポジトリも MD のままが兼用しやすい） |

---

## 全体の流れ

```text
[あなた] Partner Center アカウント作成・本人確認
    ↓
[あなた] アプリ名予約（例: uvdrop）→ Package Identity が発行される
    ↓
[開発]  Identity を AppxManifest.xml に反映 → MSIX ビルド
    ↓
[あなた] 掲載情報・年齢レーティング・パッケージアップロード
    ↓
[あなた] 「認証のために提出」→ Microsoft 審査 → ストア公開
```

Inno の Setup.exe（GitHub Releases）は **別ルート**。Store 用 MSIX と併存して問題ありません。

---

## 1. アカウント作成（あなたが必須）

入口はここ（無料の個人フロー）:

https://storedeveloper.microsoft.com

- **Individual / 個人** を選ぶ  
- Microsoft アカウントでサインイン  
- **公的身分証 + セルフィー** の本人確認  

> 直接 Partner Center の別入口から入ると、昔の有料登録画面が出ることがあります。迷ったら上記 URL から。

**費用:** 新フローの個人登録は **登録料なし**（2025年以降の案内）。  
**提出（審査申請）自体にも、通常は追加料金はかかりません。**  
有料アプリにした場合の売上配分（Microsoft の取り分）は別問題で、無料アプリなら気にしなくてよいです。

代行できない理由: 本人確認・規約同意・発行者名がアカウント所有者に紐づくため。

---

## 2. アプリ名の予約

1. https://partner.microsoft.com/dashboard/apps-and-games/overview  
2. **新しい製品 → アプリ**  
3. 種類は **MSIX**（EXE/MSI 提出ではない）  
4. 名前（例: `uvdrop`）の可用性確認 → **予約**

成功すると **Package Identity** が付きます。uvdrop 実例:

| 項目 | 例（控え） |
|------|------------|
| Identity Name | `kushi94.uvdrop` |
| Publisher | `CN=E3BB0538-56DE-400B-9683-8702B7A31930` |
| PublisherDisplayName | `kushi94` |
| PFN | `kushi94.uvdrop_t252av2yrfja0` |
| Microsoft Store ID | `9PH385P01SK4` |

### 「今しか控えられない？」について

**消えません。** Partner Center の当該アプリ → 製品 ID / パッケージ ID から **何度でも見返せます。**

ただし運用上は:

- リポジトリの `installer/msix/IDENTITY.md` やパスワードマネージャに **一度コピーしておく**と安心  
- 特に **Publisher（CN=…）** と **Identity Name** はマニフェストと一字一句一致が必要なので、メモ推奨  
- 「Web ストア URL」「ディープリンク」は **公開（有効化）後** に使えるようになる、と出るのは正常です。今取れなくて問題ありません  
- Store ID（例: `9PH385P01SK4`）も製品ページに残ります

---

## 3. MSIX のビルド（開発側）

Identity を `installer/msix/AppxManifest.xml` に合わせたうえで:

```powershell
cd path\to\uvdrop

# 1) 共通 payload（PyInstaller onedir）
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno

# 2) MSIX 化（Store 提出用は未署名でよい）
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

成果物例:

```text
installer\msix\output\uvdrop-0.3.1.msix
```

- **Store 提出:** 未署名でアップロード可（Microsoft が再署名＝証明書代不要）  
- **自分の PC でサイドロード試験:** `build-msix.ps1 -SignLocal`（自己署名）

関連:

- Inno Setup.exe 手順 → [../installer/PACKAGING.md](../installer/PACKAGING.md)  
- 配布3本柱 → [DISTRIBUTION.md](./DISTRIBUTION.md)

---

## 4. Partner Center で提出（あなたが中心）

アプリ `uvdrop` を開き、提出チェックリストを埋めます。

1. **パッケージ** … `.msix` をアップロード  
2. **ストア掲載情報** … 説明・スクショ・アイコン  
3. **プロパティ** … カテゴリ（例: 開発者ツール / ユーティリティ）  
4. **年齢レーティング** … 質問票  
5. **価格** … 無料なら Free  
6. すべて完了したら **「認証のために提出」**

審査ではフル信頼（`runFullTrust`）や「何をするアプリか」を聞かれることがあります。一文メモ例:

> ローカルの Python プロジェクト（フォルダ/ZIP）を、同梱の uv で環境作成・起動するデスクトップランチャーです。

---

## 5. 公開後

- Web ストア URL / ディープリンクが使えるようになる  
- 更新は新しい版の MSIX をまた提出（Identity の Name/Publisher は変えず、Version だけ上げる）  
- GitHub Releases の Setup.exe はこれまで通り別配布で併用可

---

## Qiita に載せるとき

- **形式は Markdown**（このファイルをほぼそのまま貼れる）  
- 自分の **Publisher CN や Store ID を全文出すか**は任意。出して問題ないことが多いが、伏せたいなら表を「例」にぼかす  
- スクショは Partner Center の画面を自分で撮って差し込むと読みやすい  
- タグ例: `Windows`, `MSIX`, `MicrosoftStore`, `Python`, `uv`

HTML が必要になるのは「独自の静的サイトを装飾したい」場合だけです。Qiita・GitHub・社内 Wiki なら **MD 一択**で十分です。

---

## よくある詰まり

| 症状 | 確認 |
|------|------|
| 登録でお金を求められる | `storedeveloper.microsoft.com` から入り直す |
| パッケージ拒否（Publisher 不一致） | Identity Name / CN がマニフェストと一致しているか |
| ストア URL がまだ無い | 公開前は「有効になると利用可能」で正常 |
| 審査でフル信頼を聞かれる | 上記の一文＋ uv 同梱・ローカル起動である旨 |

---

## 参考リンク

- 個人無料登録: https://storedeveloper.microsoft.com  
- Partner Center: https://partner.microsoft.com/dashboard/apps-and-games/overview  
- Store の MSIX 署名（無料再署名）: https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options  
- uvdrop サイト: https://uvdrop.github.io/uvdrop/  
- GitHub: https://github.com/uvdrop/uvdrop  
