"""Launch history buckets."""

from __future__ import annotations

from datetime import date

from uvdrop.usage import DAY, MONTH, WEEK, buckets


SAMPLE = {
    "app-a": {"2026-07-26": 3, "2026-07-25": 1, "2026-06-30": 5},
    "app-b": {"2026-07-26": 2},
}


def test_daily_buckets_are_zero_filled_and_ordered() -> None:
    out = buckets("app-a", DAY, periods=3, today=date(2026, 7, 26), data=SAMPLE)
    assert [b.count for b in out] == [0, 1, 3]
    assert out[-1].start == date(2026, 7, 26)


def test_all_apps_are_summed() -> None:
    out = buckets(None, DAY, periods=1, today=date(2026, 7, 26), data=SAMPLE)
    assert out[0].count == 5


def test_all_apps_bucket_carries_per_app_parts() -> None:
    out = buckets(None, DAY, periods=1, today=date(2026, 7, 26), data=SAMPLE)
    assert out[0].parts == (("app-a", 3), ("app-b", 2))


def test_single_app_parts_list_only_that_app() -> None:
    out = buckets("app-a", DAY, periods=1, today=date(2026, 7, 26), data=SAMPLE)
    assert out[0].parts == (("app-a", 3),)


def test_weekly_bucket_covers_its_week() -> None:
    out = buckets("app-a", WEEK, periods=1, today=date(2026, 7, 26), data=SAMPLE)
    # 2026-07-26 is a Sunday, so its week starts 2026-07-20 and includes 07-25/07-26
    assert out[0].start == date(2026, 7, 20)
    assert out[0].count == 4


def test_monthly_buckets_split_by_month() -> None:
    out = buckets("app-a", MONTH, periods=2, today=date(2026, 7, 26), data=SAMPLE)
    assert [b.label for b in out] == ["2026-06", "2026-07"]
    assert [b.count for b in out] == [5, 4]
