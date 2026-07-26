"""HTTP helpers that honor uvdrop proxy settings."""

from __future__ import annotations

import urllib.request
from typing import Any

from uvdrop.settings import load_settings, proxy_environ


def urlopen(req: urllib.request.Request, *, timeout: float = 30) -> Any:
    proxy = proxy_environ(load_settings())
    if not proxy:
        return urllib.request.urlopen(req, timeout=timeout)
    handler = urllib.request.ProxyHandler(
        {
            "http": proxy.get("http_proxy") or proxy.get("HTTP_PROXY"),
            "https": proxy.get("https_proxy") or proxy.get("HTTPS_PROXY"),
        }
    )
    opener = urllib.request.build_opener(handler)
    return opener.open(req, timeout=timeout)
