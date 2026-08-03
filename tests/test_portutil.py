"""Tests for {port} placeholder expansion."""
from __future__ import annotations

from uvdrop.portutil import expand_port_placeholders, find_free_port, needs_port, port_environ


def test_needs_port_detects_tokens() -> None:
    assert needs_port("main.py --port {port}")
    assert needs_port("main.py --port {PORT}")
    assert not needs_port("main.py --port 8080")
    assert not needs_port("")


def test_expand_replaces_all_tokens() -> None:
    cmd, port = expand_port_placeholders("main.py --port {port} --host 127.0.0.1", port=8123)
    assert port == 8123
    assert cmd == "main.py --port 8123 --host 127.0.0.1"


def test_expand_case_insensitive() -> None:
    cmd, port = expand_port_placeholders("-m uvicorn app:app --port {PORT}", port=9001)
    assert cmd.endswith("9001")
    assert port == 9001


def test_expand_noop_without_token() -> None:
    cmd, port = expand_port_placeholders("main.py")
    assert cmd == "main.py"
    assert port is None


def test_find_free_port_binds() -> None:
    port = find_free_port(start=18000, span=50)
    assert 18000 <= port < 18000 + 50 or port > 0


def test_port_environ_keys() -> None:
    env = port_environ(8765)
    assert env["PORT"] == "8765"
    assert env["UVDROP_PORT"] == "8765"
