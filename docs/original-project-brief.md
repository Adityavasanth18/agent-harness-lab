Yes. I looked at this as three separate reviewers because this NVIDIA role is unusually specific. It is not really a generic “AI software engineer” role; it sits at the intersection of **coding agents + systems engineering + inference performance + experimental evaluation**. The posting specifically asks for coding-agent harness experience, Harbor, Codex/Claude Code, and metrics such as TTFT, throughput, and ITL. ([Jobgether](https://jobgether.com/offer/6aaa483d02f009d735620784-software-engineer-coding-agent-harness-engineering---new-college-grad-2026?utm_source=chatgpt.com "Software Engineer, Coding Agent Harness Engineering - New College Grad 2026 at NVIDIA"))

### Reviewer 1 — NVIDIA Coding-Agent Engineer

My first question looking at a GitHub profile would be:

> “Has this person actually built the machinery around a coding model, or did they just call an LLM API?”

For this position, a normal chatbot, RAG app, LangChain workflow, PDF Q&A system, or basic multi-agent demo would not differentiate you much.

I would want to see a project where you control the **harness itself**: context management, tool execution, planning, retries, sandboxing, subagents, parallelism, compaction, failure recovery and evaluation.

That matches how NVIDIA itself describes harness engineering: the harness includes things like tools, context handling, compaction, runtime behavior and middleware surrounding the underlying model. ([NVIDIA](https://www.nvidia.com/gtc/session-catalog/sessions/gtc26-s82448/?utm_source=chatgpt.com "Open, Trusted, and Observable: Deploying AI Agents at Enterprise Scale S82448 | GTC San Jose 2026 | NVIDIA On-Demand"))

### Reviewer 2 — Inference/Performance Engineer

I would immediately look for something most applicants will probably not have:

**Can this person connect agent architecture to inference behavior?**

NVIDIA explicitly asks about TTFT, ITL and throughput. TTFT measures the delay before the first output token; ITL measures the time between subsequent generated tokens. NVIDIA also points out that queueing, prompt length/prefill, concurrency and KV-cache pressure can influence these metrics. ([NVIDIA Docs](https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html?utm_source=chatgpt.com "Metrics — NVIDIA NIM LLMs Benchmarking"))

So your GitHub should contain actual experiments rather than claims like:

> “Built a high-performance AI agent.”

It should show something like:

**Parallel subagents = 4**
→ success rate changes
→ number of inference requests changes
→ peak concurrency changes
→ TTFT p50/p95 changes
→ ITL changes
→ tokens/sec changes
→ total tokens changes
→ wall-clock completion time changes
→ cost changes.

That starts looking like research NVIDIA could actually care about.

### Reviewer 3 — Hiring Manager / Resume Reviewer

I would rather see **2 exceptional relevant projects + ContractGraph** than eight unrelated AI projects.

The strongest portfolio for this particular role would look approximately like this:

| Resume positionProjectWhat it demonstrates |                                 |                                       |
| ------------------------------------------ | ------------------------------- | ------------------------------------- |
| #1                                         | **AgentHarnessLab**             | coding-agent harness engineering      |
| #2                                         | **AgentScope / AgentPerf**      | inference workload profiling          |
| #3                                         | **ContractGraph**               | serious C++/systems/graph engineering |
| Optional                                   | Harbor contribution / benchmark | open source + scientific evaluation   |

Your existing **ContractGraph** project is useful because it demonstrates C++20, graph algorithms, parsers, dependency analysis, CI/testing and systems thinking. But by itself it doesn't satisfy the central requirement of this role.

The project I would build first is this.

---

# 1. AgentHarnessLab

### Coding Agent Harness Architecture & Evaluation Platform

This should be your flagship NVIDIA project.

Don't build another wrapper around Claude or Codex.

Build an actual experimental coding-agent harness.

Conceptually:

```text
                 ┌─────────────────┐
                 │ Coding Task     │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │ Harness Runtime │
                 └────────┬────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
      Planner        Context Engine    Tool Router
          ↓               ↓               ↓
     Subagents       Compression       Terminal
          ↓          / Pruning         Git
          ↓                            Tests
          └───────────────┬───────────────┘
                          ↓
                     LLM / Agent
                  Codex / Claude Code
                          ↓
                       Verifier
                          ↓
                Performance Tracing
```

Make architectural components configurable.

For example:

```yaml
strategy:
  planner: enabled
  max_subagents: 4
  parallel_subagents: true

context:
  strategy: summarize
  max_tokens: 32000
  tool_result_compression: true

execution:
  retries: 2
  test_feedback: true
  sandbox: docker
```

Then benchmark variants.

**Experiment A**

```text
Single agent
vs
Planner → Executor
```

**Experiment B**

```text
1 subagent
vs
2
vs
4
vs
8
```

**Experiment C**

```text
Full context
vs
Sliding window
vs
Summarized context
```

**Experiment D**

```text
Raw tool outputs
vs
Compressed tool outputs
```

**Experiment E**

```text
Serial tool execution
vs
Parallel execution
```

That is almost literally what the job description means by researching the impact of different harness architectural decisions.

---

# 2. AgentScope / AgentPerf

### Coding-Agent Inference Workload Profiler

This could be the project that makes someone stop scrolling through your resume.

Instrument coding-agent executions.

For every LLM request capture:

```text
timestamp
agent
model
input tokens
output tokens

TTFT
ITL
end-to-end latency

tool calls
tool duration

context size
conversation turn

concurrency

subagent ID
parent agent ID

retry count
success/failure
```

Then create a workload timeline:

```text
TIME ───────────────────────────────────────────>

Planner       ███████

Agent 1             █████████████
Agent 2             ██████████
Agent 3             ███████████████

Tool call                 ██

Agent 1                         ████████

Verifier                                  █████
```

Now correlate architecture with inference.

For example:

```text
                       Serial       4 Subagents

Success                  61%           73%

Median TTFT             420ms         690ms
P95 TTFT                780ms        1430ms

ITL                      31ms          37ms

Peak concurrency          1             4

Total tokens            41K           67K

Wall time               382s          224s
```

Those numbers are only an illustration—your repository should generate the real measurements.

NVIDIA's benchmarking documentation specifically treats TTFT, ITL, TPS and request throughput as key inference-performance metrics. ([NVIDIA Developer](https://developer.nvidia.com/blog/?p=98215\&utm_source=chatgpt.com "LLM Inference Benchmarking: Fundamental Concepts | NVIDIA Technical Blog"))

A dashboard could then expose:

```text
HARNESS WORKLOAD ANALYZER

Task Completion       74.8%

Inference
TTFT p50              441 ms
TTFT p95              914 ms
ITL p50                29 ms
Output throughput     812 tok/s

Agent
Model calls           143
Tool calls            297
Peak subagents          6
Context tokens        1.8M

Efficiency
Tokens / solved task  24.1K
GPU sec / solved task   ...
Cost / solved task      ...
```

Now you have something directly related to **“analyze inference workload dynamics of leading agentic harnesses under realistic conditions.”**

---

# 3. HarnessTune

### Adaptive Coding-Agent Harness Optimizer

This would take the previous two projects one step further.

Instead of simply measuring configurations, automatically search for better harness configurations.

Input:

```text
task
model
latency objective
token budget
quality requirement
```

Configuration space:

```text
number of agents
parallelism

planning depth

context strategy

tool-result compression

retry policy

test frequency

model routing

context limits
```

Objective could be:

```text
maximize:

task_success

subject to:

TTFT < threshold
token_budget < threshold
cost < threshold
```

Then have the system execute experiments and produce:

```text
Baseline

Success:     63%
Wall time:   341s
Tokens:      58K


Configuration #27

Success:     72%
Wall time:   238s
Tokens:      49K
```

Again: actual measured results, not invented numbers.

That demonstrates something extremely important:

**data → engineering decision → measurable improvement**

And NVIDIA explicitly lists the ability to translate data into product improvements as a differentiator for this role. ([Jobgether](https://jobgether.com/offer/6aaa483d02f009d735620784-software-engineer-coding-agent-harness-engineering---new-college-grad-2026?utm_source=chatgpt.com "Software Engineer, Coding Agent Harness Engineering - New College Grad 2026 at NVIDIA"))

---

# 4. Harbor contribution / Agent benchmark

I would strongly consider this as well.

Harbor is not just a random keyword in the posting. It currently supports evaluating agents including Claude Code, Codex, OpenHands and others, and supports running benchmark jobs in container environments and scaling them across cloud sandbox providers. ([GitHub](https://github.com/harbor-framework/harbor/blob/main/AGENTS.md?utm_source=chatgpt.com "harbor/AGENTS.md at main · harbor-framework/harbor · GitHub"))

Harbor's task structure naturally gives you:

```text
instruction.md
task.toml
environment/
solution/
tests/
```

and supports custom agents, datasets and containerized evaluations. ([Harbor](https://www.harborframework.com/docs/core-concepts?utm_source=chatgpt.com "Core Concepts"))

So build something like:

### Long-Horizon HarnessBench

Create perhaps **15–30 carefully designed coding tasks** specifically testing harness behaviors.

For example:

```text
01-context-recovery
02-long-build-debug
03-test-driven-repair
04-parallel-code-search
05-large-repository-navigation
06-tool-failure-recovery
07-context-overflow
08-dependency-upgrade
09-multi-service-debug
10-long-horizon-refactor
```

Then evaluate:

```text
Claude Code
Codex
your harness
your harness + planner
your harness + parallel agents
your harness + compression
```

Harbor can already evaluate popular coding agents and execute trials across containerized environments, which is exactly why this would be credible rather than building your own artificial benchmark runner. ([GitHub](https://github.com/harbor-framework/harbor?utm_source=chatgpt.com "GitHub - harbor-framework/harbor: Framework for evaluating and improving agents · GitHub"))

Even better would be getting a meaningful PR accepted upstream into Harbor or an associated benchmark.

That is much stronger than simply writing **“familiar with Harbor”** on the resume.

---

## And this changes how I view your existing projects

For this application I would **keep ContractGraph**, but I would not lead with ProcureBridge or ChannelBridge unless we substantially add genuine agent-harness engineering to them.

Instead, imagine converting ContractGraph into an evaluation workload:

```text
ContractGraph Agent Challenge

Agent receives:

old OpenAPI specification
new OpenAPI specification
10-service repository

Agent must:

discover breaking change
identify affected services
modify clients
update tests
build repositories
resolve failures
verify migration
```

Now run that task through AgentHarnessLab.

Suddenly your projects reinforce one another:

```text
              AgentHarnessLab
                     │
                     ↓
              Harness experiments
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
   ContractGraph Tasks      SWE/Terminal Tasks
          │                     │
          └──────────┬──────────┘
                     ↓
                 Harbor
                     ↓
              AgentScope
                     ↓
        TTFT / ITL / Throughput
                     ↓
               HarnessTune
                     ↓
          Optimized architecture
```

**That is a portfolio story.**

It doesn't look like:

> “Student made four projects with ChatGPT.”

It looks like:

> “This engineer is investigating coding-agent architecture and its effects on inference workloads.”

That distinction is enormous for this particular position.

### The three-reviewer consensus

**Recruiter:** I need to see *Coding Agent Harness, Harbor, Codex/Claude Code, inference benchmarking, C++/systems, open source* almost immediately.

**Senior engineer:** I want reproducible experiments and the source code for the harness—not another API wrapper.

**Hiring manager:** I want evidence you can discover something from data and then change the system because of what you discovered.

So if we are specifically targeting **NVIDIA JR2023749**, I would make your portfolio:

**AgentHarnessLab → AgentScope → ContractGraph → Harbor open-source contribution.**

ProcureBridge and ChannelBridge can still live on GitHub/your portfolio, but they shouldn't consume the prime resume space for this application.

And importantly, I would make **AgentHarnessLab + AgentScope one deeply integrated flagship system rather than two superficial repositories**. Harbor itself is designed around agents, tasks, environments and parallel experiments, so using it as part of the actual experimental pipeline would align very closely with what NVIDIA is asking for. ([GitHub](https://github.com/harbor-framework/harbor/blob/main/AGENTS.md?utm_source=chatgpt.com "harbor/AGENTS.md at main · harbor-framework/harbor · GitHub"))

If we build that properly—with the architecture, experiments, Docker environments, benchmark suite, dashboards, CI, research report and polished GitHub README—it would be much more targeted to this opening than another generic “AI agent” project.