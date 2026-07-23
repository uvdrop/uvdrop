# PyInstaller（ビルド時・バイナリ埋め込み）

uvdrop の Windows バイナリ（Inno / MSIX の中身）は [PyInstaller](https://pyinstaller.org/) で onedir 化しています。

## ライセンス上の要点

- PyInstaller 本体は **GPL-2.0-or-later** ですが、**Bootloader exception** により、PyInstaller で作ったアプリの配布が自動的に GPL になるわけではありません（公式 COPYING を確認）。
- 配布バイナリには次が含まれます。
  - PyInstaller bootloader
  - 埋め込み CPython（PSF License）
  - Tcl/Tk（Tcl/Tk License）— Tk GUI のため

## 参照

- https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt
- https://docs.python.org/3/license.html
- https://www.tcl-lang.org/software/tcltk/license.html

アプリの About / `THIRD_PARTY_NOTICES.md` から辿れるようにしてあります。
