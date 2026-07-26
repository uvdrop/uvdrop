# Microsoft Store / Partner Center notes for uvdrop

uvdrop ships three ways — **Python / Inno Setup.exe / MSIX (Store)**. Store uses MSIX.

- Shared app code (packaging differs) → [DISTRIBUTION.md](./DISTRIBUTION.md)
- Package identity → [../installer/msix/IDENTITY.md](../installer/msix/IDENTITY.md)
- Third-party licenses → [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)

---

## Japanese

### 結論だけ先に

| 疑問 | 答え |
|------|------|
| 登録・本人確認は自分がやる？ | **はい。代行不可**（身分証＋セルフィー等） |
| 申請（提出・審査）に費用はかかる？ | **個人の新フローなら登録料ゼロ。提出ごと課金も通常なし**（有料アプリの売上配分は別） |
| 製品 ID は今しか見えない？ | **いいえ。Partner Center に残り続ける**（公開前でもアプリ詳細から再確認可） |
| Qiita は HTML？ MD？ | **Markdown**（Qiita は MD。リポジトリも MD のままが兼用しやすい） |

### 全体の流れ

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

### 1. アカウント作成（あなたが必須）

入口（無料の個人フロー）: https://storedeveloper.microsoft.com

- **Individual / 個人** を選ぶ
- Microsoft アカウントでサインイン
- **公的身分証 + セルフィー** の本人確認

> 直接 Partner Center の別入口から入ると、昔の有料登録画面が出ることがあります。迷ったら上記 URL から。

**費用:** 新フローの個人登録は **登録料なし**（2025年以降の案内）。提出（審査申請）自体にも、通常は追加料金はかかりません。有料アプリにしたときの売上配分は別問題で、無料アプリなら気にしなくてよいです。

代行できない理由: 本人確認・規約同意・発行者名がアカウント所有者に紐づくため。

### 2. アプリ名の予約

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

**消えません。** Partner Center の当該アプリ → 製品 ID / パッケージ ID から何度でも見返せます。運用上は `installer/msix/IDENTITY.md` やパスワードマネージャに一度コピーしておくと安心です。特に **Publisher（CN=…）** と **Identity Name** はマニフェストと一字一句一致が必要です。「Web ストア URL」は **公開後** に使えるようになる、と出るのは正常です。

### 3. MSIX のビルド（開発側）

Identity を `installer/msix/AppxManifest.xml` に合わせたうえで:

```powershell
cd path\to\uvdrop
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

成果物例: `installer\msix\output\uvdrop-0.9.0.msix`

- **Store 提出:** 未署名でアップロード可（Microsoft が再署名＝証明書代不要）
- **自分の PC で試験:** `build-msix.ps1 -SignLocal`（自己署名）

関連: [../installer/PACKAGING.md](../installer/PACKAGING.md) · [DISTRIBUTION.md](./DISTRIBUTION.md)

### 4. Partner Center で提出

アプリ `uvdrop` を開き、提出チェックリストを埋めます。

1. **パッケージ** … `.msix` をアップロード
2. **ストア掲載情報** … 説明・スクショ・アイコン
3. **プロパティ** … カテゴリ（例: 開発者ツール / ユーティリティ）
4. **年齢レーティング** … 質問票
5. **価格** … 無料なら Free
6. すべて完了したら **「認証のために提出」**

審査ではフル信頼（`runFullTrust`）や「何をするアプリか」を聞かれることがあります。一文メモ例:

> ローカルの Python プロジェクト（フォルダ/ZIP）を、同梱の uv で環境作成・起動するデスクトップランチャーです。実行前にインストールされるパッケージ（あわせて入るもの含む）を確認できます。

### 5. 公開後

- Web ストア URL / ディープリンクが使えるようになる
- 更新は新しい版の MSIX をまた提出（Identity の Name/Publisher は変えず、Version だけ上げる）
- GitHub Releases の Setup.exe はこれまで通り別配布で併用可

### Qiita に載せるとき

- **形式は Markdown**（このファイルをほぼそのまま貼れる）
- Publisher CN や Store ID を全文出すかは任意
- タグ例: `Windows`, `MSIX`, `MicrosoftStore`, `Python`, `uv`

### よくある詰まり

| 症状 | 確認 |
|------|------|
| 登録でお金を求められる | `storedeveloper.microsoft.com` から入り直す |
| パッケージ拒否（Publisher 不一致） | Identity Name / CN がマニフェストと一致しているか |
| ストア URL がまだ無い | 公開前は「有効になると利用可能」で正常 |
| 審査でフル信頼を聞かれる | 上記の一文＋ uv 同梱・ローカル起動である旨 |
| Setup.exe 導入後に SAC がブロック（エラー 4551） | 未署名の PyInstaller/`uv.exe`。検証は `python -m uvdrop`。利用者向けは Store(MSIX) か Authenticode。詳細は [PACKAGING.md §8](../installer/PACKAGING.md) |

---

## English

### Short answers first

| Question | Answer |
|----------|--------|
| Do I register and verify identity myself? | **Yes. Cannot be delegated** (ID + selfie, etc.) |
| Does submission / review cost money? | **Individual new flow: no registration fee. Usually no per-submission fee** (paid-app revenue share is separate) |
| Are product IDs visible only once? | **No. They stay in Partner Center** (even before publish) |
| Qiita: HTML or MD? | **Markdown** |

### Overall flow

```text
[You] Create Partner Center account + identity verification
    ↓
