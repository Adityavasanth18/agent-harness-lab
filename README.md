# AgentHarnessLab + AgentScope

**A coding-agent harness you can change, measure, and compare.**

AgentHarnessLab runs controlled coding experiments; AgentScope turns their traces into workload metrics and an interactive, offline HTML dashboard. HarnessTune selects feasible configurations from observed trials. The project uses Python 3.11+ with no runtime dependencies and has a zero-cost, fully offline validation mode.

This is a research prototype with tested local execution, not a claim of production isolation or measured model superiority. Included results use a **known-answer oracle**, not an LLM. They validate the experiment pipeline. Real endpoint, Docker, Codex, Claude Code, and Harbor runs require your environment and have not been executed for this delivery.

## Start here (Windows, macOS, Linux)

1. Extract this folder and open a terminal inside it.
2. Check `python --version` (3.11 or newer). On Windows, use `py` in place of `python` if needed.
3. Run:

```bash
python -m unittest discover -s tests -v
python -m agentharness demo --trusted-local --output results/my-first-run
```

4. Open `results/my-first-run/dashboard.html` in your browser. No server, API key, or paid subscription is needed.

The demo runs 30 repair tasks through all three architectures. `--trusted-local` authorizes running these bundled Python fixtures directly on your machine. Use Docker for model-generated code. The local backend is not a security sandbox.

To try a faster demonstration:

```bash
python -m agentharness demo --trusted-local --limit 3 --output results/quick
```

Use a new output directory for each experiment, or add `--resume` to continue an interrupted one. Optional installation: `python -m pip install -e .`, then use `ahl` instead of `python -m agentharness`. Run from this repository to resolve the bundled benchmarks.

## What is implemented

| Component | Concrete behavior |
|---|---|
| Harness architectures | Single executor; planner → executor; planner → independent parallel candidates with verified winner selection |
| Tools | Read/write/list and argv-based command execution; only read-only tool batches run concurrently |
| Context | Full, sliding window, or deterministic extractive summary; pinned task/instructions; bounded character budget |
| Recovery | Bounded transient transport retries; malformed action feedback; verifier feedback and repair loop; experiment checkpoint resume |
| Isolation | Separate candidate directories; fresh allowlisted verifier directory; Docker backend with network disabled, resource caps, unprivileged user; explicitly trusted local mode |
| Adaptive feature | Switch to extractive summary after failed verification when execution continues; opt-in and traceable |
| Model transport | Streaming chat-completions-compatible HTTP endpoint, authoritative usage when provided, environment-variable credentials |
| AgentScope | JSONL trace, TTFT/chunk/ITL distinctions, percentiles, throughput, peak concurrency, configured-rate cost, tool timing, architecture comparison, timeline |
| HarnessTune | Constrained selection among measured configurations; separate synthetic/observed recommendations |
| Partial replay | Offline timeline inspection and character-count context counterfactuals; never predicts unseen model outputs |
| Benchmarks | 30 explicit microtasks with independently tested failing starters and passing reference solutions |
| Harbor | Current-format task export, Codex/Claude Code run instructions, and trial-result import into the dashboard |
| Delivery | Unit/integration tests, GitHub Actions, Dockerfile, sample configs, measured fixture report, architecture and review notes |

## Run a real model experiment

Use a chat-completions-compatible serving endpoint that streams SSE text content and a final `[DONE]` event. The agent uses a documented JSON action protocol; native function/tool-calling responses are not consumed. Set the `model` and `endpoint` fields in a copy of `configs/http-single.json`. Do not commit API keys.

```bash
# Linux/macOS, only if your endpoint requires authentication:
export AHL_API_KEY='your-key'
# PowerShell equivalent: $env:AHL_API_KEY = 'your-key'
docker pull python:3.12-slim
python -m agentharness run --config configs/http-single.json --output results/real-single
python -m agentharness experiment --config configs/http-parallel.json --repeats 3 --output results/real-comparison
```

`experiment` varies architecture across single/planner/parallel while keeping other config fields fixed. Job order is shuffled reproducibly (`--seed 42` by default). A manifest captures platform, Python version, configuration, task list, and seed; each trial includes a task-content hash. Resume keys include task content, config, and repetition. A crash between writing a trial and its checkpoint may repeat that trial; this is checkpoint resume, not exactly-once execution or mid-agent continuation.

The preflight token budget is a soft per-agent estimate when exact usage is unavailable; an individual response may exceed it. Planner and candidates each receive their own budget. Unknown token counts/cost remain null. There is no free hosted model service bundled.

## Inspect and compare

```bash
python -m agentharness report results/demo/trace.jsonl --output results/demo/report.html
python -m agentharness replay results/demo/trace.jsonl --output results/demo/replay.json
python -m agentharness replay results/demo/trace.jsonl --keep-last 4 --output results/demo/context-analysis.json
python -m agentharness tune results/demo/trace.jsonl --min-success 0.8 --output results/demo/tuning.json
python -m agentharness export-harbor --output harbor-tasks
# After an external Harbor job completes:
python -m agentharness import-harbor harbor-jobs --output results/harbor-trace.jsonl
python -m agentharness report results/harbor-trace.jsonl --output results/harbor-dashboard.html
```

Only add `--max-tokens` to tuning when the endpoint returned complete usage. Missing measurements cannot satisfy a numeric bound. Pricing is user-configured per million input/output tokens; GPU seconds, KV cache usage, and server queue time are not measured.

See [Harbor instructions](docs/harbor.md) for external agent comparisons. Harbor's pre-integrated agents are used for Codex and Claude Code; this repository does not reimplement their private runtimes.

## Read the evidence

- [Architecture and design](docs/architecture.md)
- [Metric definitions](docs/metrics.md)
- [Benchmark catalog and limits](docs/benchmarks.md)
- [Measured fixture report](docs/experiment-report.md)
- [Verification and three-engineer review](docs/verification.md)
- [Security boundaries](SECURITY.md)
- [Local dashboard](results/demo/dashboard.html) and [machine-readable results](results/demo/summary.json)

Included microtasks are small, public, and task-focused.

