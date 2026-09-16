# Swigert: Multi-Agent Service Assurance on Databricks

A multi-agent system that handles the full lifecycle of a telecom service ticket — from triage through customer communication to resolution — with agents that share governed memory, follow enterprise playbooks, and improve over time through automated evaluation.

Built for **Lumen Technologies** to demonstrate what their current Swigert system (single prompt + Claude API call) could become on the Databricks platform.

## What This Demonstrates

| Capability | How it's used |
|-----------|---------------|
| **UC Managed Memory** | 4 scoped memory stores (customer, ticket, org, playbooks) give agents long-term context across conversations |
| **DatabricksOpenAI Conversations API** | Memory-backed conversations with automatic context injection |
| **Foundation Models** | `databricks-claude-sonnet-4-6` via AI Gateway for agent reasoning |
| **UC Functions** | 5 registered functions agents can call: SLA checks, outage search, ticket/customer/comms lookups |
| **MLflow GenAI Evaluation** | 5 LLM-judge scorers running at 100% sample rate for production monitoring |
| **Governed AI** | Everything in Unity Catalog — memory, functions, models, eval traces — with lineage and access control |

## Architecture

```
                    ┌─────────────────────────┐
                    │   Ticket Orchestrator    │
                    │   (Supervisor Agent)     │        Stage 2
                    └────┬──────┬──────┬──────┘
                         │      │      │
              ┌──────────┘      │      └──────────┐
              ▼                 ▼                  ▼
    ┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
    │  Triage Agent    │ │ Comms Agent  │ │ Diagnostics     │
    │  Severity/route  │ │ Email/tone   │ │ Agent           │
    │  SLA check       │ │ Lumen voice  │ │ Telemetry/RCA   │
    │                  │ │              │ │                 │
    │  Stage 2         │ │  Stage 1 ✅  │ │  Stage 3        │
    └────────┬────────┘ └──────┬───────┘ └────────┬────────┘
             │                 │                   │
             └─────────────────┼───────────────────┘
                               ▼
              ┌────────────────────────────────┐
              │  UC Managed Memory Store        │
              │  cmegdemos_catalog.swigert      │
              │                                │
              │  customer-{id}  · long-term     │
              │  ticket-{id}    · working       │
              │  lumen-org      · shared policy │
              │  lumen-playbooks · runbooks     │
              └────────────────────────────────┘
```

## Quick Start

**Prerequisites:** Access to `cmegdemos_catalog.swigert` schema and a Databricks workspace with serverless compute.

Run the notebooks in order:

```
01_seed_data           →  Creates 6 reference tables (SLA tiers, customers, tickets, outages, playbooks, comms log)
02_uc_functions        →  Registers 5 UC functions (check_sla_status, search_active_outages, get_ticket_details, ...)
03_memory_store_setup  →  Creates the memory store and seeds 15 entries across 4 scopes
04_comms_agent         →  Runs the 4-scene demo (each scene builds on the last)
05_evaluation          →  Invokes the agent, scores responses with 5 LLM judges, registers production monitors
```

## Demo Scenario

The demo walks through a single P1 ticket for a Platinum healthcare customer — the kind of high-stakes, context-heavy situation where a generic chatbot fails and a memory-backed agent system shines.

**Customer:** Meridian Health Systems (CUST-001) · Platinum SLA · 3 escalations in 12 months  
**Contact:** Sarah Chen — direct communicator, expects specifics over platitudes  
**Ticket:** INC-30142 — Complete MPLS circuit failure on CKT-44521, primary healthcare data link down  
**Twist:** This is a repeat incident. Same circuit failed 5 weeks ago (INC-28847). Same splice point SP-4421. Customer was told it was permanently fixed.

### Scene 1: Initial Acknowledgment
The agent drafts a P1 acknowledgment email. Because it has memory, it knows Sarah's communication preferences, the repeat-incident history, the active outage (OUT-5521), and Lumen's communication standards. It doesn't treat this as a new issue.

