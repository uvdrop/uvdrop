"""Benchmark report helpers (no network or uv invocation)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "uvdrop_bench_samples",
    ROOT / "scripts" / "bench_samples.py",
)
assert SPEC is not None and SPEC.loader is not None
bench = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bench
SPEC.loader.exec_module(bench)


def _result(app_id: str, sync_s: float, total_s: float):
    result = bench.SampleResult(id=app_id, tier="light", name=app_id, ok=True)
    result.timing.sync_s = sync_s
    result.timing.total_s = total_s
    return result


def test_summary_calculates_nearest_rank_p90_and_speedup() -> None:
    summary = bench._summary(
        [_result("a", 1.0, 4.0), _result("b", 9.0, 6.0)],
        wall_s=5.0,
    )
    assert summary["sync_s_median"] == 5.0
    assert summary["sync_s_p90"] == 9.0
    assert summary["parallel_speedup"] == 2.0
    assert summary["slowest"][0]["id"] == "b"


def test_html_report_is_standalone_and_interactive() -> None:
    results = [_result("stdlib-hello", 0.2, 0.8)]
    payload = {
        "meta": {
            "started_at": "2026-01-01T00:00:00Z",
            "platform": "Windows",
            "python": "3.12",
            "uv": {"version": "uv 1"},
            "selection": "light",
            "workers": 2,
        },
        "summary": bench._summary(results, wall_s=0.8),
        "results": [
            {
                "id": results[0].id,
                "tier": results[0].tier,
                "name": results[0].name,
                "ok": True,
                "error": "",
                "stdout_tail": "uvdrop-sample-ok",
                "timing": {
                    "prepare_s": 0.1,
                    "sync_s": 0.2,
                    "run_s": 0.4,
                    "cleanup_s": 0.1,
                    "total_s": 0.8,
                },
            }
        ],
    }
    page = bench._html_report(payload)
    assert "<!doctype html>" in page
    assert "フェーズ別所要時間" in page
    assert 'id="chart"' in page
    assert "https://" not in page
