"""Measurements derived exclusively from observed events; unavailable values stay null."""
from collections import defaultdict
import math


def percentile(values, p):
    values = sorted(v for v in values if isinstance(v, (int, float)) and math.isfinite(v))
    if not values:
        return None
    x = (len(values) - 1) * p / 100
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


def distribution(values):
    values = [v for v in values if v is not None]
    return {"count": len(values), "mean": sum(values) / len(values) if values else None,
            "p50": percentile(values, 50), "p95": percentile(values, 95),
            "p99": percentile(values, 99), "max": max(values) if values else None}


def _duration(e):
    a, b = e.get("start_ns"), e.get("end_ns")
    return (b - a) / 1e6 if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b >= a else None


def _intervals(e, field):
    seq = e.get(field) or []
    return [(b - a) / 1e6 for a, b in zip(seq, seq[1:]) if b >= a]


def _tokens(requests, field):
    values = [r.get(field) for r in requests]
    known = [v for v in values if isinstance(v, int) and not isinstance(v, bool) and v >= 0]
    return {"total": sum(known) if len(known) == len(values) and values else None,
            "known_total": sum(known), "known_requests": len(known),
            "missing_requests": len(values) - len(known)}


def _requests(requests):
    ttft, token_intervals, chunk_intervals, points, tpot = [], [], [], [], []
    sources = defaultdict(int)
    for r in requests:
        start, end = r.get("start_ns"), r.get("end_ns")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start:
            points += [(start, 1), (end, -1)]
        first = r.get("first_token_ns")
        source = r.get("first_token_source", "token")
        if first is None and r.get("chunk_timestamps_ns"):
            first, source = r["chunk_timestamps_ns"][0], "content_chunk"
        if first is not None and start is not None and first >= start:
            ttft.append((first - start) / 1e6)
            sources[source] += 1
        chunks, count = r.get("chunk_timestamps_ns") or [], r.get("output_tokens")
        if len(chunks) > 1 and isinstance(count, int) and count > 1 and not r.get("estimated_tokens") and not r.get("synthetic") and chunks[-1] >= chunks[0]:
            tpot.append((chunks[-1] - chunks[0]) / 1e6 / (count - 1))
        token_intervals.extend(_intervals(r, "token_timestamps_ns"))
        chunk_intervals.extend(_intervals(r, "chunk_timestamps_ns"))
    concurrent = peak = 0
    for _, delta in sorted(points):
        concurrent += delta
        peak = max(peak, concurrent)
    bounds = [p[0] for p in points]
    window = (max(bounds) - min(bounds)) / 1e9 if bounds else None
    run_groups = defaultdict(list)
    for r in requests:
        run_groups[r.get("run_id")].append(r)
    if len(run_groups) > 1:
        # Monotonic timestamps from different runs may use unrelated clock domains.
        window = None
        peak = max(_requests(rs)["peak_concurrent_requests"] for rs in run_groups.values())
    inp, out = _tokens(requests, "input_tokens"), _tokens(requests, "output_tokens")
    return {"count": len(requests), "errors": sum(r.get("status") not in ("ok", "success", None) for r in requests),
            "estimated_token_requests": sum(bool(r.get("estimated_tokens")) for r in requests),
            "latency_ms": distribution([_duration(r) for r in requests]),
            "ttft_ms": distribution(ttft), "ttft_sources": dict(sources),
            "token_itl_ms": distribution(token_intervals), "derived_chunk_tpot_ms": distribution(tpot), "chunk_interval_ms": distribution(chunk_intervals),
            "input_tokens": inp, "output_tokens": out, "measurement_window_s": window,
            "output_tokens_per_second": out["total"] / window if out["total"] is not None and window else None,
            "peak_concurrent_requests": peak, "requests_per_second": len(requests) / window if window else None,
            "retry_attempts": sum(bool(r.get("retry", 0)) for r in requests)}


