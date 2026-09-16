"""Offline trace inspection and explicit context-size counterfactuals."""
from .metrics import aggregate


def inspect_trace(events):
    events = list(events)
    ordered = sorted(events, key=lambda e: e.get("start_ns", 0))
    return {"mode": "offline_inspection", "executed": False, "report": aggregate(events), "timeline": ordered}


def context_counterfactual(events, keep_last_messages=4):
    if not isinstance(keep_last_messages, int) or keep_last_messages < 0:
        raise ValueError("keep_last_messages must be a nonnegative integer")
    rows = []
    for e in events:
        if e.get("event") != "request":
            continue
        messages = e.get("messages")
        metadata_only = not isinstance(messages, list)
        if metadata_only:
            sizes = e.get("message_sizes")
            if not isinstance(sizes, list):
                rows.append({"task_id": e.get("task_id"), "available": False,
                             "reason": "Trace has no captured message sizes; context cannot be reconstructed."})
                continue
            messages = sizes
        # Preserve system/developer instructions and the first user task message.
        pinned, conversation, task_seen = [], [], False
        for m in messages:
            role = m.get("role")
            if role in ("system", "developer") or (role == "user" and not task_seen):
                pinned.append(m)
                if role == "user":
                    task_seen = True
            else:
                conversation.append(m)
        retained = pinned + (conversation[-keep_last_messages:] if keep_last_messages else [])
        def chars(ms):
            if metadata_only:
                values = [m.get("characters") for m in ms]
                return sum(values) if all(isinstance(v, int) and v >= 0 for v in values) else None
            return sum(len(str(m.get("content", ""))) for m in ms)
        rows.append({"task_id": e.get("task_id"), "available": True, "metadata_only": metadata_only,
                     "original_messages": len(messages), "retained_messages": len(retained),
                     "original_characters": chars(messages), "retained_characters": chars(retained),
                     "predicted_tokens": None, "predicted_latency_ms": None, "predicted_success": None})
    return {"mode": "context_size_counterfactual", "executed": False,
            "policy": {"keep_last_messages": keep_last_messages, "preserve_system_and_developer": True, "preserve_initial_user_task": True},
            "requests": rows,
            "limitations": "Character counts only. No model execution, token prediction, quality prediction, or latency prediction. Truncation may break tool-call dependencies."}
