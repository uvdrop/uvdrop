"""Tk desktop UI for uvdrop."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from uvdrop import __version__
from uvdrop.app_env import open_dotenv_in_notepad
from uvdrop.cleanup import cleanup_app, gc_stale_temp_apps
from uvdrop.launcher import launch_source, relaunch_kept
from uvdrop.paths import app_root, ensure_layout, policies_dir
from uvdrop.registry import load_registry
from uvdrop.settings import ensure_default_settings, load_settings, save_settings
from uvdrop.shortcut import create_desktop_shortcut
from uvdrop.uv_tool import UvNotFoundError, resolve_uv
from uvdrop.xlsx_policy import sync_xlsx_allowlist


class UvdropApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"uvdrop {__version__}")
        self.geometry("760x520")
        self.minsize(680, 440)
        ensure_layout()
        ensure_default_settings()
        removed = gc_stale_temp_apps()

        self._busy = False
        self._build()
        self._refresh_list()
        self._update_uv_status()
        if removed:
            self._log(f"cleaned leftover temp apps: {', '.join(removed)}")

    def _build(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X)
        ttk.Label(header, text="uvdrop", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        ver = ttk.Label(header, text=f"v{__version__}", foreground="#0b6e4f")
        ver.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(header, text="フォルダ / ZIP を渡して uv で起動", foreground="#555").pack(
            side=tk.LEFT, padx=(10, 0)
        )
        ttk.Button(header, text="設定…", command=self._open_settings).pack(side=tk.RIGHT)
        ttk.Button(header, text="ライセンス", command=self._open_licenses).pack(side=tk.RIGHT, padx=(0, 8))

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, pady=(12, 8))
        ttk.Button(actions, text="フォルダを選択して起動…", command=self._pick_folder).pack(
            side=tk.LEFT
        )
        ttk.Button(actions, text="ZIP を選択して起動…", command=self._pick_zip).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        opts = ttk.Frame(root)
        opts.pack(fill=tk.X)
        self.keep_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts,
            text="起動後も保持する（オフ=一時実行→終了後に削除）",
            variable=self.keep_var,
        ).pack(side=tk.LEFT)
        ttk.Button(opts, text=".env を編集", command=self._edit_env).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Button(opts, text="ショートカット作成", command=self._make_shortcut).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(opts, text="削除", command=self._delete_selected).pack(side=tk.LEFT, padx=(8, 0))

        mid = ttk.Panedwindow(root, orient=tk.VERTICAL)
        mid.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        list_frame = ttk.LabelFrame(mid, text="保持しているアプリ", padding=6)
        mid.add(list_frame, weight=3)
        cols = ("name", "mode", "workspace")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        self.tree.heading("name", text="名前")
        self.tree.heading("mode", text="モード")
        self.tree.heading("workspace", text="ワークスペース")
        self.tree.column("name", width=140, stretch=False)
        self.tree.column("mode", width=70, stretch=False)
        self.tree.column("workspace", width=400)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", lambda _e: self._relaunch_selected())

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_row, text="再起動", command=self._relaunch_selected).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="更新", command=self._refresh_list).pack(side=tk.LEFT, padx=(8, 0))

        log_frame = ttk.LabelFrame(mid, text="ログ", padding=6)
        mid.add(log_frame, weight=2)
        self.log = tk.Text(log_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

        status = ttk.Frame(root)
        status.pack(fill=tk.X, pady=(8, 0))
        self.status_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Label(status, text=f"v{__version__} · data: {app_root()}", foreground="#777").pack(
            side=tk.RIGHT
        )

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _update_uv_status(self) -> None:
        try:
            uv = resolve_uv()
            self.status_var.set(f"uv: {uv}")
        except UvNotFoundError as e:
            self.status_var.set(str(e))

    def _selected_key(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    def _refresh_list(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for rec in load_registry().values():
            self.tree.insert(
                "",
                tk.END,
                iid=rec.key,
                values=(rec.name, rec.mode, rec.workspace),
            )

    def _pick_folder(self) -> None:
        path = filedialog.askdirectory(title="アプリフォルダを選択")
        if path:
            self._launch_async(Path(path))

    def _pick_zip(self) -> None:
        path = filedialog.askopenfilename(
            title="アプリ ZIP を選択",
            filetypes=[("ZIP", "*.zip"), ("All", "*.*")],
        )
        if path:
            self._launch_async(Path(path))

    def _launch_async(self, source: Path) -> None:
        if self._busy:
            return
        self._busy = True
        keep = bool(self.keep_var.get())
        self._log(f"launch: {source} (keep={keep})")

        def work() -> None:
            err: Exception | None = None
            result = None
            try:
                result = launch_source(source, keep=keep)
            except Exception as e:  # noqa: BLE001
                err = e

            def done() -> None:
                self._busy = False
                if err:
                    self._log(f"error: {err}")
                    messagebox.showerror("uvdrop", str(err))
                    return
                assert result is not None
                self._log(f"ok: key={result.app_key} pid={result.pid} mode={result.mode}")
                self._log(f"workspace: {result.workspace}")
                for w in result.policy.warnings:
                    self._log(f"warn: {w}")
                if result.policy.warnings:
                    messagebox.showwarning(
                        "uvdrop",
                        "ポリシー警告:\n" + "\n".join(result.policy.warnings),
                    )
                self._refresh_list()

            self.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _relaunch_selected(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", "アプリを選択してください")
            return
        if self._busy:
            return
        self._busy = True
        self._log(f"relaunch: {key}")

        def work() -> None:
            err: Exception | None = None
            result = None
            try:
                result = relaunch_kept(key)
            except Exception as e:  # noqa: BLE001
                err = e

            def done() -> None:
                self._busy = False
                if err:
                    self._log(f"error: {err}")
                    messagebox.showerror("uvdrop", str(err))
                    return
                assert result is not None
                self._log(f"ok: key={result.app_key} pid={result.pid}")
                for w in result.policy.warnings:
                    self._log(f"warn: {w}")
                self._refresh_list()

            self.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _edit_env(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", "アプリを選択してください")
            return
        open_dotenv_in_notepad(key)
        self._log(f"opened .env for {key}")

    def _make_shortcut(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", "アプリを選択してください")
            return
        try:
            lnk = create_desktop_shortcut(key)
            self._log(f"shortcut: {lnk}")
            messagebox.showinfo("uvdrop", f"デスクトップに作成しました:\n{lnk}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("uvdrop", str(e))

    def _delete_selected(self) -> None:
        key = self._selected_key()
        if not key:
            return
        if not messagebox.askyesno(
            "uvdrop",
            f"アプリのデータごと削除しますか？\n{key}\n（ワークスペース / venv / .env）",
        ):
            return
        cleanup_app(key, remove_registry=True)
        self._refresh_list()
        self._log(f"deleted app data: {key}")

    def _open_licenses(self) -> None:
        from uvdrop.paths import project_root
        import os
        import subprocess

        candidates = [
            project_root() / "THIRD_PARTY_NOTICES.md",
            project_root() / "LICENSE",
            project_root() / "third_party",
        ]
        for p in candidates:
            if p.exists():
                try:
                    os.startfile(str(p))  # type: ignore[attr-defined]
                except Exception:
                    subprocess.Popen(["notepad.exe", str(p)])
                self._log(f"opened: {p}")
                return
        messagebox.showinfo(
            "uvdrop",
            "THIRD_PARTY_NOTICES.md が見つかりません。\nリポジトリまたはインストール先を確認してください。",
        )

    def _open_settings(self) -> None:
        s = load_settings()
        win = tk.Toplevel(self)
        win.title(f"uvdrop 設定 — v{__version__}")
        win.geometry("520x280")
        win.transient(self)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        osv_en = tk.BooleanVar(value=s.osv.enabled)
        ttk.Checkbutton(
            frm,
            text="OSV.dev で既知の悪意パッケージをチェック（要ネット）",
            variable=osv_en,
        ).pack(anchor=tk.W)
        osv_mode = tk.StringVar(value=s.osv.mode)
        mode_row = ttk.Frame(frm)
        mode_row.pack(fill=tk.X, pady=(4, 10))
        ttk.Label(mode_row, text="OSV モード:").pack(side=tk.LEFT)
        ttk.Combobox(
            mode_row, textvariable=osv_mode, values=("warn", "block"), width=10, state="readonly"
        ).pack(side=tk.LEFT, padx=(8, 0))

        xlsx_en = tk.BooleanVar(value=s.xlsx.enabled)
        ttk.Checkbutton(frm, text="xlsx URL から許可リストを取得", variable=xlsx_en).pack(
            anchor=tk.W
        )
        ttk.Label(frm, text="xlsx URL（1列目 = パッケージ名）").pack(anchor=tk.W, pady=(8, 0))
        url_var = tk.StringVar(value=s.xlsx.url)
        ttk.Entry(frm, textvariable=url_var).pack(fill=tk.X, pady=(4, 0))

        def save() -> None:
            s.osv.enabled = bool(osv_en.get())
            s.osv.mode = osv_mode.get() or "warn"
            s.xlsx.enabled = bool(xlsx_en.get())
            s.xlsx.url = url_var.get().strip()
            save_settings(s)
            self._log("settings saved")
            if s.xlsx.enabled and s.xlsx.url:
                try:
                    path = sync_xlsx_allowlist(force=True)
                    self._log(f"xlsx synced: {path}")
                except Exception as e:  # noqa: BLE001
                    messagebox.showerror("uvdrop", str(e))
                    return
            win.destroy()

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(btns, text="保存", command=save).pack(side=tk.RIGHT)
        ttk.Button(btns, text="キャンセル", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Label(frm, text=f"policies: {policies_dir()}", foreground="#777").pack(
            anchor=tk.W, pady=(12, 0)
        )


def run_app() -> None:
    app = UvdropApp()
    app.mainloop()
