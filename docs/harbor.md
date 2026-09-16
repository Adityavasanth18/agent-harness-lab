# Compare Codex and Claude Code through Harbor

**Execution status: not executed here.** The exported task layout, TOML, and shell syntax were tested locally. Docker image builds, Harbor validation, agent installation, provider authentication, and model trials remain external integration checks. These commands provide the comparison path; there are no measured Codex-versus-Claude results in this repository.

Harbor supplies the `oracle`, `codex`, and `claude-code` integrations. AgentHarnessLab exports tasks; its native runtime providers remain synthetic oracle and OpenAI-compatible HTTP. [Harbor agent reference](https://docs.harborframework.com/core-concepts/agents/pre-integrated-agents), checked 2026-09-16.

## Prerequisites and export

Use Linux, macOS Docker Desktop, or Windows WSL2 with Docker Desktop configured for Linux containers. Install Python 3.11+, this repository, a working Docker daemon, and Harbor with schema 1.3 support. The phase-specific network policy below requires Harbor's Linux Docker/nftables support. Account API credentials and access to the chosen models are required for paid trials. Set `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` securely in your shell; do not put them in files or command history.

```bash
uv tool install harbor
harbor --version
harbor run --help
docker version
python -m agentharness export-harbor --tasks benchmarks/micro --output harbor-tasks
```

Harbor's documented installation uses `uv tool install harbor`; Docker is its default sandbox. Record the resolved version and pin it for repeat experiments. [Installation reference](https://docs.harborframework.com/getting-started/installation).

The exported Docker image installs Python, bash, curl, certificates, and Git for agent setup. Building it downloads packages. Pin base-image and agent versions for publication. The baseline task policy disables network; it works for the oracle after the image is built.

## Verify with the oracle first

```bash
harbor run -p harbor-tasks -a oracle -n 1 -k 1 -r 0 -o harbor-jobs --job-name oracle-check
```

Stop if any reference solution fails. Inspect the failing trial rather than treating environment errors as model failures. The command uses the documented local dataset, output, concurrency, attempt, and retry flags. [Run-a-job reference](https://docs.harborframework.com/core-concepts/jobs/run-a-job).

## Prepare a network-enabled agent copy

Installed agents need downloads during setup and API access during inference. Preserve the offline export and create this separate copy once:

```bash
python - <<'PY'
from pathlib import Path
import shutil
shutil.copytree('harbor-tasks', 'harbor-tasks-live')
for path in Path('harbor-tasks-live').glob('*/task.toml'):
    text = path.read_text()
    text = text.replace('[environment]\nnetwork_mode = "no-network"', '[environment]\nnetwork_mode = "public"')
    text = text.replace('[agent]\n', '[agent]\nnetwork_mode = "allowlist"\nallowed_hosts = ["api.openai.com", "api.anthropic.com"]\n')
    text = text.replace('[verifier]\n', '[verifier]\nnetwork_mode = "no-network"\n')
    path.write_text(text)
PY
```

This grants setup download access, restricts the agent run to the two API hosts, and disables verifier networking. The API-host list may need deliberate changes for a provider proxy or alternate authentication. A sandbox unable to enforce this policy should reject the job; use a supported sandbox. [Network-policy reference](https://docs.harborframework.com/core-concepts/tasks/network-policies).

## Run both agents on identical tasks

Set `CODEX_MODEL` and `CLAUDE_MODEL` to exact model IDs available to your accounts. Harbor's current documentation illustrates `openai/gpt-5.6-sol` and `anthropic/claude-sonnet-5`; these examples are not an availability guarantee. Use a snapshot ID when your provider offers one. [Agent configuration reference](https://docs.harborframework.com/core-concepts/agents/pre-integrated-agents).

```bash
export CODEX_MODEL='openai/gpt-5.6-sol'
export CLAUDE_MODEL='anthropic/claude-sonnet-5'
harbor run -p harbor-tasks-live -a codex -m "$CODEX_MODEL" -n 1 -k 3 -r 0 -o harbor-jobs --job-name codex-micro
harbor run -p harbor-tasks-live -a claude-code -m "$CLAUDE_MODEL" -n 1 -k 3 -r 0 -o harbor-jobs --job-name claude-micro
```

Three attempts across 30 tasks means **90 trials per agent**. Start with `-l 1 -k 1` and a different job name to verify setup before a full paid run. Retrying infrastructure failures should be a separately recorded policy; `-r 0` avoids hidden retries in this starting protocol. The exported timeout is 180 seconds; if that is insufficient, change it identically in both datasets before rerunning and disclose the change. [Job flags](https://docs.harborframework.com/core-concepts/jobs/run-a-job).

## Preserve and compare evidence

Archive each job's config, result, verifier logs, raw agent trajectory, Harbor/agent versions, task hashes, image digest, model IDs, and host specifications. Report task-level pass rate, per-task three-attempt outcomes, infrastructure failures separately, wall-clock time, and token/cost totals only when actually recorded. A fair comparison pairs the same task and attempt counts under identical limits. Do not treat retries as extra independent tasks.

Harbor advertises ATIF trajectories for both integrations. The summary importer below reads saved trial results; it does not parse ATIF or reconstruct model request timing. [Trajectory capabilities](https://docs.harborframework.com/core-concepts/agents/pre-integrated-agents).

These public, small repairs validate integration mechanics and cannot establish long-horizon coding quality. Oracle results show verifier plumbing, not agent intelligence. Do not infer token-level ITL from coarse CLI timestamps.

## Import actual trial summaries into AgentScope

After the external jobs finish:

```bash
python -m agentharness import-harbor harbor-jobs --output results/harbor-trials.jsonl
python -m agentharness report results/harbor-trials.jsonl --output results/harbor-report
```

Check `python -m agentharness report --help` for the dashboard output options. The Python entrypoint is `import_harbor(path, output_path)` from `agentharness.harbor_import`. Output must be a new filename, preventing accidental overwrite.

The importer accepts one trial `result.json`, a job result containing `trial_results`, or a directory recursively containing trial results. It reads completed, single-step trials only. Job-only aggregates without trial records cannot reconstruct observations and are rejected. Identical duplicate trial IDs are collapsed; conflicting duplicates fail. Missing timing, malformed records, unsupported multi-step data, and nonbinary or differently named reward metrics are rejected before output is created. Its recognized structure comes from Harbor's [TrialResult](https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/trial/result.py), [JobResult](https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/job/result.py), and [VerifierResult](https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/verifier/result.py) definitions, inspected 2026-09-16.

Only `rewards.reward` equal to 0 or 1 becomes scored failure/success. An explicit Harbor exception is imported as unscored with its exception type, even if a reward is also present. The native dashboard groups task success and observed whole-trial duration under `harbor:codex`, `harbor:claude-code`, etc. Whole-trial timing includes environment/setup overhead; it is not inference latency. Naive datetime values retain within-trial duration but do not establish synchronization across machines.

Documented `agent_result` totals are retained in `harbor_usage`: input tokens include cache, cached tokens, output tokens, and observed USD cost. Missing usage stays null. These are trial totals, not inferred request records. Native request-level throughput, TTFT, token ITL, and request count therefore remain unavailable. [AgentContext field semantics](https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/agent/context.py).

Importer tests use synthetic schema-grounded fixtures covering roundtrip, duplicate handling, bad records, missing usage, exceptions, and absence of invented request metrics. This verifies conversion logic; it does not claim a live Harbor evaluation occurred.
