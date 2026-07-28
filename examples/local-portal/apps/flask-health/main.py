"""Local portal sample — tiny Flask health app with a stay-open control window."""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from flask import Flask

HOST = "127.0.0.1"
PORT = 8760


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return (
            "<!doctype html><meta charset=utf-8>"
            "<title>Flask health</title>"
            "<body style='font-family:Segoe UI,sans-serif;padding:2rem'>"
            "<h1>Flask health</h1>"
            "<p>uvdrop portal sample is running.</p>"
            "<p><a href='/health'>/health</a></p>"
            "</body>"
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "flask-health"}

    return app


def main() -> int:
    app = create_app()
    url = f"http://{HOST}:{PORT}/"
    health_url = f"http://{HOST}:{PORT}/health"

    ready = threading.Event()
    error: list[BaseException] = []

    def run_server() -> None:
        try:
            ready.set()
            # use_reloader=False so we stay in one process (needed with Tk).
            app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)
            ready.set()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    ready.wait(timeout=5)
    if error:
        raise error[0]

    print("uvdrop-portal-ok flask-health", flush=True)
    print(f"Open in browser: {url}", flush=True)
    print(f"Health JSON: {health_url}", flush=True)

    root = tk.Tk()
    root.title("Flask health — サーバ起動中")
    root.geometry("420x200")
    root.minsize(360, 160)

    frm = ttk.Frame(root, padding=16)
    frm.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frm, text="Flask サーバが起動しています", font=("Yu Gothic UI", 12, "bold")).pack(
        anchor=tk.W
    )
    ttk.Label(frm, text="ブラウザで次の URL を開いてください:", wraplength=380).pack(
        anchor=tk.W, pady=(8, 4)
    )
    url_var = tk.StringVar(value=url)
    entry = ttk.Entry(frm, textvariable=url_var, width=48)
    entry.pack(fill=tk.X, pady=(0, 8))
    entry.selection_range(0, tk.END)

    def open_browser() -> None:
        webbrowser.open(url)

    def copy_url() -> None:
        root.clipboard_clear()
        root.clipboard_append(url)

    row = ttk.Frame(frm)
    row.pack(fill=tk.X, pady=(4, 0))
    ttk.Button(row, text="ブラウザで開く", command=open_browser).pack(side=tk.LEFT)
    ttk.Button(row, text="URL をコピー", command=copy_url).pack(side=tk.LEFT, padx=8)
    ttk.Button(row, text="終了（サーバ停止）", command=root.destroy).pack(side=tk.RIGHT)

    ttk.Label(
        frm,
        text="この窓を閉じるとサーバも止まります。コンソール表示は必須ではありません。",
        wraplength=380,
    ).pack(anchor=tk.W, pady=(12, 0))

    root.after(400, open_browser)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
