"""Character-bounded context. Extractive summaries are deliberately not LLM summaries."""
import json

class ContextOverflow(ValueError):
    pass

class Context:
    def __init__(self, system, task, strategy="sliding", max_chars=48000):
        self.pinned = [{"role": "system", "content": system}, {"role": "user", "content": task}]
        self.history = []
        self.strategy = strategy
        self.max_chars = max_chars
        self.compactions = 0

    def add(self, role, content):
        self.history.append({"role": role, "content": content})

    def messages(self):
        size = lambda messages: len(json.dumps(messages, ensure_ascii=False))
        if size(self.pinned) > self.max_chars:
            raise ContextOverflow("Pinned instruction exceeds context budget")
        if size(self.pinned + self.history) <= self.max_chars:
            return self.pinned + self.history
        if self.strategy == "full":
            raise ContextOverflow("Full context exceeds configured budget")
        retained = list(self.history)
        removed = []
        while retained and size(self.pinned + retained) > self.max_chars:
            removed.append(retained.pop(0))
        if self.strategy == "summary" and removed:
            content = "Extractive memory (older text, may be incomplete):\n" + "\n".join(m["content"][:160] for m in removed[-8:])
            memory = {"role": "user", "content": content}
            while retained and size(self.pinned + [memory] + retained) > self.max_chars:
                retained.pop(0)
            if size(self.pinned + [memory] + retained) <= self.max_chars:
                retained.insert(0, memory)
        self.history = retained
        self.compactions += 1
        return self.pinned + self.history

def compress(text, limit):
    if len(text) <= limit:
        return text
    marker = f"\n... truncated {len(text) - limit} characters ...\n"
    available = max(0, limit - len(marker))
    return text[:available // 2] + marker + text[-(available - available // 2):] if available else marker[:limit]
