"""Meet AV Check — camera and microphone preview before remote meetings."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from camera_preview import CameraPreview
from devices import list_cameras, list_microphones
from mic_meter import MicMeter, play_audio, record_seconds
from ui_shell import apply_tk_theme, format_steps, maximize_tk

STEPS = ("デバイスを確認", "カメラ映像を見る", "マイクをテスト")


class MeetAvCheckApp:
    PREVIEW_SIZE = (640, 360)
    METER_INTERVAL_MS = 80

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Meet AV Check — カメラ・マイク確認")
        self.root.minsize(640, 520)
        apply_tk_theme(root, bg="#F0F3F7", ink="#0F172A")
        maximize_tk(root)

        self.camera = CameraPreview()
        self.mic_meter = MicMeter()
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_job: str | None = None
        self._meter_job: str | None = None
        self._last_recording = None
        self._last_sr = 44100
        self._cameras = []
        self._mics = []
        self._preview_alive = False

        self._build_ui()
        self.root.after(100, self.refresh_devices)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Meet AV Check", style="Hero.TLabel").pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="会議前に、相手に見える映像・聞こえる音声を確認します。",
            style="Sub.TLabel",
            wraplength=960,
        ).pack(anchor=tk.W, pady=(4, 10))

        self.steps_var = tk.StringVar(value=format_steps(STEPS, 1))
        self.status_var = tk.StringVar(value="次: デバイスを検出しています…")
        ttk.Label(outer, textvariable=self.steps_var, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 8))
        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", wraplength=960).pack(fill=tk.X)

        device_row = ttk.Frame(outer)
        device_row.pack(fill=tk.X, pady=8)

        ttk.Label(device_row, text="カメラ:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(device_row, textvariable=self.camera_var, state="readonly", width=40)
        self.camera_combo.grid(row=0, column=1, sticky=tk.W)
        self.camera_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_camera_changed())

        ttk.Label(device_row, text="マイク:").grid(row=1, column=0, sticky=tk.W, padx=(0, 6), pady=(8, 0))
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(device_row, textvariable=self.mic_var, state="readonly", width=40)
        self.mic_combo.grid(row=1, column=1, sticky=tk.W, pady=(8, 0))
        self.mic_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_mic_changed())

        ttk.Button(device_row, text="デバイス再検出", command=self.refresh_devices).grid(
            row=0, column=2, rowspan=2, padx=(12, 0)
        )

        preview_frame = ttk.LabelFrame(outer, text="カメラプレビュー", padding=8)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.preview_label = ttk.Label(preview_frame, text="カメラ準備中…", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        mic_frame = ttk.LabelFrame(outer, text="マイクレベル", padding=8)
        mic_frame.pack(fill=tk.X, pady=4)
        self.meter = ttk.Progressbar(mic_frame, orient=tk.HORIZONTAL, mode="determinate", maximum=100)
        self.meter.pack(fill=tk.X)
        self.meter_label = ttk.Label(mic_frame, text="RMS: 0.000")
        self.meter_label.pack(anchor=tk.W, pady=(4, 0))

        test_row = ttk.Frame(outer)
        test_row.pack(fill=tk.X, pady=8)
        ttk.Button(test_row, text="2秒録音して再生", command=self.test_mic).pack(side=tk.LEFT)
        ttk.Button(test_row, text="録音を再生", command=self.play_last_recording).pack(side=tk.LEFT, padx=8)
    def refresh_devices(self) -> None:
        self.stop_camera_preview()
        self.mic_meter.stop()
        self.status_var.set("デバイスを探しています…")
        self.root.update_idletasks()

        cameras = list_cameras()
        mics = list_microphones()
        self._cameras = cameras
        self._mics = mics

        cam_labels = [c.label for c in cameras] or ["（カメラが見つかりません）"]
        mic_labels = [m.label for m in mics] or ["（マイクが見つかりません）"]
        self.camera_combo["values"] = cam_labels
        self.mic_combo["values"] = mic_labels

        if cameras:
            self.camera_combo.current(0)
            self.start_camera(cameras[0].index)
        else:
            self.preview_label.configure(image="", text="カメラが見つかりません\n他アプリが占有していないか確認")
            self._preview_photo = None

        if mics:
            self.mic_combo.current(0)
            self.start_mic(mics[0].index)
        else:
            self.status_var.set("マイクが見つかりません")

        self.update_status()

    def start_camera(self, index: int) -> None:
        self.stop_camera_preview()
        if not self.camera.open(index):
            self.preview_label.configure(
                image="",
                text="カメラを開けませんでした\nTeams/Zoom などが使っていないか確認して再検出",
            )
            self._preview_photo = None
            return
        self.preview_label.configure(text="")
        self._preview_alive = True
        self.schedule_preview()

    def stop_camera_preview(self) -> None:
        self._preview_alive = False
        if self._preview_job is not None:
            try:
                self.root.after_cancel(self._preview_job)
            except Exception:  # noqa: BLE001
                pass
            self._preview_job = None
        self.camera.close()

    def schedule_preview(self) -> None:
        if not self._preview_alive:
            return
        if self._preview_job is not None:
            try:
                self.root.after_cancel(self._preview_job)
            except Exception:  # noqa: BLE001
                pass
        self._preview_job = self.root.after(33, self.update_preview)

    def update_preview(self) -> None:
        if not self._preview_alive:
            return
        try:
            image = self.camera.read_pil()
            if image is not None:
                image = image.resize(self.PREVIEW_SIZE, Image.Resampling.LANCZOS)
                self._preview_photo = ImageTk.PhotoImage(image)
                self.preview_label.configure(image=self._preview_photo, text="")
        except Exception as exc:  # noqa: BLE001
            self.preview_label.configure(image="", text=f"プレビューエラー\n{exc}")
            self._preview_alive = False
            return
        self.schedule_preview()

    def start_mic(self, index: int) -> None:
        if self._meter_job is not None:
            try:
                self.root.after_cancel(self._meter_job)
            except Exception:  # noqa: BLE001
                pass
            self._meter_job = None
        self.mic_meter.set_device(index)
        if not self.mic_meter.start():
            self.meter_label.configure(text=f"マイク開始失敗: {self.mic_meter.last_error}")
            return
        self.schedule_meter()

    def schedule_meter(self) -> None:
        if self._meter_job is not None:
            try:
                self.root.after_cancel(self._meter_job)
            except Exception:  # noqa: BLE001
                pass
        self._meter_job = self.root.after(self.METER_INTERVAL_MS, self.update_meter)

    def update_meter(self) -> None:
        rms = self.mic_meter.current_rms()
        level = min(100, int(rms * 400))
        self.meter["value"] = level
        self.meter_label.configure(text=f"RMS: {rms:.4f}")
        self.schedule_meter()

    def on_camera_changed(self) -> None:
        idx = self.camera_combo.current()
        if 0 <= idx < len(self._cameras):
            self.start_camera(self._cameras[idx].index)
            self.update_status()

    def on_mic_changed(self) -> None:
        idx = self.mic_combo.current()
        if 0 <= idx < len(self._mics):
            self.start_mic(self._mics[idx].index)
            self.update_status()

    def update_status(self) -> None:
        cam = self.camera_var.get() or "なし"
        mic = self.mic_var.get() or "なし"
        extra = ""
        if self.mic_meter.last_error:
            extra = f" / mic: {self.mic_meter.last_error}"
        if self._cameras:
            self.steps_var.set(format_steps(STEPS, 2))
            self.status_var.set(
                f"カメラ: {cam} / マイク: {mic}{extra} — 次: 映像を確認し「2秒録音して再生」"
            )
        else:
            self.steps_var.set(format_steps(STEPS, 1))
            self.status_var.set(f"デバイス未検出{extra} — 「デバイス再検出」を試してください")

    def test_mic(self) -> None:
        idx = self.mic_combo.current()
        if not (0 <= idx < len(self._mics)):
            messagebox.showwarning("マイク", "マイクが選択されていません。")
            return
        device = self._mics[idx].index
        # Live InputStream conflicts with sd.rec on many Windows setups
        self.mic_meter.stop()
        if self._meter_job is not None:
            try:
                self.root.after_cancel(self._meter_job)
            except Exception:  # noqa: BLE001
                pass
            self._meter_job = None

        self.steps_var.set(format_steps(STEPS, 3))
        self.status_var.set("2秒間録音中…（話してください）")
        self.root.update_idletasks()
        try:
            self._last_recording = record_seconds(2.0, device)
            self._last_sr = 44100
            try:
                import sounddevice as sd

                info = sd.query_devices(device, "input")
                self._last_sr = int(info.get("default_samplerate") or 44100)
            except Exception:  # noqa: BLE001
                pass
            self.status_var.set("録音完了 — 再生します")
            play_audio(self._last_recording, samplerate=self._last_sr)
            self.steps_var.set(format_steps(STEPS, 3))
            self.status_var.set("再生しました。会議前チェック完了。レベルメーターを再開します。")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("録音エラー", str(exc))
        finally:
            self.start_mic(device)
            self.update_status()
            if self._last_recording is not None:
                self.steps_var.set(format_steps(STEPS, 3))
                self.status_var.set("マイクテスト完了 — 必要なら「録音を再生」でもう一度確認")
    def play_last_recording(self) -> None:
        if self._last_recording is None:
            messagebox.showinfo("再生", "先に「2秒録音して再生」を実行してください。")
            return
        try:
            play_audio(self._last_recording, samplerate=self._last_sr)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("再生エラー", str(exc))

    def on_close(self) -> None:
        self._preview_alive = False
        if self._preview_job is not None:
            try:
                self.root.after_cancel(self._preview_job)
            except Exception:  # noqa: BLE001
                pass
        if self._meter_job is not None:
            try:
                self.root.after_cancel(self._meter_job)
            except Exception:  # noqa: BLE001
                pass
        self.mic_meter.stop()
        self.camera.close()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    MeetAvCheckApp(root)
    print("uvdrop-portal-ok meet-av-check", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
