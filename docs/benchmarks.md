# HarnessBench Micro v1

This suite contains 30 deterministic Python repair microbenchmarks. It exercises task loading, code edits, verifier feedback, candidate selection, traces, and Harbor export. These are small function repairs, **not long-horizon tasks, a representative coding benchmark, or evidence that one architecture is better**. They do not establish repository navigation, multi-service debugging, dependency migration, or sustained context recovery ability. Use a separate held-out repository-scale suite for those claims.

Each task contains a precise instruction, a broken `solution.py`, reference solution, and 3–4 independent unittest cases (some tasks have more). All starters are required to fail and all reference solutions to pass. The tests include empty inputs, boundary conditions, validation, ordering, cycles, and mutation checks as appropriate. These finite examples are not exhaustive correctness proofs.

| IDs | Contracts |
| --- | --- |
| 01–03 | Stable uniqueness, chunk boundaries, closed interval merging |
| 04–07 | Reachability, deterministic topological sort, shortest paths, cyclic SCCs |
| 08–12 | JSONL, quoted CSV, numeric versions, JSON Pointer, URL query parsing |
| 13–15 | Capped retry delays, retryable HTTP codes, exception-aware execution |
| 16–18 | Contiguous context suffixes, pinned system messages, bounded output |
| 19–25 | Percentiles, TTFT, chunk intervals, aggregate throughput, peak concurrency, cost, pooled success |
| 26–30 | Pareto front, safe paths, recursive redaction, config merging, LRU eviction |

## Task contract

`benchmarks/micro/<id>/task.json` is UTF-8 JSON:

```json
{
  "id": "example-repair",
  "instruction": "Repair solution.py according to an explicit function contract.",
  "files": {"solution.py": "def answer():\n    return 0\n"},
  "solution": {"solution.py": "def answer():\n    return 42\n"},
  "tests": {"test_solution.py": "import unittest\nfrom solution import answer\nclass Test(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(),42)\n"},
  "verify": ["python", "-m", "unittest", "-v", "test_solution"]
}
```

`load_tasks(path)` recursively finds manifests and rejects duplicate IDs, unsafe paths, invalid mappings, and overlapping starter/verifier paths. `materialize(task, workspace)` writes only starter files. The runtime keeps the tests out of the agent's editable workspace. Reference answers are available solely to the explicitly labeled synthetic oracle provider and Harbor oracle solution, never included in HTTP model prompts. The suite is public and reference solutions are in the repository; do not present it as confidential, contamination-resistant, or held out.

A task manifest and its verifier are trusted executable input. Code repaired by a model requires container isolation. The local backend is for trusted examples only. Verifier separation prevents routine test editing but is not an adversarial evaluation security guarantee: Python candidate code shares an interpreter with tests and can interfere with it. A hostile-agent benchmark needs independent external checks and stronger verifier isolation.

Run the suite integrity gate:

```bash
python -m unittest discover -s tests -p test_benchmarks.py -v
```

## Harbor bridge

The Python API `export_harbor(tasks, output)` creates an independent Harbor task directory for each task and refuses to overwrite an existing directory. Each includes `instruction.md`, `task.toml`, `environment/Dockerfile`, `environment/workspace/solution.py`, `tests/test.sh`, `tests/test_solution.py`, and `solution/solve.sh`. The build context contains starters only. The verifier initializes a zero reward before executing tests and writes one on success.

The exporter targets Harbor task schema **1.3**, checked against the [official configuration reference](https://docs.harborframework.com/core-concepts/tasks/configuration) on 2026-09-16. Its verifier follows the [documented `/tests` upload and `/logs/verifier/reward.txt` convention](https://docs.harborframework.com/core-concepts/tasks/verifier). The environment uses Python 3.12, a 180-second agent timeout, a 30-second verifier timeout, and no task network. The Docker base image must already be available or pulled during environment build. Pin its digest before publishing rigorously reproducible experiments.

```python
from agentharness.benchmarks import load_tasks
from agentharness.harbor import export_harbor
export_harbor(load_tasks('benchmarks/micro'), 'harbor-tasks')
```

With Harbor and Docker installed, use the Harbor CLI's task-path option to run an exported task with its oracle, then with your chosen model agent. Check `harbor run --help` for options supported by the installed Harbor version. A syntactically validated export is not a completed Harbor evaluation: record the Harbor version, image digest, agent, model, actual job command, and raw results before reporting integrated run numbers. Codex and Claude Code are evaluated through the external Harbor runner; they are not simulated native providers in this repository.
