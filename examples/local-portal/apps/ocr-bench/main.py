"""OCR Bench — pip-only RapidOCR + EasyOCR comparison (visual-first)."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from engines import EngineSpec, OcrBox, OcrResult, discover_engines, run_engine
from ui_shell import apply_tk_theme, format_steps, maximize_tk

BG = "#0B1020"
PANEL = "#151A2E"
INK = "#E8EEFF"
MUTED = "#8FA0C0"
ACCENT = "#4D96FF"
STEPS = ("画像を開く", "エンジンを実行", "結果を比較")

ENGINE_COLORS = {
    "rapidocr": "#6BCB77",
    "easyocr": "#FFD93D",
}


class OcrBenchApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OCR Bench")
        apply_tk_theme(root, bg=BG, ink=INK)
        maximize_tk(root)
        self.image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.results: dict[str, OcrResult] = {}
        self.engine_vars: dict[str, tk.BooleanVar] = {}
        self.engine_specs: list[EngineSpec] = list(discover_engines())
        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=INK)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("TCheckbutton", background=PANEL, foreground=INK)
        style.configure("TButton", padding=10)
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", padding=(14, 8))
        style.configure("Steps.TLabel", font=("Yu Gothic UI", 11, "bold"), background=PANEL, foreground=ACCENT)
        style.configure("Status.TLabel", font=("Yu Gothic UI", 11), background=PANEL, foreground=INK)

        head = ttk.Frame(self.root, padding=(20, 16))
        head.pack(fill=tk.X)
        ttk.Label(head, text="OCR Bench", font=("Yu Gothic UI", 22, "bold")).pack(anchor=tk.W)
        ttk.Label(
            head,
            text="pip だけで動くエンジンだけ。RapidOCR（軽め）と EasyOCR（日英・初回DL）。",
            foreground=MUTED,
        ).pack(anchor=tk.W)

        self.steps_var = tk.StringVar(value=format_steps(STEPS, 1))
        self.status_var = tk.StringVar(value="次: 「画像を開く」で比較したい画像を選ぶ")
        ttk.Label(head, textvariable=self.steps_var, style="Steps.TLabel").pack(fill=tk.X, pady=(10, 6))
        ttk.Label(head, textvariable=self.status_var, style="Status.TLabel", wraplength=1000).pack(fill=tk.X)

        outer = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        left = ttk.Frame(outer, padding=4)
        right = tk.Frame(outer, bg=PANEL, padx=12, pady=12)
        outer.add(left, weight=3)
        outer.add(right, weight=2)

        load_row = ttk.Frame(left)
        load_row.pack(fill=tk.X)
        ttk.Button(load_row, text="画像を開く", command=self.load_image).pack(side=tk.LEFT)
        ttk.Button(load_row, text="選択エンジンを実行", command=self.run_selected).pack(side=tk.LEFT, padx=8)

        self.canvas = tk.Canvas(left, bg="#070B16", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=8)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        self.legend_var = tk.StringVar(value="ボックスをクリックするとテキストを強調")
        ttk.Label(left, textvariable=self.legend_var, wraplength=520, foreground=MUTED).pack(anchor=tk.W)

        tk.Label(right, text="エンジン", bg=PANEL, fg=INK, font=("Yu Gothic UI", 12, "bold")).pack(anchor=tk.W)
        for spec in self.engine_specs:
            var = tk.BooleanVar(value=spec.available)
            self.engine_vars[spec.engine_id] = var
            state = tk.NORMAL if spec.available else tk.DISABLED
            label = spec.label if spec.available else f"{spec.label} — 利用不可"
            cb = ttk.Checkbutton(right, text=label, variable=var, state=state)
            cb.pack(anchor=tk.W, pady=2)
            if not spec.available and spec.note:
                tk.Label(right, text=f"  {spec.note[:100]}", bg=PANEL, fg=MUTED, wraplength=320).pack(anchor=tk.W)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        self.text_widgets: dict[str, tk.Text] = {}

    def load_image(self) -> None:
        path = filedialog.askopenfilename(
            title="画像を開く",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All", "*.*")],
        )
        if not path:
            return
        self.image = Image.open(path).convert("RGB")
        self.results.clear()
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.text_widgets.clear()
        self._render_canvas()
        self.steps_var.set(format_steps(STEPS, 2))
        self.status_var.set(f"読み込み: {path} — 次: エンジンを選び「選択エンジンを実行」")

    def _render_canvas(self, highlight_engine: str | None = None, highlight_box: OcrBox | None = None) -> None:
        if self.image is None:
            return
        canvas_w = max(self.canvas.winfo_width(), 400)
        canvas_h = max(self.canvas.winfo_height(), 300)
        iw, ih = self.image.size
        self.scale = min(canvas_w / iw, canvas_h / ih, 1.0)
        disp = self.image.resize((max(1, int(iw * self.scale)), max(1, int(ih * self.scale))))
        self.photo = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        for eng, result in self.results.items():
            color = ENGINE_COLORS.get(eng, "#fff")
            width = 3 if eng == highlight_engine else 2
            for box in result.boxes:
                x1 = box.x * self.scale
                y1 = box.y * self.scale
                x2 = (box.x + box.w) * self.scale
                y2 = (box.y + box.h) * self.scale
                if highlight_box is box:
                    width = 4
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width)

    def on_canvas_click(self, event: tk.Event) -> None:
        if not self.results:
            return
        x, y = event.x / self.scale, event.y / self.scale
        for eng, result in self.results.items():
            for box in result.boxes:
                if box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h:
                    self.legend_var.set(f"[{eng}] {box.text}")
                    self._render_canvas(highlight_engine=eng, highlight_box=box)
                    tab = self.text_widgets.get(eng)
                    if tab is not None:
                        for i, tid in enumerate(self.notebook.tabs()):
                            if self.notebook.nametowidget(tid) == tab.master:
                                self.notebook.select(i)
                                break
                    return

    def run_selected(self) -> None:
        if self.image is None:
            messagebox.showinfo("画像", "先に画像を開いてください。")
            return
        selected = [eid for eid, var in self.engine_vars.items() if var.get()]
        if not selected:
            messagebox.showinfo("エンジン", "1つ以上選んでください。")
            return
        self.steps_var.set(format_steps(STEPS, 2))
        self.status_var.set("実行中…（初回はモデル取得で時間がかかることがあります）")
        image = self.image.copy()

        def work() -> None:
            for eid in selected:
                result = run_engine(eid, image)
                self.root.after(0, lambda r=result: self._apply_result(r))
            self.root.after(0, self._done)

        threading.Thread(target=work, daemon=True).start()

    def _done(self) -> None:
        self.steps_var.set(format_steps(STEPS, 3))
        self.status_var.set("完了 — 右タブと色付きボックスでエンジン結果を比較してください")

    def _apply_result(self, result: OcrResult) -> None:
        self.results[result.engine_id] = result
        if result.engine_id in self.text_widgets:
            tw = self.text_widgets[result.engine_id]
            tw.delete("1.0", tk.END)
        else:
            frame = ttk.Frame(self.notebook)
            tw = tk.Text(frame, wrap=tk.WORD, bg="#070B16", fg=INK, insertbackground=INK, relief=tk.FLAT)
            tw.pack(fill=tk.BOTH, expand=True)
            self.notebook.add(frame, text=result.engine_id)
            self.text_widgets[result.engine_id] = tw
        if result.error:
            self.text_widgets[result.engine_id].insert(tk.END, f"ERROR\n{result.error}")
        else:
            header = f"{result.label}\n{result.elapsed_sec:.2f}s · boxes={len(result.boxes)}\n\n"
            self.text_widgets[result.engine_id].insert(tk.END, header + result.text)
        self._render_canvas()


def main() -> int:
    root = tk.Tk()
    OcrBenchApp(root)
    print("uvdrop-portal-ok ocr-bench", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
