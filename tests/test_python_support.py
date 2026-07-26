"""Python support-window (EOL) helpers."""

from __future__ import annotations

from datetime import date

from uvdrop.python_support import check_python_support, merge_eol_map


def test_eol_past_emits_eol_hit() -> None:
    hits = check_python_support(
        "3.9",
        eol_map=merge_eol_map(),
        today=date(2026, 7, 26),
        warn_days=365,
    )
    assert len(hits) == 1
    assert hits[0].kind == "eol"


def test_nearing_eol_within_warn_window() -> None:
    # 3.10 EOL 2026-10-31 → within 365 days of 2026-07-26
    hits = check_python_support(
        "3.10.12",
        eol_map=merge_eol_map(),
        today=date(2026, 7, 26),
        warn_days=365,
    )
    assert len(hits) == 1
    assert hits[0].kind == "nearing_eol"
    assert hits[0].days_remaining is not None
    assert 0 <= hits[0].days_remaining <= 365


def test_supported_far_from_eol_is_silent() -> None:
    hits = check_python_support(
        "3.13",
        eol_map=merge_eol_map(),
        today=date(2026, 7, 26),
        warn_days=365,
    )
    assert hits == []


def test_policy_wires_support_warnings(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout, policies_dir
    from uvdrop.policy import check_python_versions

    ensure_layout()
    (policies_dir() / "python-versions.json").write_text(
        '{"version":1,"mode":"warn","allowed":["3.10","3.11"],'
        '"eol":{"3.10":"2026-10-31"},"eol_warn_days":365,"eol_mode":"warn"}',
        encoding="utf-8",
    )
    hits = check_python_versions(">=3.10")
    kinds = {h.kind for h in hits}
    assert "python_support" in kinds
    assert all(not h.blocking for h in hits if h.kind == "python_support")
