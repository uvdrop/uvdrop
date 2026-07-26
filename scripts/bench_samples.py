"""Benchmark uvdrop: prepare → uv sync (venv) → run → discard, with reports.

Examples:
  python scripts/bench_samples.py --tier light
  python scripts/bench_samples.py --tier light,medium --workers 3
  python scripts/bench_samples.py --ids stdlib-hello,flask-app

Reports land under ``reports/bench/`` (standalone HTML + JSON). All workspaces,
virtual environments, dotenv files, and the run-local uv cache are deleted.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass
class PhaseTiming:
    prepare_s: float | None = None
    sync_s: float | None = None
    run_s: float | None = None
    cleanup_s: float | None = None
    total_s: float | None = None


@dataclass
class SampleResult:
    id: str
    tier: str
    name: str
    ok: bool
    error: str = ""
    timing: PhaseTiming = field(default_factory=PhaseTiming)
    policy_warnings: list[str] = field(default_factory=list)
    policy_errors: list[str] = field(default_factory=list)
    app_key: str = ""
    stdout_tail: str = ""


def _load_index() -> list[dict]:
    gen = ROOT / "samples" / "generate_samples.py"
    # ensure trees exist
    subprocess.run([sys.executable, str(gen)], check=True, cwd=str(ROOT))
    data = json.loads((ROOT / "samples" / "index.json").read_text(encoding="utf-8"))
    return list(data.get("samples") or [])


def _configure_isolated_appdata(base: Path) -> Path:
    la = base / "LocalAppData"
    la.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(la)
    # Fresh import path after env set
    from uvdrop.paths import ensure_layout
    from uvdrop.settings import Settings, save_settings

    ensure_layout()
    s = Settings()
    s.guard.confirm_before_run = False
    s.guard.no_allowlist = "allow"
    s.allowlist.enabled = False
    s.blocklist.enabled = False
    save_settings(s)
    return la


def _discard_artifacts(app_key: str) -> None:
    """Delete benchmark artifacts without touching the shared app registry."""
    from uvdrop.paths import apps_dir, dotenv_dir, envs_dir

    for path in (apps_dir() / app_key, envs_dir() / app_key, dotenv_dir() / app_key):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def _run_one(spec: dict, *, run_timeout: float) -> SampleResult:
    from uvdrop.launcher import prepare_launch
    from uvdrop.project import parse_entry
    from uvdrop.settings import load_settings, proxy_environ
    from uvdrop.uv_tool import resolve_uv, sync_project

    sample_dir = ROOT / "samples" / "scenarios" / spec["id"]
    result = SampleResult(
        id=spec["id"],
        tier=spec.get("tier", ""),
        name=spec.get("name", spec["id"]),
        ok=False,
    )
    platforms = spec.get("platforms") or ["any"]
    if "any" not in platforms and sys.platform not in platforms:
        result.ok = True
        result.error = f"skipped (platform {sys.platform} not in {platforms})"
        result.timing.total_s = 0.0
        return result

    t0 = time.perf_counter()
    try:
        t_prep = time.perf_counter()
        prep = prepare_launch(sample_dir, app_key=f"bench-{spec['id']}")
        result.timing.prepare_s = time.perf_counter() - t_prep
        result.app_key = prep.app_key
        result.policy_warnings = list(prep.policy.warnings)
        result.policy_errors = list(prep.policy.errors)
        if prep.policy.blocking:
            raise RuntimeError("policy blocked:\n" + "\n".join(prep.policy.errors))

        t_sync = time.perf_counter()
        sync_project(prep.project_dir, prep.venv_dir)
        result.timing.sync_s = time.perf_counter() - t_sync

        t_run = time.perf_counter()
        entry = parse_entry(prep.entry_command or "main.py", prep.project_dir, prep.workspace)
        uv = resolve_uv()
        env = os.environ.copy()
        env.update(proxy_environ(load_settings()))
        env["UV_PROJECT_ENVIRONMENT"] = str(prep.venv_dir)
        cmd = [str(uv), "run", "--directory", str(prep.project_dir), "python", *entry]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        proc = subprocess.Popen(
            cmd,
            cwd=str(prep.project_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
        )
        try:
            stdout, stderr = proc.communicate(timeout=run_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise TimeoutError(f"run exceeded {run_timeout}s") from None
        result.timing.run_s = time.perf_counter() - t_run
        out = (stdout or b"").decode("utf-8", errors="replace")
        err = (stderr or b"").decode("utf-8", errors="replace")
        result.stdout_tail = (out + ("\n" + err if err else ""))[-800:]
        if proc.returncode != 0:
            raise RuntimeError(f"exit {proc.returncode}\n{result.stdout_tail}")
        if "uvdrop-sample-ok" not in out:
            raise RuntimeError("missing uvdrop-sample-ok marker\n" + result.stdout_tail)

        result.ok = True
    except Exception as e:  # noqa: BLE001
        result.error = f"{e}\n{traceback.format_exc()[-800:]}"
    finally:
        if result.app_key:
            t_clean = time.perf_counter()
            _discard_artifacts(result.app_key)
            result.timing.cleanup_s = time.perf_counter() - t_clean
    result.timing.total_s = time.perf_counter() - t0
    return result


def _uv_info() -> dict:
    try:
        from uvdrop.uv_tool import resolve_uv_info

        info = resolve_uv_info()
        return {"path": str(info.path), "source": info.source, "version": info.version}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def _summary(results: list[SampleResult], wall_s: float) -> dict:
    completed = [r for r in results if r.ok and not r.error.startswith("skipped")]
    sync_values = [r.timing.sync_s for r in completed if r.timing.sync_s is not None]
    total_values = [r.timing.total_s for r in completed if r.timing.total_s is not None]
    slowest = sorted(
        completed,
        key=lambda r: r.timing.total_s or 0,
        reverse=True,
    )[:5]
    sequential_s = sum(total_values)
    return {
        "total": len(results),
        "ok": len(completed),
        "failed": sum(1 for r in results if not r.ok),
        "skipped": sum(1 for r in results if r.error.startswith("skipped")),
        "wall_s": round(wall_s, 3),
        "sync_s_sum": round(sum(sync_values), 3),
        "total_s_sum": round(sequential_s, 3),
        "sync_s_median": round(statistics.median(sync_values), 3) if sync_values else None,
        "sync_s_p90": round(
            sorted(sync_values)[max(0, math.ceil(len(sync_values) * 0.9) - 1)], 3
        ) if sync_values else None,
        "parallel_speedup": round(sequential_s / wall_s, 2) if wall_s > 0 else None,
        "slowest": [
            {"id": r.id, "total_s": round(r.timing.total_s or 0, 3)}
            for r in slowest
        ],
    }


def _html_report(payload: dict) -> str:
    """Return a standalone, interactive report with no external dependencies."""
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    summary = payload["summary"]
    meta = payload["meta"]
    uv = html.escape(str(meta.get("uv", "")))
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>uvdrop benchmark report</title>
<style>
:root{{--bg:#0b1020;--card:#141b2d;--line:#29334d;--text:#edf2ff;--muted:#9eabc8;
--prepare:#7dd3fc;--sync:#818cf8;--run:#34d399;--cleanup:#fbbf24;--bad:#fb7185}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1280px;margin:auto;padding:28px}} h1{{margin:0 0 4px;font-size:28px}}
.muted{{color:var(--muted)}} .grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:22px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}}
.metric b{{display:block;font-size:24px;margin-top:4px}} .wide{{grid-column:span 3}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}
input,select{{background:#0f1628;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0 18px}} .dot{{width:10px;height:10px;display:inline-block;border-radius:2px;margin-right:5px}}
.chart{{display:grid;gap:9px}} .barrow{{display:grid;grid-template-columns:210px 1fr 70px;gap:10px;align-items:center}}
.barlabel{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}} .bar{{height:24px;display:flex;background:#0f1628;border-radius:5px;overflow:hidden}}
.seg{{height:100%;min-width:0}} .prepare{{background:var(--prepare)}} .sync{{background:var(--sync)}}
.run{{background:var(--run)}} .cleanup{{background:var(--cleanup)}} .bad{{background:var(--bad)}}
table{{width:100%;border-collapse:collapse;margin-top:12px}} th,td{{padding:9px;border-bottom:1px solid var(--line);text-align:right}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}} th{{cursor:pointer;color:var(--muted)}}
.ok{{color:#34d399}} .fail{{color:var(--bad)}} details{{max-width:420px;text-align:left}} pre{{white-space:pre-wrap}}
@media(max-width:850px){{.grid{{grid-template-columns:repeat(2,1fr)}}.wide{{grid-column:span 2}}.barrow{{grid-template-columns:120px 1fr 55px}}}}
</style>
</head>
<body><main>
<h1>uvdrop 仮想環境ベンチマーク</h1>
<div class="muted">{html.escape(str(meta.get("started_at", "")))} / {html.escape(str(meta.get("platform", "")))}</div>
<div class="grid">
 <div class="card metric"><span>成功</span><b>{summary["ok"]}/{summary["total"]}</b></div>
 <div class="card metric"><span>失敗</span><b>{summary["failed"]}</b></div>
 <div class="card metric"><span>実時間</span><b>{summary["wall_s"]:.1f}s</b></div>
 <div class="card metric"><span>並列短縮倍率</span><b>{summary.get("parallel_speedup") or "-"}×</b></div>
 <div class="card metric"><span>sync 中央値</span><b>{summary.get("sync_s_median") or "-"}s</b></div>
 <div class="card metric"><span>sync P90</span><b>{summary.get("sync_s_p90") or "-"}s</b></div>
 <div class="card wide"><b>実行条件</b><div class="muted">workers={meta.get("workers")} / {html.escape(str(meta.get("selection", "")))}</div><div class="muted">uv: {uv}</div></div>
 <div class="card wide"><b>簡易診断</b><div id="diagnosis" class="muted"></div></div>
</div>
<section class="card">
 <h2>フェーズ別所要時間</h2>
 <div class="legend"><span><i class="dot" style="background:var(--prepare)"></i>prepare</span><span><i class="dot" style="background:var(--sync)"></i>uv sync / venv</span><span><i class="dot" style="background:var(--run)"></i>run</span><span><i class="dot" style="background:var(--cleanup)"></i>cleanup</span></div>
 <div class="controls"><input id="search" placeholder="サンプルを絞り込み"><select id="tier"><option value="">全 tier</option><option>light</option><option>medium</option><option>heavy</option></select><select id="sort"><option value="total">total 降順</option><option value="sync">sync 降順</option><option value="name">名前順</option></select></div>
 <div id="chart" class="chart"></div>
</section>
<section class="card" style="margin-top:16px"><h2>詳細</h2><table><thead><tr><th>id</th><th>tier</th><th>状態</th><th>prepare</th><th>sync</th><th>run</th><th>cleanup</th><th>total</th><th>ログ</th></tr></thead><tbody id="rows"></tbody></table></section>
<p class="muted">sync が突出: 通信・プロキシ・PyPI ミラー・ウイルス対策を確認。run が突出: import/初期化コスト。cleanup が突出: 大量ファイルとAV走査の影響を確認。作業用アプリ・venv・キャッシュはレポート生成後に削除されます。</p>
</main>
<script>
const report={data_json}; const all=report.results;
const f=n=>n==null?"-":Number(n).toFixed(2)+"s";
function filtered(){{
 const q=document.querySelector("#search").value.toLowerCase(), tier=document.querySelector("#tier").value, sort=document.querySelector("#sort").value;
 const a=all.filter(r=>(!tier||r.tier===tier)&&(!q||(r.id+" "+r.name).toLowerCase().includes(q)));
 a.sort((x,y)=>sort==="name"?x.id.localeCompare(y.id):(Number(y.timing[sort+"_s"]||0)-Number(x.timing[sort+"_s"]||0))); return a;
}}
function render(){{
 const a=filtered(), max=Math.max(1,...a.map(r=>Number(r.timing.total_s||0)));
 document.querySelector("#chart").innerHTML=a.map(r=>{{
  const t=r.timing, seg=k=>`<span class="seg ${{k}}" title="${{k}}: ${{f(t[k+"_s"])}}" style="width:${{100*Number(t[k+"_s"]||0)/max}}%"></span>`;
  return `<div class="barrow"><span class="barlabel" title="${{r.name}}">${{r.id}}</span><div class="bar">${{r.ok?seg("prepare")+seg("sync")+seg("run")+seg("cleanup"):`<span class="seg bad" style="width:${{100*Number(t.total_s||0)/max}}%"></span>`}}</div><b>${{f(t.total_s)}}</b></div>`;
 }}).join("");
 document.querySelector("#rows").innerHTML=a.map(r=>`<tr><td>${{r.id}}</td><td>${{r.tier}}</td><td class="${{r.ok?"ok":"fail"}}">${{r.ok?"OK":"FAIL"}}</td><td>${{f(r.timing.prepare_s)}}</td><td>${{f(r.timing.sync_s)}}</td><td>${{f(r.timing.run_s)}}</td><td>${{f(r.timing.cleanup_s)}}</td><td>${{f(r.timing.total_s)}}</td><td><details><summary>表示</summary><pre>${{(r.error||r.stdout_tail||"").replaceAll("&","&amp;").replaceAll("<","&lt;")}}</pre></details></td></tr>`).join("");
}}
["search","tier","sort"].forEach(id=>document.querySelector("#"+id).addEventListener("input",render));
const s=report.summary, slow=(s.slowest||[]).slice(0,3).map(x=>`${{x.id}} (${{x.total_s.toFixed(1)}}s)`).join("、");
document.querySelector("#diagnosis").textContent=(s.failed?`失敗 ${{s.failed}} 件。詳細ログを確認。 `:"全対象が成功。 ")+`遅い順: ${{slow||"-"}}。 sync中央値 ${{s.sync_s_median??"-"}}s、P90 ${{s.sync_s_p90??"-"}}s。`;
render();
</script></body></html>"""


