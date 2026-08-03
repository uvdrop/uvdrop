"""Flask health — guided full-screen control window + auto port."""
from __future__ import annotations

import argparse
import os
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from flask import Flask

from ui_shell import apply_tk_theme, format_steps, maximize_tk

HOST = "127.0.0.1"
STEPS = ("サーバ起動", "ブラウザで開く", " /health を確認", "窓を閉じて停止")


def resolve_port(cli_port: int | None) -> int:
    if cli_port is not None and cli_port > 0:
        return cli_port
    for key in ("UVDROP_PORT", "PORT"):
        raw = (os.environ.get(key) or "").strip()
        if raw.isdigit():
            return int(raw)
    return 8760


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return (
            "<!doctype html><meta charset=utf-8>"
            "<title>Flask health</title>"
            "<body style='font-family:Yu Gothic UI,Segoe UI,sans-serif;margin:0;"
            "min-height:100vh;background:linear-gradient(160deg,#0B1020,#1A2744);"
            "color:#E8EEFF;display:grid;place-items:center'>"
            "<main style='max-width:32rem;padding:2.5rem;background:#151A2E;"
            "border-radius:1.5rem'>"
            "<p style='color:#6BCB77;letter-spacing:.12em;margin:0'>STEP 2/4</p>"
            "<h1 style='margin:.5rem 0 1rem'>Flask health</h1>"
            "<p style='color:#8FA0C0;line-height:1.7'>uvdrop から起動した Web サンプルです。"
            "ポートは <code>{port}</code> で自動割当できます。</p>"
            "<p><a href='/health' style='color:#4D96FF;font-size:1.1rem'>→ /health を開く（STEP 3）</a></p>"
            "</main></body>"
        )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "app": "flask-health", "hint": "この JSON が見えれば成功"}

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)
    port = resolve_port(args.port)
    url = f"http://{HOST}:{port}/"
    health_url = f"http://{HOST}:{port}/health"

    ready = threading.Event()
    error: list[BaseException] = []
    app = create_app()

    def run_server() -> None:
        try:
            ready.set()
            app.run(host=HOST, port=port, debug=False, use_reloader=False, threaded=True)
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)
            ready.set()

    threading.Thread(target=run_server, daemon=True).start()
    ready.wait(timeout=5)
    if error:
        raise error[0]

    print("uvdrop-portal-ok flask-health", flush=True)
    print(f"UVDROP_URL={url}", flush=True)

    root = tk.Tk()
    root.title("Flask health — 制御窓（閉じるとサーバ停止）")
    apply_tk_theme(root, bg="#0B1020", ink="#E8EEFF")
    maximize_tk(root)

    steps = tk.StringVar(value=format_steps(STEPS, 1))
    status = tk.StringVar(value=f"サーバ起動済み  ポート {port}  — 次はブラウザで開いてください。")

    outer = ttk.Frame(root, padding=28)
    outer.pack(fill=tk.BOTH, expand=True)
    ttk.Label(outer, text="Flask health", style="Hero.TLabel").pack(anchor=tk.W)
    ttk.Label(
        outer,
        text="Web アプリをデスクトップから配る実演。この制御窓がプロセスの寿命です（閉じると停止）。",
        style="Sub.TLabel",
        wraplength=1000,
    ).pack(anchor=tk.W, pady=(6, 12))
    ttk.Label(outer, textvariable=steps, style="Steps.TLabel").pack(fill=tk.X, pady=(0, 10))
    ttk.Label(outer, textvariable=status, style="Status.TLabel", wraplength=1000).pack(fill=tk.X)

    card = ttk.Frame(outer, style="Card.TFrame", padding=24)
    card.pack(fill=tk.BOTH, expand=True, pady=16)
    tk.Label(card, text="いまの URL", bg="#FFFFFF", fg="#64748B", font=("Yu Gothic UI", 11)).pack(anchor=tk.W)
    url_var = tk.StringVar(value=url)
    entry = ttk.Entry(card, textvariable=url_var, font=("Cascadia Mono", 14))
    entry.pack(fill=tk.X, pady=(6, 14))
    tk.Label(
        card,
        text="流れ: ブラウザでトップ → /health の JSON → 戻ってこの窓を閉じる",
        bg="#FFFFFF",
        fg="#0F172A",
        font=("Yu Gothic UI", 12),
        justify=tk.LEFT,
    ).pack(anchor=tk.W)

    def open_browser() -> None:
        webbrowser.open(url)
        steps.set(format_steps(STEPS, 2))
        status.set("ブラウザを開きました。ページ内の /health リンクへ進んでください（STEP 3）。")

    def open_health() -> None:
        webbrowser.open(health_url)
        steps.set(format_steps(STEPS, 3))
        status.set(" /health を開きました。{\"status\":\"ok\"} が見えれば成功。終わったら窓を閉じて停止。")

    def copy_url() -> None:
        root.clipboard_clear()
        root.clipboard_append(url)
        status.set("URL をコピーしました。")

    row = ttk.Frame(outer)
    row.pack(fill=tk.X)
    ttk.Button(row, text="1. ブラウザで開く", command=open_browser).pack(side=tk.LEFT)
    ttk.Button(row, text="2. /health を開く", command=open_health).pack(side=tk.LEFT, padx=8)
    ttk.Button(row, text="URL をコピー", command=copy_url).pack(side=tk.LEFT)
    ttk.Button(row, text="終了（サーバ停止）", command=root.destroy).pack(side=tk.RIGHT)

    root.after(500, open_browser)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
