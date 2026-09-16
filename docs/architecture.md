# Architecture

The runtime owns the loop, not just the endpoint call. An experiment produces immutable trial workspaces and an append-only event trace. Each trial follows prepare → optional plan → execute candidates → verify → select → record. The CLI adds a checkpoint after completion. All three architectures share the same task, action protocol, tools, verifier, and model configuration.

## Boundaries

- `config.py`: validated experiment configuration; no credentials stored.
- `providers.py`: network transport or explicitly synthetic oracle. Transient failures are distinguished from malformed responses and nonretryable HTTP errors.
- `context.py`: pinned task/instruction plus bounded history. Summary mode is deterministic extraction; it is not a generated semantic summary.
- `sandbox.py`: workspace path confinement for file tools and local/Docker subprocess execution. The local backend is for trusted code only.
- `runtime.py`: action validation, retries, tool routing, context, verifier feedback, parallel candidate lifecycle and selection.
- `trace.py`: process-local thread-safe JSONL writer. Traces contain metadata and message lengths, not full prompts, tool contents, API keys, or completion text.
- `metrics.py` / `dashboard.py`: derived statistics and a standalone browser report.
- `optimize.py` / `replay.py`: measured-configuration selection and offline trace analysis.
- `benchmarks.py` / `harbor.py`: validated task format and Harbor export.

## Parallelism and reproducibility

Parallel candidates receive a common plan but mutate independent workspaces. There is no shared mutable checkout, patch merge, or speculative cross-agent context. All candidates finish and are verified; the first passing candidate in deterministic submission order wins. Parallel mode is a best-of-N search architecture, not collaborative file ownership, and its extra model calls must be counted when comparing efficiency.

Read/list batches may run concurrently. Writes and commands execute serially, because arbitrary commands may mutate shared state. Configured step/retry ceilings bound the loop; subprocess and endpoint timeouts bound individual operations. Experiments execute sequential trials, with concurrency inside each parallel trial, so the principal variable is harness architecture rather than simultaneous task scheduling.

A run ID, trial ID, parent agent ID, monotonic timestamps, task hash, configuration, and platform manifest make outputs inspectable. Monotonic timestamps only share a clock within the same host process lifetime/boot; never combine unrelated machines as one absolute timeline. Resume skips checkpointed trials but does not restore partial model state. Existing output requires explicit `--resume`.

## Adaptive behavior

With `adaptive=true`, a failed verification increments the repair counter. After the next tool step, context mode switches to extractive summary. This is one small, inspectable heuristic, not an automatically learned policy or proof of optimization. Compare `configs/http-adaptive.json` against an otherwise identical nonadaptive planner configuration and preserve both traces.

## Extending

Add a task manifest using the validated Task schema. Add a provider with `synthetic` and `complete(messages, task=..., role=..., step=...)`, returning text, usage, chunk timestamps, and optional genuine token timestamps. Preserve missing values. Expand a long-horizon dataset through Harbor rather than relabeling microtasks as realistic repository migrations.