def _write_report(
    results: list[SampleResult],
    out_dir: Path,
    meta: dict,
    *,
    wall_s: float,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "meta": meta,
        "summary": _summary(results, wall_s),
        "results": [
            {
                **{k: getattr(r, k) for k in ("id", "tier", "name", "ok", "error", "app_key", "stdout_tail")},
                "policy_warnings": r.policy_warnings,
                "policy_errors": r.policy_errors,
                "timing": asdict(r.timing),
            }
            for r in results
        ],
    }
    json_path = out_dir / f"bench-{stamp}.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    html_path = out_dir / f"bench-{stamp}.html"
    html_path.write_text(_html_report(payload), encoding="utf-8")
    (out_dir / "latest.html").write_text(html_path.read_text(encoding="utf-8"), encoding="utf-8")
    (out_dir / "latest.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    return json_path, html_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        default="light",
        help="Comma-separated tiers: light,medium,heavy (default: light)",
    )
    parser.add_argument("--ids", default="", help="Comma-separated sample ids (overrides tier)")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-sample run timeout seconds")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(3, max(1, os.cpu_count() or 1)),
        help="Parallel samples (default: up to 3)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "bench",
        help="Report output directory",
    )
    args = parser.parse_args(argv)

    samples = _load_index()
    if args.ids.strip():
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        selected = [s for s in samples if s["id"] in want]
    else:
        tiers = {x.strip() for x in args.tier.split(",") if x.strip()}
        selected = [s for s in samples if s.get("tier") in tiers]

    if not selected:
        print("No samples selected", file=sys.stderr)
        return 2

    workers = max(1, min(int(args.workers), len(selected)))
    temp_root = Path(tempfile.mkdtemp(prefix="uvdrop-bench-"))
    started = time.perf_counter()
    try:
        _configure_isolated_appdata(temp_root)
        meta = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": sys.version.replace("\n", " "),
            "uv": _uv_info(),
            "selection": args.tier if not args.ids else f"ids:{args.ids}",
            "workers": workers,
            "cwd": str(ROOT),
            "disposable": True,
        }

        by_id: dict[str, SampleResult] = {}
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="uvdrop-bench") as pool:
            futures = {
                pool.submit(_run_one, spec, run_timeout=args.timeout): spec
                for spec in selected
            }
            for i, future in enumerate(as_completed(futures), 1):
                spec = futures[future]
                try:
                    r = future.result()
                except Exception as e:  # defensive: _run_one normally captures failures
                    r = SampleResult(
                        id=spec["id"],
                        tier=spec.get("tier", ""),
                        name=spec.get("name", spec["id"]),
                        ok=False,
                        error=str(e),
                    )
                by_id[r.id] = r
                status = "OK" if r.ok else "FAIL"
                sync = f"{r.timing.sync_s:.1f}s" if r.timing.sync_s is not None else "-"
                print(f"[{i}/{len(selected)}] {r.id}: {status} sync={sync} total={r.timing.total_s:.1f}s", flush=True)

        results = [by_id[s["id"]] for s in selected]
        wall_s = time.perf_counter() - started
        json_path, html_path = _write_report(results, args.out, meta, wall_s=wall_s)
    finally:
        # Last line of defense: no app, venv, dotenv, or run-local uv cache survives.
        shutil.rmtree(temp_root, ignore_errors=True)

    print(f"\nHTML:   {html_path}")
    print(f"JSON:   {json_path}")
    print(f"Work directory deleted: {temp_root}")
    failed = sum(1 for r in results if not r.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
