"""CSV / XLSX report — generate workbook with a guided full-screen flow."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pandas as pd
import tkinter as tk
from tkinter import ttk

from ui_shell import apply_tk_theme, format_steps, maximize_tk

STEPS = ("表データを用意", "Excel に書き出す", "ファイルを開いて確認")


def main() -> int:
    out = Path(__file__).resolve().parent / "_out.xlsx"
    df = pd.DataFrame(
        {
            "item": ["alpha", "beta", "gamma", "delta"],
            "qty": [3, 5, 2, 8],
            "note": ["ok", "ok", "check", "ok"],
        }
    )
    df.to_excel(out, index=False)
    print("uvdrop-portal-ok csv-report", flush=True)
    print(f"wrote {out}", flush=True)

    root = tk.Tk()
    root.title("CSV / XLSX report")
    apply_tk_theme(root)
    maximize_tk(root)

    steps = tk.StringVar(value=format_steps(STEPS, 2))
    status = tk.StringVar(value=f"書き出し完了: {out.name}  — 次はファイルの場所を開いて中身を確認してください。")

    outer = ttk.Frame(root, padding=28)
    outer.pack(fill=tk.BOTH, expand=True)
    ttk.Label(outer, text="CSV / XLSX report", style="Hero.TLabel").pack(anchor=tk.W)
    ttk.Label(
        outer,
        text="pandas + openpyxl で表計算系アプリの入口を体験します。コンソールが消えても、この画面で結果が分かります。",
        style="Sub.TLabel",
        wraplength=960,
    ).pack(anchor=tk.W, pady=(6, 12))
    ttk.Label(outer, textvariable=steps, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 10))
    ttk.Label(outer, textvariable=status, style="Status.TLabel", wraplength=960).pack(fill=tk.X)

    card = ttk.Frame(outer, style="Card.TFrame", padding=20)
    card.pack(fill=tk.BOTH, expand=True, pady=16)
    preview = tk.Text(card, height=12, font=("Cascadia Mono", 11), bg="#0F172A", fg="#E2E8F0", relief=tk.FLAT)
    preview.pack(fill=tk.BOTH, expand=True)
    preview.insert("1.0", df.to_string(index=False) + f"\n\n保存先:\n{out}")
    preview.configure(state=tk.DISABLED)

    def open_folder() -> None:
        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", str(out)])
        else:
            subprocess.Popen(["xdg-open", str(out.parent)])
        steps.set(format_steps(STEPS, 3))
        status.set("エクスプローラーを開きました。_out.xlsx を Excel で開いて確認してください。")

    row = ttk.Frame(outer)
    row.pack(fill=tk.X)
    ttk.Button(row, text="ファイルの場所を開く", command=open_folder).pack(side=tk.LEFT)
    ttk.Button(row, text="閉じる", command=root.destroy).pack(side=tk.RIGHT)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
