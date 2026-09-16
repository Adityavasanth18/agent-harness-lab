"""Append-only, process-local thread-safe JSONL event writer; no prompts or secrets."""
import json
import threading
import time
from pathlib import Path

class Trace:
    def __init__(self, path, run_id):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.lock = threading.Lock()

    def emit(self, event, **fields):
        record = dict(schema_version=1, event=event, run_id=self.run_id,
                      timestamp_ns=time.perf_counter_ns(), **fields)
        with self.lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        return record

def read_events(path):
    result = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict) or event.get("schema_version") != 1:
                    raise ValueError("unsupported trace schema")
                result.append(event)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"invalid trace at line {number}: {exc}") from exc
    return result
