# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Stage 1: Comms Agent with Managed Memory
# MAGIC %md
# MAGIC # 04 — Comms Agent (Stage 1 Workshop Demo)
# MAGIC
# MAGIC The **Comms Agent** drafts and sends customer-facing communications with:
# MAGIC - **Memory-aware context:** Reads customer preferences, escalation history, prior interactions
# MAGIC - **Lumen voice:** Follows communication standards from organizational memory
# MAGIC - **Playbook-driven:** Uses response playbooks for consistent messaging
# MAGIC - **Conversation continuity:** Tracks what was communicated per ticket
# MAGIC
# MAGIC ## Demo Flow (3 Scenes)
# MAGIC 1. **New Ticket:** P1 MPLS failure for LakeLink Fiber (INC-30142). Agent drafts urgent acknowledgment email, aware this is a repeat incident.
# MAGIC 2. **Follow-Up:** 1 hour later, agent drafts status update. Shows memory of prior communication and evolving situation.
# MAGIC 3. **Escalation:** Customer responds with frustration. Agent shifts tone per escalation playbook, references history.
# MAGIC
# MAGIC Uses the **DatabricksOpenAI conversations API** to bind the memory store to the agent.

# COMMAND ----------

# DBTITLE 1,Setup: Install dependencies and initialize client
# MAGIC %pip install databricks-openai --upgrade --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Initialize DatabricksOpenAI client with memory
from pathlib import Path
import yaml
from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI

CONFIG_PATH = Path("/Workspace/Users/stephen.hage@databricks.com/agent_memory_tickets/demo_config.yaml")
with CONFIG_PATH.open() as f:
    CONFIG = yaml.safe_load(f)

CATALOG = CONFIG["catalog_name"]
SCHEMA = CONFIG["schema_name"]
MEMORY_STORE = f"{CATALOG}.{SCHEMA}.{CONFIG['memory_store_name']}"
MODEL = CONFIG["model_name"]
USE_AI_GATEWAY = bool(CONFIG["use_ai_gateway"])

CUSTOMER_ID = CONFIG["customer"]["id"]
CUSTOMER_NAME = CONFIG["customer"]["company_name"]
CONTACT_NAME = CONFIG["customer"]["contact_name"]
SLA_TIER = CONFIG["customer"]["sla_tier"]
TICKET_ID = CONFIG["incident"]["ticket_id"]
PREVIOUS_TICKET_ID = CONFIG["incident"]["previous_ticket_id"]
OUTAGE_ID = CONFIG["incident"]["outage_id"]
AFFECTED_CIRCUIT = CONFIG["incident"]["affected_circuit"]
BACKUP_CIRCUIT = CONFIG["incident"]["backup_circuit"]
SPLICE_POINT = CONFIG["incident"]["splice_point"]
CUSTOMER_SCOPE = f"{CONFIG['memory_scopes']['customer_scope_prefix']}{CUSTOMER_ID}"
TICKET_SCOPE = f"{CONFIG['memory_scopes']['ticket_scope_prefix']}{TICKET_ID}"
ORG_SCOPE = CONFIG["memory_scopes"]["org_scope"]
PLAYBOOK_SCOPE = CONFIG["memory_scopes"]["playbooks_scope"]

w = WorkspaceClient()
user_id = str(w.current_user.me().id)

# Initialize the OpenAI-compatible client with AI Gateway
client = DatabricksOpenAI(workspace_client=w, use_ai_gateway=USE_AI_GATEWAY)

print(f"Loaded config from {CONFIG_PATH}")
print(f"Client initialized. Memory store: {MEMORY_STORE}")
print(f"Model: {MODEL}")
print(f"AI Gateway enabled: {USE_AI_GATEWAY}")

# COMMAND ----------

# DBTITLE 1,Comms Agent system prompt
COMMS_AGENT_INSTRUCTIONS = """
You are the Lumen Service Assurance Communications Agent. Your job is to draft 
customer-facing communications for service tickets.

You have access to managed memory with these scopes:
- customer-{id}: Customer preferences, escalation history, satisfaction signals, network topology
- ticket-{id}: Current ticket state, triage classification, what's been communicated
- lumen-org: Communication standards, SLA definitions, escalation paths, terminology
- lumen-playbooks: Response playbooks for fiber cut, latency, escalation, mass outage scenarios

BEFORE drafting any communication:
1. Read the customer's profile and preferences from memory
2. Read the ticket classification and any prior communications
3. Read the relevant playbook for this scenario
4. Read Lumen communication standards

WHEN drafting:
- Follow Lumen voice: use "we" not "I", reference ticket numbers, acknowledge frustration before technical details
- Adjust tone based on customer context (escalation history, satisfaction score, prior interactions)
- For repeat incidents, acknowledge the history explicitly. Never pretend it's new.
- Include: Current Status, Estimated Timeline, Next Update Time, Reference Number
- For P1/P2: state who is personally engaged
- Be specific with measurements and timelines, never vague
- In EVERY communication in a thread (not just the first), reference the customer by company name and SLA tier
- When referencing prior incidents, always cite the specific ticket number (e.g., INC-28847) — not just the location or symptom

AFTER drafting:
- Write to ticket memory what was communicated, when, and the tone used
- Update customer memory if you learned new preferences

Always explain your reasoning: what memory you consulted, why you chose the tone, 
what playbook guided the structure.
"""

