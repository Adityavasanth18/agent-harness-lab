"""Command-line experiments, reports, trace replay, and Harbor task export."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import platform
import random
import sys
import uuid
from .config import Config
from .runtime import Runtime
from .trace import Trace, read_events
from .metrics import aggregate
from .dashboard import render_dashboard
from .optimize import select_configurations
from .replay import inspect_trace, context_counterfactual

def main(argv=None):
    parser = argparse.ArgumentParser(prog="ahl", description="AgentHarnessLab · coding-agent experiments and telemetry")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "experiment", "demo"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--tasks", default="benchmarks")
        cmd.add_argument("--output", default="results/" + name)
        cmd.add_argument("--config")
        cmd.add_argument("--limit", type=int)
        cmd.add_argument("--repeats", type=int, default=1)
        cmd.add_argument("--seed", type=int, default=42)
        cmd.add_argument("--trusted-local", action="store_true", help="Permit local execution of trusted fixtures; not isolation")
        cmd.add_argument("--resume", action="store_true", help="Skip already completed task/config/repetition trials")
    for name in ("report", "replay", "tune"):
        cmd = commands.add_parser(name)
        cmd.add_argument("trace")
        cmd.add_argument("--output")
        if name == "replay":
            cmd.add_argument("--keep-last", type=int)
        if name == "tune":
            cmd.add_argument("--min-success", type=float, default=0.8)
            cmd.add_argument("--max-tokens", type=int)
            cmd.add_argument("--max-latency-ms", type=float)
    cmd = commands.add_parser("export-harbor")
    cmd.add_argument("--tasks", default="benchmarks")
    cmd.add_argument("--output", default="harbor-tasks")
    cmd = commands.add_parser("import-harbor")
    cmd.add_argument("path", help="Harbor result.json or job directory")
    cmd.add_argument("--output", required=True, help="New native JSONL trace path")
    args = parser.parse_args(argv)
    try:
        if args.command == "import-harbor":
            from .harbor_import import import_harbor
            events = import_harbor(args.path, args.output)
            print(f"Imported {len(events)} Harbor trial summaries to {args.output}")
            return 0
        if args.command == "export-harbor":
            from .benchmarks import load_tasks
            from .harbor import export_harbor
            export_harbor(load_tasks(args.tasks), Path(args.output))
            print(f"Exported Harbor tasks to {args.output}")
            return 0
        if args.command in {"report", "replay", "tune"}:
            events = read_events(args.trace)
            if args.command == "report":
                output = args.output or str(Path(args.trace).with_suffix(".html"))
                result = render_dashboard(events, output)
                Path(output).with_suffix(".json").write_text(json.dumps(result, indent=2))
                print(output)
                return 0
            if args.command == "replay":
                result = context_counterfactual(events, keep_last_messages=args.keep_last) if args.keep_last else inspect_trace(events)
            else:
                result = select_configurations(events, min_success_rate=args.min_success, max_tokens=args.max_tokens, max_p95_latency_ms=args.max_latency_ms)
            rendered = json.dumps(result, indent=2)
            if args.output:
                Path(args.output).write_text(rendered)
            else:
                print(rendered)
            return 0
        from .benchmarks import load_tasks
        config = Config.load(args.config) if args.config else Config()
        if args.command == "demo":
            config = replace(config, provider="oracle", model="local-test-fixture")
        if args.trusted_local:
            config = replace(config, sandbox="local")
        if config.sandbox == "local" and not args.trusted_local:
            raise ValueError("local execution requires explicit --trusted-local")
        if args.repeats < 1 or (args.limit is not None and args.limit < 1):
            raise ValueError("repeats and limit must be positive")
        tasks = load_tasks(args.tasks)
        if args.limit:
            tasks = tasks[:args.limit]
        if not tasks:
            raise ValueError("No benchmark tasks found")
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        trace_path = output / "trace.jsonl"
        if trace_path.exists() and not args.resume:
            raise ValueError("Output already has a trace; choose a new output or use --resume")
        trace = Trace(trace_path, uuid.uuid4().hex)
        configs = [config] if args.command == "run" else [replace(config, architecture=a) for a in ("single", "planner", "parallel")]
        previous = read_events(trace_path) if trace_path.exists() else []
        completed = {e.get("experiment_key"): e.get("success", False) for e in previous if e.get("event") == "checkpoint"}
        jobs = [(task, cfg, repetition) for repetition in range(args.repeats) for cfg in configs for task in tasks]
        random.Random(args.seed).shuffle(jobs)
        manifest = {"python": sys.version, "platform": platform.platform(), "seed": args.seed,
                    "repeats": args.repeats, "task_ids": [t.id for t in tasks], "configs": [c.to_dict() for c in configs],
                    "mode": "synthetic known-answer fixture" if config.provider == "oracle" else "observed endpoint",
                    "run_id": trace.run_id}
        (output / f"manifest-{trace.run_id}.json").write_text(json.dumps(manifest, indent=2))
        failed = 0
        for index, (task, cfg, repetition) in enumerate(jobs, 1):
            import hashlib
            identity = {"task": task.id, "files": task.files, "tests": task.tests, "instruction": task.instruction,
                        "config": cfg.to_dict(), "repetition": repetition, "verify": task.verify,
                        "oracle_solution": task.solution if cfg.provider == "oracle" else None}
            key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            if key in completed:
                failed += not completed[key]
                continue
            result = Runtime(cfg, trace).run_task(task, output / "trials")
            trace.emit("checkpoint", experiment_key=key, trial_id=result["trial_id"], success=result["success"])
            failed += not result["success"]
            print(f"[{index}/{len(jobs)}] {cfg.architecture:8} {task.id}: {'PASS' if result['success'] else 'FAIL'}", flush=True)
        events = read_events(trace_path)
        summary = render_dashboard(events, output / "dashboard.html")
        (output / "summary.json").write_text(json.dumps(summary, indent=2))
        (output / "recommendations.json").write_text(json.dumps(select_configurations(events, min_success_rate=0.8), indent=2))
        print(f"Results: {output.resolve()}")
        return 1 if failed else 0
    except (ValueError, OSError) as exc:
        print(f"ahl: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
