"""Version rule validation, explanation, and unresolvable-notation reporting."""

from __future__ import annotations

from uvdrop.i18n import set_language
from uvdrop.package_spec import (
    PackageRule,
    describe_rule,
    match_uncertainty,
    parse_declared_dep,
    validate_rule,
    version_notation_note,
    version_rule_guide,
)


def test_wildcard_rules_are_accepted() -> None:
    for rule in ("", "*", "2.*", "2.*.*", "0.0.*", "1.2.*", "2.31.0", ">=1.0", ">=1.0,<2"):
        assert validate_rule(rule).ok, rule


def test_unsupported_notations_are_rejected_with_reason() -> None:
    for rule in ("~=1.4", "===1.0", "==1.*", "v1.2", "1.x", ">=abc"):
        check = validate_rule(rule)
        assert not check.ok, rule
        assert check.message


def test_describe_rule_reads_in_plain_japanese() -> None:
    assert describe_rule("*") == "全バージョンOK"
    assert describe_rule("") == "全バージョンOK"
    assert "2." in describe_rule("2.*")
    assert "0.0." in describe_rule("0.0.*")
    assert "完全一致" in describe_rule("2.31.0")
    assert "かつ" in describe_rule(">=1.0,<2")


def test_version_notation_note_flags_pypi_specific_forms() -> None:
    assert version_notation_note("2.31.0") is None
    assert version_notation_note("1.0") is None
    assert version_notation_note("2.0.0rc1")
    assert version_notation_note("1.0.post1")
    assert version_notation_note("1.0.dev0")
    assert version_notation_note("1.0+cu118")
    assert version_notation_note("1!2.0")


def test_match_uncertainty_reports_but_does_not_block() -> None:
    dep = parse_declared_dep("torch==2.1.0+cu118")
    assert dep is not None
    note = match_uncertainty(PackageRule("torch", "2.*"), dep)
    assert note is not None and "torch" in note

    # name-only rules never need a note
    assert match_uncertainty(PackageRule("torch", "*"), dep) is None

    clean = parse_declared_dep("httpx==0.27.2")
    assert clean is not None
    assert match_uncertainty(PackageRule("httpx", "0.27.*"), clean) is None


def test_unusable_rule_is_reported_against_any_dep() -> None:
    dep = parse_declared_dep("httpx==0.27.2")
    assert dep is not None
    note = match_uncertainty(PackageRule("httpx", "~=0.27"), dep)
    assert note is not None and "~=" in note


def test_rule_messages_localize() -> None:
    """Safety-critical version messages must exist in every language."""
    set_language("en")
    assert describe_rule("*") == "any version is allowed"
    assert "supported" in validate_rule("~=1.4").message.lower()
    guide_en = version_rule_guide()
    assert "basics" in guide_en.lower()

    set_language("zh")
    assert describe_rule("*") == "允许任意版本"
    guide_zh = version_rule_guide()
    assert "版本" in guide_zh

    set_language("ja")
    assert describe_rule("*") == "全バージョンOK"
