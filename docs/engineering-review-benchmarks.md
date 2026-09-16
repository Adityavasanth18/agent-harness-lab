# Engineer 3: benchmark and integration review

Review date: 2026-09-16. This is an independent AI engineering role in the three-agent implementation workflow, not a claim of external human certification.

## Evidence inspected

Inspected the task manifest loader, workspace creation, all 30 contracts and reference implementations, Harbor export, native runtime verification, and sandbox subprocess output handling. Compared Harbor export and usage with official task configuration, verifier, installation, job, agent, and network-policy documentation. See [the integration procedure](harbor.md) for primary-source links and exact commands.

Executed:

```bash
python -m unittest discover -s tests -p test_benchmarks.py -v
python -m unittest discover -s tests -p test_runtime.py -v
```

The benchmark suite passed 4 test methods. The task-integrity method ran 60 subprocess checks: every one of 30 starters failed and every reference solution passed. Export checks covered all 30 tasks' TOML schema and network policy, presence/separation of verifier files, shell syntax, initial failure reward, and refusal to overwrite existing exports. Path traversal, symlink writing, duplicate IDs, and verifier/start-file collisions were rejected.

The runtime suite passed 6 test methods, including all three architectures, oracle separation from model prompts, transient retries, failed model output, HTTP streaming contract, and injected unittest-file rejection. These are local deterministic checks; they are not live-provider evaluations.

## Findings and disposition

| Finding | Disposition | Evidence and remaining boundary |
| --- | --- | --- |
| Candidate files could inject a replacement `unittest.py` into verification | Resolved in native runtime | Verification now copies only declared candidate files into a fresh directory, rejecting missing, symlinked, or oversized inputs; injected-unittest regression passes. |
| Subprocess output was spooled without a disk-size bound | Resolved | Sandbox now drains a pipe continuously and retains a capped byte buffer; inspected implementation has no output disk spool. |
| Reference answers could accidentally become model context | Prevented and tested | Materialization writes starters only, provider tests verify no solution leakage, and Docker build context excludes oracle/test material. Reference data remain public in repository. |
| Harbor schema/version assumptions could become stale | Checked against current official docs | Export targets schema 1.3 with valid task naming and numerical reward convention; full Harbor package validation still requires external runtime. |
| Offline task policy prevents CLI-agent installation and inference | Documented explicit configuration | Separate live-copy procedure enables setup downloads, API-host-only agent phase, and no-network verifier; original offline tasks remain usable for oracle. |
| Slim Python image lacks common agent setup utilities | Addressed in exporter | Dockerfile installs bash, certificates, curl, and Git; actual image build and agent installer compatibility remain unexecuted. |
| Pipe stream emitted resource warnings during runtime tests | Resolved | Reader now owns and closes the pipe with a context manager; the integrated suite passes with ResourceWarning elevated to error. |
| Public microtasks risk overstatement of capability | Scoped honestly | Documentation calls them microbenchmarks, not long-horizon workloads or held-out evaluation; oracle results are synthetic plumbing evidence. |

## Residual limitations

The native verifier executes candidate Python in the same process as unittest, so malicious candidate code could interfere with test machinery. Fresh directories and file allowlists prevent ordinary test tampering, not all reward hacking. The external Harbor export uses shared verification and has the same non-adversarial evaluation limitation. Neither approach is certified for hostile code. Local execution is explicitly trusted-only; Docker isolation is the intended model-generated-code path.

Finite contract tests are not exhaustive. No real provider, GPU, Docker, Harbor oracle, Codex, or Claude Code evaluation was executed by this reviewer. No inference performance improvement, architecture advantage, or two-agent comparison outcome is established by these checks. The documented comparison path runs the actual external Harbor integrations when credentials and a suitable container runtime are available.
