# Experiment report: offline pipeline validation

## Question and provenance

Can all three harness architectures execute, verify, trace, and report the same 30 repair tasks reproducibly? This experiment measures **known-answer fixture execution**, not a model's coding quality or GPU inference performance.

Command:

```bash
python -m agentharness demo --trusted-local --repeats 3 --seed 42 --output results/demo
```

Environment: Python 3.12.14, Linux, trusted local subprocess backend. The archived manifest records exact platform and config. Thirty tasks × three architectures × three repetitions = **270 completed trials**. All passed. There were **900 oracle request calls**. Job order was seeded and shuffled. The oracle writes the published reference solution, so 100% success is expected and cannot support a claim about agent intelligence.

## Observed wall-clock measurements

| Architecture | Trials | Fixture pass rate | Median trial ms | p95 trial ms |
|---|---:|---:|---:|---:|
| parallel | 90 | 100% | 69.544 | 104.960 |
| planner | 90 | 100% | 67.058 | 70.400 |
| single | 90 | 100% | 66.924 | 71.354 |

These values include filesystem work, Python verifier startup, orchestration, and local scheduling. They vary by host and load. Parallel mode runs two independent candidates and verifies each. Its tiny oracle calls are so short that observed request concurrency may be one even though candidate execution overlaps. No artificial sleeps were inserted into the measurement run to manufacture performance effects.

## Inference measurements deliberately unavailable

The oracle is not an inference server. Input/output token counts, TTFT, token ITL, derived TPOT, token throughput, and model cost are null. Microsecond request durations are fixture function timings, not model latency. The dashboard marks the run synthetic. The streaming HTTP contract has a local mock-server test, but those test timings are not presented as model measurements.

## Interpretation

The evidence supports plumbing correctness on the bundled functional tasks. It does not demonstrate improved success rate, lower inference latency, long-horizon repository competence, cost savings, or an advantage for any architecture. The optimizer's synthetic recommendation illustrates mechanics only.

## Reproducible real experiment protocol

1. Validate Docker and one actual endpoint trial, including model identity, streaming usage, and verifier behavior.
2. Freeze tasks and tests, image digest, model version, configuration, pricing, and hardware. Use a held-out task set for any publishable generalization claim.
3. Run each architecture with identical budgets and task/repetition counts, randomized order, and at least three repeated trials; log transport and infrastructure failures separately.
4. Compare paired per-task outcomes, distributions rather than only averages, total calls/tokens/cost, and trial wall time. Additional agents consume additional per-agent budgets; report that explicitly.
5. Compare the adaptive feature against its otherwise identical baseline. Select configurations on a tuning split, then evaluate on held-out tasks.
6. Keep raw trace, manifest, generated solutions, verifier outputs where available, and exact commands. Recompute all summary values from those records.

Codex and Claude Code comparisons run through Harbor and require their own credentials. See `docs/harbor.md`. No live model, Docker, Harbor job, or GPU was run for this report.
