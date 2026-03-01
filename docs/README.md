# Apex

**Self-hosted autonomous AI agent platform — works with any OpenAI-compatible LLM.**

Apex is a modular, locally-run AI agent that plans, executes, and verifies tasks using the tools you give it. Point it at Ollama, an OpenAI-compatible endpoint, or Anthropic's API and it starts working immediately — no cloud accounts, no data leaving your machine unless you choose.

The agent follows a strict **Plan → Execute → Verify** loop. Every action is logged to a tamper-evident ledger, every tool call is verified before moving to the next step, and the agent escalates to you when its confidence drops below your configured threshold.

---

## Features

| Category | What's included |
|---|---|
| **LLM providers** | Ollama (local), OpenAI API, Anthropic API, any OpenAI-compatible endpoint |
| **Memory** | Persistent deep memory, experience engine, dream-cycle reflection, learning engine |
| **Security** | Legal compliance gating, engagement authorisation, forensic evidence collection, penetration testing toolkit, malware analysis sandbox, network IDS, bug bounty scanning |
| **Tools** | Code generation and review, book and app writing assistants, data annotation |
| **Hardware** | Raspberry Pi Pico serial bridge, AR glasses, drone fleet control, mobile WebSocket bridge |
| **Infrastructure** | AWS S3 + Dropbox cloud sync, Docker service deployment, self-improvement, backup and recovery, notification centre |
| **Interfaces** | Desktop dashboard, voice activation (wake-word), screen reading and control |
| **Governance** | Full audit ledger, tool reputation tracking, confidence scoring, auto-recovery on failure |

---

## Requirements

