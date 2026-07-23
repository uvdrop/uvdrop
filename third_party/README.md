# third_party/

再配布時に同梱する第三者ライセンス全文・メモです。  
概要はリポジトリ直下の [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) を見てください。

| ディレクトリ | 対象 |
|--------------|------|
| `uv/` | Astral uv（`LICENSE-APACHE`, `LICENSE-MIT`） |
| `pyinstaller/` | PyInstaller / 埋め込みランタイムのメモ |

`installer/build.ps1` は payload（`dist/uvdrop/`）へこのツリーと `LICENSE` / `THIRD_PARTY_NOTICES.md` をコピーします。
