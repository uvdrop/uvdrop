"""OCR Bench — compare multiple OCR engines side by side."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from engines import EngineSpec, OcrBox, OcrResult, discover_engines, run_engine

ENGINE_COLORS = {
    "tesseract": "#2563eb",
    "pyocr": "#7c3aed",
    "easyocr": "#059669",
    "paddleocr": "#dc2626",
    "baberu": "#db2777",
    "manga_ocr": "#d97706",
}


class OcrBenchApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OCR Bench — エンジン比較")
        self.root.geometry("1100x720")

        self.image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.results: dict[str, OcrResult] = {}
        self.engine_vars: dict[str, tk.BooleanVar] = {}
        self.engine_specs: list[EngineSpec] = list(discover_engines())
        self._render_job: str | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.Frame(outer, padding=4)
        right = ttk.Frame(outer, padding=4)
        outer.add(left, weight=3)
        outer.add(right, weight=2)

        load_row = ttk.Frame(left)
        load_row.pack(fill=tk.X)
        ttk.Button(load_row, text="画像を開く", command=self.load_image).pack(side=tk.LEFT)
        ttk.Button(load_row, text="選択エンジンを実行", command=self.run_selected).pack(side=tk.LEFT, padx=8)

        self.canvas = tk.Canvas(left, bg="#222", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=8)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        legend = ttk.LabelFrame(left, text="凡例（クリックで強調）", padding=6)
        legend.pack(fill=tk.X)
        self.legend_var = tk.StringVar(value="—")
        ttk.Label(legend, textvariable=self.legend_var, wraplength=520).pack(anchor=tk.W)

        engines_frame = ttk.LabelFrame(right, text="エンジン", padding=8)
        engines_frame.pack(fill=tk.X)
        for spec in self.engine_specs:
            var = tk.BooleanVar(value=spec.available)
            self.engine_vars[spec.engine_id] = var
            state = tk.NORMAL if spec.available else tk.DISABLED
            label = spec.label if spec.available else f"{spec.label} — 利用不可"
            cb = ttk.Checkbutton(engines_frame, text=label, variable=var, state=state)
            cb.pack(anchor=tk.W)
            if not spec.available and spec.note:
                ttk.Label(engines_frame, text=f"  ↳ {spec.note[:120]}", wraplength=360).pack(anchor=tk.W)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=8)
        self.text_widgets: dict[str, tk.Text] = {}

        self.status_var = tk.StringVar(value="画像を読み込んでください。")
        ttk.Label(right, textvariable=self.status_var, wraplength=420).pack(anchor=tk.W)

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
        self.status_var.set(f"読み込み: {path}")

    def _render_canvas(self, highlight_engine: str | None = None, highlight_box: OcrBox | None = None) -> None:
        if self.image is None:
            return
        canvas_w = max(self.canvas.winfo_width(), 400)
        canvas_h = max(self.canvas.winfo_height(), 300)
        img = self.image.copy()
        self.scale = min(canvas_w / img.width, canvas_h / img.height, 1.0)
        disp = img.resize(
            (max(1, int(img.width * self.scale)), max(1, int(img.height * self.scale))),
            Image.Resampling.LANCZOS,
        )
        self.photo = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo, tags="base")

        legend_parts: list[str] = []
        for engine_id, result in self.results.items():
            if result.error:
                continue
            color = ENGINE_COLORS.get(engine_id, "#ffffff")
            legend_parts.append(f"{result.label}: {color}")
            for box in result.boxes:
                x1 = int(box.x * self.scale)
                y1 = int(box.y * self.scale)
                x2 = int((box.x + box.w) * self.scale)
                y2 = int((box.y + box.h) * self.scale)
                width = 3 if highlight_engine == engine_id and highlight_box is box else 1
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width, tags=engine_id)

        self.legend_var.set(" / ".join(legend_parts) if legend_parts else "ボックス付き結果がここに表示されます")

    def run_selected(self) -> None:
        if self.image is None:
            messagebox.showinfo("OCR", "先に画像を開いてください。")
            return
        selected = [eid for eid, var in self.engine_vars.items() if var.get()]
        if not selected:
            messagebox.showinfo("OCR", "エンジンを1つ以上選んでください。")
            return
        self.status_var.set("OCR 実行中…")

        def task() -> None:
            for engine_id in selected:
                result = run_engine(engine_id, self.image)  # type: ignore[arg-type]
                self.root.after(0, lambda r=result: self._apply_result(r))
            self.root.after(0, lambda: self.status_var.set("完了"))

        threading.Thread(target=task, daemon=True).start()

    def _apply_result(self, result: OcrResult) -> None:
        self.results[result.engine_id] = result
        existing = self.text_widgets.get(result.engine_id)
        if existing is not None:
            try:
                self.notebook.forget(existing["frame"])
            except tk.TclError:
                pass
        frame = ttk.Frame(self.notebook)
        text = tk.Text(frame, wrap=tk.WORD, height=12)
        text.pack(fill=tk.BOTH, expand=True)
        if result.error:
            body = f"エラー:\n{result.error}"
        else:
            body = f"所要: {result.elapsed_sec:.2f}s\n\n{result.text}"
            if not result.boxes:
                body += "\n\n（このエンジンは文字範囲ボックスを返しません）"
        text.insert("1.0", body)
        text.configure(state=tk.DISABLED)
        self.notebook.add(frame, text=result.label[:18])
        self.text_widgets[result.engine_id] = {"frame": frame, "text": text}
        self._render_canvas()

    def on_canvas_click(self, event: tk.Event) -> None:  # noqa: ANN001
        if self.image is None or not self.results:
            return
        x = event.x / self.scale
        y = event.y / self.scale
        best: tuple[str, OcrBox] | None = None
        best_area = None
        for engine_id, result in self.results.items():
            for box in result.boxes:
                if box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h:
                    area = box.w * box.h
                    if best is None or area < best_area:  # type: ignore[operator]
                        best = (engine_id, box)
                        best_area = area
        if best is None:
            return
        engine_id, box = best
        self._render_canvas(highlight_engine=engine_id, highlight_box=box)
        self.status_var.set(f"{self.results[engine_id].label}: {box.text}")


def main() -> int:
    root = tk.Tk()
    app = OcrBenchApp(root)

    def on_configure(_event: tk.Event) -> None:  # noqa: ANN001
        if app.image is None:
            return
        if app._render_job is not None:
            root.after_cancel(app._render_job)
        app._render_job = root.after(120, app._render_canvas)

    root.bind("<Configure>", on_configure)
    print("uvdrop-portal-ok ocr-bench", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
