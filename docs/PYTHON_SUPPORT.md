# Python support window (EOL warnings)

uvdrop can warn when an app's `requires-python` points at a CPython release that is
**already past upstream end-of-support**, or **within one year** of that date
(default `eol_warn_days: 365`).

This is **separate from** the allow-list (`allowed` + `mode`). A version may be
allowed by policy and still show a support warning in the review dialog.

## Policy file

Copy `policies/python-versions.example.json` to
`%LOCALAPPDATA%\uvdrop\policies\python-versions.json` (seeded on first run).

```json
{
  "version": 1,
  "mode": "warn",
  "allowed": ["3.11", "3.12", "3.13"],
  "eol": {
    "3.10": "2026-10-31",
    "3.11": "2027-10-31"
  },
  "eol_warn_days": 365,
  "eol_mode": "warn"
}
```

| Field | Meaning |
|---|---|
| `allowed` / `mode` | Existing allow-list (`warn` \| `block`) |
| `eol` | Map of `X.Y` → ISO date of upstream EOS |
| `eol_warn_days` | Warn when remaining days ≤ this (default 365) |
| `eol_mode` | `warn` (default) or `block` only for **already EOL** |

Built-in dates ship in `uvdrop.python_support.DEFAULT_EOL` and are overridden by `eol`.

## Japanese

- サポート切れ → 警告（必要なら `eol_mode: block` で中止）
- サポート切れまで 1 年以内 → 警告（確認ダイアログに表示）
- パッケージ許可リストとは独立（両方出せる）
