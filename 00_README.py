# Databricks notebook source
# DBTITLE 1,Swigert Multi-Agent Service Assurance
# MAGIC %md
# MAGIC # Swigert Multi-Agent Service Assurance Demo
# MAGIC
# MAGIC ## Vision
# MAGIC A multi-agent service assurance system where specialized agents handle different parts of the ticket lifecycle, share a governed memory layer, and get smarter over time. This demonstrates what Lumen's current Swigert (single prompt + Claude API call) could become on Databricks.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Architecture
# MAGIC
# MAGIC ```
# MAGIC                     ┌─────────────────────────┐
# MAGIC                     │   Ticket Orchestrator    │
# MAGIC                     │   (Supervisor Agent)     │
# MAGIC                     └────┬──────┬──────┬──────┘
# MAGIC                          │      │      │
# MAGIC               ┌──────────┘      │      └──────────┐
# MAGIC               ▼                 ▼                  ▼
# MAGIC     ┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
# MAGIC     │  Triage Agent    │ │ Comms Agent  │ │ Diagnostics     │
# MAGIC     │  Severity/route  │ │ Email/tone   │ │ Agent           │
# MAGIC     │  SLA check       │ │ Lumen voice  │ │ Telemetry/RCA   │
# MAGIC     └────────┬────────┘ └──────┬───────┘ └────────┬────────┘
# MAGIC              │                 │                   │
# MAGIC              └─────────────────┼───────────────────┘
# MAGIC                                ▼
# MAGIC               ┌────────────────────────────────┐
# MAGIC               │  Shared Memory Store            │
# MAGIC               │  cmegdemos_catalog.swigert      │
# MAGIC               │                                │
# MAGIC               │  Scopes:                        │
# MAGIC               │  • customer-{id}  (long-term)   │
# MAGIC               │  • ticket-{id}    (working)     │
# MAGIC               │  • lumen-org      (shared)      │
# MAGIC               │  • lumen-playbooks (runbooks)   │
# MAGIC               └────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC ## Catalog & Schema
# MAGIC - **Catalog:** `cmegdemos_catalog`
# MAGIC - **Schema:** `swigert`
# MAGIC - **Memory Store:** `cmegdemos_catalog.swigert.agent_memory` (Managed Memory for Agents)
# MAGIC
# MAGIC ## Agents
# MAGIC
# MAGIC | Agent | Role | Stage |
# MAGIC |-------|------|-------|
# MAGIC | **Comms Agent** | Drafts customer emails in Lumen voice, manages tone, uses memory for context | Stage 1 (Workshop Demo) |
# MAGIC | **Triage Agent** | Classifies severity (P1-P4), routes tickets, checks SLA compliance | Stage 2 |
# MAGIC | **Ticket Orchestrator** | Supervisor that routes to sub-agents, manages workflow | Stage 2 |
# MAGIC | **Diagnostics Agent** | Queries telemetry, runs diagnostics, produces RCA summaries | Stage 3 |
# MAGIC
# MAGIC ## Notebooks
# MAGIC
# MAGIC | Notebook | Purpose |
# MAGIC |----------|--------|
# MAGIC | `01_seed_data` | Creates seed tables: tickets, customers, SLA tiers, outages, org knowledge |
# MAGIC | `02_uc_functions` | UC functions: check_sla_status, search_active_outages, get_ticket_details, get_customer_profile |
# MAGIC | `03_memory_store_setup` | Sets up managed memory store with 4 scopes + seeds initial entries |
# MAGIC | `04_comms_agent` | Stage 1 Comms Agent — DatabricksOpenAI conversations API with memory integration, 4-scene demo |
# MAGIC | `05_evaluation` | MLflow genai eval — 5 scorers × 4 scenes, production monitoring registered |
# MAGIC
# MAGIC ## Build Stages
# MAGIC
# MAGIC ### Stage 1: Workshop Demo ✅ COMPLETE — 20/20 Eval Pass Rate
# MAGIC - Memory store + seed data (4 scopes, 15 entries)
# MAGIC - Comms Agent with managed memory (`databricks-claude-sonnet-4-6`)
# MAGIC - 4-scene demo: acknowledge → status update → escalation → resolution
# MAGIC - 5 MLflow scorers registered for production monitoring
# MAGIC - Show memory governance in UC after each interaction
# MAGIC
# MAGIC #### Evaluation Scorecard
# MAGIC
# MAGIC | Scene | Voice | Context | Tone | Playbook | Facts |
# MAGIC |-------|-------|---------|------|----------|-------|
# MAGIC | 1: New Ticket | ✅ | ✅ | ✅ | ✅ | ✅ |
# MAGIC | 2: Status Update | ✅ | ✅ | ✅ | ✅ | ✅ |
# MAGIC | 3: Escalation | ✅ | ✅ | ✅ | ✅ | ✅ |
# MAGIC | 4: Resolution | ✅ | ✅ | ✅ | ✅ | ✅ |
# MAGIC
# MAGIC **Scorers** (all registered at 100% sample rate in `/Users/stephen.hage@databricks.com/swigert_eval`):
# MAGIC - **Lumen Voice** — "we" not "I", ticket references, specific not vague, repeat-incident history
# MAGIC - **Context Utilization** — customer identifiers, escalation history, prior ticket numbers from memory
# MAGIC - **Tone Calibration** — severity-matched, escalation-elevated, substantive empathy
# MAGIC - **Playbook Compliance** — fiber cut cadence, escalation tone shift, "know → doing → next steps" structure
# MAGIC - **Expected Facts** — per-scenario checklist (4/3/5/7 facts across the 4 scenes)
# MAGIC
# MAGIC #### Demo Scenario
# MAGIC - **Customer:** LakeLink Fiber (CUST-001, Platinum SLA, 3 escalations in 12 months)
# MAGIC - **Contact:** Sarah Chen — direct, expects specifics over platitudes
# MAGIC - **Ticket:** INC-30142 — P1 MPLS failure on CKT-44521 (repeat: same circuit failed in INC-28847)
# MAGIC - **Active outage:** OUT-5521 fiber cut on MKE-ORD-14, splice point SP-4421
# MAGIC - **Resolution:** Contractor error (mechanical splice vs fusion splice spec NET-SPLICE-007)
# MAGIC
# MAGIC ### Stage 2: Multi-Agent with Triage (Follow-on)
# MAGIC - Triage Agent + Supervisor Agent
# MAGIC - UC functions for SLA and outage checking
# MAGIC - Ticket-scoped memory: triage writes classification, comms reads it
# MAGIC - Evaluation judges for triage accuracy + comms quality
# MAGIC
# MAGIC ### Stage 3: Full System with Diagnostics (Hackathon)
# MAGIC - Diagnostics Agent with Genie Agent MCP
# MAGIC - Vector search over vendor documentation
# MAGIC - External MCP for network diagnostic commands
# MAGIC - Full evaluation suite