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
# MAGIC | `04_comms_agent` | Stage 1 Comms Agent — OpenAI Agents SDK with memory integration |
# MAGIC | `05_evaluation` | MLflow evaluation: Lumen voice, context utilization, factual accuracy judges |
# MAGIC
# MAGIC ## Build Stages
# MAGIC
# MAGIC ### Stage 1: Workshop Demo ✅ (Build First)
# MAGIC - Memory store + seed data
# MAGIC - Comms Agent with managed memory
# MAGIC - 3-scene demo: new ticket → follow-up → escalation
# MAGIC - Show memory governance in UC after each interaction
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