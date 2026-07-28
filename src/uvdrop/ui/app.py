"""Tk desktop UI for uvdrop."""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from uvdrop import __version__
from uvdrop.app_env import open_dotenv_in_notepad
from uvdrop.catalog import CatalogApp, check_app_path, load_all_catalogs
from uvdrop.cleanup import cleanup_app, gc_inactive_venvs, gc_stale_temp_apps, hibernate_venv
from uvdrop.clipboard_image import clipboard_png
from uvdrop.i18n import LANG_EN, LANG_JA, LANG_ZH, apply_from_settings, language_label, t
from uvdrop.launcher import PreparedLaunch, execute_launch, prepare_launch, prepare_relaunch
from uvdrop.appicon import ensure_ico, find_icon_candidates
from uvdrop.package_spec import version_rule_guide
from uvdrop.paths import apps_dir, ensure_layout, envs_dir, launchers_dir, policies_dir, project_root
from uvdrop.policy import needs_launch_confirm
from uvdrop.registry import load_registry, set_icon
from uvdrop.usage import DAY, MONTH, WEEK, buckets
from uvdrop.sample_app import list_samples, write_sample_tree, write_sample_zip
from uvdrop.sample_icons import PALETTE, THEMES, render_theme_png
from uvdrop.settings import CatalogRef, ensure_default_settings, load_settings, save_settings
from uvdrop.shortcut import create_desktop_shortcut, shortcut_path
from uvdrop.ui.launch_activity import JobStore, LaunchJob
from uvdrop.ui.package_table import PackageSheet
from uvdrop.ui.tooltips import ToolTip
from uvdrop.uv_tool import UvNotFoundError, resolve_uv_info
from uvdrop.xlsx_policy import sync_file_allowlist

# --- short copy: all user-facing text now lives in uvdrop.i18n (see t()) ---

_COLOR_KEYS = {
    "#2f7d62": "color.forest",
    "#3b6ea5": "color.blue",
    "#c47b2b": "color.amber",
    "#8b4d6b": "color.rose",
    "#4a5568": "color.slate",
    "#2c7a7b": "color.teal",
}


def _theme_label(theme: object) -> str:
    return t(f"theme.{theme.id}")  # type: ignore[attr-defined]


def _color_label(hex_color: str, fallback: str) -> str:
    key = _COLOR_KEYS.get(hex_color)
    return t(key) if key else fallback


def _preferred_font(root: tk.Misc, candidates: tuple[str, ...]) -> str:
    from tkinter import font as tkfont

    available = {name.lower() for name in tkfont.families(root)}
    for name in candidates:
        if name.lower() in available:
            return name
    return "TkDefaultFont"


