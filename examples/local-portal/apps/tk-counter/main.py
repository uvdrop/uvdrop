"""Local portal sample — tiny Tkinter GUI."""
from __future__ import annotations

import tkinter as tk


def main() -> int:
    root = tk.Tk()
    root.title("uvdrop portal — Tk Counter")
    root.geometry("280x140")
    count = tk.IntVar(value=0)

    tk.Label(root, text="Local portal demo").pack(pady=(16, 8))
    value = tk.Label(root, textvariable=count, font=("Segoe UI", 18))
    value.pack()

    def bump() -> None:
        count.set(count.get() + 1)

    tk.Button(root, text="+1", command=bump).pack(pady=12)
    print("uvdrop-portal-ok tk-counter", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
