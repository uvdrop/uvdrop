"""Shared chrome for uvdrop local-portal samples (copied into each app folder).

Goals: maximized window by default, visible step flow, hard-to-get-lost status.
"""
from __future__ import annotations

from typing import Sequence


def maximize_tk(root) -> None:  # noqa: ANN001
    try:
        root.state("zoomed")
    except Exception:  # noqa: BLE001
        try:
            root.attributes("-zoomed", True)
        except Exception:  # noqa: BLE001
            root.geometry("1280x800")


def maximize_qt(window) -> None:  # noqa: ANN001
    try:
        window.showMaximized()
    except Exception:  # noqa: BLE001
        window.resize(1280, 800)


def format_steps(steps: Sequence[str], current: int) -> str:
    """1-based current index. Example: [1] → 2 → 3"""
    parts: list[str] = []
    for i, label in enumerate(steps, start=1):
        mark = f"[{i}]" if i == current else str(i)
        parts.append(f"{mark} {label}")
    return "  →  ".join(parts)


def qt_flow_stylesheet(*, bg: str = "#0B1020", ink: str = "#E8EEFF", muted: str = "#8FA0C0", accent: str = "#0D9488") -> str:
    return f"""
    QMainWindow, QWidget {{ background: {bg}; color: {ink}; }}
    QLabel#hero {{ font-size: 28px; font-weight: 800; color: {ink}; }}
    QLabel#sub {{ color: {muted}; font-size: 14px; }}
    QLabel#steps {{
        background: #151A2E; color: {accent}; border-radius: 12px;
        padding: 12px 16px; font-size: 13px; font-weight: 700;
    }}
    QLabel#status {{
        background: #151A2E; color: {ink}; border-radius: 12px;
        padding: 12px 16px; font-size: 14px;
    }}
    QPushButton {{
        background: {accent}; color: #042f2e; border: none; border-radius: 12px;
        padding: 12px 18px; font-size: 14px; font-weight: 800;
    }}
    QPushButton:hover {{ background: #14b8a6; }}
    QPushButton#ghost {{
        background: transparent; border: 1px solid #334155; color: {ink};
    }}
    """


def apply_tk_theme(root, *, bg: str = "#F0F3F7", ink: str = "#0F172A") -> None:  # noqa: ANN001
    import tkinter as tk
    from tkinter import ttk

    root.configure(bg=bg)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", background=bg, foreground=ink)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=ink)
    style.configure("TButton", padding=10)
    style.configure("Hero.TLabel", font=("Yu Gothic UI", 22, "bold"), background=bg, foreground=ink)
    style.configure("Sub.TLabel", font=("Yu Gothic UI", 11), background=bg, foreground="#64748B")
    style.configure("Steps.TLabel", font=("Yu Gothic UI", 11, "bold"), background="#E2E8F0", foreground="#0F766E")
    style.configure("Status.TLabel", font=("Yu Gothic UI", 11), background="#E2E8F0", foreground=ink)
    style.configure("Card.TFrame", background="#FFFFFF")
