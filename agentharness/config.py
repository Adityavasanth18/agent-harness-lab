from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path

@dataclass(frozen=True)
class Config:
    architecture: str = "single"
    provider: str = "oracle"
    model: str = "local-test-fixture"
    endpoint: str = "http://localhost:8000/v1/chat/completions"
    api_key_env: str = "AHL_API_KEY"
    sandbox: str = "docker"
    docker_image: str = "python:3.12-slim"
    context_strategy: str = "sliding"
    context_chars: int = 48000
    compress_tool_outputs: bool = True
    max_steps: int = 12
    retries: int = 2
    parallel_agents: int = 2
    parallel_tools: bool = False
    adaptive: bool = False
    timeout_seconds: float = 60.0
    request_timeout_seconds: float = 120.0
    max_output_chars: int = 12000
    token_budget: int = 64000
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None

    def __post_init__(self):
        for key in ("max_steps", "retries", "parallel_agents", "context_chars", "max_output_chars", "token_budget"):
            if type(getattr(self, key)) is not int:
                raise ValueError(f"{key} must be an integer")
        for key in ("timeout_seconds", "request_timeout_seconds", "input_cost_per_million", "output_cost_per_million"):
            value = getattr(self, key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError(f"{key} must be a finite number")
        for key in ("compress_tool_outputs", "parallel_tools", "adaptive"):
            if type(getattr(self, key)) is not bool:
                raise ValueError(f"{key} must be boolean")
        choices = {"architecture": {"single", "planner", "parallel"},
                   "provider": {"oracle", "http"}, "sandbox": {"local", "docker"},
                   "context_strategy": {"full", "sliding", "summary"}}
        for key, allowed in choices.items():
            if getattr(self, key) not in allowed:
                raise ValueError(f"{key} must be one of {sorted(allowed)}")
        for key in ("max_steps", "parallel_agents", "timeout_seconds", "request_timeout_seconds", "max_output_chars", "token_budget"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if self.retries < 0 or self.context_chars < 2048:
            raise ValueError("retries must be nonnegative; context_chars must be >= 2048")
        if self.parallel_agents > 8:
            raise ValueError("parallel_agents is capped at 8")
        for key in ("input_cost_per_million", "output_cost_per_million"):
            if getattr(self, key) is not None and getattr(self, key) < 0:
                raise ValueError(f"{key} must be nonnegative")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text()))