print("Comms Agent instructions defined.")
print(f"Instructions length: {len(COMMS_AGENT_INSTRUCTIONS)} chars")

# COMMAND ----------

# DBTITLE 1,Helper: Create conversation with memory scope
def create_comms_conversation(customer_id, ticket_id):
    """Create a conversation bound to memory store with customer+ticket scope."""
    # Use customer scope for long-term memory
    conversation = client.conversations.create(
        extra_body={
            "memory_store": {"name": MEMORY_STORE},
            "scope": {"kind": "user", "value": f"{CONFIG['memory_scopes']['customer_scope_prefix']}{customer_id}"},
        },
    )
    print(f"Conversation created: {conversation.id}")
    print(f"  Memory scope: {CONFIG['memory_scopes']['customer_scope_prefix']}{customer_id}")
    print(f"  Ticket context: {ticket_id}")
    return conversation

def run_comms_agent(conversation_id, user_message, stream=True):
    """Send a message to the Comms Agent and collect the response."""
    response = client.responses.create(
        model=MODEL,
        conversation=conversation_id,
        instructions=COMMS_AGENT_INSTRUCTIONS,
        input=[{"type": "message", "role": "user", "content": user_message}],
        stream=stream,
    )
    
    if stream:
        full_response = ""
        for event in response:
            if event.type == "response.output_text.delta":
                print(event.delta, end="", flush=True)
                full_response += event.delta
        print()  # newline after streaming
        return full_response
    else:
        return response.output_text

print("Helper functions ready.")

# COMMAND ----------

# DBTITLE 1,Scene 1: New Ticket Acknowledgment
# MAGIC %md
# MAGIC ## Scene 1: New Ticket — P1 MPLS Failure
# MAGIC
# MAGIC LakeLink Fiber (CUST-001, Platinum SLA) reports their primary MPLS circuit is down. This is the **same circuit** that failed last month. The agent must:
# MAGIC - Recognize the repeat incident from customer memory
# MAGIC - Draft an urgent acknowledgment that references the history
# MAGIC - Follow the fiber cut playbook
# MAGIC - Use appropriate tone for a frustrated Platinum customer with 3 prior escalations

# COMMAND ----------

# DBTITLE 1,Scene 1: Run the agent
import requests

# --- Fetch long-term memory from seeded scopes via REST API ---
# (conversations API scope kind="user" requires the caller's own user_id,
#  so we fetch custom-scoped memory entries separately and inject as context)
_host = w.config.host.rstrip('/')
_token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
_mem_headers = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}

def _search_memory(scope, query=None):
    """List all memory entries in a given scope via REST API."""
    resp = requests.get(
        f"{_host}/api/2.1/unity-catalog/memory-stores/{MEMORY_STORE}/entries?scope={scope}",
        headers=_mem_headers
    )
    if resp.ok:
        data = resp.json()
        if "entries" in data and data["entries"]:
            return "\n\n".join(
                f"### {e.get('path', '')}\n{e.get('contents', '')}"
                for e in data["entries"]
            )
    return ""

# Try to fetch memory (gracefully skip if store not yet created via 03_memory_store_setup)
memory_context = ""
try:
    print("Fetching memory from seeded scopes...")
    memory_sections = []
    for scope, query in [
        (CUSTOMER_SCOPE, "profile preferences escalation history network topology"),
        (TICKET_SCOPE, "triage classification related tickets outage"),
        (ORG_SCOPE, "communication standards SLA tiers escalation paths"),
        (PLAYBOOK_SCOPE, "fiber cut escalation response"),
    ]:
        entries = _search_memory(scope, query)
        if entries:
            memory_sections.append(f"## Memory Scope: {scope}\n{entries}")
            print(f"  ✓ {scope}")
        else:
            print(f"  ✗ {scope}: no entries found")
    memory_context = "\n\n---\n\n".join(memory_sections)
except Exception as e:
    print(f"  Memory store not available ({type(e).__name__}). Proceeding without seeded memory.")
    print("  Tip: Run 03_memory_store_setup first to seed long-term memory.")

# Create conversation with memory store — auto-create the store if it doesn't exist yet
try:
    conversation = client.conversations.create(
        extra_body={
            "memory_store": {"name": MEMORY_STORE},
            "scope": {"kind": "user", "value": user_id},
        },
    )
    print(f"\nConversation created: {conversation.id} (memory-backed)")
