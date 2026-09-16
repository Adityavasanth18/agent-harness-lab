# Measurement semantics

`agentharness.metrics.aggregate(events)` consumes recorded JSONL dictionaries. All durations use nanosecond monotonic timestamps and are reported in milliseconds. Timestamps must come from one clock domain. Request attempts, including retries, each contribute once. Request latency measures end minus start. Percentiles use linear interpolation between ordered observations; they are descriptive, not confidence estimates.

TTFT uses `first_token_ns` when available, otherwise the first **content** chunk timestamp. Providers must not include metadata-only chunks in that list. The report labels sample sources. Token inter-token latency requires actual per-token timestamps. Transport chunk arrival intervals are a separate metric and cannot establish token ITL. Empty distributions contain a zero count and null summary values.

Throughput is the sum of output tokens divided by the elapsed first-request-start to last-request-end window, including concurrent work and idle gaps. It is null if any request lacks output usage. The known subtotal is available separately. Estimated usage is counted and surfaced explicitly. Peak concurrency uses half-open intervals `[start, end)`, so adjoining requests do not overlap. Zero-duration events do not contribute to concurrency or the timing window.

Trials report boolean success outcomes only; unscored trials are counted separately. Comparisons group requests by provider and model. Architecture/configuration comparisons and recommendations use completed trials in `select_configurations`. Synthetic trials are identified and recommendations are kept separate from observed trials. A recommended configuration is merely the lowest measured p95 latency satisfying supplied bounds; it is not a claim of statistical superiority. The token constraint means mean input + output tokens per trial, including all attempts. Missing metrics disqualify a configuration when the respective constraint applies.

The HTML dashboard is self-contained and makes no network requests. Timeline filters do not alter whole-trace summary cards. Text is inserted as text rather than executable markup; embedded JSON escapes HTML-significant characters. Reports still contain the input trace, which may contain sensitive content. Share only after reviewing/redacting it.

Offline replay is trace inspection. The optional context counterfactual preserves system/developer messages and counts characters after retaining a chosen number of conversational messages. It does not execute a model or predict tokens, latency, success, or semantic equivalence. Tool dependencies can become invalid after truncation. Missing message bodies remain unavailable.

`derived_chunk_tpot_ms` is a separately labeled average proxy: `(last content chunk time - first content chunk time) / (authoritative output tokens - 1)`. It requires at least two content chunks and more than one nonestimated output token. It is not token ITL, because chunks may contain multiple tokens. No proxy is calculated from synthetic or estimated token usage.

Cost is computed from each uniquely matched trial's user-configured `input_cost_per_million` and `output_cost_per_million`, multiplying the corresponding recorded usage. Totals remain null when any request lacks rates, usage, or an unambiguous trial match. The known cost subtotal is separate. These configured rates are not fetched prices or billing records; use a consistent currency across an experiment. GPU time is null because the harness does not instrument a GPU.

A monotonic clock is scoped to one run ID. Multi-run aggregate timing windows and throughput are null because clocks may be unrelated; aggregate concurrency means maximum concurrency within any one run. `by_run` provides individual timing summaries. The dashboard timeline selects one run at a time.

Replay prefers captured message bodies when provided by an imported trace, otherwise uses runtime `message_sizes` metadata. Both policies preserve the first user task as well as system/developer instructions before retaining the last N later messages. Metadata-only character counts support size analysis without storing prompts.
