"""Hello — uvdrop ポータルの基準線。何が起きているかを説明する案内アプリ。"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from ui_shell import apply_tk_theme, format_steps, maximize_tk

STEPS = ("起動できた", "依存なしを確認", "次のサンプルへ")


def main() -> int:
    root = tk.Tk()
    root.title("Hello — uvdrop のはじめの一歩")
    apply_tk_theme(root)
    maximize_tk(root)

    outer = ttk.Frame(root, padding=28)
    outer.pack(fill=tk.BOTH, expand=True)

    ttk.Label(outer, text="Hello（stdlib）", style="Hero.TLabel").pack(anchor=tk.W)
    ttk.Label(
        outer,
        text="uvdrop が「フォルダを取り込んで、そのアプリを起動できた」ことを確認する基準線です。",
        style="Sub.TLabel",
        wraplength=900,
    ).pack(anchor=tk.W, pady=(6, 12))

    steps = tk.StringVar(value=format_steps(STEPS, 1))
    status = tk.StringVar(value="いまここ: この窓が開けていれば、ポータル経由の起動は成功しています。")

    ttk.Label(outer, textvariable=steps, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 10))
    ttk.Label(outer, textvariable=status, style="Status.TLabel", wraplength=900).pack(fill=tk.X, pady=(0, 18))

    card = ttk.Frame(outer, style="Card.TFrame", padding=20)
    card.pack(fill=tk.BOTH, expand=True)
    body = (
        "このサンプルの意味\n"
        "・追加パッケージなし（標準ライブラリのみ）\n"
        "・カタログ → 実行前確認 → 起動、の最短ルートを試す\n"
        "・ここが動くなら、次は Tk Counter / Flask / 画像系へ進める\n\n"
        "uvdrop で起きていること（ざっくり）\n"
        "1. アプリを作業フォルダへ取り込む\n"
        "2. 依存を確認・仮想環境を用意（この Hello は依存なし）\n"
        "3. 指定した起動コマンド（main.py）を実行する\n\n"
        "迷ったら: この窓を閉じてカタログに戻り、次のアプリを選んでください。"
    )
    tk.Label(
        card,
        text=body,
        bg="#FFFFFF",
        fg="#0F172A",
        justify=tk.LEFT,
        font=("Yu Gothic UI", 12),
        anchor=tk.NW,
    ).pack(fill=tk.BOTH, expand=True)

    row = ttk.Frame(outer)
    row.pack(fill=tk.X, pady=(16, 0))

    def mark_done() -> None:
        steps.set(format_steps(STEPS, 3))
        status.set("完了: 基準線OK。カタログで次のサンプルを開きましょう。")

    ttk.Button(row, text="理解した（完了にする）", command=mark_done).pack(side=tk.LEFT)
    ttk.Button(row, text="閉じる", command=root.destroy).pack(side=tk.LEFT, padx=8)

    print("uvdrop-portal-ok hello-stdlib", flush=True)
    steps.set(format_steps(STEPS, 2))
    status.set("依存パッケージは使っていません。閉じてもポータル側の一覧には残ります（保持した場合）。")
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