[You] Reserve app name (e.g. uvdrop) → Package Identity issued
    ↓
[Dev] Put Identity into AppxManifest.xml → build MSIX
    ↓
[You] Listing, age rating, upload package
    ↓
[You] Submit for certification → Microsoft review → Store publish
```

Inno Setup.exe on GitHub Releases is a **separate path** and can coexist with Store MSIX.

### 1. Account (you must do this)

Entry (free individual flow): https://storedeveloper.microsoft.com

- Choose **Individual**
- Sign in with a Microsoft account
- Complete **government ID + selfie** verification

> Other Partner Center entry points may still show the old paid registration screen. Prefer the URL above.

**Cost:** New individual registration is **free** (guidance from 2025 onward). Submission usually has no extra fee. Paid-app revenue share is a separate topic; free apps do not need to worry about it.

Why it cannot be delegated: identity checks, terms, and publisher name bind to the account owner.

### 2. Reserve the app name

1. https://partner.microsoft.com/dashboard/apps-and-games/overview
2. **New product → App**
3. Type **MSIX** (not EXE/MSI submission)
4. Check name availability (e.g. `uvdrop`) → **Reserve**

You get a **Package Identity**. uvdrop example:

| Field | Example |
|-------|---------|
| Identity Name | `kushi94.uvdrop` |
| Publisher | `CN=E3BB0538-56DE-400B-9683-8702B7A31930` |
| PublisherDisplayName | `kushi94` |
| PFN | `kushi94.uvdrop_t252av2yrfja0` |
| Microsoft Store ID | `9PH385P01SK4` |

These **do not disappear**. Copy them into `installer/msix/IDENTITY.md` or a password manager. **Publisher (CN=…)** and **Identity Name** must match the manifest exactly. Missing Web Store URL before publish is normal.

### 3. Build MSIX (dev)

Align Identity in `installer/msix/AppxManifest.xml`, then:

```powershell
cd path\to\uvdrop
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

Example output: `installer\msix\output\uvdrop-0.9.0.msix`

- **Store submission:** unsigned upload is fine (Microsoft re-signs)
- **Local sideload test:** `build-msix.ps1 -SignLocal`

See also: [../installer/PACKAGING.md](../installer/PACKAGING.md) · [DISTRIBUTION.md](./DISTRIBUTION.md)

### 4. Submit in Partner Center

Open the `uvdrop` app and complete the checklist:

1. **Package** — upload `.msix`
2. **Store listing** — description, screenshots, icons
3. **Properties** — category (e.g. Developer tools / Utilities)
4. **Age ratings** — questionnaire
5. **Pricing** — Free if free
6. When complete → **Submit for certification**

Reviewers may ask about full trust (`runFullTrust`) and what the app does. One-line note:

> A desktop launcher that takes a local Python project (folder/ZIP), creates an environment with the bundled uv, and starts it. Before running, you can review packages that will be installed, including packages that come along.

### 5. After publish

- Web Store URL / deep links become available
- Updates: submit a new MSIX version (keep Name/Publisher; bump Version only)
- GitHub Releases Setup.exe can keep shipping in parallel

### Common blockers

| Symptom | Check |
|---------|-------|
| Asked to pay at registration | Re-enter via `storedeveloper.microsoft.com` |
| Package rejected (Publisher mismatch) | Identity Name / CN match the manifest |
| No Store URL yet | Normal before publish |
| Review asks about full trust | Use the one-line note above + bundled uv / local launch |
| SAC blocks after Setup.exe (error 4551) | Unsigned PyInstaller/`uv.exe`. Verify with `python -m uvdrop`. For users prefer Store (MSIX) or Authenticode. See [PACKAGING.md §8](../installer/PACKAGING.md) |

---

## 中文

### 先看结论

| 问题 | 回答 |
|------|------|
| 注册与本人验证必须自己做？ | **是。不可代办**（证件 + 自拍等） |
| 提交 / 审核要收费吗？ | **个人新流程通常无注册费，提交本身通常也不另收费**（付费应用分成另计） |
| 产品 ID 只能看一次？ | **否。会一直留在 Partner Center**（公开前也可再查） |
| Qiita 用 HTML 还是 MD？ | **Markdown** |

