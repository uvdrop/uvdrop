"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import gradio  # noqa: F401
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
