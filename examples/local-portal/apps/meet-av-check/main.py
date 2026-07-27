"""Meet AV Check — camera and microphone preview before remote meetings."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from camera_preview import CameraPreview
from devices import list_cameras, list_microphones
from mic_meter import MicMeter, play_audio, record_seconds


class MeetAvCheckApp:
    PREVIEW_SIZE = (640, 360)
    METER_INTERVAL_MS = 80

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Meet AV Check — カメラ・マイク確認")
        self.root.geometry("760x620")
        self.root.minsize(640, 520)

        self.camera = CameraPreview()
        self.mic_meter = MicMeter()
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_job: str | None = None
        self._meter_job: str | None = None
        self._last_recording = None

        self._build_ui()
        self.refresh_devices()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        tip = ttk.Label(
            outer,
            text="会議前に、相手に見える映像・聞こえる音声を確認してください。",
            wraplength=700,
        )
        tip.pack(anchor=tk.W, pady=(0, 8))

        device_row = ttk.Frame(outer)
        device_row.pack(fill=tk.X, pady=4)

        ttk.Label(device_row, text="カメラ:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(device_row, textvariable=self.camera_var, state="readonly", width=36)
        self.camera_combo.grid(row=0, column=1, sticky=tk.W)
        self.camera_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_camera_changed())

        ttk.Label(device_row, text="マイク:").grid(row=1, column=0, sticky=tk.W, padx=(0, 6), pady=(6, 0))
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(device_row, textvariable=self.mic_var, state="readonly", width=36)
        self.mic_combo.grid(row=1, column=1, sticky=tk.W, pady=(6, 0))
        self.mic_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_mic_changed())

        ttk.Button(device_row, text="デバイス再検出", command=self.refresh_devices).grid(
            row=0, column=2, rowspan=2, padx=(12, 0)
        )

        preview_frame = ttk.LabelFrame(outer, text="カメラプレビュー（相手に見える映像）", padding=8)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.preview_label = ttk.Label(preview_frame, text="カメラ未接続", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        mic_frame = ttk.LabelFrame(outer, text="マイクレベル（相手に聞こえる音量）", padding=8)
        mic_frame.pack(fill=tk.X, pady=4)
        self.meter = ttk.Progressbar(mic_frame, orient=tk.HORIZONTAL, mode="determinate", maximum=100)
        self.meter.pack(fill=tk.X)
        self.meter_label = ttk.Label(mic_frame, text="RMS: 0.000")
        self.meter_label.pack(anchor=tk.W, pady=(4, 0))

        test_row = ttk.Frame(outer)
        test_row.pack(fill=tk.X, pady=6)
        ttk.Button(test_row, text="2秒録音して再生", command=self.test_mic).pack(side=tk.LEFT)
        ttk.Button(test_row, text="録音を再生", command=self.play_last_recording).pack(side=tk.LEFT, padx=8)

        self.status_var = tk.StringVar(value="準備中…")
        ttk.Label(outer, textvariable=self.status_var, wraplength=700).pack(anchor=tk.W, pady=(8, 0))

    def refresh_devices(self) -> None:
        cameras = list_cameras()
        mics = list_microphones()

        cam_labels = [c.label for c in cameras] or ["（カメラが見つかりません）"]
        mic_labels = [m.label for m in mics] or ["（マイクが見つかりません）"]

        self._cameras = cameras
        self._mics = mics

        self.camera_combo["values"] = cam_labels
        self.mic_combo["values"] = mic_labels

        if cameras:
            self.camera_combo.current(0)
            self.start_camera(cameras[0].index)
        else:
            self.stop_camera_preview()

        if mics:
            self.mic_combo.current(0)
            self.start_mic(mics[0].index)
        else:
            self.mic_meter.stop()

        self.update_status()

    def start_camera(self, index: int) -> None:
        if not self.camera.open(index):
            self.preview_label.configure(image="", text="カメラを開けませんでした")
            self._preview_photo = None
            return
        self.preview_label.configure(text="")
        self.schedule_preview()

    def stop_camera_preview(self) -> None:
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
            self._preview_job = None
        self.camera.close()
        self.preview_label.configure(image="", text="カメラ停止")
        self._preview_photo = None

    def schedule_preview(self) -> None:
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(33, self.update_preview)

    def update_preview(self) -> None:
        image = self.camera.read_pil()
        if image is not None:
            image = image.resize(self.PREVIEW_SIZE, Image.Resampling.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self._preview_photo)
        self.schedule_preview()

    def start_mic(self, index: int) -> None:
        self.mic_meter.set_device(index)
        self.mic_meter.start()
        self.schedule_meter()

    def schedule_meter(self) -> None:
        if self._meter_job is not None:
            self.root.after_cancel(self._meter_job)
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
        self.status_var.set(f"使用中 — カメラ: {cam} / マイク: {mic}")

    def test_mic(self) -> None:
        idx = self.mic_combo.current()
        if not (0 <= idx < len(self._mics)):
            messagebox.showwarning("マイク", "マイクが選択されていません。")
            return
        device = self._mics[idx].index
        self.status_var.set("2秒間録音中…")
        self.root.update_idletasks()
        try:
            self._last_recording = record_seconds(2.0, device)
            self.status_var.set("録音完了。再生ボタンで確認できます。")
            play_audio(self._last_recording)
            self.status_var.set("録音を再生しました。")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("録音エラー", str(exc))
            self.update_status()

    def play_last_recording(self) -> None:
        if self._last_recording is None:
            messagebox.showinfo("再生", "先に「2秒録音して再生」を実行してください。")
            return
        try:
            play_audio(self._last_recording)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("再生エラー", str(exc))

    def on_close(self) -> None:
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
        if self._meter_job is not None:
            self.root.after_cancel(self._meter_job)
        self.mic_meter.stop()
        self.camera.close()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    MeetAvCheckApp(root)
    print("uvdrop-portal-ok meet-av-check", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
