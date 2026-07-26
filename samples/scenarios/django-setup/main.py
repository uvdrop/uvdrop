"""uvdrop scenario sample — import / tiny smoke, then exit."""
from __future__ import annotations


def main() -> int:

    import django  # noqa: F401
    import django
    from django.conf import settings
    if not settings.configured:
        settings.configure(DEBUG=True, SECRET_KEY='uvdrop-bench', USE_TZ=True)
        django.setup()
    
    print("uvdrop-sample-ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