### 整体流程

```text
[你] 创建 Partner Center 账户并完成本人验证
    ↓
[你] 预约应用名（如 uvdrop）→ 获得 Package Identity
    ↓
[开发] 将 Identity 写入 AppxManifest.xml → 构建 MSIX
    ↓
[你] 填写上架信息、年龄分级、上传包
    ↓
[你] 「提交认证」→ Microsoft 审核 → 商店上架
```

GitHub Releases 上的 Inno Setup.exe 是 **另一条路径**，可与 Store 的 MSIX 并存。

### 1. 创建账户（必须本人）

入口（个人免费流程）: https://storedeveloper.microsoft.com

- 选择 **Individual / 个人**
- 用 Microsoft 账户登录
- 完成 **官方证件 + 自拍** 验证

> 从其他 Partner Center 入口进入，可能仍看到旧的收费注册页。请优先使用上述 URL。

**费用:** 个人新流程 **无注册费**（2025 年起相关说明）。提交审核通常也不另收费。付费应用的分成是另一回事；免费应用可忽略。

不可代办的原因: 本人验证、协议同意、发布者名称都绑定账户所有者。

### 2. 预约应用名

1. https://partner.microsoft.com/dashboard/apps-and-games/overview
2. **新产品 → 应用**
3. 类型选 **MSIX**（不是 EXE/MSI 提交）
4. 确认名称可用（如 `uvdrop`）→ **预约**

成功后会得到 **Package Identity**。uvdrop 示例:

| 项 | 示例 |
|----|------|
| Identity Name | `kushi94.uvdrop` |
| Publisher | `CN=E3BB0538-56DE-400B-9683-8702B7A31930` |
| PublisherDisplayName | `kushi94` |
| PFN | `kushi94.uvdrop_t252av2yrfja0` |
| Microsoft Store ID | `9PH385P01SK4` |

这些信息 **不会消失**。建议复制到 `installer/msix/IDENTITY.md` 或密码管理器。**Publisher（CN=…）** 与 **Identity Name** 必须与清单一字不差。公开前没有 Web 商店 URL 是正常的。

### 3. 构建 MSIX（开发侧）

将 Identity 对齐到 `installer/msix/AppxManifest.xml` 后:

```powershell
cd path\to\uvdrop
powershell -ExecutionPolicy Bypass -File .\installer\build.ps1 -SkipInno
powershell -ExecutionPolicy Bypass -File .\installer\msix\build-msix.ps1
```

产物示例: `installer\msix\output\uvdrop-0.9.0.msix`

- **提交 Store:** 可上传未签名包（Microsoft 会重新签名）
- **本机侧载测试:** `build-msix.ps1 -SignLocal`

另见: [../installer/PACKAGING.md](../installer/PACKAGING.md) · [DISTRIBUTION.md](./DISTRIBUTION.md)

### 4. 在 Partner Center 提交

打开应用 `uvdrop`，按清单填写:

1. **包** — 上传 `.msix`
2. **商店刊登信息** — 说明、截图、图标
3. **属性** — 分类（如开发者工具 / 实用工具）
4. **年龄分级** — 问卷
5. **价格** — 免费则选 Free
6. 全部完成后 → **提交认证**

审核可能询问完全信任（`runFullTrust`）以及应用做什么。一句话示例:

> 这是一个桌面启动器：接收本地 Python 项目（文件夹/ZIP），用随附的 uv 创建环境并启动。运行前可确认将要安装的软件包（含一并安装的软件包）。

### 5. 上架之后

- Web 商店 URL / 深度链接可用
- 更新时再提交新版本 MSIX（Name/Publisher 不变，只升 Version）
- GitHub Releases 的 Setup.exe 可继续并行分发

### 常见卡住点

| 现象 | 检查 |
|------|------|
| 注册时被要求付费 | 从 `storedeveloper.microsoft.com` 重新进入 |
| 包被拒（Publisher 不一致） | Identity Name / CN 是否与清单一致 |
| 还没有商店 URL | 公开前属正常 |
| 审核询问完全信任 | 用上面那句话 + 说明随附 uv、本地启动 |
| Setup.exe 安装后被 SAC 拦截（错误 4551） | 未签名的 PyInstaller/`uv.exe`。验证可用 `python -m uvdrop`。面向用户优先 Store(MSIX) 或 Authenticode。详见 [PACKAGING.md §8](../installer/PACKAGING.md) |

---

## 参考リンク / Reference links / 参考链接

- Individual free registration: https://storedeveloper.microsoft.com
- Partner Center: https://partner.microsoft.com/dashboard/apps-and-games/overview
- Store MSIX signing (free re-sign): https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options
- uvdrop site: https://uvdrop.github.io/uvdrop/
- GitHub: https://github.com/uvdrop/uvdrop
