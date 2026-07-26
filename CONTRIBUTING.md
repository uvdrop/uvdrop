# Contributing to uvdrop / 開発への参加

Thanks for your interest! uvdrop is a small, dependency-light Windows launcher
built on the Python standard library plus `uv`. Contributions that keep it
simple, safe, and easy for non-engineers to use are very welcome.

## 開発環境 / Setup

- Windows x64, Python 3.11+
- No runtime dependencies. Dev/test needs only `pytest`.

```powershell
git clone https://github.com/uvdrop/uvdrop.git
cd uvdrop
python -m pip install -e ".[dev]"
python -m uvdrop            # launch the GUI
```

## テスト / Tests

All logic is covered by `pytest`. Run it before opening a PR:

```powershell
python -m pytest
```

CI (`.github/workflows/ci.yml`) runs the same suite on Windows for every push
and pull request. Please add tests for any behavior you change, especially in:

- `policy.py` / `package_spec.py` (allow / block / version rules — safety critical)
- `resolve_deps.py` (dependency resolution + `--no-build`)
- `launcher.py` (ZIP-slip protection, launch flow)
- `i18n.py` (every user-facing string must exist in `ja` / `en` / `zh`)

## コード方針 / Guidelines

- **Standard library only** for runtime code. Do not add third-party runtime deps.
- **All user-facing text goes through `uvdrop.i18n.t(...)`** with `ja` / `en` / `zh`
  entries. Never hard-code UI strings in a module.
- Keep the safety guarantees intact: pre-run review, `uv lock --no-build` before
  confirmation, block-list precedence, and the conservative "block mode + could
  not resolve → refuse" rule. See [SECURITY.md](./SECURITY.md).
- Keep the UI friendly for non-engineers; prefer plain wording over jargon.
- Match the existing formatting (the project targets clean `ruff`-style code).

## バージョン管理 / Versioning

The single source of truth for the version is `src/uvdrop/version.py`. When you
bump it, also update:

- `pyproject.toml` (`project.version`)
- `installer/uvdrop.iss` (`MyAppVersion`) — build scripts override this, but keep
  it in sync for direct builds
- `installer/msix/AppxManifest.xml` (`Identity/@Version`)
- `CHANGELOG.md`
- The version strings in `README.md` and `docs/`

## プルリクエスト / Pull requests

1. Create a topic branch.
2. Add or update tests; run `python -m pytest`.
3. Update docs / `CHANGELOG.md` as needed.
4. Describe *why* the change is needed, not just *what* changed.

## 貢献者行動規範 / Conduct

Be respectful and constructive. Assume good intent, and keep discussions focused
on making uvdrop safer and easier to use.
