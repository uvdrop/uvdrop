"""Allocate a free TCP port and expand ``{port}`` placeholders in launch commands."""
from __future__ import annotations

import re
import socket
from typing import Iterable

# {port} / {PORT} / {{port}} (double-brace escape not supported — keep simple)
_PORT_TOKEN = re.compile(r"\{port\}", re.IGNORECASE)

DEFAULT_PORT_BASE = 8000
DEFAULT_PORT_SPAN = 2000


def find_free_port(
    *,
    host: str = "127.0.0.1",
    start: int = DEFAULT_PORT_BASE,
    span: int = DEFAULT_PORT_SPAN,
) -> int:
    """Return an unused TCP port, preferring ``start`` then scanning upward."""
    last = start + max(1, span)
    for port in range(start, last):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    # Fall back to OS-assigned ephemeral
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def needs_port(command: str) -> bool:
    return bool(_PORT_TOKEN.search(command or ""))


def expand_port_placeholders(command: str, port: int | None = None) -> tuple[str, int | None]:
    """Replace ``{port}`` tokens. Returns ``(command, port_or_None)``.

    If there is no placeholder, returns the command unchanged and ``None``.
    """
    if not needs_port(command):
        return command, None
    chosen = find_free_port() if port is None else int(port)
    return _PORT_TOKEN.sub(str(chosen), command), chosen


def port_environ(port: int) -> dict[str, str]:
    """Env vars apps can read even without CLI flags."""
    value = str(port)
    return {
        "UVDROP_PORT": value,
        "PORT": value,
    }
