"""Docker command isolation and an explicitly trusted local development backend."""
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import stat
import threading
import uuid

@dataclass
class Result:
    returncode: int
    output: str
    timed_out: bool = False

class Sandbox:
    def __init__(self, root, backend="docker", image="python:3.12-slim", timeout=60, output_limit=12000):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.backend, self.image = backend, image
        self.timeout, self.output_limit = timeout, output_limit

    def path(self, relative):
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ValueError("Expected a relative workspace path")
        target = (self.root / relative).resolve()
        if target == self.root or self.root not in target.parents:
            raise ValueError("Path escapes workspace")
        # Reject even internal symlinks to avoid surprising indirection.
        current = self.root
        for part in Path(relative).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Symlink paths are not permitted")
        return target

    def write(self, relative, content):
        if not isinstance(content, str) or len(content) > 1_000_000:
            raise ValueError("File content must be text <= 1 MB")
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {relative}"

    def read(self, relative):
        target = self.path(relative)
        if not stat.S_ISREG(target.stat().st_mode):
            raise ValueError("Only regular files can be read")
        with target.open(encoding="utf-8") as stream:
            return stream.read(self.output_limit)

    def run(self, argv):
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x and '\x00' not in x for x in argv):
            raise ValueError("Command must be a nonempty argv string list")
        name = "ahl-" + uuid.uuid4().hex
        command = argv
        if self.backend == "docker":
            command = ["docker", "run", "--rm", "--name", name, "--network=none", "--read-only",
                       "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=128",
                       "--memory=512m", "--cpus=1", "--user=65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=64m",
                       "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", f"{self.root}:/workspace:rw", "-w", "/workspace", self.image, *argv]
        elif self.backend != "local":
            raise ValueError("Unsupported sandbox backend")
        safe_env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
        safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
        process = subprocess.Popen(command, cwd=self.root, env=safe_env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=(os.name != "nt"))
        captured = bytearray()
        def drain():
            # Continuously drain the pipe, retaining only the cap in RAM and no disk spool.
            with process.stdout:
                while True:
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    if len(captured) < self.output_limit:
                        captured.extend(data[:self.output_limit - len(captured)])
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        timed_out = False
        try:
            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
        finally:
            # Terminate descendants that may keep stdout open after the parent exits.
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if self.backend == "docker" and timed_out:
                subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        reader.join(timeout=2)
        return Result(124 if timed_out else process.returncode, captured.decode("utf-8", errors="replace"), timed_out)