def _fit_dialog(win: tk.Toplevel, width: int, height: int) -> None:
    """Place a dialog at a size that fits the usable screen."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w = min(width, max(480, sw - 80))
    h = min(height, max(360, sh - 100))
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.minsize(min(480, w), min(360, h))


def _scrollable_panel(
    parent: tk.Misc,
    *,
    bg: str,
    style: str = "App.TFrame",
    padding: int = 0,
) -> tuple[tk.Canvas, ttk.Frame]:
    """Vertical scroll area. Returns (canvas, inner frame to pack widgets into)."""
    shell = ttk.Frame(parent, style=style)
    shell.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(shell, bg=bg, highlightthickness=0, bd=0)
    bar = ttk.Scrollbar(shell, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)
    bar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = ttk.Frame(canvas, style=style, padding=padding)
    window_id = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

    def _sync_scroll(_event: object | None = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(window_id, width=max(1, canvas.winfo_width()))

    inner.bind("<Configure>", _sync_scroll)
    canvas.bind("<Configure>", _sync_scroll)

    def _on_wheel(event: tk.Event) -> str | None:
        if getattr(event, "delta", 0):
            canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _bind_wheel(_event: object | None = None) -> None:
        canvas.bind_all("<MouseWheel>", _on_wheel)

    def _unbind_wheel(_event: object | None = None) -> None:
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _bind_wheel)
    canvas.bind("<Leave>", _unbind_wheel)
    inner.bind("<Enter>", _bind_wheel)
    inner.bind("<Leave>", _unbind_wheel)

    top = parent.winfo_toplevel()

    def _on_destroy(event: tk.Event) -> None:
        if event.widget is top:
            _unbind_wheel()

    top.bind("<Destroy>", _on_destroy, add="+")
    return canvas, inner


class UvdropApp(tk.Tk):
    # palette — soft, low-contrast surfaces with a calm green accent
    BG = "#f4f7f5"
    CARD = "#ffffff"
    CARD_BORDER = "#d8e2dc"
    INK = "#25322c"
    MUTED = "#69796f"
    ACCENT = "#2f7d62"
    ACCENT_HOVER = "#276a53"
    ACCENT_ZIP = "#2f6f8a"
    ACCENT_ZIP_HOVER = "#255a70"
    ACCENT_CATALOG = "#6b5b8a"
    ACCENT_CATALOG_HOVER = "#564870"
    WARN = "#8a5a1a"

    def __init__(self) -> None:
        super().__init__()
        self.title(f"uvdrop {__version__}")
        self.geometry("1000x720")
        self.minsize(820, 600)
        self.configure(bg=self.BG)
        ensure_layout()
        settings = ensure_default_settings()
        apply_from_settings()
        removed = gc_stale_temp_apps()
        hibernated = (
            gc_inactive_venvs(settings.storage.inactive_days)
            if settings.storage.hibernate_enabled
            else []
        )

        self._busy = False
        self._jobs = JobStore()
        self._job_rows: dict[str, dict[str, object]] = {}
        self._activity_shell: tk.Frame | None = None
        self._activity_body: ttk.Frame | None = None
        self._activity_header: tk.StringVar | None = None
        self._card_widgets: list[tk.Misc] = []
        self._lib_action_btns: list[ttk.Button] = []
        self._status_frame: ttk.Frame | None = None
        self._apply_style()
        self._build()
        self._refresh_list()
        self._update_uv_status()
        self._maximize()
        if removed:
            self._log(f"cleaned leftover temp apps: {', '.join(removed)}", reveal=False)
        if hibernated:
            self._log(
                t("hibernate.gc_log", n=len(hibernated), keys=", ".join(hibernated)),
                reveal=False,
            )

    def _maximize(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)

    def _apply_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.ui_font = _preferred_font(self, ("Yu Gothic UI", "Meiryo UI", "Segoe UI"))
        self.mono_font = _preferred_font(self, ("Cascadia Mono", "Consolas", "Courier New"))
        body = (self.ui_font, 11)

        self.option_add("*Font", body)
        style.configure(".", font=body, background=self.BG, foreground=self.INK)
        style.configure("App.TFrame", background=self.BG)
        style.configure("Title.TLabel", font=(self.ui_font, 22, "bold"), background=self.BG, foreground=self.INK)
        style.configure("Sub.TLabel", font=(self.ui_font, 11), background=self.BG, foreground=self.MUTED)
        style.configure("Section.TLabel", font=(self.ui_font, 13, "bold"), background=self.BG, foreground=self.INK)
        style.configure("Hint.TLabel", font=(self.ui_font, 10), background=self.BG, foreground=self.MUTED)
        style.configure("Status.TLabel", font=(self.ui_font, 10), background=self.BG, foreground=self.MUTED)
        style.configure("TCheckbutton", background=self.BG, foreground=self.INK)
        style.configure("TRadiobutton", background=self.BG, foreground=self.INK)
        style.configure("TButton", padding=(14, 7), background="#e6ede9", foreground=self.INK)
        style.map("TButton", background=[("active", "#d9e5df"), ("disabled", "#eef2f0")])
        style.configure("Ghost.TButton", padding=(12, 6))
        style.configure(
            "Primary.TButton",
            padding=(16, 8),
            background=self.ACCENT,
            foreground="#ffffff",
            font=(self.ui_font, 11, "bold"),
        )
        style.map("Primary.TButton", background=[("active", self.ACCENT_HOVER)])
        style.configure("Treeview", rowheight=28, fieldbackground=self.CARD, background=self.CARD)
        style.configure("Treeview.Heading", font=(self.ui_font, 10, "bold"))
        style.configure("TNotebook", background=self.BG)
        style.configure("TNotebook.Tab", padding=(16, 8), font=(self.ui_font, 11))

    def _build(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=(18, 14))
        root.pack(fill=tk.BOTH, expand=True)
        self._root_frame = root

        # --- header ---
        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill=tk.X)
        left = ttk.Frame(header, style="App.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        title_row = ttk.Frame(left, style="App.TFrame")
        title_row.pack(anchor=tk.W)
        ttk.Label(title_row, text="uvdrop", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(title_row, text=f"  v{__version__}", style="Sub.TLabel").pack(
            side=tk.LEFT, pady=(8, 0)
        )
        ttk.Label(
            left,
            text=t("app.subtitle"),
            style="Sub.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        nav = ttk.Frame(header, style="App.TFrame")
        nav.pack(side=tk.RIGHT)
        ttk.Button(nav, text=t("app.help"), command=self._open_help, style="Ghost.TButton").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(nav, text=t("app.settings"), command=self._open_settings, style="Ghost.TButton").pack(
            side=tk.LEFT
        )

        # --- step 1: launch ---
        step1 = ttk.Frame(root, style="App.TFrame")
        step1.pack(fill=tk.X, pady=(18, 8))
        ttk.Label(step1, text=t("app.step1"), style="Section.TLabel").pack(side=tk.LEFT)
        sample_link = tk.Label(
            step1,
            text=t("app.sample_link"),
            bg=self.BG,
            fg=self.ACCENT,
            font=(self.ui_font, 10, "underline"),
            cursor="hand2",
        )
        sample_link.pack(side=tk.LEFT, padx=(12, 0), pady=(2, 0))
        sample_link.bind("<Button-1>", lambda _e: self._save_sample())
        ToolTip(sample_link, t("app.sample_link"))

        cards = ttk.Frame(root, style="App.TFrame")
        cards.pack(fill=tk.X)
        cards.columnconfigure(0, weight=1, uniform="cards")
        cards.columnconfigure(1, weight=1, uniform="cards")
        cards.columnconfigure(2, weight=1, uniform="cards")

        self._make_card(
            cards,
            col=0,
            title=t("app.open_folder"),
            subtitle=t("app.open_folder_sub"),
            command=self._pick_folder,
            accent=self.ACCENT,
            accent_hover=self.ACCENT_HOVER,
        )
        self._make_card(
            cards,
            col=1,
            title=t("app.open_zip"),
            subtitle=t("app.open_zip_sub"),
            command=self._pick_zip,
            accent=self.ACCENT_ZIP,
            accent_hover=self.ACCENT_ZIP_HOVER,
        )
        self._make_card(
            cards,
            col=2,
            title=t("app.open_catalog"),
            subtitle=t("app.open_catalog_sub"),
            command=self._open_catalog,
            accent=self.ACCENT_CATALOG,
            accent_hover=self.ACCENT_CATALOG_HOVER,
        )

        mode_row = ttk.Frame(root, style="App.TFrame")
        mode_row.pack(fill=tk.X, pady=(12, 0))
        self._activity_anchor = mode_row
        ttk.Label(
            mode_row,
            text=t("app.hint_confirm"),
            style="Hint.TLabel",
        ).pack(side=tk.LEFT)

        # --- in-progress launches (catalog / folder / zip) ---
        self._activity_shell = tk.Frame(root, bg="#c45c26", padx=2, pady=2)
        # packed only while jobs exist
        inner = tk.Frame(self._activity_shell, bg="#fff4e8", padx=12, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)
        self._activity_header = tk.StringVar(value="")
        tk.Label(
            inner,
            textvariable=self._activity_header,
            bg="#fff4e8",
            fg="#7a2e0b",
            font=(self.ui_font, 12, "bold"),
            anchor=tk.W,
        ).pack(fill=tk.X)
        ttk.Label(
            inner,
            text=t("job.banner_hint"),
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(2, 6))
        self._activity_body = ttk.Frame(inner, style="App.TFrame")
        self._activity_body.pack(fill=tk.X)

        # --- step 2: library ---
        lib_hdr = ttk.Frame(root, style="App.TFrame")
        lib_hdr.pack(fill=tk.X, pady=(20, 8))
        ttk.Label(lib_hdr, text=t("app.step2"), style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Label(lib_hdr, text=t("app.filter"), style="Hint.TLabel").pack(side=tk.LEFT, padx=(16, 6))
        self.filter_var = tk.StringVar(value="")
        filter_entry = ttk.Entry(lib_hdr, textvariable=self.filter_var, width=24)
        filter_entry.pack(side=tk.LEFT)
        ToolTip(filter_entry, t("app.filter_hint"))
        self.filter_var.trace_add("write", lambda *_a: self._refresh_list())
        ttk.Button(
            lib_hdr, text=t("app.filter_clear"), command=lambda: self.filter_var.set(""), style="Ghost.TButton"
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            lib_hdr, text=t("app.usage"), command=self._open_usage, style="Ghost.TButton"
        ).pack(side=tk.RIGHT)

        lib_shell = tk.Frame(root, bg=self.CARD_BORDER, padx=1, pady=1)
        lib_shell.pack(fill=tk.BOTH, expand=True)
        lib = tk.Frame(lib_shell, bg=self.CARD)
        lib.pack(fill=tk.BOTH, expand=True)

        list_wrap = tk.Frame(lib, bg=self.CARD)
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        cols = ("name", "mode", "last_run", "runs", "workspace")
        self._sort_key = "last_run"
        self._sort_desc = True
        self.tree = ttk.Treeview(list_wrap, columns=cols, show="headings", height=7)
        headings = {
            "name": t("app.col_name"),
            "mode": t("app.col_mode"),
            "last_run": t("app.col_last"),
            "runs": t("app.col_runs"),
            "workspace": t("app.col_place"),
        }
        for col, text in headings.items():
            self.tree.heading(col, text=text, command=lambda c=col: self._sort_by(c))
        self.tree.column("name", width=160, stretch=False)
        self.tree.column("mode", width=72, stretch=False)
        self.tree.column("last_run", width=130, stretch=False, anchor=tk.W)
        self.tree.column("runs", width=80, stretch=False, anchor=tk.E)
        self.tree.column("workspace", width=420)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", lambda _e: self._relaunch_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._sync_lib_actions())

        self.empty_lbl = tk.Label(
            lib,
            text=t("app.empty"),
            bg=self.CARD,
            fg=self.MUTED,
            font=(self.ui_font, 11),
            justify=tk.LEFT,
        )

        btn_row = tk.Frame(lib, bg=self.CARD)
        btn_row.pack(fill=tk.X, padx=10, pady=10)
        for text, cmd in (
            (t("app.relaunch"), self._relaunch_selected),
            (t("app.edit_env"), self._edit_env),
            (t("app.shortcut"), self._make_shortcut),
            (t("app.hibernate"), self._hibernate_selected),
            (t("app.delete"), self._delete_selected),
            (t("app.refresh"), self._refresh_list),
        ):
            b = ttk.Button(btn_row, text=text, command=cmd)
            b.pack(side=tk.LEFT, padx=(0, 8))
            if text != t("app.refresh"):
                self._lib_action_btns.append(b)

        # --- log (hidden until needed) ---
        log_hdr = ttk.Frame(root, style="App.TFrame")
        log_hdr.pack(fill=tk.X, pady=(14, 4))
        ttk.Label(log_hdr, text=t("app.log"), style="Section.TLabel").pack(side=tk.LEFT)
        self._log_visible = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            log_hdr,
            text=t("app.log_show"),
            variable=self._log_visible,
            command=self._relayout_log,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.log_frame = tk.Frame(root, bg=self.CARD_BORDER, padx=1, pady=1)
        inner_log = tk.Frame(self.log_frame, bg=self.CARD)
        inner_log.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(
            inner_log,
            height=6,
            wrap=tk.WORD,
            font=(self.mono_font, 10),
            relief=tk.FLAT,
            padx=8,
            pady=6,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

        self._status_frame = ttk.Frame(root, style="App.TFrame")
        self._status_frame.pack(fill=tk.X, pady=(8, 0))
        self.status_var = tk.StringVar(value="")
        ttk.Label(self._status_frame, textvariable=self.status_var, style="Status.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Button(
            self._status_frame, text=t("app.licenses"), command=self._open_licenses, style="Ghost.TButton"
        ).pack(side=tk.RIGHT)
        ttk.Label(
            self._status_frame,
            text=f"apps → {apps_dir()}",
            style="Status.TLabel",
        ).pack(side=tk.RIGHT, padx=(0, 10))

        self._sync_lib_actions()

    def _make_card(
        self,
        parent: ttk.Frame,
        *,
        col: int,
        title: str,
        subtitle: str,
        command,
        accent: str,
        accent_hover: str,
    ) -> None:
        outer = tk.Frame(parent, bg=self.CARD_BORDER, padx=1, pady=1)
        outer.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
        bg = accent
        fg = "#ffffff"
        sub_fg = "#e4f0ea"
        body = tk.Frame(outer, bg=bg, cursor="hand2", padx=16, pady=18)
        body.pack(fill=tk.BOTH, expand=True)

        title_lbl = tk.Label(
            body, text=title, bg=bg, fg=fg, font=(self.ui_font, 15, "bold"), anchor=tk.W
        )
        title_lbl.pack(fill=tk.X)
        sub_lbl = tk.Label(
            body, text=subtitle, bg=bg, fg=sub_fg, font=(self.ui_font, 10), anchor=tk.W
        )
        sub_lbl.pack(fill=tk.X, pady=(4, 0))

        def run(_e: object | None = None) -> None:
            command()

        for w in (body, title_lbl, sub_lbl, outer):
            w.bind("<Button-1>", run)
            self._card_widgets.append(w)

        def enter(_e: object | None = None) -> None:
            for x in (body, title_lbl, sub_lbl):
                x.configure(bg=accent_hover)

        def leave(_e: object | None = None) -> None:
            for x in (body, title_lbl, sub_lbl):
                x.configure(bg=accent)

        for w in (body, title_lbl, sub_lbl):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

    def _relayout_log(self) -> None:
        self.log_frame.pack_forget()
        if self._status_frame is not None:
            self._status_frame.pack_forget()
        if self._log_visible.get():
            self.log_frame.pack(fill=tk.BOTH, expand=False)
        if self._status_frame is not None:
            self._status_frame.pack(fill=tk.X, pady=(8, 0))

    def _sync_lib_actions(self) -> None:
        has = bool(self.tree.get_children())
        if has:
            self.empty_lbl.place_forget()
        else:
            self.empty_lbl.place(relx=0.5, rely=0.42, anchor=tk.CENTER)
        sel = bool(self.tree.selection())
        state = tk.NORMAL if sel else tk.DISABLED
        for b in self._lib_action_btns:
            b.configure(state=state)

    def _log(self, msg: str, *, reveal: bool = True) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        if reveal and not self._log_visible.get():
            self._log_visible.set(True)
            self._relayout_log()

    def _update_uv_status(self) -> None:
        try:
            info = resolve_uv_info()
            src = t("status.bundled") if info.source == "bundled" else "PATH"
            self.status_var.set(f"uv [{src}] {info.version}")
        except UvNotFoundError as e:
            self.status_var.set(str(e).split("\n")[0])

    def _selected_key(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    @staticmethod
    def _format_last_run(ts: float | None) -> str:
        if not ts:
            return "—"
        when = datetime.fromtimestamp(ts)
        days = (datetime.now().date() - when.date()).days
        if days == 0:
            return f"{t('common.today')} {when:%H:%M}"
        if days == 1:
            return f"{t('common.yesterday')} {when:%H:%M}"
        return f"{when:%Y-%m-%d}"

    def _sort_by(self, column: str) -> None:
        if self._sort_key == column:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_key = column
            self._sort_desc = column in {"last_run", "runs"}
        self._refresh_list()

    def _refresh_list(self) -> None:
        selected = set(self.tree.selection())
        for i in self.tree.get_children():
            self.tree.delete(i)

        needle = self.filter_var.get().strip().lower()
        tokens = [tok for tok in needle.split() if tok]

        def matches(rec) -> bool:
            if not tokens:
                return True
            haystack = " ".join(
                (
                    rec.name,
                    rec.mode,
                    rec.workspace,
                    rec.source_path,
                    self._format_last_run(rec.last_run_at),
                    str(rec.run_count or 0),
                )
            ).lower()
            # Every token must appear somewhere (substring / 部分一致).
            return all(tok in haystack for tok in tokens)

        records = [rec for rec in load_registry().values() if matches(rec)]

        def sort_value(rec):
            if self._sort_key == "runs":
                return int(rec.run_count or 0)
            if self._sort_key == "last_run":
                return rec.last_run_at or 0.0
            if self._sort_key == "mode":
                return rec.mode
            if self._sort_key == "workspace":
                return rec.workspace.lower()
            return rec.name.lower()

        records.sort(key=sort_value, reverse=self._sort_desc)

        for rec in records:
            mode = (
                t("app.mode_hibernated")
                if rec.mode == "keep" and not (envs_dir() / rec.key).exists()
                else t("app.mode_ready") if rec.mode == "keep" else rec.mode
            )
            self.tree.insert(
                "",
                tk.END,
                iid=rec.key,
                values=(
                    rec.name,
                    mode,
                    self._format_last_run(rec.last_run_at),
                    rec.run_count or 0,
                    rec.workspace,
                ),
            )

        arrow = " ▼" if self._sort_desc else " ▲"
        for col, text in (
            ("name", t("app.col_name")),
            ("mode", t("app.col_mode")),
            ("last_run", t("app.col_last")),
            ("runs", t("app.col_runs")),
            ("workspace", t("app.col_place")),
        ):
            self.tree.heading(col, text=text + (arrow if col == self._sort_key else ""))

        restore = [k for k in selected if self.tree.exists(k)]
        if restore:
            self.tree.selection_set(restore)
        self._sync_lib_actions()

    def _pick_folder(self) -> None:
        path = filedialog.askdirectory(title=t("pick.folder_title"))
        if path:
            self._launch_async(Path(path))

    def _pick_zip(self) -> None:
        path = filedialog.askopenfilename(
            title=t("pick.zip_title"),
            filetypes=[("ZIP", "*.zip"), ("All", "*.*")],
        )
        if path:
            self._launch_async(Path(path))

    def _confirm_launch(self, prep: PreparedLaunch) -> tuple[str, bool] | None:
        """Confirm what runs and what gets installed.

        Returns ``(entry_command, show_console)`` or ``None`` if aborted.
        """
        policy = prep.policy
        if policy.blocking:
            messagebox.showerror(
                t("confirm.blocked"),
                t("confirm.blocked_body") + "\n\n" + "\n".join(policy.errors),
            )
            return None

        default_console = bool(load_settings().guard.show_console)

        # Respect settings: skip the dialog when the user opted out and
        # nothing needs attention — but still require a command to run.
        if (
            not needs_launch_confirm(policy)
            and prep.entry_command.strip()
        ):
            self._log("confirm skipped (settings)")
            return prep.entry_command.strip(), default_console

        win = tk.Toplevel(self)
        win.title(t("confirm.title"))
        win.transient(self)
        win.configure(bg=self.BG)
        win.grab_set()
        _fit_dialog(win, 620, 520)

        outer = ttk.Frame(win, padding=12, style="App.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        decision: dict[str, object] = {"command": None, "show_console": default_console}
        console_var = tk.BooleanVar(value=default_console)

        def accept() -> None:
            command = entry_var.get().strip()
            if not command:
                messagebox.showwarning("uvdrop", t("confirm.need_cmd"), parent=win)
                return
            decision["command"] = command
            decision["show_console"] = bool(console_var.get())
            win.destroy()

        # Sticky footer first so it never scrolls away
        btns = ttk.Frame(outer, style="App.TFrame")
        btns.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        console_cb = ttk.Checkbutton(
            btns, text=t("confirm.show_console"), variable=console_var
        )
        console_cb.pack(side=tk.LEFT)
        ToolTip(console_cb, t("help.console"))
        ttk.Button(btns, text=t("confirm.run"), command=accept, style="Primary.TButton").pack(
            side=tk.RIGHT
        )
        ttk.Button(btns, text=t("confirm.abort"), command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))

        _canvas, frm = _scrollable_panel(outer, bg=self.BG)

        ttk.Label(frm, text=prep.workspace.name, style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            frm,
            text=t("confirm.lead"),
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(2, 10))

        if prep.converted_from is not None:
            self._notice_box(
                frm,
                t("confirm.converted"),
                t("confirm.converted_body")
                + (
                    t("confirm.converted_skipped", n=len(prep.conversion_skipped))
                    if prep.conversion_skipped
                    else ""
                ),
            )

        if not prep.entry_options:
            self._notice_box(
                frm,
                t("confirm.no_entry"),
                t("confirm.no_entry_body"),
            )

        if not policy.allowlist_active:
            self._notice_box(
                frm,
                t("confirm.no_allow"),
                t("confirm.no_allow_body"),
            )

        if not policy.resolved_tree:
            self._notice_box(
                frm,
                t("confirm.resolve_fail"),
                t("confirm.resolve_fail_body"),
            )

        if policy.unresolved:
            shown = policy.unresolved[:6]
            extra = (
                t("confirm.unresolved_more", n=len(policy.unresolved) - 6)
                if len(policy.unresolved) > 6
                else ""
            )
            self._notice_box(
                frm,
                t("confirm.unresolved_title"),
                t("confirm.unresolved_body")
                + "\n\n"
                + "\n".join(f"・{u}" for u in shown)
                + extra,
                action=(t("confirm.version_guide"), self._open_version_help),
            )

        ttk.Label(frm, text=t("confirm.cmd_label"), style="Section.TLabel").pack(
            anchor=tk.W, pady=(4, 2)
        )
        ttk.Label(
            frm,
            text=t("confirm.cmd_hint", dir=prep.project_dir),
            style="Hint.TLabel",
            wraplength=560,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 6))

        entry_row = ttk.Frame(frm, style="App.TFrame")
        entry_row.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            entry_row,
            text="uv run python",
            bg=self.BG,
            fg=self.MUTED,
            font=(self.mono_font, 10),
        ).pack(side=tk.LEFT, padx=(0, 8))
        entry_var = tk.StringVar(value=prep.entry_command)
        entry_input = ttk.Combobox(
            entry_row,
            textvariable=entry_var,
            values=prep.entry_options,
            font=(self.mono_font, 10),
        )
        entry_input.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(
            frm,
            text=(
                t("confirm.pkg_count_resolved", n=len(policy.dependencies))
                if policy.resolved_tree
                else t("confirm.pkg_count_declared", n=len(policy.dependencies))
            ),
            style="Section.TLabel",
        ).pack(anchor=tk.W, pady=(4, 4))
        if policy.resolved_tree:
            ttk.Label(
                frm,
                text=t("confirm.resolved_hint"),
                style="Hint.TLabel",
            ).pack(anchor=tk.W, pady=(0, 4))

        list_shell = tk.Frame(frm, bg=self.CARD_BORDER, padx=1, pady=1)
        list_shell.pack(fill=tk.X)
        dep_box = tk.Listbox(
            list_shell,
            font=(self.mono_font, 10),
            relief=tk.FLAT,
            bg=self.CARD,
            fg=self.INK,
            highlightthickness=0,
            activestyle="none",
            height=min(12, max(4, len(policy.dependencies) or 1)),
        )
        dep_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dep_scroll = ttk.Scrollbar(list_shell, orient=tk.VERTICAL, command=dep_box.yview)
        dep_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        dep_box.configure(yscrollcommand=dep_scroll.set)

        unlisted = set(policy.unlisted)
        if not policy.dependencies:
            dep_box.insert(tk.END, t("confirm.no_extra_pkgs"))
        for label in policy.dependencies:
            pkg_name = label.split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].split("!", 1)[0].split(
                "[", 1
            )[0].strip()
            if policy.allowlist_active and pkg_name in unlisted:
                dep_box.insert(tk.END, f"{label}{t('confirm.unlisted_tag')}")
                dep_box.itemconfigure(tk.END, foreground=self.WARN)
            else:
                dep_box.insert(tk.END, label)

        if policy.notes:
            ttk.Label(
                frm,
                text="\n".join(policy.notes),
                style="Hint.TLabel",
                wraplength=560,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(10, 0))

        if policy.warnings:
            ttk.Label(
                frm,
                text=t("confirm.warn_prefix") + " / ".join(policy.warnings),
                style="Hint.TLabel",
                foreground=self.WARN,
                wraplength=560,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(6, 0))

        win.bind("<Escape>", lambda _e: win.destroy())
        entry_input.focus_set()
        self.wait_window(win)
        command = decision["command"]
        if not isinstance(command, str) or not command:
            return None
        return command, bool(decision.get("show_console"))

    def _notice_box(
        self,
        parent: ttk.Frame,
        title: str,
        body: str,
        *,
        action: tuple[str, object] | None = None,
    ) -> None:
        shell = tk.Frame(parent, bg="#f2e6cf", padx=12, pady=10)
        shell.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            shell,
            text=title,
            bg="#f2e6cf",
            fg=self.WARN,
            font=(self.ui_font, 11, "bold"),
            anchor=tk.W,
        ).pack(fill=tk.X)
        tk.Label(
            shell,
            text=body,
            bg="#f2e6cf",
            fg=self.INK,
            font=(self.ui_font, 10),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=560,
        ).pack(fill=tk.X, pady=(2, 0))
        if action is not None:
            label, command = action
            ttk.Button(shell, text=label, command=command).pack(  # type: ignore[arg-type]
                anchor=tk.W, pady=(8, 0)
            )

    def _set_busy(self, busy: bool) -> None:
        # Kept for soft UI hints; launches may run in parallel via job store.
        self._busy = busy or bool(self._jobs.active())
        self._sync_lib_actions()

    def _sync_busy_from_jobs(self) -> None:
        self._busy = bool(self._jobs.active())
        self._sync_lib_actions()

    def _refresh_activity_panel(self) -> None:
        if self._activity_shell is None or self._activity_body is None or self._activity_header is None:
            return
        visible = [j for j in self._jobs.jobs.values() if j.state in {"running", "waiting"}]
        lingering = [j for j in self._jobs.jobs.values() if j.state in {"done", "error"}]
        if not visible and not lingering:
            self._activity_shell.pack_forget()
            for child in self._activity_body.winfo_children():
                child.destroy()
            self._job_rows.clear()
            self._sync_busy_from_jobs()
            return

        try:
            self._activity_shell.pack_forget()
        except tk.TclError:
            pass
        anchor = getattr(self, "_activity_anchor", None)
        if anchor is not None:
            self._activity_shell.pack(fill=tk.X, pady=(14, 0), after=anchor)
        else:
            self._activity_shell.pack(fill=tk.X, pady=(14, 0))

        n = len(visible) if visible else len(lingering)
        self._activity_header.set(t("job.banner_title", n=n))

        existing = set(self._job_rows)
        current_ids = set(self._jobs.jobs)
        for jid in list(existing - current_ids):
            row = self._job_rows.pop(jid, None)
            if row and isinstance(row.get("frame"), tk.Misc):
                row["frame"].destroy()  # type: ignore[union-attr]

        for job in list(self._jobs.jobs.values()):
            self._upsert_job_row(job)
        self._sync_busy_from_jobs()

    def _upsert_job_row(self, job: LaunchJob) -> None:
        assert self._activity_body is not None
        row = self._job_rows.get(job.id)
        if row is None:
            frame = ttk.Frame(self._activity_body, style="App.TFrame")
            frame.pack(fill=tk.X, pady=3)
            title = tk.StringVar()
            detail = tk.StringVar()
            ttk.Label(frame, textvariable=title, style="Section.TLabel").pack(anchor=tk.W)
            bar = ttk.Progressbar(frame, mode="indeterminate", length=420)
            bar.pack(fill=tk.X, pady=(2, 0))
            ttk.Label(frame, textvariable=detail, style="Hint.TLabel").pack(anchor=tk.W)
            row = {"frame": frame, "title": title, "detail": detail, "bar": bar}
            self._job_rows[job.id] = row
            bar.start(12)

        title_var = row["title"]
        detail_var = row["detail"]
        bar = row["bar"]
        assert isinstance(title_var, tk.StringVar)
        assert isinstance(detail_var, tk.StringVar)
        assert isinstance(bar, ttk.Progressbar)

        title_var.set(t("job.row_title", name=job.title, progress=job.progress_label))
        detail_var.set(job.detail)
        if job.state == "waiting":
            try:
                bar.stop()
            except tk.TclError:
                pass
            bar.configure(mode="determinate", maximum=job.total, value=job.step)
        elif job.state in {"running"}:
            if str(bar.cget("mode")) != "indeterminate":
                bar.configure(mode="indeterminate")
                bar.start(12)
        else:
            try:
                bar.stop()
            except tk.TclError:
                pass
            bar.configure(mode="determinate", maximum=job.total, value=job.total if job.state == "done" else job.step)

    def _job_begin(self, title: str, *, detail: str) -> str:
        job = self._jobs.start(title, detail=detail)
        self._refresh_activity_panel()
        self._log(t("job.log_start", name=title))
        return job.id

    def _job_phase(self, job_id: str, step: int, detail: str, *, waiting: bool = False) -> None:
        def apply() -> None:
            self._jobs.update(
                job_id,
                step=step,
                detail=detail,
                state="waiting" if waiting else "running",
            )
            job = self._jobs.jobs.get(job_id)
            if job:
                self._upsert_job_row(job)
            self._refresh_activity_panel()

        self.after(0, apply)

    def _job_finish(self, job_id: str, *, ok: bool, detail: str) -> None:
        def apply() -> None:
            self._jobs.finish(job_id, state="done" if ok else "error", detail=detail)
            job = self._jobs.jobs.get(job_id)
            if job:
                job.step = job.total
                self._upsert_job_row(job)
            self._refresh_activity_panel()
            # Remove finished row shortly so the banner stays readable then clears.
            self.after(2500, lambda: self._job_dismiss(job_id))

        self.after(0, apply)

    def _job_dismiss(self, job_id: str) -> None:
        self._jobs.remove(job_id)
        row = self._job_rows.pop(job_id, None)
        if row and isinstance(row.get("frame"), tk.Misc):
            row["frame"].destroy()  # type: ignore[union-attr]
        self._refresh_activity_panel()

    def _launch_async(
        self,
        source: Path,
        *,
        app_key: str | None = None,
        preferred_command: str | None = None,
        title: str | None = None,
    ) -> None:
        label = (title or source.name).strip() or str(source)
        job_id = self._job_begin(label, detail=t("job.phase_prepare"))
        self._log(f"launch: {source}")

        def work_prepare() -> None:
            err: Exception | None = None
            prep: PreparedLaunch | None = None
            try:
                prep = prepare_launch(
                    source,
                    app_key=app_key,
                    preferred_command=preferred_command,
                )
            except Exception as e:  # noqa: BLE001
                err = e

            def after_prep() -> None:
                if err or prep is None:
                    self._job_finish(job_id, ok=False, detail=t("job.phase_error", err=str(err)))
                    self._log(f"error: {err}")
                    messagebox.showerror("uvdrop", str(err))
                    return
                if prep.converted_from is not None:
                    self._log(f"converted from requirements: {prep.converted_from}")
                self._log(
                    f"policy: warnings={len(prep.policy.warnings)} errors={len(prep.policy.errors)}"
                )
                self._log(f"venv will be: {prep.venv_dir}")
                self._job_phase(job_id, 2, t("job.phase_confirm"), waiting=True)
                confirmed = self._confirm_launch(prep)
                if confirmed is None:
                    self._job_finish(job_id, ok=False, detail=t("job.phase_aborted"))
                    self._log("aborted before venv sync")
                    return
                command, show_console = confirmed
                self._log(f"entry: python {command}")
                if show_console:
                    self._log("console: visible")

                def work_run() -> None:
                    run_err: Exception | None = None
                    result = None

                    def on_phase(phase: str) -> None:
                        if phase == "sync":
                            self._job_phase(job_id, 3, t("job.phase_sync"))
                        elif phase == "run":
                            self._job_phase(job_id, 4, t("job.phase_run"))
                        elif phase == "dotenv":
                            self._job_phase(job_id, 3, t("job.phase_dotenv"))

                    try:
                        result = execute_launch(
                            prep,
                            keep=True,
                            entry_command=command,
                            show_console=show_console,
                            on_phase=on_phase,
                        )
                    except Exception as e:  # noqa: BLE001
                        run_err = e

                    def done() -> None:
                        if run_err:
                            self._job_finish(job_id, ok=False, detail=t("job.phase_error", err=str(run_err)))
                            self._log(f"error: {run_err}")
                            messagebox.showerror("uvdrop", str(run_err))
                            return
                        assert result is not None
                        self._job_finish(job_id, ok=True, detail=t("job.phase_done"))
                        self._log(
                            f"ok: key={result.app_key} pid={result.pid} mode={result.mode} "
                            f"venv={result.venv_dir}"
                        )
                        self._refresh_list()
                        self._offer_shortcut(result.app_key, prep.workspace)

                    self.after(0, done)

                threading.Thread(target=work_run, daemon=True).start()

            self.after(0, after_prep)

        threading.Thread(target=work_prepare, daemon=True).start()

    def _open_catalog(self) -> None:
        """List apps from registered catalog JSON files (no folder scanning)."""
        win = tk.Toplevel(self)
        win.title(t("catalog.win_title"))
        win.transient(self)
        win.configure(bg=self.BG)
        _fit_dialog(win, 720, 480)

        outer = ttk.Frame(win, padding=12, style="App.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            outer, text=t("help.catalog"), style="Hint.TLabel", wraplength=680, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 8))

        footer = ttk.Frame(outer, style="App.TFrame")
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        list_wrap = ttk.Frame(outer, style="App.TFrame")
        list_wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("name", "summary", "source", "path")
        tree = ttk.Treeview(list_wrap, columns=cols, show="headings", height=12)
        tree.heading("name", text=t("catalog.col_name"))
        tree.heading("summary", text=t("catalog.col_summary"))
        tree.heading("source", text=t("catalog.col_source"))
        tree.heading("path", text=t("catalog.col_path"))
        tree.column("name", width=140, stretch=False)
        tree.column("summary", width=220, stretch=True)
        tree.column("source", width=120, stretch=False)
        tree.column("path", width=200, stretch=True)
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        apps_by_iid: dict[str, CatalogApp] = {}
        status = tk.StringVar(value="")

        def reload() -> None:
            for i in tree.get_children():
                tree.delete(i)
            apps_by_iid.clear()
            s = load_settings()
            paths = [c.path for c in s.catalogs if c.enabled and c.path.strip()]
            result = load_all_catalogs(paths)
            if not paths:
                status.set(t("catalog.none"))
            elif result.errors:
                status.set(t("catalog.load_notes", n=len(result.errors)))
                for err in result.errors[:5]:
                    self._log(f"catalog: {err}", reveal=False)
            else:
                status.set("")
            if paths and not result.apps and not status.get():
                status.set(t("catalog.none"))
            for idx, app in enumerate(result.apps):
                iid = f"app-{idx}"
                apps_by_iid[iid] = app
                src = app.catalog_title or Path(app.catalog_path).name
                tree.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(app.name, app.summary, src, app.path),
                )

        def open_selected(_event: object | None = None) -> None:
            sel = tree.selection()
            if not sel:
                return
            app = apps_by_iid.get(sel[0])
            if app is None:
                return
            try:
                target = check_app_path(app)
            except (OSError, ValueError, FileNotFoundError) as e:
                messagebox.showerror(t("catalog.win_title"), str(e), parent=win)
                return
            status.set(t("catalog.queued", name=app.name))
            self._log(f"catalog: {app.name} → {target}")
            self.lift()
            self._launch_async(
                target,
                app_key=app.app_key_hint,
                preferred_command=app.command or None,
                title=app.name,
            )

        tree.bind("<Double-1>", open_selected)
        ttk.Label(footer, textvariable=status, style="Hint.TLabel").pack(side=tk.LEFT)
        ttk.Button(footer, text=t("common.close"), command=win.destroy).pack(side=tk.RIGHT)
        ttk.Button(
            footer, text=t("catalog.run"), command=open_selected, style="Primary.TButton"
        ).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(footer, text=t("catalog.refresh"), command=reload, style="Ghost.TButton").pack(
            side=tk.RIGHT, padx=(0, 8)
        )
        reload()

    def _save_sample(self) -> None:
        samples = list_samples()
        pick = tk.Toplevel(self)
        pick.title(t("sample.title"))
        pick.geometry("540x340")
        pick.transient(self)
        pick.configure(bg=self.BG)
        frm = ttk.Frame(pick, padding=16, style="App.TFrame")
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text=t("sample.which"), style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            frm,
            text=t("sample.after"),
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(4, 10))

        var = tk.StringVar(value=samples[0].id)
        for sp in samples:
            box = tk.Frame(
                frm, bg=self.CARD, highlightbackground=self.CARD_BORDER, highlightthickness=1
            )
            box.pack(fill=tk.X, pady=(0, 8))
            ttk.Radiobutton(
                box,
                text=f"{sp.title}\n{sp.blurb}",
                value=sp.id,
                variable=var,
            ).pack(anchor=tk.W, padx=10, pady=10)

        fmt = tk.StringVar(value="folder")
        fmt_row = ttk.Frame(frm, style="App.TFrame")
        fmt_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(fmt_row, text=t("sample.format"), style="Hint.TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(fmt_row, text=t("sample.folder"), variable=fmt, value="folder").pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Radiobutton(fmt_row, text="ZIP", variable=fmt, value="zip").pack(
            side=tk.LEFT, padx=(8, 0)
        )

        def go() -> None:
            sid = var.get()
            as_zip = fmt.get() == "zip"
            pick.destroy()
            self._save_sample_id(sid, as_zip=as_zip)

        btns = ttk.Frame(frm, style="App.TFrame")
        btns.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(btns, text=t("sample.save_continue"), command=go).pack(side=tk.RIGHT)
        ttk.Button(btns, text=t("sample.cancel"), command=pick.destroy).pack(
            side=tk.RIGHT, padx=(0, 8)
        )

    def _save_sample_id(self, sample_id: str, *, as_zip: bool = False) -> None:
        from uvdrop.sample_app import SAMPLES

        spec = SAMPLES[sample_id]
        if not as_zip:
            dest = filedialog.askdirectory(title=t("sample.save_dir_title"))
            if not dest:
                return
            root = write_sample_tree(Path(dest), sample_id=sample_id)
            self._log(f"sample folder: {root}")
            if messagebox.askyesno("uvdrop", t("sample.saved_run", path=root)):
                self._launch_async(root)
            else:
                try:
                    os.startfile(str(root))  # type: ignore[attr-defined]
                except Exception:
                    pass
        else:
            path = filedialog.asksaveasfilename(
                title=t("sample.save_zip_title"),
                defaultextension=".zip",
                initialfile=f"{spec.folder_name}.zip",
                filetypes=[("ZIP", "*.zip")],
            )
            if not path:
                return
            zip_path = write_sample_zip(Path(path), sample_id=sample_id)
            self._log(f"sample zip: {zip_path}")
            if messagebox.askyesno("uvdrop", t("sample.saved_run", path=zip_path)):
                self._launch_async(zip_path)

    def _open_help(self) -> None:
        self._show_text_window(t("help.title"), t("help.body"), size=(620, 560))

    def _open_version_help(self) -> None:
        self._show_text_window(
            t("confirm.version_guide"), version_rule_guide(), mono=True, size=(640, 620)
        )

    def _show_text_window(
        self,
        title: str,
        body: str,
        *,
        mono: bool = False,
        size: tuple[int, int] = (520, 400),
    ) -> None:
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.configure(bg=self.BG)
        _fit_dialog(win, *size)
        frm = ttk.Frame(win, padding=14, style="App.TFrame")
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frm, text=t("common.close"), command=win.destroy).pack(
            side=tk.BOTTOM, anchor=tk.E, pady=(10, 0)
        )
        body_wrap = tk.Frame(frm, bg=self.CARD_BORDER, padx=1, pady=1)
        body_wrap.pack(fill=tk.BOTH, expand=True)
        font = (self.mono_font, 10) if mono else (self.ui_font, 10)
        txt = tk.Text(
            body_wrap,
            wrap=tk.WORD,
            font=font,
            relief=tk.FLAT,
            padx=10,
            pady=8,
            bg=self.CARD,
            fg=self.INK,
        )
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bar = ttk.Scrollbar(body_wrap, orient=tk.VERTICAL, command=txt.yview)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        txt.configure(yscrollcommand=bar.set)
        txt.insert("1.0", body)
        txt.configure(state=tk.DISABLED)

    def _open_usage(self) -> None:
        """Launch history chart: day / week / month, selected app or all."""
        win = tk.Toplevel(self)
        win.title(t("usage.title"))
        win.transient(self)
        win.configure(bg=self.BG)
        _fit_dialog(win, 720, 520)

        frm = ttk.Frame(win, padding=14, style="App.TFrame")
        frm.pack(fill=tk.BOTH, expand=True)

        apps = load_registry()
        name_by_key = {rec.key: rec.name for rec in apps.values()}
        scope_labels = [t("usage.scope_all")] + [rec.name for rec in apps.values()]
        scope_keys: list[str | None] = [None] + [rec.key for rec in apps.values()]
        selected = self._selected_key()
        initial = scope_keys.index(selected) if selected in scope_keys else 0

        top = ttk.Frame(frm, style="App.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(top, text=t("usage.scope")).pack(side=tk.LEFT)
        scope_var = tk.StringVar(value=scope_labels[initial])
        scope_box = ttk.Combobox(
            top, textvariable=scope_var, values=scope_labels, state="readonly", width=28
        )
        scope_box.pack(side=tk.LEFT, padx=(8, 16))
        ttk.Label(top, text=t("usage.unit")).pack(side=tk.LEFT)
        gran_labels = [t("usage.daily"), t("usage.weekly"), t("usage.monthly")]
        # label -> (granularity, periods, unit-label key)
        gran_spec = {
            gran_labels[0]: (DAY, 30, "usage.u_day"),
            gran_labels[1]: (WEEK, 16, "usage.u_week"),
            gran_labels[2]: (MONTH, 12, "usage.u_month"),
        }
        gran_var = tk.StringVar(value=gran_labels[0])
        gran_box = ttk.Combobox(
            top,
            textvariable=gran_var,
            values=gran_labels,
            state="readonly",
            width=10,
        )
        gran_box.pack(side=tk.LEFT, padx=(8, 0))

        summary = tk.StringVar(value="")
        ttk.Label(frm, textvariable=summary, style="Hint.TLabel").pack(anchor=tk.W, pady=(10, 6))

        chart_wrap = tk.Frame(frm, bg=self.CARD_BORDER, padx=1, pady=1)
        chart_wrap.pack(fill=tk.BOTH, expand=True)
        chart = tk.Canvas(chart_wrap, bg=self.CARD, highlightthickness=0, height=280)
        chart.pack(fill=tk.BOTH, expand=True)

        tip_var = tk.StringVar(value="")
        tip_lbl = tk.Label(
            chart,
            textvariable=tip_var,
            justify=tk.LEFT,
            background="#f7faf7",
            foreground=self.INK,
            relief=tk.SOLID,
            borderwidth=1,
            font=(self.ui_font, 9),
            padx=8,
            pady=6,
            anchor=tk.NW,
        )
        hit_regions: list[tuple[float, float, float, float, object]] = []

        def hide_tip(_event: object | None = None) -> None:
            tip_var.set("")
            tip_lbl.place_forget()

        def show_tip(event) -> None:
            hit = None
            for x0, y0, x1, y1, bucket in hit_regions:
                if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                    hit = bucket
                    break
            if hit is None or not hit.count:
                hide_tip()
                return
            lines = [f"{hit.label}  ·  {t('usage.tip_total', n=hit.count)}"]
            if len(hit.parts) > 1 or (len(hit.parts) == 1 and scope_var.get() == scope_labels[0]):
                for app_key, n in hit.parts:
                    name = name_by_key.get(app_key, app_key)
                    lines.append(t("usage.tip_part", name=name, n=n))
            tip_var.set("\n".join(lines))
            tip_lbl.update_idletasks()
            tw = max(tip_lbl.winfo_reqwidth(), 1)
            th = max(tip_lbl.winfo_reqheight(), 1)
            cw = max(chart.winfo_width(), 1)
            ch = max(chart.winfo_height(), 1)
            x = min(event.x + 14, cw - tw - 6)
            y = min(event.y + 14, ch - th - 6)
            tip_lbl.place(x=max(6, x), y=max(6, y))

        def current_spec() -> tuple[str | None, str, int, str]:
            key = (
                scope_keys[scope_labels.index(scope_var.get())]
                if scope_var.get() in scope_labels
                else None
            )
            gran, periods, unit_key = gran_spec.get(gran_var.get(), (DAY, 30, "usage.u_day"))
            return key, gran, periods, unit_key

        def redraw(_event: object | None = None) -> None:
            hide_tip()
            key, gran, periods, unit_key = current_spec()
            data = buckets(key, gran, periods=periods)
            total = sum(b.count for b in data)
            summary.set(
                t("usage.summary", scope=scope_var.get(), unit=t(unit_key), total=total)
            )
            stacked = key is None
            hit_regions.clear()
            hit_regions.extend(
                self._draw_bar_chart(
                    chart,
                    data,
                    stacked=stacked,
                    name_by_key=name_by_key,
                )
            )

        scope_box.bind("<<ComboboxSelected>>", redraw)
        gran_box.bind("<<ComboboxSelected>>", redraw)
        chart.bind("<Configure>", redraw)
        chart.bind("<Motion>", show_tip)
        chart_wrap.bind("<Leave>", hide_tip)

        ttk.Button(frm, text=t("common.close"), command=win.destroy).pack(anchor=tk.E, pady=(10, 0))
        redraw()

    # Distinct segment colors for stacked "all apps" bars (cycles as needed).
    _STACK_COLORS = (
        "#2f7d62",
        "#2f6f8a",
        "#8a6a2f",
        "#6b4f8a",
        "#3d7a4a",
        "#8a4f5a",
        "#2f7a7a",
        "#5a6f8a",
    )

    def _draw_bar_chart(
        self,
        canvas: tk.Canvas,
        data: list,
        *,
        stacked: bool = False,
        name_by_key: dict[str, str] | None = None,
    ) -> list[tuple[float, float, float, float, object]]:
        """Draw bars; return hit regions (x0,y0,x1,y1,bucket) for hover tooltips."""
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 200)
        left, right, top, bottom = 44, 12, 16, 34
        plot_w = width - left - right
        plot_h = height - top - bottom
        hits: list[tuple[float, float, float, float, object]] = []
        if plot_w <= 0 or plot_h <= 0 or not data:
            return hits

        peak = max((b.count for b in data), default=0)
        axis_max = max(1, peak)
        canvas.create_line(left, top + plot_h, left + plot_w, top + plot_h, fill=self.CARD_BORDER)

        for frac in (0.0, 0.5, 1.0):
            y = top + plot_h - plot_h * frac
            value = int(round(axis_max * frac))
            canvas.create_line(left, y, left + plot_w, y, fill="#eef3f0")
            canvas.create_text(
                left - 8, y, text=str(value), anchor=tk.E, fill=self.MUTED, font=(self.ui_font, 9)
            )

        # Stable color assignment across the whole chart (by app key).
        color_of: dict[str, str] = {}
        if stacked:
            order: list[str] = []
            for bucket in data:
                for app_key, _n in bucket.parts:
                    if app_key not in color_of:
                        color_of[app_key] = self._STACK_COLORS[len(order) % len(self._STACK_COLORS)]
                        order.append(app_key)

        slot = plot_w / len(data)
        bar_w = max(3.0, min(28.0, slot * 0.66))
        # Thin out labels so they never overlap
        step = max(1, int(len(data) / max(1, int(plot_w / 60))))

        for i, bucket in enumerate(data):
            cx = left + slot * (i + 0.5)
            x0 = cx - bar_w / 2
            x1 = cx + bar_w / 2
            if bucket.count:
                if stacked and len(bucket.parts) > 1:
                    y_cursor = top + plot_h
                    for app_key, n in reversed(bucket.parts):
                        seg_h = (n / axis_max) * plot_h
                        y1 = y_cursor
                        y0 = y_cursor - seg_h
                        canvas.create_rectangle(
                            x0,
                            y0,
                            x1,
                            y1,
                            fill=color_of.get(app_key, self.ACCENT),
                            outline="",
                        )
                        y_cursor = y0
                    bar_top = y_cursor
                else:
                    bar_h = (bucket.count / axis_max) * plot_h
                    bar_top = top + plot_h - bar_h
                    fill = (
                        color_of.get(bucket.parts[0][0], self.ACCENT)
                        if stacked and bucket.parts
                        else self.ACCENT
                    )
                    canvas.create_rectangle(x0, bar_top, x1, top + plot_h, fill=fill, outline="")
                hits.append((x0, bar_top, x1, top + plot_h, bucket))
                if bar_w >= 16:
                    canvas.create_text(
                        cx,
                        bar_top - 8,
                        text=str(bucket.count),
                        fill=self.MUTED,
                        font=(self.ui_font, 8),
                    )
            if i % step == 0 or i == len(data) - 1:
                canvas.create_text(
                    cx,
                    top + plot_h + 12,
                    text=bucket.label,
                    fill=self.MUTED,
                    font=(self.ui_font, 8),
                )

        if peak == 0:
            canvas.create_text(
                left + plot_w / 2,
                top + plot_h / 2,
                text=t("usage.no_data"),
                fill=self.MUTED,
                font=(self.ui_font, 10),
            )
        elif stacked and color_of and name_by_key is not None:
            # Compact legend along the top-right when several apps are present.
            legend_items = list(color_of.items())[:6]
            lx = left + plot_w - 4
            ly = top + 6
            for app_key, color in reversed(legend_items):
                name = name_by_key.get(app_key, app_key)
                text_id = canvas.create_text(
                    lx, ly, text=name, anchor=tk.NE, fill=self.MUTED, font=(self.ui_font, 8)
                )
                bbox = canvas.bbox(text_id)
                if bbox:
                    canvas.create_rectangle(
                        bbox[0] - 14,
                        ly - 4,
                        bbox[0] - 4,
                        ly + 6,
                        fill=color,
                        outline="",
                    )
                ly += 14

        return hits

    def _relaunch_selected(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", t("dlg.select_app"))
            return
        apps = load_registry()
        rec = apps.get(key)
        title = rec.name if rec else key
        job_id = self._job_begin(title, detail=t("job.phase_prepare"))
        self._log(f"relaunch: {key}")

        def work_prepare() -> None:
            err: Exception | None = None
            prep: PreparedLaunch | None = None
            try:
                prep = prepare_relaunch(key)
            except Exception as e:  # noqa: BLE001
                err = e

            def after_prep() -> None:
                if err or prep is None:
                    self._job_finish(job_id, ok=False, detail=t("job.phase_error", err=str(err)))
                    self._log(f"error: {err}")
                    messagebox.showerror("uvdrop", str(err))
                    return
                self._job_phase(job_id, 2, t("job.phase_confirm"), waiting=True)
                confirmed = self._confirm_launch(prep)
                if confirmed is None:
                    self._job_finish(job_id, ok=False, detail=t("job.phase_aborted"))
                    self._log("aborted before venv sync")
                    return
                command, show_console = confirmed

                def work_run() -> None:
                    run_err: Exception | None = None
                    result = None

                    def on_phase(phase: str) -> None:
                        if phase == "sync":
                            self._job_phase(job_id, 3, t("job.phase_sync"))
                        elif phase == "run":
                            self._job_phase(job_id, 4, t("job.phase_run"))
                        elif phase == "dotenv":
                            self._job_phase(job_id, 3, t("job.phase_dotenv"))

                    try:
                        result = execute_launch(
                            prep,
                            keep=True,
                            entry_command=command,
                            show_console=show_console,
                            on_phase=on_phase,
                        )
                    except Exception as e:  # noqa: BLE001
                        run_err = e

                    def done() -> None:
                        if run_err:
                            self._job_finish(
                                job_id, ok=False, detail=t("job.phase_error", err=str(run_err))
                            )
                            self._log(f"error: {run_err}")
                            messagebox.showerror("uvdrop", str(run_err))
                            return
                        assert result is not None
                        self._job_finish(job_id, ok=True, detail=t("job.phase_done"))
                        self._log(f"ok: key={result.app_key} pid={result.pid}")
                        self._refresh_list()

                    self.after(0, done)

                threading.Thread(target=work_run, daemon=True).start()

            self.after(0, after_prep)

        threading.Thread(target=work_prepare, daemon=True).start()

    def _edit_env(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", t("dlg.select_app"))
            return
        open_dotenv_in_notepad(key)
        self._log(f"opened .env for {key}")

    def _make_shortcut(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", t("dlg.select_app"))
            return
        rec = load_registry().get(key)
        workspace = Path(rec.workspace) if rec else apps_dir() / key
        self._shortcut_dialog(key, workspace, ask_first=False)

    def _offer_shortcut(self, key: str, workspace: Path) -> None:
        """Right after a successful launch, suggest a desktop shortcut once."""
        if shortcut_path(key).exists():
            return
        self._shortcut_dialog(key, workspace, ask_first=True)

    def _shortcut_dialog(self, key: str, workspace: Path, *, ask_first: bool) -> None:
        rec = load_registry().get(key)
        candidates = find_icon_candidates(workspace)

        win = tk.Toplevel(self)
        win.title(t("shortcut.win_title"))
        win.transient(self)
        win.configure(bg=self.BG)
        win.grab_set()
        _fit_dialog(win, 560, 420)
        # Keep PhotoImage refs alive for the dialog lifetime
        win._preview_images = []  # type: ignore[attr-defined]

        outer = ttk.Frame(win, padding=12, style="App.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            outer,
            text=t("shortcut.offer_title") if ask_first else t("shortcut.make_now"),
            style="Section.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text=t("shortcut.bypass_note"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 8))

        # Fixed bottom buttons — always reachable
        btns = ttk.Frame(outer, style="App.TFrame")
        btns.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        # Body: scrollable left + fixed preview right
        body = ttk.Frame(outer, style="App.TFrame")
        body.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(body, style="App.TFrame")
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))

        scroll_shell = ttk.Frame(body, style="App.TFrame")
        scroll_shell.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _canvas, left = _scrollable_panel(scroll_shell, bg=self.BG, padding=0)

        # selection value: "" | file:<path> | theme:<id>
        icon_var = tk.StringVar(value="")
        if rec and rec.icon_path:
            if rec.icon_path.startswith("theme:"):
                icon_var.set(rec.icon_path)
            else:
                icon_var.set(f"file:{rec.icon_path}")

        theme_var = tk.StringVar(value=THEMES[0].id)
        color_var = tk.StringVar(value=PALETTE[0][0])
        color2_var = tk.StringVar(value="#ffffff")
        if icon_var.get().startswith("theme:"):
            parts = icon_var.get().split(":", 3)
            if len(parts) >= 2 and parts[1]:
                theme_var.set(parts[1])
            if len(parts) >= 3 and parts[2]:
                color_var.set(parts[2])
            if len(parts) >= 4 and parts[3]:
                color2_var.set(parts[3])

        ttk.Label(left, text=t("shortcut.pick_icon"), style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            left,
            text=t("shortcut.pick_icon_hint"),
            style="Hint.TLabel",
            wraplength=340,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(2, 6))

        ttk.Radiobutton(
            left, text=t("shortcut.default_icon"), variable=icon_var, value=""
        ).pack(anchor=tk.W)

        sample_box = ttk.LabelFrame(left, text=t("shortcut.samples"), padding=8)
        sample_box.pack(fill=tk.X, pady=(8, 0))

        # Visual icon grid — no text blurbs, just thumbnails
        grid = ttk.Frame(sample_box)
        grid.pack(fill=tk.X)
        theme_thumbs: dict[str, tk.Label] = {}
        thumb_border = self.CARD_BORDER
        thumb_selected = self.ACCENT

        def _png_photo(data: bytes) -> tk.PhotoImage:
            import base64

            img = tk.PhotoImage(data=base64.b64encode(data))
            win._preview_images.append(img)  # type: ignore[attr-defined]
            return img

        def _mark_theme_selection() -> None:
            chosen = theme_var.get() if icon_var.get().startswith("theme:") else ""
            for tid, lbl in theme_thumbs.items():
                lbl.configure(
                    highlightbackground=thumb_selected if tid == chosen else thumb_border,
                    highlightthickness=2 if tid == chosen else 1,
                )

        def _pick_theme(tid: str) -> None:
            theme_var.set(tid)
            icon_var.set(f"theme:{tid}")
            _mark_theme_selection()

        def _rebuild_theme_thumbs() -> None:
            color = color_var.get() or PALETTE[0][0]
            color2 = color2_var.get() or "#ffffff"
            for tid, lbl in theme_thumbs.items():
                img = _png_photo(render_theme_png(tid, color, color2, size=56))
                lbl.configure(image=img)
                lbl.image = img  # type: ignore[attr-defined]
            _mark_theme_selection()

        cols = 4
        for i, theme in enumerate(THEMES):
            cell = tk.Frame(grid, bg=self.BG)
            cell.grid(row=i // cols, column=i % cols, padx=4, pady=4)
            img = _png_photo(
                render_theme_png(theme.id, color_var.get(), color2_var.get(), size=56)
            )
            lbl = tk.Label(
                cell,
                image=img,
                bg=self.CARD,
                cursor="hand2",
                highlightbackground=thumb_border,
                highlightthickness=1,
                bd=0,
            )
            lbl.image = img  # type: ignore[attr-defined]
            lbl.pack()
            lbl.bind("<Button-1>", lambda _e, tid=theme.id: _pick_theme(tid))
            ToolTip(lbl, _theme_label(theme))
            theme_thumbs[theme.id] = lbl

        if icon_var.get().startswith("theme:"):
            _mark_theme_selection()

        def make_color_row(
            label_key: str, variable: tk.StringVar, *, default: str
        ) -> None:
            row = ttk.Frame(sample_box)
            row.pack(fill=tk.X, pady=(10, 0))
            ttk.Label(row, text=t(label_key), style="Hint.TLabel", width=8).pack(side=tk.LEFT)

            current = tk.Label(
                row,
                text="  ",
                bg=variable.get() or default,
                width=3,
                relief=tk.SUNKEN,
                bd=1,
            )
            current.pack(side=tk.LEFT, padx=(0, 3))

            def choose(c: str) -> None:
                variable.set(c)
                current.configure(bg=c)
                if not icon_var.get().startswith("theme:"):
                    icon_var.set(f"theme:{theme_var.get()}")
                _rebuild_theme_thumbs()

            for hex_color, label in PALETTE:
                swatch = tk.Label(
                    row,
                    text=" ",
                    bg=hex_color,
                    width=2,
                    cursor="hand2",
                    relief=tk.RAISED,
                    bd=1,
                )
                swatch.pack(side=tk.LEFT, padx=(3, 0))
                ToolTip(swatch, _color_label(hex_color, label))
                swatch.bind("<Button-1>", lambda _e, c=hex_color: choose(c))

            def custom() -> None:
                _rgb, chosen = colorchooser.askcolor(
                    color=variable.get() or default,
                    title=t("shortcut.custom_color"),
                    parent=win,
                )
                if chosen:
                    choose(chosen)

            ttk.Button(row, text=t("shortcut.custom"), width=4, command=custom).pack(
                side=tk.LEFT, padx=(5, 0)
            )

        make_color_row("shortcut.color1", color_var, default=PALETTE[0][0])
        make_color_row("shortcut.color2", color2_var, default="#ffffff")

        file_box = ttk.LabelFrame(left, text=t("shortcut.inapp_file"), padding=8)
        file_box.pack(fill=tk.X, pady=(10, 0))
        if candidates:
            for path in candidates[:12]:
                try:
                    label = str(path.relative_to(workspace))
                except ValueError:
                    label = str(path)
                ttk.Radiobutton(
                    file_box,
                    text=label,
                    variable=icon_var,
                    value=f"file:{path}",
                ).pack(anchor=tk.W, pady=1)
        else:
            ttk.Label(file_box, text=t("shortcut.no_images"), style="Hint.TLabel").pack(anchor=tk.W)

        def browse() -> None:
            picked = filedialog.askopenfilename(
                title=t("shortcut.pick_file"),
                filetypes=[(t("shortcut.icon_images"), "*.ico *.png"), ("All", "*.*")],
                parent=win,
            )
            if picked:
                icon_var.set(f"file:{picked}")
                ttk.Radiobutton(
                    file_box, text=Path(picked).name, variable=icon_var, value=f"file:{picked}"
                ).pack(anchor=tk.W, pady=1)
                refresh_preview()

        file_actions = ttk.Frame(file_box)
        file_actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(file_actions, text=t("shortcut.pick_from_file"), command=browse).pack(
            side=tk.LEFT
        )

        def paste_image(_event: object | None = None) -> str:
            try:
                png = clipboard_png()
                pasted = launchers_dir() / f"_clipboard-{key}.png"
                pasted.parent.mkdir(parents=True, exist_ok=True)
                pasted.write_bytes(png)
            except (OSError, ValueError) as e:
                messagebox.showwarning(
                    t("shortcut.paste_title"),
                    t("shortcut.paste_failed", e=e),
                    parent=win,
                )
                return "break"
            icon_var.set(f"file:{pasted}")
            refresh_preview()
            return "break"

        ttk.Button(file_actions, text=t("shortcut.paste"), command=paste_image).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Label(file_box, text=t("shortcut.paste_hint"), style="Hint.TLabel").pack(
            anchor=tk.W, pady=(5, 0)
        )
        win.bind("<Control-v>", paste_image)
        win.bind("<Control-V>", paste_image)

        # --- preview (fixed on the right) ---
        ttk.Label(right, text=t("shortcut.preview"), style="Section.TLabel").pack(anchor=tk.W)
        preview_shell = tk.Frame(right, bg=self.CARD_BORDER, padx=1, pady=1)
        preview_shell.pack(pady=(6, 0))
        preview_bg = tk.Frame(preview_shell, bg=self.CARD, width=132, height=132)
        preview_bg.pack()
        preview_bg.pack_propagate(False)
        preview_lbl = tk.Label(preview_bg, text=t("shortcut.none"), bg=self.CARD, fg=self.MUTED)
        preview_lbl.pack(expand=True)

        def _photo_from_path(path: Path) -> tk.PhotoImage | None:
            try:
                if path.suffix.lower() == ".png":
                    img = tk.PhotoImage(file=str(path))
                elif path.suffix.lower() == ".ico":
                    raw = path.read_bytes()
                    if b"\x89PNG" in raw:
                        png = raw[raw.index(b"\x89PNG") :]
                        return _png_photo(png)
                    return None
                else:
                    return None
                while img.width() > 112 or img.height() > 112:
                    img = img.subsample(2, 2)
                win._preview_images.append(img)  # type: ignore[attr-defined]
                return img
            except tk.TclError:
                return None

        def refresh_preview(*_a: object) -> None:
            choice = icon_var.get()
            img: tk.PhotoImage | None = None
            caption = t("shortcut.default_short")
            if choice.startswith("theme:"):
                tid = theme_var.get() or choice.split(":")[1] or THEMES[0].id
                theme_var.set(tid)
                data = render_theme_png(
                    tid, color_var.get(), color2_var.get(), size=112
                )
                img = _png_photo(data)
                theme = next((th for th in THEMES if th.id == tid), THEMES[0])
                caption = _theme_label(theme)
                _mark_theme_selection()
            elif choice.startswith("file:"):
                path = Path(choice[5:])
                img = _photo_from_path(path)
                caption = path.name
                _mark_theme_selection()
            else:
                _mark_theme_selection()
            if img is not None:
                preview_lbl.configure(image=img, text="")
            else:
                preview_lbl.configure(image="", text=caption if choice else t("shortcut.none"))

        icon_var.trace_add("write", refresh_preview)
        color_var.trace_add("write", refresh_preview)
        color2_var.trace_add("write", refresh_preview)
        theme_var.trace_add("write", refresh_preview)
        refresh_preview()

        def resolve_icon_file() -> tuple[Path | None, str]:
            """Return (ico_path_or_none, stored_icon_token)."""
            choice = icon_var.get().strip()
            if not choice:
                return None, ""
            if choice.startswith("theme:"):
                tid = theme_var.get() or THEMES[0].id
                color = color_var.get() or PALETTE[0][0]
                color2 = color2_var.get() or "#ffffff"
                png = render_theme_png(tid, color, color2, size=256)
                tmp = launchers_dir() / f"_theme-{key}.png"
                tmp.write_bytes(png)
                ico = ensure_ico(tmp, launchers_dir(), key)
                try:
                    tmp.unlink()
                except OSError:
                    pass
                return ico, f"theme:{tid}:{color}:{color2}"
            if choice.startswith("file:"):
                src = Path(choice[5:])
                return ensure_ico(src, launchers_dir(), key), str(src)
            return None, ""

        def create() -> None:
            try:
                icon, token = resolve_icon_file()
            except (OSError, ValueError) as e:
                messagebox.showerror(t("shortcut.icon_err"), str(e), parent=win)
                return
            try:
                lnk = create_desktop_shortcut(key, icon=icon)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("uvdrop", str(e), parent=win)
                return
            set_icon(key, token)
            self._log(f"shortcut: {lnk}" + (f" (icon: {icon})" if icon else ""))
            win.destroy()
            messagebox.showinfo(
                "uvdrop",
                t("shortcut.done_body", lnk=lnk, key=key),
                parent=self,
            )

        ttk.Button(btns, text=t("shortcut.create"), command=create, style="Primary.TButton").pack(
            side=tk.RIGHT
        )
        ttk.Button(
            btns,
            text=t("shortcut.later") if ask_first else t("confirm.abort"),
            command=win.destroy,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        win.bind("<Escape>", lambda _e: win.destroy())

    def _hibernate_selected(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", t("dlg.select_app"), parent=self)
            return
        rec = load_registry().get(key)
        label = rec.name if rec else key
        venv = envs_dir() / key
        if not venv.exists():
            messagebox.showinfo("uvdrop", t("hibernate.already", name=label), parent=self)
            return
        if not messagebox.askyesno(
            "uvdrop",
            t("hibernate.confirm", name=label),
            parent=self,
        ):
            return
        try:
            reclaimed = hibernate_venv(key)
        except OSError as e:
            messagebox.showerror("uvdrop", t("hibernate.failed", e=e), parent=self)
            return
        self._refresh_list()
        mib = reclaimed / (1024 * 1024)
        self._log(t("hibernate.done", name=label, size=f"{mib:.1f} MiB"))
        messagebox.showinfo(
            "uvdrop",
            t("hibernate.done", name=label, size=f"{mib:.1f} MiB"),
            parent=self,
        )

    def _delete_selected(self) -> None:
        key = self._selected_key()
        if not key:
            messagebox.showinfo("uvdrop", t("dlg.select_app"), parent=self)
            return
        rec = load_registry().get(key)
        label = rec.name if rec else key
        if not messagebox.askyesno(
            "uvdrop",
            t("delete.confirm", key=f"{label}\n({key})"),
            parent=self,
        ):
            return
        try:
            # Best-effort: also drop a desktop shortcut if we created one.
            lnk = shortcut_path(key, display_name=rec.name if rec else None)
            if lnk.is_file():
                try:
                    lnk.unlink()
                except OSError:
                    pass
            cleanup_app(key, remove_registry=True)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("uvdrop", t("delete.failed", e=e), parent=self)
            self._log(f"delete failed: {key}: {e}")
            return
        self._refresh_list()
        self._log(t("delete.done", key=key))
        messagebox.showinfo("uvdrop", t("delete.done", key=label), parent=self)
    def _open_licenses(self) -> None:
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
        messagebox.showinfo("uvdrop", t("licenses.missing"))

    def _open_settings(self) -> None:
        s = load_settings()
        win = tk.Toplevel(self)
        win.title(t("settings.title"))
        win.transient(self)
        win.configure(bg=self.BG)
        _fit_dialog(win, 640, 520)

        outer = ttk.Frame(win, padding=12, style="App.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        lang_var = tk.StringVar(value=s.ui_language or "auto")
        prev_lang = s.ui_language or "auto"

        def save() -> None:
            problems = al_table.problems() + bl_table.problems()
            if problems:
                shown = "\n".join(f"・{p}" for p in problems[:8])
                extra = (
                    t("settings.badver_more", n=len(problems) - 8) if len(problems) > 8 else ""
                )
                if not messagebox.askyesno(
                    t("settings.badver_title"),
                    t("settings.badver_body", list=shown, extra=extra),
                    parent=win,
                ):
                    return
            try:
                inactive_days = int(storage_days.get())
                if not 1 <= inactive_days <= 3650:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    t("settings.tab_storage"),
                    t("settings.hibernate_days_invalid"),
                    parent=win,
                )
                return
            s.guard.confirm_before_run = bool(confirm_en.get())
            s.guard.no_allowlist = no_al.get() or "confirm"
            s.guard.allow_requirements_txt = bool(req_en.get())
            s.guard.show_console = bool(console_en.get())
            s.storage.hibernate_enabled = bool(storage_en.get())
            s.storage.inactive_days = inactive_days
            s.ui_language = lang_var.get() or "auto"
            s.allowlist.enabled = bool(al_en.get())
            s.allowlist.packages = al_table.get_rules()
            s.allowlist.mode = al_mode.get() or "warn"
            s.blocklist.enabled = bool(bl_en.get())
            s.blocklist.packages = bl_table.get_rules()
            s.xlsx.enabled = bool(xlsx_en.get())
            s.xlsx.url = url_var.get().strip()
            s.proxy.enabled = bool(proxy_en.get())
            s.proxy.http = http_var.get().strip()
            s.proxy.https = https_var.get().strip()
            s.proxy.no_proxy = nop_var.get().strip()
            s.catalogs = [
                CatalogRef(path=p, enabled=True)
                for p in catalog_paths
                if p.strip()
            ]
            save_settings(s)
            apply_from_settings()
            self._log("settings saved")
            if s.allowlist.enabled:
                self._log(f"manual allowlist: {len(s.allowlist.packages)} package(s)")
            if s.blocklist.enabled:
                self._log(f"blocklist: {len(s.blocklist.packages)} package(s)")
            if s.xlsx.enabled and s.xlsx.url:
                try:
                    path = sync_file_allowlist(force=True)
                    self._log(f"file allowlist synced: {path}")
                except Exception as e:  # noqa: BLE001
                    messagebox.showerror("uvdrop", str(e))
                    return
            win.destroy()
            if (s.ui_language or "auto") != (prev_lang or "auto"):
                messagebox.showinfo(t("settings.title"), t("settings.lang_hint"))

        # Sticky footer — always visible, even when tab content is tall
        btns = ttk.Frame(outer, style="App.TFrame")
        btns.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        ttk.Label(btns, text=f"policies: {policies_dir()}", style="Hint.TLabel").pack(side=tk.LEFT)
        ttk.Button(btns, text=t("settings.save"), command=save, style="Primary.TButton").pack(
            side=tk.RIGHT
        )
        ttk.Button(btns, text=t("settings.cancel"), command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))

        ttk.Label(outer, text=t("settings.heading"), style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            outer,
            text=t("settings.save_hint"),
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(2, 8))

        nb = ttk.Notebook(outer)
        nb.pack(fill=tk.BOTH, expand=True)

        # --- guard tab (scrollable) ---
        tab_guard_outer = ttk.Frame(nb)
        nb.add(tab_guard_outer, text=t("settings.tab_guard"))
        _g_canvas, tab_guard = _scrollable_panel(tab_guard_outer, bg=self.BG, padding=12)

        confirm_en = tk.BooleanVar(value=s.guard.confirm_before_run)
        g_row = ttk.Frame(tab_guard)
        g_row.pack(fill=tk.X)
        ttk.Checkbutton(
            g_row, text=t("settings.confirm_each"), variable=confirm_en
        ).pack(side=tk.LEFT)
        ttk.Button(
            g_row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo(t("settings.q_guard"), t("help.guard")),
        ).pack(side=tk.RIGHT)
        ttk.Label(
            tab_guard,
            text=t("help.guard"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 14))

        no_al = tk.StringVar(value=s.guard.no_allowlist)
        ttk.Label(tab_guard, text=t("settings.no_al"), style="Hint.TLabel").pack(anchor=tk.W)
        ttk.Radiobutton(
            tab_guard, text=t("settings.no_al_confirm"), variable=no_al, value="confirm"
        ).pack(anchor=tk.W, pady=(4, 0))
        ttk.Radiobutton(
            tab_guard, text=t("settings.no_al_allow"), variable=no_al, value="allow"
        ).pack(anchor=tk.W, pady=(2, 14))

        req_en = tk.BooleanVar(value=s.guard.allow_requirements_txt)
        r_row = ttk.Frame(tab_guard)
        r_row.pack(fill=tk.X)
        ttk.Checkbutton(
            r_row, text=t("settings.req"), variable=req_en
        ).pack(side=tk.LEFT)
        ttk.Button(
            r_row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo("requirements.txt", t("help.requirements")),
        ).pack(side=tk.RIGHT)
        ttk.Label(
            tab_guard,
            text=t("help.requirements"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 14))

        console_en = tk.BooleanVar(value=s.guard.show_console)
        c_row = ttk.Frame(tab_guard)
        c_row.pack(fill=tk.X)
        ttk.Checkbutton(
            c_row,
            text=t("settings.console"),
            variable=console_en,
        ).pack(side=tk.LEFT)
        ttk.Button(
            c_row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo(t("settings.q_console"), t("help.console")),
        ).pack(side=tk.RIGHT)
        ttk.Label(
            tab_guard,
            text=t("help.console"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 0))

        # --- storage / venv hibernation tab (scrollable) ---
        tab_storage_outer = ttk.Frame(nb)
        nb.add(tab_storage_outer, text=t("settings.tab_storage"))
        _storage_canvas, tab_storage = _scrollable_panel(
            tab_storage_outer, bg=self.BG, padding=12
        )
        storage_en = tk.BooleanVar(value=s.storage.hibernate_enabled)
        storage_days = tk.StringVar(value=str(s.storage.inactive_days))
        ttk.Label(
            tab_storage,
            text=t("settings.hibernate_title"),
            style="Section.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            tab_storage,
            text=t("settings.hibernate_help"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 14))
        ttk.Checkbutton(
            tab_storage,
            text=t("settings.hibernate_enable"),
            variable=storage_en,
        ).pack(anchor=tk.W)
        days_row = ttk.Frame(tab_storage)
        days_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(days_row, text=t("settings.hibernate_after")).pack(side=tk.LEFT)
        ttk.Spinbox(
            days_row,
            from_=1,
            to=3650,
            width=7,
            textvariable=storage_days,
        ).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Label(days_row, text=t("settings.hibernate_days")).pack(side=tk.LEFT)
        ttk.Label(
            tab_storage,
            text=t("settings.hibernate_note"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(14, 0))

        # --- allowlist tab (scrollable) ---
        tab_al_outer = ttk.Frame(nb)
        nb.add(tab_al_outer, text=t("settings.tab_allow"))
        _al_canvas, tab_al = _scrollable_panel(tab_al_outer, bg=self.BG, padding=10)
        al_en = tk.BooleanVar(value=s.allowlist.enabled)
        row = ttk.Frame(tab_al)
        row.pack(fill=tk.X)
        ttk.Checkbutton(row, text=t("settings.allow_use"), variable=al_en).pack(side=tk.LEFT)
        ttk.Button(
            row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo(t("settings.tab_allow"), t("help.manual_allow")),
        ).pack(side=tk.RIGHT)

        al_table = PackageSheet(
            tab_al,
            ui_font=self.ui_font,
            mono_font=self.mono_font,
            rows=6,
            on_help=self._open_version_help,
        )
        al_table.pack(fill=tk.X, pady=(6, 0))
        al_table.set_rules(s.allowlist.packages)

        al_mode = tk.StringVar(value=s.allowlist.mode)
        al_mode_row = ttk.Frame(tab_al)
        al_mode_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(al_mode_row, text=t("settings.mode_label")).pack(side=tk.LEFT)
        ttk.Combobox(
            al_mode_row, textvariable=al_mode, values=("warn", "block"), width=10, state="readonly"
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(
            al_mode_row,
            text=t("settings.save_note"),
            style="Hint.TLabel",
        ).pack(side=tk.LEFT, padx=(12, 0))

        xlsx_en = tk.BooleanVar(value=s.xlsx.enabled)
        xlsx_row = ttk.Frame(tab_al)
        xlsx_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Checkbutton(
            xlsx_row, text=t("settings.file_import"), variable=xlsx_en
        ).pack(side=tk.LEFT)
        ttk.Button(
            xlsx_row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo("Excel / CSV", t("help.xlsx")),
        ).pack(side=tk.RIGHT)
        url_row = ttk.Frame(tab_al)
        url_row.pack(fill=tk.X, pady=(4, 0))
        url_var = tk.StringVar(value=s.xlsx.url)
        ttk.Entry(url_row, textvariable=url_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse_list_file() -> None:
            picked = filedialog.askopenfilename(
                title=t("settings.file_pick_title"),
                filetypes=[
                    ("Excel / CSV", "*.xlsx *.csv *.txt"),
                    ("Excel", "*.xlsx"),
                    ("CSV", "*.csv *.txt"),
                    ("All", "*.*"),
                ],
                parent=win,
            )
            if picked:
                url_var.set(picked)

        ttk.Button(url_row, text=t("settings.browse"), command=browse_list_file).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # --- blocklist tab (scrollable) ---
        tab_bl_outer = ttk.Frame(nb)
        nb.add(tab_bl_outer, text=t("settings.tab_block"))
        _bl_canvas, tab_bl = _scrollable_panel(tab_bl_outer, bg=self.BG, padding=10)
        bl_en = tk.BooleanVar(value=s.blocklist.enabled)
        bl_row = ttk.Frame(tab_bl)
        bl_row.pack(fill=tk.X)
        ttk.Checkbutton(bl_row, text=t("settings.block_use"), variable=bl_en).pack(
            side=tk.LEFT
        )
        ttk.Button(
            bl_row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo(t("settings.tab_block"), t("help.block")),
        ).pack(side=tk.RIGHT)
        ttk.Label(
            tab_bl, text=t("help.block"), style="Hint.TLabel", wraplength=520, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(6, 4))
        bl_table = PackageSheet(
            tab_bl,
            ui_font=self.ui_font,
            mono_font=self.mono_font,
            rows=6,
            on_help=self._open_version_help,
        )
        bl_table.pack(fill=tk.X)
        bl_table.set_rules(s.blocklist.packages)
        ttk.Label(
            tab_bl,
            text=t("settings.save_note"),
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(6, 0))

        # --- proxy tab (scrollable) ---
        tab_px_outer = ttk.Frame(nb)
        nb.add(tab_px_outer, text=t("settings.tab_proxy"))
        _px_canvas, tab_px = _scrollable_panel(tab_px_outer, bg=self.BG, padding=12)
        proxy_en = tk.BooleanVar(value=s.proxy.enabled)
        px_row = ttk.Frame(tab_px)
        px_row.pack(fill=tk.X)
        ttk.Checkbutton(px_row, text=t("settings.tab_proxy"), variable=proxy_en).pack(side=tk.LEFT)
        ttk.Button(
            px_row,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo(t("settings.tab_proxy"), t("help.proxy")),
        ).pack(side=tk.RIGHT)
        http_var = tk.StringVar(value=s.proxy.http)
        https_var = tk.StringVar(value=s.proxy.https)
        nop_var = tk.StringVar(value=s.proxy.no_proxy)
        ttk.Label(tab_px, text="HTTP_PROXY", style="Hint.TLabel").pack(anchor=tk.W, pady=(12, 2))
        ttk.Entry(tab_px, textvariable=http_var).pack(fill=tk.X)
        ttk.Label(tab_px, text=t("settings.https_hint"), style="Hint.TLabel").pack(
            anchor=tk.W, pady=(8, 2)
        )
        ttk.Entry(tab_px, textvariable=https_var).pack(fill=tk.X)
        ttk.Label(tab_px, text="NO_PROXY", style="Hint.TLabel").pack(anchor=tk.W, pady=(8, 2))
        ttk.Entry(tab_px, textvariable=nop_var).pack(fill=tk.X)

        # --- catalog tab (scrollable) ---
        tab_cat_outer = ttk.Frame(nb)
        nb.add(tab_cat_outer, text=t("settings.tab_catalog"))
        _cat_canvas, tab_cat = _scrollable_panel(tab_cat_outer, bg=self.BG, padding=12)
        cat_hdr = ttk.Frame(tab_cat)
        cat_hdr.pack(fill=tk.X)
        ttk.Label(cat_hdr, text=t("settings.tab_catalog"), style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Button(
            cat_hdr,
            text=t("common.help_q"),
            width=3,
            command=lambda: messagebox.showinfo(t("settings.tab_catalog"), t("help.catalog"), parent=win),
        ).pack(side=tk.RIGHT)
        ttk.Label(
            tab_cat,
            text=t("settings.catalog_hint"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 8))

        catalog_paths: list[str] = [c.path for c in s.catalogs if c.path.strip()]
        cat_list = tk.Listbox(
            tab_cat,
            height=8,
            font=(self.ui_font, 10),
            relief=tk.FLAT,
            bg=self.CARD,
            fg=self.INK,
            highlightthickness=1,
            highlightbackground=self.CARD_BORDER,
            activestyle="none",
        )
        cat_list.pack(fill=tk.X)
        for p in catalog_paths:
            cat_list.insert(tk.END, p)

        cat_empty = tk.StringVar(
            value=t("settings.catalog_empty") if not catalog_paths else ""
        )

        def _sync_cat_empty() -> None:
            cat_empty.set(t("settings.catalog_empty") if not catalog_paths else "")

        cat_btns = ttk.Frame(tab_cat)
        cat_btns.pack(fill=tk.X, pady=(8, 0))

        def add_catalog() -> None:
            picked = filedialog.askopenfilename(
                title=t("settings.catalog_pick"),
                filetypes=[("JSON", "*.json"), ("All", "*.*")],
                parent=win,
            )
            if not picked:
                return
            if picked in catalog_paths:
                return
            catalog_paths.append(picked)
            cat_list.insert(tk.END, picked)
            _sync_cat_empty()

        def add_catalog_url() -> None:
            url = simpledialog.askstring(
                t("settings.tab_catalog"),
                t("settings.catalog_url_prompt"),
                parent=win,
            )
            if not url:
                return
            url = url.strip()
            if not url:
                return
            if url in catalog_paths:
                return
            catalog_paths.append(url)
            cat_list.insert(tk.END, url)
            _sync_cat_empty()

        def remove_catalog() -> None:
            sel = list(cat_list.curselection())
            if not sel:
                return
            # remove from bottom so indices stay valid
            for i in reversed(sel):
                catalog_paths.pop(i)
                cat_list.delete(i)
            _sync_cat_empty()

        ttk.Button(cat_btns, text=t("settings.catalog_add"), command=add_catalog).pack(side=tk.LEFT)
        ttk.Button(cat_btns, text=t("settings.catalog_add_url"), command=add_catalog_url).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(cat_btns, text=t("settings.catalog_remove"), command=remove_catalog).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Label(
            tab_cat,
            textvariable=cat_empty,
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 0))

        # --- language tab (scrollable) ---
        tab_lang_outer = ttk.Frame(nb)
        nb.add(tab_lang_outer, text=t("settings.tab_lang"))
        _lang_canvas, tab_lang = _scrollable_panel(tab_lang_outer, bg=self.BG, padding=12)
        ttk.Label(tab_lang, text=t("settings.lang_label"), style="Hint.TLabel").pack(anchor=tk.W)
        lang_choices = ("auto", LANG_JA, LANG_EN, LANG_ZH)
        lang_labels = [f"{code} — {language_label(code)}" for code in lang_choices]
        # Map display label back to code
        label_to_code = dict(zip(lang_labels, lang_choices, strict=True))
        current_label = next(
            (lab for lab, code in label_to_code.items() if code == (s.ui_language or "auto")),
            lang_labels[0],
        )
        lang_display = tk.StringVar(value=current_label)

        def _sync_lang(_event: object | None = None) -> None:
            lang_var.set(label_to_code.get(lang_display.get(), "auto"))

        lang_box = ttk.Combobox(
            tab_lang,
            textvariable=lang_display,
            values=lang_labels,
            state="readonly",
            width=36,
        )
        lang_box.pack(anchor=tk.W, pady=(8, 0))
        lang_box.bind("<<ComboboxSelected>>", _sync_lang)
        _sync_lang()
        ttk.Label(
            tab_lang,
            text=t("settings.lang_hint"),
            style="Hint.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(12, 0))


def run_app() -> None:
    app = UvdropApp()
    app.mainloop()
