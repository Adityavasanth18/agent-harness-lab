"""Select measured configurations, never extrapolate unexecuted experiments."""
import json
from collections import defaultdict
from .metrics import percentile


def select_configurations(events, min_success_rate=0, max_tokens=None, max_p95_latency_ms=None):
    if not 0 <= min_success_rate <= 1:
        raise ValueError("min_success_rate must be in [0, 1]")
    if max_tokens is not None and max_tokens < 0:
        raise ValueError("max_tokens must be nonnegative")
    if max_p95_latency_ms is not None and max_p95_latency_ms < 0:
        raise ValueError("max_p95_latency_ms must be nonnegative")
    events = list(events)
    groups = defaultdict(list)
    for t in events:
        if t.get("event") == "trial":
            key = json.dumps({"architecture": t.get("architecture"), "config": t.get("config", {}),
                              "synthetic": bool(t.get("synthetic"))}, sort_keys=True)
            groups[key].append(t)
    results = []
    for key, trials in sorted(groups.items()):
        durations, token_counts, scores = [], [], []
        for t in trials:
            start, end = t.get("start_ns"), t.get("end_ns")
            if start is not None and end is not None and end >= start:
                durations.append((end - start) / 1e6)
            if isinstance(t.get("success"), bool):
                scores.append(t["success"])
            rs = [e for e in events if e.get("event") == "request"
                  and e.get("run_id") == t.get("run_id") and e.get("task_id") == t.get("task_id")
                  and (not t.get("trial_id") or not e.get("trial_id") or e.get("trial_id") == t["trial_id"])
                  and (start is None or e.get("start_ns", -1) >= start)
                  and (end is None or e.get("end_ns", float("inf")) <= end)]
            vals = [r.get(f) for r in rs for f in ("input_tokens", "output_tokens")]
            if vals and all(isinstance(v, int) and v >= 0 for v in vals):
                token_counts.append(sum(vals))
        rate = sum(scores) / len(scores) if len(scores) == len(trials) and scores else None
        latency = percentile(durations, 95) if len(durations) == len(trials) else None
        tokens = sum(token_counts) / len(token_counts) if len(token_counts) == len(trials) and token_counts else None
        reasons = []
        if rate is None or rate < min_success_rate:
            reasons.append("success rate missing or below minimum")
        if max_tokens is not None and (tokens is None or tokens > max_tokens):
            reasons.append("mean total tokens missing or above bound")
        if max_p95_latency_ms is not None and (latency is None or latency > max_p95_latency_ms):
            reasons.append("p95 trial latency missing or above bound")
        results.append({**json.loads(key), "trials": len(trials), "success_rate": rate,
                        "mean_total_tokens": tokens, "p95_latency_ms": latency,
                        "feasible": not reasons, "reasons": reasons})
    feasible = [r for r in results if r["feasible"]]
    feasible.sort(key=lambda r: (r["p95_latency_ms"] if r["p95_latency_ms"] is not None else float("inf"),
                                 r["mean_total_tokens"] if r["mean_total_tokens"] is not None else float("inf")))
    # Synthetic and real measurements must never compete for a recommendation.
    best = {mode: next((r for r in feasible if r["synthetic"] == synthetic), None)
            for mode, synthetic in (("observed", False), ("synthetic", True))}
    return {"configurations": results, "recommendations": best,
            "objective": "Minimum observed p95 trial latency among feasible configurations; tokens break ties.",
            "limitations": "Finite observed trials only; no statistical generalization or prediction. Token bound is mean input + output per trial."}