- Python 3.10 or later
- A running LLM — any of:
  - [Ollama](https://ollama.com) running locally (default, no API key needed)
  - An OpenAI API key
  - An Anthropic API key
  - Any other OpenAI-compatible endpoint

---

## Installation

### 1. Clone or copy the apex folder

```
C:\ai_agent\
└── apex\          ← this folder
    ├── core\
    ├── memory\
    ├── security\
    └── ...
```

### 2. Install dependencies

**Core only** (LLM calls, config, basic tasks):
```bash
cd C:\ai_agent\apex
pip install -r requirements.txt
```

**Everything** (vision, speech, cloud, containers, security tools):
```bash
pip install .[full]
```

**Selective subsystems:**
```bash
pip install .[vision]      # screen control, OCR, image processing
pip install .[speech]      # microphone input, text-to-speech
pip install .[cloud]       # AWS S3, Dropbox
pip install .[security]    # cryptography
pip install .[containers]  # Docker SDK
```

### 3. Add apex to your Python path

If you are not installing via pip, add the parent directory to `PYTHONPATH` so that `import apex` resolves correctly:

```bash
# Windows
set PYTHONPATH=C:\ai_agent

# Linux / macOS
export PYTHONPATH=/path/to/ai_agent
```

---

## Configuration

All behaviour is controlled by a single file: `apex/core/config.yaml`.

### Provider

```yaml
# Which LLM backend to use. Switch without touching any other code.
provider: ollama    # options: ollama | openai | anthropic
```

### Ollama (default — no API key needed)

```yaml
providers:
  ollama:
    endpoint: http://localhost:11434
    model: llama3.3:70b-instruct-q4_K_M
    timeout: 120
    parameters:
      temperature: 0.3
      num_ctx: 16384
```

Start Ollama and pull a model:
```bash
ollama serve
ollama pull llama3.3:70b-instruct-q4_K_M
```

Any model that fits in your VRAM works. Smaller options: `llama3.2:3b`, `mistral:7b`, `qwen2.5:14b`.

### OpenAI

```yaml
provider: openai

providers:
  openai:
    endpoint: https://api.openai.com/v1
    model: gpt-4o
    api_key_env: OPENAI_API_KEY
    timeout: 60
    parameters:
      temperature: 0.3
      max_tokens: 4096
```

```bash
set OPENAI_API_KEY=sk-...
```

Any OpenAI-compatible endpoint works here — LM Studio, vLLM, Together AI, Groq — just change `endpoint` and `model`.

### Anthropic

```yaml
provider: anthropic

providers:
  anthropic:
    endpoint: https://api.anthropic.com/v1
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
    timeout: 60
```

```bash
set ANTHROPIC_API_KEY=sk-ant-...
```

### Storage paths

```yaml
storage:
  base:    C:/ai_agent/apex/data        # root for all runtime data
  memory:  C:/ai_agent/apex/memory      # persistent memory files
  logs:    C:/ai_agent/apex/data/logs   # audit ledger and agent logs
  reports: C:/ai_agent/apex/data/reports
  cache:   C:/ai_agent/apex/data/cache
  exports: C:/ai_agent/apex/data/exports
```

All directories are created automatically on first run.

### Agent behaviour

```yaml
agent:
  name: Apex
  trust_threshold: 70    # escalate to user when confidence < 70 %
  max_retries: 3         # retry a failed tool call up to 3 times
  audit_trail: true      # write every action to the ledger
  verify_actions: true   # verify each step before proceeding
```

### Enabling / disabling modules

```yaml
modules:
  memory:         true
  security:       true
  tools:          true
  hardware:       true
  infrastructure: true
  interfaces:     true
```

Set a module to `false` to skip loading it entirely at startup. Useful when those optional dependencies (e.g. OpenCV, Docker SDK) are not installed.

### Logging

```yaml
logging:
  level: INFO              # DEBUG | INFO | WARNING | ERROR
  file: C:/ai_agent/apex/data/logs/apex.log
  max_size_mb: 10
  backup_count: 5
```

---

## Running Apex

### Quickstart (Python)

```python
from apex.core.apex import create_apex

# Bootstrap — discovers all enabled tools automatically
apex = create_apex()

# Execute a task
result = apex.execute_task("Summarise every Python file in C:/projects")
print(result)
```

### With background systems

```python
apex = create_apex(start_background=True)
# Dream cycle (nightly reflection) and network monitoring now run in the background
```

### Check system status

```python
print(apex.status())
# {
#   "tools_registered": 87,
#   "tools_enabled": 87,
#   "learning_active": True,
#   "perception_active": True,
#   "mobile_active": False,
#   "ledger_session": "session_1748000000",
#   "bg_threads": 1
# }
```

### Low-level — manual wiring

If you only want the core agent without loading every module:

```python
from apex.core import (
    ToolRegistry, call_ai,
    create_agent, create_verification_engine
)

registry = ToolRegistry()
registry.register("my_tool", "Does a thing", my_fn, module="custom")

verifier = create_verification_engine(registry)
agent    = create_agent(call_ai, registry, verifier)
result   = agent.execute_task("Do the thing using my_tool")
```

---

## Module overview

```
apex/
├── core/                    Bootstrap, config, LLM bridge, tool registry
│   ├── apex.py              Main entry point — wires everything together
│   ├── ai_bridge.py         Universal LLM caller (Ollama / OpenAI / Anthropic)
│   ├── agent_core.py        Plan → Execute → Verify engine
│   ├── tool_registry.py     Central tool hub with auto-discovery
│   ├── verification_engine.py  Reality-grounding: checks actions actually worked
│   ├── task_ledger.py       Tamper-evident audit trail
│   └── config.yaml          Single configuration file
│
├── memory/                  Persistent agent memory and learning
│   ├── memory_tools.py      Surface and deep memory read/write
│   ├── experience_engine.py Tool reputation and task pattern tracking
│   ├── dream_cycle.py       Idle reflection and insight synthesis
│   └── learning_engine.py   Knowledge-gap tracking and self-study queue
│
├── security/                Ethical security toolkit
│   ├── legal_compliance_framework.py   Jurisdiction-aware legal gating
│   ├── authorization_manager.py        Engagement contracts and access control
│   ├── forensic_evidence_handler.py    Chain-of-custody evidence collection
│   ├── malware_analysis_sandbox.py     Isolated malware examination
│   ├── penetration_testing_toolkit.py  Authorised pentest framework
│   ├── security_monitoring_dashboard.py  Network IDS and incident tracking
│   └── bug_bounty_automation.py        Web and network vulnerability scanning
│
├── tools/                   AI-powered productivity tools
│   ├── programming_assistant.py        Code generation, review, debugging
│   ├── book_writing_ai.py              Long-form content generation
│   ├── app_development_assistant.py    Full-stack app scaffolding
│   └── data_annotation_system.py       Dataset labelling and export
│
├── hardware/                Physical device bridges
│   ├── pico_bridge.py       Raspberry Pi Pico serial + web UI
│   ├── ar_glasses_bridge.py AR overlay and camera feed
│   ├── drone_control.py     MAVLink drone fleet management
│   └── mobile_bridge.py     WebSocket bridge for mobile apps
│
├── infrastructure/          System operations
│   ├── cloud_sync.py        AWS S3 and Dropbox synchronisation
│   ├── docker_deployment.py Container orchestration
│   ├── self_improvement.py  Package management and script execution
│   ├── self_evolution.py    Autonomous code improvement proposals
│   ├── notification_center.py  Cross-platform alert dispatch
│   └── backup_recovery_system.py  Scheduled backup and restore
│
└── interfaces/              User-facing I/O
    ├── enhanced_perception_system.py  Screen reading, OCR, network discovery
    ├── voice_activation.py            Wake-word detection and voice commands
    └── desktop_dashboard.py           Flask-based local web dashboard
```

---

## Architecture

```
                         config.yaml
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ToolRegistry         ai_bridge            TaskLedger
    (discover all         (call_ai)           (audit trail)
     register_tools)          │
          │                   │
          └──────────► AgentCore ◄──── VerificationEngine
                       │
              ┌────────┴─────────┐
              │                  │
         Plan (LLM)        Execute tools
              │                  │
              └────────┬─────────┘
                       │
                   Verify (LLM)
                       │
                  ┌────┴────┐
               pass       fail → retry / escalate
```

**Request flow:**
1. `apex.execute_task(description)` is called
2. `AgentCore` asks the LLM to produce a JSON step-by-step plan
3. Each step runs one or more registered tools
4. `VerificationEngine` confirms the outcome before moving to the next step
5. On failure: retry up to `max_retries`, then escalate to user
6. Full trace is written to `TaskLedger`

---

## Adding your own tools

Any Python function can become a tool. Two patterns are supported:

**Option A — decorator (zero boilerplate):**

```python
# my_module.py
from apex.core.tool_registry import tool

@tool("send_email", "Send an email to an address (to, subject, body)", tags=["comms"])
def send_email(to: str, subject: str, body: str) -> str:
    ...
    return "sent"
```

**Option B — explicit registration in `__init__.py`:**

```python
# apex/my_module/__init__.py
def register_tools(registry):
    from .email import send_email, list_inbox
    registry.register("send_email",  "Send an email",      send_email,  module="comms")
    registry.register("list_inbox",  "List email inbox",   list_inbox,  module="comms")
```

Then enable the module in `config.yaml`:

```yaml
modules:
  my_module: true
```

`ToolRegistry.discover()` will find and register the tools automatically at next startup.

---

## Governance and safety

Apex is designed to be accountable:

- **Trust threshold** — the agent escalates to you before acting when its confidence is below the configured percentage.
- **Audit ledger** — every tool call, decision, and verification result is written to an append-only JSONL file.
- **Legal compliance module** — security tools gate every action against jurisdiction-aware legal rules and require an active engagement contract before any offensive capability is used.
- **Verify before proceeding** — the agent does not mark a step complete until the `VerificationEngine` independently confirms the outcome.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'apex'`**
Add the parent of the `apex/` folder to your Python path:
```bash
set PYTHONPATH=C:\ai_agent
```

**Ollama connection refused**
Make sure Ollama is running: `ollama serve`

**Optional module unavailable warnings at startup**
These are non-fatal. Modules with missing dependencies log a warning and are skipped. Install the relevant extras (`pip install .[vision]`, etc.) to enable them.

**LLM returns malformed JSON plan**
Lower `temperature` in `config.yaml` to `0.1` or `0.2`. Larger models produce more reliable structured output.

**Agent keeps retrying a failing step**
Check the audit ledger at `storage.logs/ledger/action_ledger.jsonl` for the exact error. Tool errors are logged with full tracebacks.