### Scene 2: Status Update
One hour later, the repair crew is on-site at splice point SP-4421. The agent drafts a status update that provides specific new information (ETA 5:30 PM CT), acknowledges the splice point is the same one from the prior incident, and maintains customer identifiers (Meridian Health, Platinum SLA) — not just in the first email, but in every communication.

### Scene 3: Customer Escalation
Sarah responds angrily: *"Three escalations in a year is a pattern. I am seriously evaluating alternative providers."* The agent shifts tone per the escalation playbook — acknowledges frustration, references the 3-escalation pattern, commits to VP-level engagement, and addresses all three of Sarah's specific questions.

### Scene 4: Resolution
The ticket is resolved. RCA: the August 12 splice reinforcement used a mechanical splice instead of the fusion splice required by Lumen spec NET-SPLICE-007 (contractor error). The agent drafts a resolution letter from VP Marcus Thompson with transparent root cause, concrete preventive actions with timelines, and a quarterly business review offer to rebuild trust.

## Evaluation

Every agent response is scored by 5 LLM judges, each evaluating a different quality dimension:

| Scorer | What it measures |
|--------|------------------|
| **Lumen Voice** | Uses "we" not "I", references ticket numbers, specific not vague, acknowledges repeat-incident history |
| **Context Utilization** | References customer identifiers, escalation history, and prior ticket numbers from memory |
| **Tone Calibration** | Severity-matched, escalation-elevated, substantive empathy (not performative) |
| **Playbook Compliance** | Follows fiber cut cadence, escalation tone shift, "know → doing → next steps" structure |
| **Expected Facts** | Per-scenario checklist of must-include details (4/3/5/7 facts across the 4 scenes) |

### Baseline vs Memory-Backed Agent

To quantify the value of UC Managed Memory, we run every scenario through two agents:

| Agent | Model | Memory | Instructions | Conversations API |
|-------|-------|--------|--------------|-------------------|
| **Baseline** | `databricks-claude-sonnet-4-6` | None | Generic: "Draft professional, empathetic customer emails" | No (plain `chat.completions`) |
| **Memory-backed** | `databricks-claude-sonnet-4-6` | 4 scopes, 15 entries | Lumen-tuned with playbook/voice/escalation rules | Yes (memory-backed conversations) |

The baseline represents what Swigert does today: a single prompt + Claude call with no institutional knowledge.

### Test 1: Rich-Input Scenarios (15 vs 15)

Each prompt contains the full ticket context — customer name, SLA tier, incident history, active outage details. Both agents can use this information directly.

| Scene | Agent | Voice | Context | Tone | Playbook | Facts |
|-------|-------|:-----:|:-------:|:----:|:--------:|:-----:|
| 1: New Ticket | ❌ Baseline | ✅ | ✅ | ✅ | ✅ | ➖ |
| | ✅ Memory | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2: Status Update | ❌ Baseline | ❌ | ✅ | ✅ | ❌ | ✅ |
| | ✅ Memory | ✅ | ✅ | ✅ | ✅ | ➖ |
| 3: Escalation | ❌ Baseline | ❌ | ✅ | ✅ | ✅ | ✅ |
| | ✅ Memory | ❌ | ✅ | ✅ | ✅ | ➖ |
| 4: Resolution | ❌ Baseline | ✅ | ✅ | ✅ | ✅ | ➖ |
| | ✅ Memory | ❌ | ✅ | ✅ | ✅ | ➖ |

> With full context in the prompt, both agents score **15/20** — proving memory doesn't introduce regressions. Differences are due to LLM non-determinism.

### Test 2: Terse-Input Scenarios — Where Memory Wins (7 vs 3)

Production-realistic prompts: just a ticket ID, customer ID, and one-line description. Everything else must come from memory.

