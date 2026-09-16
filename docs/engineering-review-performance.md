# Engineering review: performance and trace integrity

Reviewer role: inference/performance engineer. This is an automated engineering review, not a claim of external human approval.

## Scope

Independently inspected runtime, providers, sandbox, context, configuration, and trace writer. Implemented and reviewed aggregation, standalone dashboard, measured configuration selection, and offline replay. Reviewed metrics against their required inputs rather than assuming streaming chunks represent individual tokens.

## Findings and remediation

- HTTP content chunks initially populated the first-token timestamp as though token timing were available. Provider output now leaves actual token timestamps unavailable; metrics derive TTFT from the first content chunk and label that source.
- Trial IDs existed only on trial events, breaking exact request joins. The runtime now records request trial IDs. Analysis also supports older traces through run/task/time matching, with ambiguous cost matches left unknown.
- Numeric configuration fields needed type and finite-value validation. Runtime owner added validation.
- Capping output only when reading a temporary spool did not prevent disk exhaustion. Runtime owner replaced spooling with bounded pipe draining. Nonregular-file reads are rejected to prevent FIFO hangs.
- Counterfactual replay lacked input because sensitive prompts are intentionally absent from traces. Runtime now records role/character metadata. Replay uses that metadata while preserving system/developer instructions and the initial user task. It makes no model outcome predictions.
- Combining absolute monotonic timestamps across runs risks comparing unrelated clock domains. Combined multi-run throughput and timing windows are now null. Concurrency is the maximum observed within one run, per-run metrics remain available, and the timeline selects exactly one run.
- Dashboard embeds JSON with HTML-significant characters escaped and inserts displayed values using text nodes. A malicious model name cannot close the data script tag. Timeline bounds no longer spread large arrays into function arguments.

## Validation

Thirteen focused unit tests cover unavailable data, exact chunk versus token distinctions, touching and overlapping intervals, partial usage, quantiles, script-tag escaping, optimizer constraints and trial matching, configured-rate costs, derived TPOT, multiple clock domains, and metadata replay. Generated dashboard JavaScript passes Node syntax validation.

## Remaining limits

Derived TPOT uses chunk endpoints and authoritative output token counts; it is an average proxy, not token ITL. True token ITL and GPU seconds require instrumentation not supplied by generic streaming HTTP endpoints. Configured-rate cost is an estimate in the user's chosen currency, not a billing record. Missing usage or prices remains unknown.

A run ID must identify one clock domain. Reusing a run ID across unrelated machines or reboots violates the trace contract. Synthetic and real runs should be analyzed separately; the optimizer returns separate recommendations. Pooled distributions are descriptive and do not establish statistical superiority.

Token budgeting is a soft per-agent preflight estimate and cannot guarantee provider-side limits or account for unknown failed-request usage. Local execution is explicitly trusted development mode. Docker command isolation does not itself provide host filesystem quotas. Hidden verification resists ordinary agent editing, but generated code executing alongside Python tests is not a tamper-proof adversarial grader; process exits and runtime test interference remain part of the evaluator trust boundary.

Review conclusions are limited to the inspected code and automated tests. No live paid model, GPU instrumentation, remote container fleet, or external benchmark validation was performed by this reviewer.
