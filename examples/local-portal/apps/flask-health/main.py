"""Local portal sample — Flask smoke (no blocking server)."""
from __future__ import annotations

from flask import Flask


def main() -> int:
    app = Flask(__name__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    client = app.test_client()
    res = client.get("/health")
    print("uvdrop-portal-ok flask-health", flush=True)
    print(f"status={res.status_code} body={res.get_json()}", flush=True)
    return 0 if res.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