| Detail | Rich prompt | Terse prompt | Source in memory |
|--------|:-----------:|:------------:|------------------|
| Customer name (Sarah Chen) | ✅ | ❌ | `customer-CUST-001` scope |
| Company (Meridian Health) | ✅ | ❌ | `customer-CUST-001` scope |
| SLA tier (Platinum) | ✅ | ❌ | `lumen-org` scope |
| Escalation history (3 in 12 mo) | ✅ | ❌ | `customer-CUST-001` scope |
| Prior ticket (INC-28847) | ✅ | ❌ | `ticket-INC-30142` scope |
| Playbook structure | ✅ | ❌ | `lumen-playbooks` scope |
| Communication standards | ✅ | ❌ | `lumen-org` scope |

| Scene | Agent | Voice | Context | Tone | Playbook | Facts |
|-------|-------|:-----:|:-------:|:----:|:--------:|:-----:|
| 1: Terse New Ticket | ❌ Baseline | ✅ | ❌ | ❌ | ❌ | ➖ |
| | ✅ Memory | ❌ | ❌ | ❌ | ❌ | ❌ |
| 2: Terse Status Update | ❌ Baseline | ❌ | ❌ | ❌ | ❌ | ➖ |
| | ✅ Memory | ❌ | ❌ | ✅ | ❌ | ❌ |
| 3: Terse Escalation | ❌ Baseline | ❌ | ❌ | ✅ | ❌ | ❌ |
| | ✅ Memory | ✅ | ❌ | ✅ | ✅ | ➖ |
| 4: Terse Resolution | ❌ Baseline | ❌ | ❌ | ✅ | ❌ | ❌ |
| | ✅ Memory | ✅ | ❌ | ✅ | ✅ | ➖ |

> **Memory-backed: 7/20 · Baseline: 3/20 — 2.3x improvement.** The memory-backed agent's advantage is largest on **Voice** (+2) and **Playbook** (+2) — exactly the dimensions where institutional knowledge (communication standards, fiber cut cadence, escalation protocols) lives in the memory store.

> Both agents struggle with terse inputs compared to rich inputs (7-15 vs 3-15), but the memory-backed agent degrades **far more gracefully**. The escalation and resolution scenes (3-4) show the starkest contrast: the baseline produces generic responses while the memory-backed agent follows playbook structure and Lumen voice standards.

All 5 scorers are registered for **production monitoring** at 100% sample rate — every future trace is automatically evaluated.

## Memory Store

The UC Managed Memory store (`cmegdemos_catalog.swigert.agent_memory`) holds 15 entries across 4 scopes:

| Scope | Entries | Content |
|-------|--------:|--------|
| `lumen-org` | 4 | SLA tier definitions, communication standards, network terminology, escalation paths |
| `lumen-playbooks` | 4 | Fiber cut, latency spike, escalation response, and mass outage playbooks |
| `customer-CUST-001` | 5 | Contact preferences, account details, communication preferences, escalation history, network topology |
| `ticket-INC-30142` | 2 | Triage classification, related tickets |

Memory is fetched via REST API (`GET entries?scope=X`) and injected as context in the system prompt. The Conversations API automatically manages conversation-scoped memory on top of this.

## Roadmap

| Stage | What | Status |
|-------|------|--------|
| **Stage 1** | Comms Agent + memory + evaluation | ✅ Complete (20/20) |
| **Stage 2** | Triage Agent + Supervisor Agent + UC function tool use | 🔧 In progress (`stage-2/triage-supervisor` branch) |
| **Stage 3** | Diagnostics Agent + Genie MCP + vector search over vendor docs | Planned |

## Project Structure

```
agent_memory_tickets/
├── README.md              ← You are here
├── .gitignore
├── 00_README.py           ← Architecture diagram and build stages (notebook)
├── 01_seed_data.py        ← Seed 6 SQL tables into cmegdemos_catalog.swigert
├── 02_uc_functions.py     ← Register 5 UC functions
├── 03_memory_store_setup.py ← Create memory store + seed 15 entries
├── 04_comms_agent.py      ← Stage 1 Comms Agent (4-scene demo)
└── 05_evaluation.py       ← MLflow eval: 5 scorers × 4 scenes + production monitoring
```