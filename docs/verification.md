# Verification and engineering review

Three independent AI engineering roles contributed to implementation and review. This is not three human engineers, an external audit, or a guarantee of perfection.

| Role | Ownership | Review focus |
|---|---|---|
| Systems/runtime engineer (lead) | Configuration, execution loop, providers, context, sandbox, CLI, integration, delivery | Architecture, failure handling, operational boundaries, reproducibility |
| Performance engineer | Metrics, dashboard, optimizer, replay | Correct denominators, missing values, chunk/token distinction, clock domains, trace integrity |
| Benchmark/integration engineer | 30 tasks, task loader, Harbor export/import | Failing starters, valid reference solutions, hidden test separation, integration schema |

Detailed independent findings are in `engineering-review-performance.md` and `engineering-review-benchmarks.md`. The lead integrated fixes for trial joins, timestamp semantics, type validation, bounded subprocess output, stream cleanup, file confinement, verifier allowlists, and private-context metadata replay.

## Executed verification

The final local suite passed **38 test methods**. The exact final test output is saved in `results/test-output.txt`. Tests use Python unittest and no third-party packages. They cover:

- All 30 broken starters fail and all 30 reference solutions pass (60 subprocess checks).
- All three architectures solve fixture tasks; bad output fails and receives verification feedback.
- A transient provider failure is retried and traced.
- A localhost SSE server exercises the HTTP wire contract, empty chunks, split content, usage, and completion marker.
- Traversal/symlink escapes, invalid config, command timeout, capped output, corrupted traces, verifier injection, and context limits.
- Percentiles, overlapping request concurrency, missing usage, token/chunk timing, derived TPOT, costs, optimization constraints, and cross-run clock separation.
- Dashboard escaping and JavaScript syntax; context replay without raw prompt storage.
- CLI duplicate-output refusal, explicit local opt-in, and checkpoint resume without duplicated completed trials.
- Harbor export TOML/shell structure and adapter fixture contracts.

The completed fixture experiment has 270/270 passing trials. The HTML report, JSON summary, event trace, manifests, selected outputs and recommendations are included.

## Not executed

Docker image builds/command backend, real model endpoint calls, external Codex/Claude Code agents, full Harbor jobs, GitHub-hosted CI, Windows/macOS runtime tests, and GPU-side metrics. The CI matrix is supplied for Linux and Windows/Python 3.11–3.13; creating a workflow is not equivalent to observing it pass on GitHub.

## Remaining engineering limits

- Research prototype and microbenchmark suite, not a production multiuser service or hostile-code grader.
- Extractive context summaries may lose important information; success impact must be measured.
- Soft per-agent token budgets do not enforce account billing limits.
- Trial checkpoint resume cannot restore an interrupted model turn; a crash before checkpoint can repeat a trial.
- Local subprocess isolation is not a security boundary. Docker workspace disk quotas require host configuration.
- Public task solutions mean this is not a contamination-resistant benchmark.
- Generic HTTP chunks cannot yield genuine per-token latency samples; absent metrics remain unknown.
- Harbor version/schema changes may require adapter updates. Fixture coverage is not live compatibility certification.
