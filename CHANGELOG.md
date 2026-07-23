# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- CI that builds Setup.exe on tagged releases
- Optional GuardDog deep scan
- Richer xlsx column mapping (Python versions sheet)

## [0.3.0] — 2026-07-23

### Added

- End-to-end Windows packaging scripts: `fetch-uv.ps1`, `build.ps1`, `sign.ps1`
- PyInstaller `uvdrop.spec` (onedir) for Inno payload
- Beginner-oriented Inno Setup guide: `installer/PACKAGING.md`
- Installed layout looks for `{app}\tools\uv.exe`

### Changed

- Version bump to 0.3.0; `.iss` version synced by `build.ps1`

## [0.2.0] — 2026-07-22

### Added

- Temporary run cleans up workspace / venv / dotenv after the process exits
- Startup GC for leftover temp apps
- Optional OSV.dev malicious-package check (`settings.json` → `osv.enabled`)
- Optional allowlist sync from a remote `.xlsx` URL
- GitHub Pages site (`docs/`) covering features, usage, and operations
- Inno Setup installer skeleton (`installer/uvdrop.iss`)
- Version shown prominently in the GUI title and header
- `CHANGELOG.md` and centralized `version.py`

### Changed

- Bump package version to 0.2.0

## [0.1.0] — 2026-07-22

### Added

- Initial offline uv launcher (Tk GUI + CLI)
- Folder / ZIP import → dedicated `.env` → `uv sync` / `uv run`
- Keep vs temp mode (temp cleanup landed in 0.2.0)
- Desktop shortcut creation (Windows)
- Local JSON policies for package allowlist and Python versions
- MIT license, example policies, basic tests

[Unreleased]: https://github.com/uvdrop/uvdrop/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/uvdrop/uvdrop/releases/tag/v0.3.0
[0.2.0]: https://github.com/uvdrop/uvdrop/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/uvdrop/uvdrop/releases/tag/v0.1.0
