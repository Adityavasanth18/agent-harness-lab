"""Versioned, transparent microbenchmark contracts and safe workspace creation."""
from dataclasses import dataclass, field
import json
from pathlib import Path, PurePosixPath
import re


@dataclass(frozen=True)
class Task:
    id: str
    instruction: str
    files: dict[str, str]
    solution: dict[str, str]
    tests: dict[str, str]
    verify: list[str] = field(default_factory=lambda: ['python', '-m', 'unittest', '-v', 'test_solution'])


def safe_relative(name: str) -> str:
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError(f'Invalid task path: {name!r}')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts or ':' in name:
        raise ValueError(f'Unsafe task path: {name!r}')
    return str(path)


def write_files(files: dict[str, str], workspace: str | Path) -> None:
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        target = root / safe_relative(name)
        # Reject symlinks even if they happen to resolve within this workspace.
        if any(p.is_symlink() for p in [target, *target.parents] if p != root and root in p.parents):
            raise ValueError(f'Symlink task path: {name}')
        if not target.resolve().is_relative_to(root):
            raise ValueError(f'Escaping task path: {name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')


def load_tasks(path: str | Path) -> list[Task]:
    path = Path(path)
    manifests = [path] if path.is_file() else sorted(path.rglob('task.json'))
    if not manifests:
        raise ValueError(f'No task.json manifests found in {path}')
    tasks = []
    ids = set()
    for manifest in manifests:
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if not isinstance(data.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', data['id']):
            raise ValueError(f'Invalid task ID in {manifest}')
        if data['id'] in ids:
            raise ValueError(f'Duplicate task ID: {data["id"]}')
        ids.add(data['id'])
        if not isinstance(data.get('instruction'), str) or not data['instruction'].strip():
            raise ValueError(f'Missing instruction in {manifest}')
        for key in ('files', 'solution', 'tests'):
            mapping = data.get(key)
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError(f'{key} must be a nonempty file mapping in {manifest}')
            normalized = set()
            for name, content in mapping.items():
                clean = safe_relative(name)
                if clean in normalized or not isinstance(content, str):
                    raise ValueError(f'Invalid or duplicate file in {manifest}')
                normalized.add(clean)
            data[key] = {safe_relative(name): value for name, value in mapping.items()}
        if set(data['files']) & set(data['tests']):
            raise ValueError(f'Candidate and verifier paths overlap in {manifest}')
        verify = data.get('verify', ['python', '-m', 'unittest', '-v', 'test_solution'])
        if not isinstance(verify, list) or not verify or not all(isinstance(x, str) and x and '\x00' not in x for x in verify):
            raise ValueError(f'Invalid verifier argv in {manifest}')
        tasks.append(Task(**{k: data[k] for k in ('id','instruction','files','solution','tests')}, verify=verify))
    return tasks


def materialize(task: Task, workspace: str | Path) -> None:
    """Copy candidate starters only; never expose oracle or hidden verifier files."""
    write_files(task.files, workspace)
