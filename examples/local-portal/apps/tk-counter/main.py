"""Tk Counter — stdlib GUI entry with clear steps."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui_shell import apply_tk_theme, format_steps, maximize_tk

STEPS = ("窓を開く", "ボタンを押す", "GUIが動くと確認")


def main() -> int:
    root = tk.Tk()
    root.title("Tk Counter — 標準ライブラリ GUI")
    apply_tk_theme(root)
    maximize_tk(root)

    n = tk.IntVar(value=0)
    steps = tk.StringVar(value=format_steps(STEPS, 1))
    status = tk.StringVar(value="いまここ: 標準の tkinter だけで窓を出せています。")

    outer = ttk.Frame(root, padding=28)
    outer.pack(fill=tk.BOTH, expand=True)
    ttk.Label(outer, text="Tk Counter", style="Hero.TLabel").pack(anchor=tk.W)
    ttk.Label(
        outer,
        text="追加依存なしで GUI が動く入口。uvdrop 経由でもウィンドウアプリを配れる、の実演です。",
        style="Sub.TLabel",
        wraplength=900,
    ).pack(anchor=tk.W, pady=(6, 12))
    ttk.Label(outer, textvariable=steps, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 10))
    ttk.Label(outer, textvariable=status, style="Status.TLabel", wraplength=900).pack(fill=tk.X)

    stage = ttk.Frame(outer, style="Card.TFrame", padding=40)
    stage.pack(fill=tk.BOTH, expand=True, pady=18)
    tk.Label(stage, textvariable=n, bg="#FFFFFF", fg="#0D9488", font=("Yu Gothic UI", 96, "bold")).pack()
    tk.Label(
        stage,
        text="＋ / − を押すたびに数が変わります。これが「操作できる GUI」の確認です。",
        bg="#FFFFFF",
        fg="#64748B",
        font=("Yu Gothic UI", 12),
    ).pack(pady=(12, 0))

    def bump(delta: int) -> None:
        n.set(n.get() + delta)
        steps.set(format_steps(STEPS, 2))
        status.set(f"操作中: 現在値 {n.get()}  — ウィンドウが応答していれば成功です。")

    def finish() -> None:
        steps.set(format_steps(STEPS, 3))
        status.set("完了: stdlib GUI の起動ルートを確認できました。次は画像や Web サンプルへ。")

    row = ttk.Frame(outer)
    row.pack(fill=tk.X)
    ttk.Button(row, text="−1", command=lambda: bump(-1)).pack(side=tk.LEFT)
    ttk.Button(row, text="+1", command=lambda: bump(1)).pack(side=tk.LEFT, padx=8)
    ttk.Button(row, text="リセット", command=lambda: n.set(0)).pack(side=tk.LEFT)
    ttk.Button(row, text="確認できた", command=finish).pack(side=tk.LEFT, padx=16)
    ttk.Button(row, text="閉じる", command=root.destroy).pack(side=tk.RIGHT)

    print("uvdrop-portal-ok tk-counter", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
