"""Create a Windows desktop shortcut (.lnk) for a kept app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from uvdrop.paths import ensure_layout, launchers_dir


def desktop_dir() -> Path:
    user = Path.home() / "Desktop"
    if user.is_dir():
        return user
    # OneDrive Desktop fallback
    od = Path.home() / "OneDrive" / "Desktop"
    if od.is_dir():
        return od
    return user


def _launcher_cmd(app_key: str) -> Path:
    ensure_layout()
    cmd_path = launchers_dir() / f"run-{app_key}.cmd"
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # Packaged build: pass app key to CLI relaunch path
        body = f'@echo off\r\n"{exe}" --cli "{app_key}"\r\n'
    else:
        py = Path(sys.executable).resolve()
        body = "@echo off\r\n" f'"{py}" -m uvdrop.relaunch "{app_key}"\r\n'
    cmd_path.write_text(body, encoding="utf-8")
    return cmd_path


def create_desktop_shortcut(app_key: str, display_name: str | None = None) -> Path:
    if os.name != "nt":
        raise RuntimeError("Desktop shortcuts are only supported on Windows")

    cmd = _launcher_cmd(app_key)
    name = display_name or app_key
    lnk = desktop_dir() / f"{name}.lnk"

    # PowerShell + WScript.Shell; Base64 path to avoid encoding issues
    import base64
    import subprocess

    target = str(cmd)
    workdir = str(cmd.parent)
    lnk_s = str(lnk)
    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{base64.b64encode(lnk_s.encode("utf-8")).decode("ascii")}')))
$s.TargetPath = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{base64.b64encode(target.encode("utf-8")).decode("ascii")}'))
$s.WorkingDirectory = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{base64.b64encode(workdir.encode("utf-8")).decode("ascii")}'))
$s.WindowStyle = 7
$s.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
    )
    return lnk
