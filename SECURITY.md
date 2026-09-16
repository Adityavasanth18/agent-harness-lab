# Execution and evaluation boundaries

The trusted-local backend executes arbitrary commands with the user's filesystem permissions. Workspace checks constrain the built-in read/write tools only; they do not constrain Python, shell programs, subprocesses, or network calls made by generated code. Do not use local mode for untrusted model output, downloaded tasks, or malicious samples. The CLI requires `--trusted-local` even when local mode is in a config.

The Docker backend mounts only a disposable candidate workspace, disables networking, drops capabilities, uses an unprivileged UID, read-only root filesystem, PID/memory/CPU caps and timeout cleanup. Docker itself must be installed. No host Docker socket or API keys are passed into the candidate. Container images should be pinned by digest for controlled experiments. Docker integration was not run in the delivery environment.

Docker is defense in depth, not a hostile-code research sandbox. Bind-mounted workspace disk usage is not quota-enforced; use an isolated VM or quota-controlled filesystem for untrusted workloads. Linux local process groups are killed on timeout, including descendants. Windows local mode cannot guarantee descendant termination; use Docker there for generated code. Output capture is capped in memory and discards excess bytes while draining.

The verifier receives only declared candidate files in a fresh directory, then trusted tests. This prevents injecting a replacement unittest module through undeclared files. It does not stop an adversarial candidate solution from monkeypatching the test runner, calling process exit, or inspecting tests while executing. These are functional, non-adversarial microbenchmarks, not tamper-proof scoring. Stronger evaluation needs a separate trusted process/container protocol and adversarial grading tests.

Task manifests contain executable verifier commands and must be trusted. Oracle solutions are public by design but are not materialized into candidate workspaces or model messages. The full host repository remains visible to local processes; only container execution separates that host content.

Traces omit raw prompts, completions, command output, and credentials. Selected workspaces may contain generated code or task-sensitive data. Review artifacts before publishing. Network credentials are read from an environment variable only; remote HTTP endpoints require TLS. No authentication proxy, hosted dashboard, or multiuser service is bundled.
