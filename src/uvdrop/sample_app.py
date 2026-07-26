"""Generate sample apps for first-run learning."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

SAMPLES: dict[str, "SampleSpec"] = {}


@dataclass(frozen=True)
class SampleSpec:
    id: str
    title: str
    folder_name: str
    blurb: str
    pyproject: str
    main_py: str
    readme: str
    manifest: str


def _register(spec: SampleSpec) -> SampleSpec:
    SAMPLES[spec.id] = spec
    return spec


SAMPLE_1 = _register(
    SampleSpec(
        id="1",
        title="サンプル1: Tk のみ（追加パッケージなし）",
        folder_name="hello-uvdrop",
        blurb="stdlib の tkinter だけ。ただし uv が Python 自体を用意することはあります。",
        pyproject="""\
[project]
name = "hello-uvdrop"
version = "0.1.0"
description = "Minimal Tk sample for uvdrop (no PyPI deps)"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
hello-uvdrop = "main:main"
""",
        main_py=r'''\
"""Minimal Tk welcome screen — no third-party packages."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def main() -> None:
    root = tk.Tk()
    root.title("hello-uvdrop")
    root.geometry("520x340")
    root.minsize(480, 300)
    root.configure(bg="#0f1f1a")

    shell = tk.Frame(root, bg="#0f1f1a", padx=28, pady=28)
    shell.pack(fill=tk.BOTH, expand=True)
    card = tk.Frame(shell, bg="#f4f7f4")
    card.pack(fill=tk.BOTH, expand=True)
    inner = tk.Frame(card, bg="#f4f7f4", padx=28, pady=28)
    inner.pack(fill=tk.BOTH, expand=True)

    tk.Label(inner, text="uvdrop", font=("Segoe UI", 28, "bold"), fg="#0b6e4f", bg="#f4f7f4").pack(
        anchor=tk.W
    )
    tk.Label(inner, text="Sample 1 — stdlib only", font=("Segoe UI", 13), fg="#5a6b63", bg="#f4f7f4").pack(
        anchor=tk.W, pady=(4, 0)
    )
    tk.Label(
        inner,
        text="起動成功です。PyPI パッケージは入れていません。\n（uv が Python ランタイムを用意する場合はあります）",
        font=("Segoe UI", 11),
        fg="#24302b",
        bg="#f4f7f4",
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(18, 0))
    ttk.Button(inner, text="閉じる", command=root.destroy).pack(anchor=tk.W, pady=(22, 0))
    root.mainloop()


if __name__ == "__main__":
    main()
''',
        readme="""\
# hello-uvdrop（サンプル1）

追加の PyPI 依存はありません。`pyproject.toml` + `main.py` の最小例です。
""",
        manifest='{\n  "entry": { "file": "main.py" }\n}\n',
    )
)

SAMPLE_2 = _register(
    SampleSpec(
        id="2",
        title="サンプル2: httpx を install（軽量・有名）",
        folder_name="hello-httpx",
        blurb="有名で軽い httpx を uv sync で入れ、バージョンを Tk に表示します。",
        pyproject="""\
[project]
name = "hello-httpx"
version = "0.1.0"
description = "uvdrop sample that installs httpx"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
]

[project.scripts]
hello-httpx = "main:main"
""",
        main_py=r'''\
"""Tk sample that uses httpx (installed via uv sync)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import httpx


def main() -> None:
    root = tk.Tk()
    root.title("hello-httpx")
    root.geometry("540x360")
    root.minsize(500, 320)
    root.configure(bg="#101820")

    shell = tk.Frame(root, bg="#101820", padx=28, pady=28)
    shell.pack(fill=tk.BOTH, expand=True)
    card = tk.Frame(shell, bg="#f7f3ea")
    card.pack(fill=tk.BOTH, expand=True)
    inner = tk.Frame(card, bg="#f7f3ea", padx=28, pady=28)
    inner.pack(fill=tk.BOTH, expand=True)

    tk.Label(inner, text="uvdrop", font=("Segoe UI", 26, "bold"), fg="#0b6e4f", bg="#f7f3ea").pack(
        anchor=tk.W
    )
    tk.Label(
        inner, text="Sample 2 — httpx installed", font=("Segoe UI", 13), fg="#6a5f4b", bg="#f7f3ea"
    ).pack(anchor=tk.W, pady=(4, 0))

    status = tk.StringVar(value="httpx で example.com に HEAD しています…")
    tk.Label(inner, textvariable=status, font=("Segoe UI", 11), fg="#24302b", bg="#f7f3ea", justify=tk.LEFT).pack(
        anchor=tk.W, pady=(18, 0)
    )

    meta = tk.Label(
        inner,
        text=f"httpx {httpx.__version__}",
        font=("Consolas", 10),
        fg="#0b6e4f",
        bg="#f7f3ea",
    )
    meta.pack(anchor=tk.W, pady=(12, 0))

    def ping() -> None:
        try:
            r = httpx.head("https://example.com", timeout=10.0, follow_redirects=True)
            status.set(f"OK — HTTP {r.status_code} from example.com\n（httpx が仮想環境に入っています）")
        except Exception as e:  # noqa: BLE001
            status.set(f"通信エラー（プロキシ設定を確認）:\n{e}")

    root.after(200, ping)
    ttk.Button(inner, text="閉じる", command=root.destroy).pack(anchor=tk.W, pady=(22, 0))
    root.mainloop()


if __name__ == "__main__":
    main()
''',
        readme="""\
# hello-httpx（サンプル2）

`httpx` を dependencies に含みます。uvdrop 起動時の `uv sync` でインストールされます。
""",
        manifest='{\n  "entry": { "file": "main.py" }\n}\n',
    )
)


def list_samples() -> list[SampleSpec]:
    return [SAMPLES["1"], SAMPLES["2"]]


def write_sample_tree(dest: Path, sample_id: str = "1") -> Path:
    spec = SAMPLES[sample_id]
    root = dest / spec.folder_name
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(spec.pyproject, encoding="utf-8")
    (root / "main.py").write_text(spec.main_py, encoding="utf-8")
    (root / "README.md").write_text(spec.readme, encoding="utf-8")
    (root / "uvdrop.manifest.json").write_text(spec.manifest, encoding="utf-8")
    return root


def write_sample_zip(zip_path: Path, sample_id: str = "1") -> Path:
    parent = zip_path.parent
    root = write_sample_tree(parent, sample_id=sample_id)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(parent)).replace("\\", "/"))
    return zip_path


# Back-compat names
SAMPLE_NAME = SAMPLE_1.folder_name
