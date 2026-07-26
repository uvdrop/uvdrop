"""Create a Windows desktop shortcut (.lnk) for a kept app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from uvdrop.paths import ensure_layout, launchers_dir, project_root


def desktop_dir() -> Path:
    user = Path.home() / "Desktop"
    if user.is_dir():
        return user
    od = Path.home() / "OneDrive" / "Desktop"
    if od.is_dir():
        return od
    return user


def _dev_src_path() -> Path | None:
    """If running from a source checkout, return …/src for PYTHONPATH."""
    root = project_root()
    src = root / "src"
    if (src / "uvdrop").is_dir():
        return src
    return None


def _launcher_cmd(app_key: str) -> Path:
    """Write a .cmd that relaunches the kept app (with logging on failure)."""
    ensure_layout()
    cmd_path = launchers_dir() / f"run-{app_key}.cmd"
    log_path = launchers_dir() / f"run-{app_key}.log"

    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # Packaged: uvdrop.exe --relaunch <key>
        body = (
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            f'set "LOG={log_path}"\r\n'
            f'"{exe}" --relaunch "{app_key}" >"%LOG%" 2>&1\r\n'
            "if errorlevel 1 (\r\n"
            "  echo uvdrop shortcut failed. See:\r\n"
            "  echo %LOG%\r\n"
            "  type \"%LOG%\"\r\n"
            "  pause\r\n"
            ")\r\n"
        )
    else:
        py = Path(sys.executable).resolve()
        src = _dev_src_path()
        lines = [
            "@echo off",
            "chcp 65001 >nul",
            f'set "LOG={log_path}"',
        ]
        if src is not None:
            lines.append(f'set "PYTHONPATH={src}"')
        lines.extend(
            [
                f'"{py}" -m uvdrop.relaunch "{app_key}" >"%LOG%" 2>&1',
                "if errorlevel 1 (",
                "  echo uvdrop shortcut failed. See:",
                "  echo %LOG%",
                '  type "%LOG%"',
                "  pause",
                ")",
            ]
        )
        body = "\r\n".join(lines) + "\r\n"

    cmd_path.write_text(body, encoding="utf-8")
    return cmd_path


def shortcut_path(app_key: str, display_name: str | None = None) -> Path:
    return desktop_dir() / f"{display_name or app_key}.lnk"


def create_desktop_shortcut(
    app_key: str,
    display_name: str | None = None,
    *,
    icon: Path | None = None,
) -> Path:
    if os.name != "nt":
        raise RuntimeError("Desktop shortcuts are only supported on Windows")

    cmd = _launcher_cmd(app_key)
    lnk = shortcut_path(app_key, display_name)

    import base64
    import subprocess

    def b64(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    def decode(text: str) -> str:
        return f"[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64(text)}'))"

    # WindowStyle 7 = minimized (hides the brief .cmd flash).
    # WindowStyle 1 = normal — use when console debug is on so failures are visible.
    from uvdrop.settings import load_settings

    window_style = 1 if load_settings().guard.show_console else 7
    lines = [
        "$ws = New-Object -ComObject WScript.Shell",
        f"$s = $ws.CreateShortcut({decode(str(lnk))})",
        f"$s.TargetPath = {decode(str(cmd))}",
        f"$s.WorkingDirectory = {decode(str(cmd.parent))}",
        f"$s.WindowStyle = {window_style}",
        f"$s.Description = {decode(f'uvdrop launch {app_key}')}",
    ]
    if icon is not None and icon.is_file():
        lines.append(f"$s.IconLocation = {decode(f'{icon},0')}")
    lines.append("$s.Save()")

    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "\n".join(lines)],
        check=True,
        capture_output=True,
        text=True,
    )
    return lnk
