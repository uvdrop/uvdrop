"""Per-app launch history.

Stored as day buckets in usage.json so the file stays small no matter how
often an app is launched:

    {"version": 1, "apps": {"<key>": {"2026-07-26": 3}}}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from uvdrop.paths import ensure_layout, usage_path

Granularity = str  # "day" | "week" | "month"

DAY = "day"
WEEK = "week"
MONTH = "month"


@dataclass(frozen=True)
class Bucket:
    label: str
    count: int
    start: date
    # Per-app counts for stacked charts / hover tooltips: (app_key, count),
    # highest first. Empty when the bucket has no runs.
    parts: tuple[tuple[str, int], ...] = ()


def _today() -> date:
    return datetime.now().date()


def load_usage() -> dict[str, dict[str, int]]:
    path = usage_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    apps = raw.get("apps") if isinstance(raw, dict) else None
    if not isinstance(apps, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    for key, days in apps.items():
        if not isinstance(days, dict):
            continue
        clean: dict[str, int] = {}
        for day, count in days.items():
            try:
                date.fromisoformat(str(day))
            except ValueError:
                continue
            try:
                clean[str(day)] = int(count)
            except (TypeError, ValueError):
                continue
        if clean:
            out[str(key)] = clean
    return out


def save_usage(data: dict[str, dict[str, int]]) -> None:
    ensure_layout()
    payload = {"version": 1, "apps": data}
    usage_path().write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def record_run(key: str, when: date | None = None) -> None:
    if not key:
        return
    day = (when or _today()).isoformat()
    data = load_usage()
    days = data.setdefault(key, {})
    days[day] = int(days.get(day, 0)) + 1
    save_usage(data)


def drop_app(key: str) -> None:
    data = load_usage()
    if key in data:
        del data[key]
        save_usage(data)


def total_runs(key: str) -> int:
    return sum(load_usage().get(key, {}).values())


def _daily_parts(
    data: dict[str, dict[str, int]], key: str | None
) -> dict[str, dict[date, int]]:
    """Per-app day→count maps. When `key` is set, only that app is included."""
    out: dict[str, dict[date, int]] = {}
    items = [(key, data.get(key, {}))] if key else list(data.items())
    for app_key, days in items:
        if not app_key:
            continue
        clean: dict[date, int] = {}
        for day, count in days.items():
            try:
                d = date.fromisoformat(day)
            except ValueError:
                continue
            clean[d] = clean.get(d, 0) + int(count)
        if clean:
            out[str(app_key)] = clean
    return out


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def buckets(
    key: str | None,
    granularity: Granularity = DAY,
    *,
    periods: int = 30,
    today: date | None = None,
    data: dict[str, dict[str, int]] | None = None,
) -> list[Bucket]:
    """Contiguous buckets ending at today, oldest first (zero-filled).

    Each bucket also carries ``parts`` — per-app counts in that period — so the
    UI can draw a stacked bar and show a hover breakdown when viewing all apps.
    """
    raw = load_usage() if data is None else data
    per_app = _daily_parts(raw, key)
    end = today or _today()
    periods = max(1, periods)

    starts: list[date] = []
    if granularity == MONTH:
        cursor = _month_start(end)
        for _ in range(periods):
            starts.append(cursor)
            cursor = (
                date(cursor.year - 1, 12, 1)
                if cursor.month == 1
                else date(cursor.year, cursor.month - 1, 1)
            )
    elif granularity == WEEK:
        cursor = _week_start(end)
        for _ in range(periods):
            starts.append(cursor)
            cursor = cursor - timedelta(days=7)
    else:
        cursor = end
        for _ in range(periods):
            starts.append(cursor)
            cursor = cursor - timedelta(days=1)
    starts.reverse()

    def bucket_end(start: date) -> date:
        if granularity == MONTH:
            return _add_month(start) - timedelta(days=1)
        if granularity == WEEK:
            return start + timedelta(days=6)
        return start

    out: list[Bucket] = []
    for start in starts:
        stop = bucket_end(start)
        by_app: dict[str, int] = {}
        for app_key, days in per_app.items():
            n = sum(c for d, c in days.items() if start <= d <= stop)
            if n:
                by_app[app_key] = n
        parts = tuple(sorted(by_app.items(), key=lambda kv: (-kv[1], kv[0])))
        count = sum(by_app.values())
        if granularity == MONTH:
            label = start.strftime("%Y-%m")
        elif granularity == WEEK:
            label = start.strftime("%m/%d~")
        else:
            label = start.strftime("%m/%d")
        out.append(Bucket(label=label, count=count, start=start, parts=parts))
    return out
