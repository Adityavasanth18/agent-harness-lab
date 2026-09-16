"""Import observed Harbor trial summaries; never synthesize inference requests.

Source schema inspected 2026-09-16:
https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/trial/result.py
https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/agent/context.py
https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/job/result.py
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Missing or invalid {name}')
    return value


def _timestamp(value, name):
    _text(value, name)
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'Invalid {name}: ISO datetime required') from exc
    if stamp.tzinfo is None:
        # Older Harbor results use naive local datetimes. Durations are valid in
        # that clock domain, but cross-job synchronization cannot be inferred.
        stamp = stamp.replace(tzinfo=timezone.utc)
    delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return ((delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds) * 1000


def _usage(context):
    if context is None:
        return None
    if not isinstance(context, dict):
        raise ValueError('agent_result must be an object or null')
    result = {}
    for name in ('n_input_tokens', 'n_cache_tokens', 'n_output_tokens', 'cost_usd'):
        value = context.get(name)
        if value is not None:
            valid = isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
            if name != 'cost_usd':
                valid = valid and isinstance(value, int)
            if not valid:
                raise ValueError(f'Invalid {name}')
        result[name] = value
    return result


def _convert(data, source, run_id=None):
    if not isinstance(data, dict):
        raise ValueError('Trial must be an object')
    trial_id = _text(data.get('id'), 'trial id')
    task = _text(data.get('task_name'), 'task_name')
    _text(data.get('trial_name'), 'trial_name')
    agent = data.get('agent_info')
    if not isinstance(agent, dict):
        raise ValueError('Missing agent_info')
    name = _text(agent.get('name'), 'agent_info.name')
    start = _timestamp(data.get('started_at'), 'started_at')
    end = _timestamp(data.get('finished_at'), 'finished_at')
    if end < start:
        raise ValueError('finished_at precedes started_at')
    a = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
    b = datetime.fromisoformat(data['finished_at'].replace('Z', '+00:00'))
    if (a.tzinfo is None) != (b.tzinfo is None):
        raise ValueError('Mixed naive and timezone-aware timestamps')
    if data.get('step_results'):
        raise ValueError('Multi-step Harbor trials are not supported by this importer')
    exception = data.get('exception_info')
    if exception is not None and not isinstance(exception, dict):
        raise ValueError('Invalid exception_info')
    error = _text(exception.get('exception_type'), 'exception_type') if exception else None
    verifier = data.get('verifier_result')
    rewards = verifier.get('rewards') if isinstance(verifier, dict) else None
    if verifier is not None and not isinstance(verifier, dict):
        raise ValueError('Invalid verifier_result')
    if rewards is None:
        if error is None:
            raise ValueError('Missing reward for completed non-error trial')
        success = None  # Infrastructure/agent errors remain unscored, not zero reward.
    else:
        if not isinstance(rewards, dict) or set(rewards) != {'reward'}:
            raise ValueError('Only one binary reward named reward is supported')
        reward = rewards['reward']
        if isinstance(reward, bool) or not isinstance(reward, (int, float)) or reward not in (0, 1):
            raise ValueError('Binary reward must be 0 or 1')
        success = bool(reward) if error is None else None
    model = agent.get('model_info')
    if model is not None and not isinstance(model, dict):
        raise ValueError('Invalid model_info')
    if model:
        _text(model.get('name'), 'model_info.name')
    digest = hashlib.sha256(str(source.parent.parent.resolve()).encode()).hexdigest()[:16]
    return dict(schema_version=1, event='trial', run_id=run_id or 'harbor-' + digest,
                timestamp_ns=end, start_ns=start, end_ns=end, clock_source='harbor_datetime',
                task_id=task, trial_id=trial_id, agent_id=trial_id + ':' + name,
                architecture='harbor:' + name, provider=(model or {}).get('provider'),
                model=(model or {}).get('name'), success=success, error=error,
                synthetic=name in ('oracle', 'nop'), source='harbor',
                source_file=str(source), task_hash=data.get('task_checksum'),
                harbor_agent_version=agent.get('version'), harbor_rewards=rewards,
                harbor_usage=_usage(data.get('agent_result')),
                measurement_scope='trial_summary', config={})


def import_harbor(path, output_path):
    """Read one result JSON or recursively a job(s) directory; write fresh JSONL.

    Supports completed single-step TrialResult and JobResult.trial_results.
    Known job summaries without embedded trials are ignored when child trial
    files exist. Invalid files, empty imports, conflicting duplicate IDs and
    unsupported scoring are rejected before the output is created.
    """
    path, output_path = Path(path), Path(output_path)
    if not path.exists():
        raise ValueError(f'Harbor path does not exist: {path}')
    sources = [path] if path.is_file() else sorted(path.rglob('result.json'))
    records = {}
    loaded = {}
    jobs = {}
    for source in sources:
        try:
            loaded[source] = json.loads(source.read_text(encoding='utf-8'))
        except (ValueError, OSError) as exc:
            raise ValueError(f'Cannot import {source}: {exc}') from exc
        data = loaded[source]
        if isinstance(data, dict) and 'stats' in data and 'n_total_trials' in data and 'id' in data:
            jobs[source.parent.resolve()] = 'harbor-job-' + _text(data['id'], 'job id')
    for source in sources:
        try:
            data = loaded[source]
            if not isinstance(data, dict):
                raise ValueError('Result must be an object')
            if 'task_name' in data or 'trial_name' in data:
                trials = [data]
                run_id = jobs.get(source.parent.parent.resolve())
            elif 'stats' in data and 'n_total_trials' in data and 'id' in data:
                trials = data.get('trial_results', [])
                run_id = jobs.get(source.parent.resolve())
                if not isinstance(trials, list):
                    raise ValueError('trial_results must be a list')
            else:
                raise ValueError('Unrecognized Harbor result schema')
            for trial in trials:
                event = _convert(trial, source, run_id)
                key = event['trial_id']
                if key in records:
                    if records[key][0] != trial:
                        raise ValueError(f'Conflicting duplicate trial: {key}')
                    continue
                records[key] = (trial, event)
        except (ValueError, TypeError, OSError) as exc:
            raise ValueError(f'Cannot import {source}: {exc}') from exc
    if not records:
        raise ValueError('No completed Harbor trial results found')
    events = sorted((item[1] for item in records.values()), key=lambda e: (e['start_ns'], e['trial_id']))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x', encoding='utf-8') as stream:
        for event in events:
            stream.write(json.dumps(event, allow_nan=False) + '\n')
    return events
