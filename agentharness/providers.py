"""Minimal streaming chat-completions transport, independent of an SDK."""
import json
import os
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

class RetryableError(RuntimeError):
    pass

class ProviderError(RuntimeError):
    pass

class HTTPProvider:
    synthetic = False

    def __init__(self, config):
        self.config = config
        parsed = urlparse(config.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("endpoint must be an http(s) URL")
        if parsed.username or parsed.password:
            raise ValueError("Do not put credentials in endpoint URLs")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Remote model endpoints require HTTPS")

    def complete(self, messages, **kwargs):
        payload = {"model": self.config.model, "messages": messages, "stream": True,
                   "stream_options": {"include_usage": True}, "temperature": 0}
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        key = os.environ.get(self.config.api_key_env)
        if key:
            headers["Authorization"] = "Bearer " + key
        request = urllib.request.Request(self.config.endpoint, json.dumps(payload).encode(), headers)
        chunks, timestamps, usage = [], [], {}
        try:
            with urllib.request.urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                done = False
                total = 0
                deadline = time.monotonic() + self.config.request_timeout_seconds
                for raw in response:
                    if time.monotonic() > deadline:
                        raise RetryableError("Streaming request deadline exceeded")
                    total += len(raw)
                    if total > 4_000_000:
                        raise ProviderError("Response exceeds 4 MB transport limit")
                    line = raw.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        done = True
                        break
                    item = json.loads(data)
                    if item.get("error"):
                        raise ProviderError("Endpoint returned an error event")
                    if item.get("usage"):
                        usage = item["usage"]
                    for choice in item.get("choices", []):
                        content = choice.get("delta", {}).get("content")
                        if content:
                            chunks.append(content)
                            timestamps.append(time.perf_counter_ns())
                if not done:
                    raise RetryableError("Stream terminated without [DONE]")
        except urllib.error.HTTPError as exc:
            if exc.code in {408, 429, 500, 502, 503, 504}:
                raise RetryableError(f"Transient HTTP {exc.code}") from None
            raise ProviderError(f"Endpoint HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise RetryableError(type(exc).__name__) from None
        except (ValueError, UnicodeError) as exc:
            raise ProviderError("Malformed streaming response") from exc
        return {"text": "".join(chunks), "chunk_timestamps_ns": timestamps,
                "first_token_ns": None,
                "token_timestamps_ns": [], "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"), "estimated_tokens": False}

class OracleProvider:
    """Known-answer fixture. Never a model quality or inference performance baseline."""
    synthetic = True

    def complete(self, messages, *, task, role, step, **kwargs):
        if role == "planner":
            data = {"plan": "Inspect specification, implement solution, verify behavior."}
        elif step == 0:
            data = {"tools": [{"name": "write", "path": path, "content": content} for path, content in task.solution.items()]}
        else:
            data = {"done": True}
        return {"text": json.dumps(data), "input_tokens": None, "output_tokens": None,
                "first_token_ns": None, "token_timestamps_ns": [], "chunk_timestamps_ns": [], "estimated_tokens": False}
