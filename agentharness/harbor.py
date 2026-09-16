"""Export Harbor 1.3-format tasks; Harbor remains an optional external runner."""
import json
from pathlib import Path
import shlex
from .benchmarks import Task, write_files


def export_harbor(tasks: list[Task], output: str | Path) -> list[Path]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for task in tasks:
        # Tasks are normally validated by load_tasks; enforce ID locally as well.
        import re
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', task.id):
            raise ValueError('Unsafe task ID')
        folder = output / task.id
        folder.mkdir(exist_ok=False)
        write_files(task.files, folder / 'environment' / 'workspace')
        write_files(task.tests, folder / 'tests')
        files = {
            'instruction.md': task.instruction + '\n\nYour working directory is /app.\n',
            'task.toml': f'''schema_version = "1.3"

[task]
name = "agentharnesslab/{task.id}"

[metadata]
category = "programming"
difficulty = "easy"
suite = "deterministic-micro-v1"

[agent]
timeout_sec = 180.0

[verifier]
timeout_sec = 30.0

[environment]
network_mode = "no-network"
cpus = 1
memory_mb = 512
storage_mb = 1024
''',
            'environment/Dockerfile': 'FROM python:3.12-slim\nRUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git && rm -rf /var/lib/apt/lists/*\nWORKDIR /app\nCOPY workspace/ /app/\n',
            'tests/test.sh': '#!/bin/sh\nset -u\nmkdir -p /logs/verifier\nprintf "0\\n" > /logs/verifier/reward.txt\ncd /app || exit 1\nif PYTHONPATH=/tests:/app ' + shlex.join(task.verify) + '; then\n  printf "1\\n" > /logs/verifier/reward.txt\nfi\n',
            'solution/solve.sh': '#!/bin/sh\nset -eu\ncd /app\npython - <<\'HARBOR_ORACLE_PY\'\nimport json\nfrom pathlib import Path\nfiles=json.loads(' + repr(json.dumps(task.solution)) + ')\nfor name, content in files.items():\n    target=Path(name)\n    target.parent.mkdir(parents=True,exist_ok=True)\n    target.write_text(content,encoding="utf-8")\nHARBOR_ORACLE_PY\n',
        }
        write_files(files, folder)
        (folder / 'tests/test.sh').chmod(0o755)
        (folder / 'solution/solve.sh').chmod(0o755)
        paths.append(folder)
    return paths