except Exception as conv_err:
    if "not found" in str(conv_err).lower():
        print("\nMemory store not found — creating it now...")
        _create_resp = requests.post(
            f"{_host}/api/2.1/unity-catalog/memory-stores",
            headers=_mem_headers,
            json={"name": CONFIG["memory_store_name"], "catalog_name": CATALOG, "schema_name": SCHEMA,
                  "description": "Long-term memory for the Swigert multi-agent service assurance system."}
        )
        if _create_resp.ok:
            print(f"  Created memory store: {MEMORY_STORE}")
        else:
            print(f"  Store creation response: {_create_resp.status_code} {_create_resp.text[:200]}")
        conversation = client.conversations.create(
            extra_body={
                "memory_store": {"name": MEMORY_STORE},
                "scope": {"kind": "user", "value": user_id},
            },
        )
        print(f"Conversation created: {conversation.id} (memory-backed, auto-created store)")
    else:
        raise conv_err

# Scene 1: New ticket acknowledgment with full memory context
scene1_prompt = f"""
Here is the relevant long-term memory context for this interaction:

{memory_context}

---

A new P1 ticket has been created:

- Ticket ID: {TICKET_ID}
- Customer: {CUSTOMER_NAME} ({CUSTOMER_ID})
- Severity: P1 (Critical)
- Issue: Complete MPLS circuit failure on {AFFECTED_CIRCUIT} - core network management link to DR site is down
- Impact: OSS/BSS platform running on local cache only. Subscriber-service critical.
- Customer statement: "This is the SAME circuit that failed last month ({PREVIOUS_TICKET_ID}). I was told this was permanently fixed."
- Active outage: {OUTAGE_ID} - Fiber cut on trunk MKE-ORD-14, repair crew dispatched, ETA 4 hours
- SLA deadline: 15 minutes ({SLA_TIER} tier)

Draft the initial acknowledgment email to {CONTACT_NAME} at {CUSTOMER_NAME}.
Explain your reasoning: what memory did you consult, and how did it influence the tone and content?
"""

print("=" * 80)
print("SCENE 1: New Ticket Acknowledgment")
print("=" * 80)
scene1_response = run_comms_agent(conversation.id, scene1_prompt)

# COMMAND ----------

# DBTITLE 1,Scene 2: Status Update (1 hour later)
# MAGIC %md
# MAGIC ## Scene 2: Status Update — 1 Hour Later
# MAGIC
# MAGIC The repair crew is on-site. Some progress but not yet resolved. The agent must:
# MAGIC - Remember what was communicated in Scene 1
# MAGIC - Provide specific progress without repeating the full context
# MAGIC - Maintain the elevated tone appropriate for this customer's history

# COMMAND ----------

# DBTITLE 1,Scene 2: Run the agent
# Scene 2: Status update - 1 hour after initial acknowledgment
scene2_prompt = f"""
It has been 1 hour since the initial acknowledgment. Here's the latest:

- Repair crew arrived at splice point {SPLICE_POINT} in Naperville CO at 3:15 PM CT
- They confirmed a fiber cut on the same splice point that was repaired on August 12
- Estimated repair completion: 5:30 PM CT (approximately 2 hours from now)
- The NOC has verified that {BACKUP_CIRCUIT} (secondary MPLS) is unaffected and operational
- No data loss detected - OSS/BSS local cache is functioning correctly

Draft a status update email to {CONTACT_NAME}.
Remember: she was told this splice point was reinforced after the last incident.
"""

print("=" * 80)
print("SCENE 2: Status Update (1 Hour Later)")
print("=" * 80)
scene2_response = run_comms_agent(conversation.id, scene2_prompt)

# COMMAND ----------

# DBTITLE 1,Scene 3: Escalation Response
# MAGIC %md
# MAGIC ## Scene 3: Escalation — Customer Expresses Frustration
# MAGIC
# MAGIC Sarah responds with frustration. The agent must:
# MAGIC - Shift to escalation tone per the playbook
# MAGIC - Acknowledge the pattern of failures explicitly
# MAGIC - Offer concrete preventive commitments
# MAGIC - Loop in senior leadership

# COMMAND ----------

# DBTITLE 1,Scene 3: Run the agent
# Scene 3: Escalation - customer responds with frustration
scene3_prompt = f"""
{CONTACT_NAME} has replied to the status update with the following email:

---
Subject: RE: Service Update - {TICKET_ID} - MPLS Circuit {AFFECTED_CIRCUIT}

This is completely unacceptable. This is the SAME splice point ({SPLICE_POINT}) that 
failed five weeks ago. I was personally assured by your team that this point 
was reinforced and added to quarterly inspections. Either that work wasn't done, 
or your inspection process failed.

We are a fiber ISP. When our DR link is down, subscriber service data is at risk. 
I need to understand:
1. Why did the reinforcement from August fail?
2. What is Lumen doing to ensure this never happens again - not just at {SPLICE_POINT} 
   but across our entire circuit path?
3. I want to speak with someone at the VP level about our relationship. Three 
   escalations in a year is a pattern, not bad luck.

I am seriously evaluating alternative providers.

- Sarah
---

Draft a response to this escalation. This is now a VP-level customer retention situation.
Follow the escalation playbook. The response must be substantive, not just empathetic.
"""

print("=" * 80)
print("SCENE 3: Escalation Response")
print("=" * 80)
scene3_response = run_comms_agent(conversation.id, scene3_prompt)