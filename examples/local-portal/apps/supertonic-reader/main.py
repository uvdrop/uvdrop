"""Supertonic Reader — Tkinter text-to-speech."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import sounddevice as sd
import soundfile as sf

from tts_engine import LANGS, VOICES, TtsEngine
from ui_shell import apply_tk_theme, format_steps, maximize_tk

STEPS = ("原稿を入れる", "再生する", "必要ならWAV書き出し")


class SupertonicReaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Supertonic Reader — 読み上げ")
        apply_tk_theme(root)
        maximize_tk(root)

        self.engine = TtsEngine()
        self._playing = False
        self._last_audio: np.ndarray | None = None
        self._last_sr = 44100
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.set_status("次: 原稿を確認（または開く）→ 「再生」。初回はモデルDL（約400MB）。")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Supertonic Reader", style="Hero.TLabel").pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="原稿を入れて再生。初回はモデル取得があります。",
            style="Sub.TLabel",
            wraplength=960,
        ).pack(anchor=tk.W, pady=(4, 10))

        self.steps_var = tk.StringVar(value=format_steps(STEPS, 1))
        self.status_var = tk.StringVar(value="")
        ttk.Label(outer, textvariable=self.steps_var, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 8))
        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", wraplength=960).pack(fill=tk.X)

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill=tk.X, pady=(12, 8))
        ttk.Button(toolbar, text="テキストを開く", command=self.load_file).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="保存", command=self.save_text).pack(side=tk.LEFT, padx=6)

        self.text = tk.Text(outer, wrap=tk.WORD, height=16, font=("Yu Gothic UI", 11))
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.insert(
            "1.0",
            "こんにちは。Supertonic Reader のサンプルです。\n"
            "原稿を入力するか、.txt / .md を読み込んでください。",
        )

        opts = ttk.LabelFrame(outer, text="読み上げ設定", padding=8)
        opts.pack(fill=tk.X, pady=8)

        ttk.Label(opts, text="声:").grid(row=0, column=0, sticky=tk.W)
        self.voice_var = tk.StringVar(value="F3")
        ttk.Combobox(opts, textvariable=self.voice_var, values=VOICES, state="readonly", width=6).grid(
            row=0, column=1, sticky=tk.W, padx=(4, 16)
        )

        ttk.Label(opts, text="言語:").grid(row=0, column=2, sticky=tk.W)
        self.lang_var = tk.StringVar(value="ja")
        ttk.Combobox(opts, textvariable=self.lang_var, values=LANGS, state="readonly", width=8).grid(
            row=0, column=3, sticky=tk.W, padx=4
        )

        ttk.Label(opts, text="速度:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.speed_var = tk.DoubleVar(value=1.05)
        ttk.Scale(opts, from_=0.7, to=2.0, variable=self.speed_var, orient=tk.HORIZONTAL, length=180).grid(
            row=1, column=1, columnspan=2, sticky=tk.W, pady=(8, 0)
        )

        ttk.Label(opts, text="間 (秒):").grid(row=1, column=2, sticky=tk.W, pady=(8, 0))
        self.gap_var = tk.DoubleVar(value=0.3)
        ttk.Scale(opts, from_=0.0, to=1.5, variable=self.gap_var, orient=tk.HORIZONTAL, length=140).grid(
            row=1, column=3, sticky=tk.W, pady=(8, 0)
        )

        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="再生", command=self.play).pack(side=tk.LEFT)
        ttk.Button(actions, text="停止", command=self.stop).pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="WAV 書き出し", command=self.export_wav).pack(side=tk.LEFT)

    def set_status(self, message: str) -> None:
        self.root.after(0, lambda: self.status_var.set(message))

    def set_step(self, step: int) -> None:
        self.root.after(0, lambda: self.steps_var.set(format_steps(STEPS, step)))

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="原稿を開く",
            filetypes=[("Text", "*.txt *.md"), ("All", "*.*")],
        )
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8")
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)
        self.set_step(1)
        self.set_status(f"読み込み: {path} — 次: 「再生」")

    def save_text(self) -> None:
        path = filedialog.asksaveasfilename(
            title="原稿を保存",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md")],
        )
        if not path:
            return
        Path(path).write_text(self.text.get("1.0", tk.END).strip() + "\n", encoding="utf-8")
        self.set_status(f"保存: {path}")

    def _script(self) -> str:
        return self.text.get("1.0", tk.END).strip()

    def play(self) -> None:
        script = self._script()
        if not script:
            messagebox.showinfo("再生", "原稿が空です。")
            return
        if self._worker and self._worker.is_alive():
            return

        self.set_step(2)
        self.set_status("準備中…")

        def task() -> None:
            try:
                result = self.engine.synthesize(
                    text=script,
                    voice=self.voice_var.get(),
                    speed=float(self.speed_var.get()),
                    silence_duration=float(self.gap_var.get()),
                    lang=self.lang_var.get(),
                    on_status=self.set_status,
                )
                self._last_audio = result.audio
                self._last_sr = result.samplerate
                self.set_status("再生中…")
                sd.play(result.audio, result.samplerate)
                sd.wait()
                self.set_step(3)
                self.set_status("再生が完了しました — 必要なら「WAV 書き出し」")
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: messagebox.showerror("TTS エラー", str(exc)))
                self.set_status(f"エラー: {exc}")

        self._worker = threading.Thread(target=task, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        sd.stop()
        self.set_status("停止しました。")

    def export_wav(self) -> None:
        script = self._script()
        if not script:
            messagebox.showinfo("書き出し", "原稿が空です。")
            return
        dest = filedialog.asksaveasfilename(
            title="WAV 書き出し",
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav")],
        )
        if not dest:
            return

        self.set_step(3)

        def task() -> None:
            try:
                if self._last_audio is None or self._script() != script:
                    result = self.engine.synthesize(
                        text=script,
                        voice=self.voice_var.get(),
                        speed=float(self.speed_var.get()),
                        silence_duration=float(self.gap_var.get()),
                        lang=self.lang_var.get(),
                        on_status=self.set_status,
                    )
                    audio = result.audio
                    sr = result.samplerate
                else:
                    audio = self._last_audio
                    sr = self._last_sr
                sf.write(dest, audio, sr)
                self.set_status(f"WAV 保存: {dest}")
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: messagebox.showerror("書き出しエラー", str(exc)))

        threading.Thread(target=task, daemon=True).start()


def main() -> int:
    root = tk.Tk()
    SupertonicReaderApp(root)
    print("uvdrop-portal-ok supertonic-reader", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