def aggregate(events):
    """Aggregate request attempts and completed trials without inferring missing usage."""
    events = list(events)
    requests = [e for e in events if e.get("event") == "request"]
    trials = [e for e in events if e.get("event") == "trial"]
    groups = defaultdict(list)
    for r in requests:
        groups[(str(r.get("provider", "unknown")), str(r.get("model", "unknown")))].append(r)
    scored = [e for e in trials if isinstance(e.get("success"), bool)]
    tools = [e for e in events if e.get("event") == "tool"]
    successful = sum(t["success"] for t in scored)
    request_summary = _requests(requests)
    usage = [request_summary[f]["total"] for f in ("input_tokens", "output_tokens")]
    total_tokens = sum(usage) if all(v is not None for v in usage) else None
    costs = []
    for r in requests:
        matches = [t for t in trials if t.get("run_id") == r.get("run_id") and t.get("task_id") == r.get("task_id")
                   and (not r.get("trial_id") or r.get("trial_id") == t.get("trial_id"))
                   and t.get("start_ns", float("inf")) <= r.get("start_ns", -1)
                   and t.get("end_ns", -1) >= r.get("end_ns", float("inf"))]
        if len(matches) != 1:
            continue
        config = matches[0].get("config", {})
        vals = [r.get("input_tokens"), r.get("output_tokens"), config.get("input_cost_per_million"), config.get("output_cost_per_million")]
        if all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in vals):
            costs.append((vals[0] * vals[2] + vals[1] * vals[3]) / 1e6)
    total_cost = sum(costs) if requests and len(costs) == len(requests) else None
    architectures = defaultdict(list)
    for t in trials:
        architectures[str(t.get("architecture", "unknown"))].append(t)
    architecture_rows = []
    for name, ts in sorted(architectures.items()):
        sc = [t["success"] for t in ts if isinstance(t.get("success"), bool)]
        architecture_rows.append({"architecture": name, "trials": len(ts), "scored": len(sc),
                                  "synthetic_trials": sum(bool(t.get("synthetic")) for t in ts),
                                  "success_rate": sum(sc) / len(sc) if sc else None,
                                  "latency_ms": distribution([_duration(t) for t in ts])})
    return {"schema_version": 1, "events": len(events), "requests": request_summary,
            "by_run": [{"run_id": rid, **_requests([r for r in requests if r.get("run_id") == rid])}
                       for rid in sorted({r.get("run_id") for r in requests}, key=str)],
            "tools": {"count": len(tools), "duration_ms": distribution([_duration(t) for t in tools])},
            "efficiency": {"total_tokens": total_tokens,
                           "tokens_per_successful_trial": total_tokens / successful if total_tokens is not None and successful else None,
                           "gpu_seconds_per_successful_trial": None,
                           "configured_rate_total_cost": total_cost,
                           "configured_rate_known_cost": sum(costs),
                           "costed_requests": len(costs),
                           "cost_per_successful_trial": total_cost / successful if total_cost is not None and successful else None},
            "by_architecture": architecture_rows,
            "trials": {"count": len(trials), "scored": len(scored),
                       "success_rate": sum(t["success"] for t in scored) / len(scored) if scored else None,
                       "synthetic": sum(bool(t.get("synthetic")) for t in trials),
                       "latency_ms": distribution([_duration(t) for t in trials])},
            "by_provider_model": [{"provider": p, "model": m, **_requests(rs)} for (p, m), rs in sorted(groups.items())],
            "notes": ["TTFT uses the first observed token or first content chunk; transport chunks are not tokens.",
                      "Multiple runs may have unrelated monotonic clocks: combined throughput/window is null, peak concurrency is the maximum within one run, and per-run metrics remain available.",
                      "Token ITL is unavailable without actual token timestamps. Missing usage remains null.",
                      "Derived chunk TPOT divides first-to-last content chunk time by authoritative output_tokens minus one; it is an average proxy, not token interval samples.",
                      "Cost uses user-configured per-million rates and recorded usage; missing rates or usage leave total cost null. GPU time is unavailable.",
                      "Throughput includes all request attempts over the first-start to last-end measurement window."]}
