"""Version rule and declared-dep parsing."""

from __future__ import annotations

from uvdrop.package_spec import (
    PackageRule,
    parse_declared_dep,
    parse_pasted_table,
    rule_allows,
    rule_blocks,
    version_matches,
)


def test_parse_declared_exact_and_open() -> None:
    exact = parse_declared_dep("httpx==0.27.2")
    assert exact is not None
    assert exact.name == "httpx"
    assert exact.version == "0.27.2"

    open_ = parse_declared_dep("httpx>=0.27")
    assert open_ is not None
    assert open_.name == "httpx"
    assert open_.version is None
    assert open_.has_constraint

    bare = parse_declared_dep("rich")
    assert bare is not None and bare.version is None and not bare.has_constraint


def test_wildcard_and_comparison() -> None:
    assert version_matches("1.*", "1.2.3")
    assert version_matches("1.*.*", "1.9.0")
    assert not version_matches("1.*", "2.0.0")
    assert version_matches(">=1.0,<2", "1.5.0")
    assert not version_matches(">=1.0,<2", "2.0.0")
    assert version_matches("*", "9.9.9")
    assert version_matches("2.31.0", "2.31.0")


def test_rule_allows_notes_open_pin() -> None:
    dep = parse_declared_dep("httpx>=0.27")
    assert dep is not None
    ok, note = rule_allows(PackageRule("httpx", "0.27.*"), dep)
    assert ok
    assert "名前のみ" in note


def test_rule_blocks_name() -> None:
    dep = parse_declared_dep("evil-pkg")
    assert dep is not None
    assert rule_blocks(PackageRule("evil-pkg", "*"), dep)
    assert not rule_blocks(PackageRule("other", "*"), dep)


def test_paste_from_excel_tsv() -> None:
    text = "パッケージ名\tバージョン\r\nhttpx\t0.27.*\r\nrich\t\r\n\r\nnumpy\t>=1.26,<2\r\n"
    assert parse_pasted_table(text) == [
        ("httpx", "0.27.*"),
        ("rich", ""),
        ("numpy", ">=1.26,<2"),
    ]


def test_paste_csv_and_space_forms() -> None:
    assert parse_pasted_table('httpx,"0.27.*"\nrich,*') == [("httpx", "0.27.*"), ("rich", "*")]
    assert parse_pasted_table("httpx 0.27.*\nrich") == [("httpx", "0.27.*"), ("rich", "")]


def test_package_sheet_grows_for_large_paste() -> None:
    import tkinter as tk

    from uvdrop.ui.package_table import PackageSheet

    root = tk.Tk()
    root.withdraw()
    try:
        sheet = PackageSheet(root, rows=4)
        sheet.pack()
        blob = "\n".join(f"pkg{i}\t1.*" for i in range(1000))
        sheet.paste_text(blob)
        rules = sheet.get_rules()
        assert len(rules) == 1000
        assert rules[0].name == "pkg0"
        assert rules[-1].name == "pkg999"
        assert rules[-1].version == "1.*"
    finally:
        root.destroy()
