"""Pillow thumbnail — generate sample art and show it full-screen guided."""
from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from ui_shell import apply_tk_theme, format_steps, maximize_tk

STEPS = ("画像を生成", "プレビューで確認", "ファイル保存先を把握")


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("Yu Gothic UI", "Segoe UI", "Arial"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    out = Path(__file__).resolve().parent / "_thumb.png"
    img = Image.new("RGB", (960, 540), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((48, 48, 912, 492), radius=36, fill=(13, 148, 136))
    draw.text((80, 160), "uvdrop", fill=(255, 255, 255), font=_font(72))
    draw.text((80, 260), "Pillow で画像を作れる入口サンプル", fill=(204, 251, 241), font=_font(28))
    draw.text((80, 330), str(out.name), fill=(167, 243, 208), font=_font(20))
    img.save(out)
    print("uvdrop-portal-ok pillow-thumb", flush=True)

    root = tk.Tk()
    root.title("Pillow thumbnail")
    apply_tk_theme(root, bg="#0F172A", ink="#E2E8F0")
    maximize_tk(root)

    steps = tk.StringVar(value=format_steps(STEPS, 2))
    status = tk.StringVar(value=f"生成済み → 大きく表示中。保存先はアプリフォルダの {out.name}")

    outer = ttk.Frame(root, padding=28)
    outer.pack(fill=tk.BOTH, expand=True)
    ttk.Label(outer, text="Pillow thumbnail", style="Hero.TLabel").pack(anchor=tk.W)
    ttk.Label(
        outer,
        text="画像系依存の入口。生成→表示→ファイル確認まで、画面上で完結します。",
        style="Sub.TLabel",
        wraplength=960,
    ).pack(anchor=tk.W, pady=(6, 12))
    ttk.Label(outer, textvariable=steps, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 10))
    ttk.Label(outer, textvariable=status, style="Status.TLabel", wraplength=960).pack(fill=tk.X)

    photo = ImageTk.PhotoImage(img)
    stage = tk.Label(outer, image=photo, bg="#0F172A")
    stage.image = photo  # type: ignore[attr-defined]
    stage.pack(fill=tk.BOTH, expand=True, pady=16)

    def done() -> None:
        steps.set(format_steps(STEPS, 3))
        status.set(f"完了: {out} を確認できれば OK。次は Diff Shot / Clip Factory など実務寄りの画像ツールへ。")

    row = ttk.Frame(outer)
    row.pack(fill=tk.X)
    ttk.Button(row, text="確認できた", command=done).pack(side=tk.LEFT)
    ttk.Button(row, text="閉じる", command=root.destroy).pack(side=tk.RIGHT)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
