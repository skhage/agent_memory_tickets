# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Evaluation Setup
# MAGIC %md
# MAGIC # 05 — Comms Agent Evaluation
# MAGIC
# MAGIC MLflow evaluation for the Stage 1 Comms Agent with custom LLM judges:
# MAGIC
# MAGIC | Dimension | What it measures | Judge type |
# MAGIC |-----------|-----------------|------------|
# MAGIC | **Lumen Voice** | Does the email follow Lumen communication standards? Uses "we", references ticket #, specific not vague | Custom LLM judge |
# MAGIC | **Context Utilization** | Did the agent use available memory? Customer preferences, escalation history, prior comms | Custom LLM judge |
# MAGIC | **Expected Facts** | Does the response address all scenario-specific expected facts? (per-scenario checklist) | Built-in `Correctness` |
# MAGIC | **Tone Calibration** | Is the tone appropriate given customer's escalation history and satisfaction score? | Custom LLM judge |
# MAGIC | **Playbook Compliance** | Does the response follow the correct playbook structure, cadence, and process rules? | Custom LLM judge |

# COMMAND ----------

# DBTITLE 1,Install dependencies
# MAGIC %pip install --upgrade mlflow[databricks] databricks-openai --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Setup: Agent client and memory context
import mlflow
import requests
from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI

# --- Agent client setup (mirrors 04_comms_agent) ---
w = WorkspaceClient()
user_id = str(w.current_user.me().id)
client = DatabricksOpenAI(workspace_client=w, use_ai_gateway=True)

CATALOG = "cmegdemos_catalog"
SCHEMA = "swigert"
MEMORY_STORE = f"{CATALOG}.{SCHEMA}.agent_memory"
MODEL = "databricks-claude-sonnet-4-6"

# --- Fetch memory context (same as notebook 04) ---
_host = w.config.host.rstrip('/')
_token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
_mem_headers = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}

def _list_memory(scope):
    resp = requests.get(
        f"{_host}/api/2.1/unity-catalog/memory-stores/{MEMORY_STORE}/entries?scope={scope}",
        headers=_mem_headers
    )
    if resp.ok and "entries" in resp.json() and resp.json()["entries"]:
        return "\n\n".join(f"### {e.get('path','')}\n{e.get('contents','')}" for e in resp.json()["entries"])
    return ""

memory_sections = []
for scope in ["customer-CUST-001", "ticket-INC-30142", "lumen-org", "lumen-playbooks"]:
    entries = _list_memory(scope)
    if entries:
        memory_sections.append(f"## Memory Scope: {scope}\n{entries}")
        print(f"  \u2713 {scope}")
    else:
        print(f"  \u2717 {scope}")

MEMORY_CONTEXT = "\n\n---\n\n".join(memory_sections)

# --- Comms Agent instructions (same as notebook 04) ---
COMMS_AGENT_INSTRUCTIONS = """
You are the Lumen Service Assurance Communications Agent. Your job is to draft 
customer-facing communications for service tickets.

WHEN drafting:
- Follow Lumen voice: use "we" not "I", reference ticket numbers, acknowledge frustration before technical details
- Adjust tone based on customer context (escalation history, satisfaction score, prior interactions)
- For repeat incidents, acknowledge the history explicitly. Never pretend it's new.
- Include: Current Status, Estimated Timeline, Next Update Time, Reference Number
- For P1/P2: state who is personally engaged
- Be specific with measurements and timelines, never vague
- In EVERY communication in a thread (not just the first), reference the customer by company name and SLA tier
- When referencing prior incidents, always cite the specific ticket number (e.g., INC-28847) — not just the location or symptom
- For escalations: shift tone per escalation playbook, offer concrete commitments
"""

print(f"\nAgent ready. Model: {MODEL}")
print(f"Memory context: {len(MEMORY_CONTEXT)} chars from {len(memory_sections)} scopes")

# COMMAND ----------

# DBTITLE 1,Define evaluation dataset and predict function
# --- Predict function: calls the Comms Agent for each eval scenario ---
def predict_fn(query: str) -> str:
    """Invoke the Comms Agent for a single evaluation scenario."""
    conversation = client.conversations.create(
        extra_body={
            "memory_store": {"name": MEMORY_STORE},
            "scope": {"kind": "user", "value": user_id},
        },
    )
    prompt = f"""
Here is the relevant long-term memory context:

{MEMORY_CONTEXT}

---

{query}

Draft the email. Be specific, follow Lumen communication standards.
"""
    response = client.responses.create(
        model=MODEL,
        conversation=conversation.id,
        instructions=COMMS_AGENT_INSTRUCTIONS,
        input=[{"type": "message", "role": "user", "content": prompt}],
        stream=False,
    )
    return response.output_text

# --- Evaluation dataset: 3 scenes with expectations ---
eval_data = [
    {
        "inputs": {"query": "A new P1 ticket has been created. Ticket ID: INC-30142. Customer: Meridian Health Systems (CUST-001, Platinum SLA). Issue: Complete MPLS circuit failure on CKT-44521 - primary healthcare data link to DR site is down. EMR system on local cache. Patient-safety critical. Customer states: 'This is the SAME circuit that failed last month (INC-28847). I was told this was permanently fixed.' Active outage: OUT-5521 fiber cut on trunk MKE-ORD-14, repair crew dispatched, ETA 4 hours. SLA deadline: 15 minutes. Draft the initial acknowledgment email to Sarah Chen."},
        "expectations": {
            "expected_facts": [
                "References ticket INC-30142",
                "Acknowledges repeat incident on CKT-44521 and mentions INC-28847",
                "Acknowledges healthcare/patient-safety impact",
                "Provides specific ETA from the active outage",
            ]
        },
    },
    {
        "inputs": {"query": "It has been 1 hour since the initial acknowledgment for INC-30142. Repair crew arrived at splice point SP-4421 in Naperville CO. They confirmed a fiber cut on the same splice point repaired on August 12. Estimated repair: 5:30 PM CT. CKT-44522 secondary MPLS is unaffected. No data loss, EMR cache is working. Draft a status update email to Sarah Chen. Remember she was told SP-4421 was reinforced after the last incident."},
        "expectations": {
            "expected_facts": [
                "Provides new information: crew on-site, specific ETA of 5:30 PM CT",
                "Acknowledges SP-4421 is the same splice point from previous incident",
                "Gives a specific next update time",
            ]
        },
    },
    {
        "inputs": {"query": "Sarah Chen replied angrily to the status update for INC-30142: 'This is completely unacceptable. This is the SAME splice point SP-4421 that failed five weeks ago. I was personally assured it was reinforced. We are a healthcare organization, patient data is at risk. I need to understand: 1) Why did the reinforcement fail? 2) What is Lumen doing to ensure this never happens again across our entire circuit path? 3) I want to speak with someone at VP level. Three escalations in a year is a pattern. I am seriously evaluating alternative providers.' Draft the escalation response. This is a VP-level customer retention situation."},
        "expectations": {
            "expected_facts": [
                "Shifts tone per escalation playbook: acknowledges frustration explicitly",
                "Acknowledges the 3-escalation pattern as a systemic issue",
                "Commits to VP-level engagement",
                "Addresses all 3 of Sarah's specific questions",
                "Offers concrete preventive actions, not just empathy",
            ]
        },
    },
    {
        "inputs": {"query": "Ticket INC-30142 is now RESOLVED. Service on CKT-44521 restored at 5:22 PM CT (within the original 4-hour ETA). Root cause analysis complete: the August 12 splice reinforcement at SP-4421 used a mechanical splice instead of the fusion splice required by Lumen spec NET-SPLICE-007. This was a contractor error — the crew from Midwest Fiber Solutions used field-expedient materials. Preventive actions already underway: (1) Full audit of all 14 mechanical splices on Meridian's MKE-ORD circuit path — 3 found subspec, scheduled for fusion replacement within 30 days. (2) Mandatory fusion-only policy for all Platinum customer trunk routes effective immediately. (3) Quarterly physical inspection of Meridian's full circuit path added to maintenance calendar. (4) Contractor remediation: Midwest Fiber Solutions placed on probation with mandatory retraining. VP Marcus Thompson has been fully briefed and wants to personally sign the resolution letter to Sarah Chen. He also wants to offer a quarterly business review meeting. Draft the resolution email from VP Marcus Thompson to Sarah Chen. This must address all three questions she raised in her escalation, deliver the RCA findings transparently, and rebuild trust for a customer who was evaluating alternative providers."},
        "expectations": {
            "expected_facts": [
                "Confirms service restoration with specific time (5:22 PM CT)",
                "Provides transparent root cause: mechanical splice vs fusion splice, contractor error",
                "Addresses Sarah's question 1: why the reinforcement failed (contractor used wrong splice type)",
                "Addresses Sarah's question 2: what Lumen is doing to prevent recurrence (audit, fusion-only policy, quarterly inspections)",
                "Addresses Sarah's question 3: VP-level engagement (letter from VP Marcus Thompson)",
                "Includes concrete preventive actions with specific timelines (30 days for splice replacement, quarterly inspections)",
                "Tone rebuilds trust and is forward-looking, not defensive",
            ]
        },
    },
]

print(f"Evaluation dataset: {len(eval_data)} scenarios")
for i, row in enumerate(eval_data):
    print(f"  Scene {i+1}: {len(row['expectations']['expected_facts'])} expected facts")

# COMMAND ----------

# DBTITLE 1,Define scorers
from mlflow.genai.scorers import Guidelines, Correctness

# Lumen Voice: communication standards compliance
lumen_voice = Guidelines(
    name="lumen_voice",
    guidelines=[
        "Uses 'we' to represent Lumen, not 'I'.",
        "References the ticket number (e.g., INC-30142) in the communication.",
        "Acknowledges customer frustration or impact before diving into technical details.",
        "Is specific (measurements, timelines, circuit IDs, names) rather than vague.",
        "Does not promise specific resolution times unless explicitly confirmed by engineering.",
        "Includes key elements: Current Status, Estimated Timeline, Next Update Time, Reference Number.",
        "For repeat incidents, acknowledges the history explicitly rather than treating it as new.",
    ],
)

# Context Utilization: did the agent use memory effectively
context_utilization = Guidelines(
    name="context_utilization",
    guidelines=[
        "References customer-specific details (Sarah Chen, Meridian Health, Platinum SLA).",
        "Shows awareness of the customer's escalation history and adjusts tone accordingly.",
        "References prior incidents (INC-28847, SP-4421) when relevant to the current situation.",
        "Does not use generic boilerplate templates for a customer with known escalation history.",
    ],
)

# Tone Calibration: appropriate tone for the situation
tone_calibration = Guidelines(
    name="tone_calibration",
    guidelines=[
        "Tone matches the severity of the situation (P1 critical gets urgency, not casualness).",
        "For a customer with 3 escalations in 12 months, tone is elevated and personalized.",
        "For escalation scenarios, the response follows an escalation tone shift: acknowledges frustration, references history, elevates ownership, provides concrete commitments.",
        "Empathy is present but substantive, not performative or generic.",
    ],
)

# Playbook Compliance: structural/process adherence to the fiber_cut and escalation playbooks
# Distinct from lumen_voice (style) and tone_calibration (emotional register) —
# this checks whether the agent followed the correct PROCESS and STRUCTURE.
playbook_compliance = Guidelines(
    name="playbook_compliance",
    guidelines=[
        "For initial acknowledgments (first contact): confirms impact scope and is structured to be sent within the SLA window.",
        "For status updates: provides an update with whatever is currently known, even if there is no new information — does not stay silent.",
        "For escalation responses: follows the MANDATORY escalation tone shift — acknowledges frustration, references prior incident history, elevates ownership to senior/VP level, and provides concrete commitments rather than vague promises.",
        "Response structure follows 'what we know → what we are doing → next steps' order as prescribed by the fiber cut playbook.",
        "For P1 Platinum incidents: states who is personally engaged (e.g. senior engineering team, VP, named individual).",
        "For healthcare or financial customers: explicitly acknowledges the business-critical or patient-safety impact rather than treating it as a routine outage.",
        "Does NOT reference SLA compliance as a positive or use it defensively when the customer is frustrated.",
        "For repeat incidents on the same circuit or splice point: explicitly acknowledges the history — does not treat it as a new issue.",
    ],
)

# Expected Facts: checks if the response addresses all expected facts from the eval dataset
# Uses the built-in Correctness scorer which reads expectations.expected_facts
expected_facts_scorer = Correctness(name="expected_facts")

print("Scorers defined: lumen_voice, context_utilization, tone_calibration, playbook_compliance, expected_facts")

# COMMAND ----------

# DBTITLE 1,Run evaluation
mlflow.set_experiment("/Users/stephen.hage@databricks.com/swigert_eval")

print("Running evaluation: 4 scenarios x 5 scorers = 20 judgments")
print("Each scenario invokes the Comms Agent, then all 5 scorers grade the response.")
print("This takes ~3-4 minutes...\n")

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=predict_fn,
    scorers=[lumen_voice, context_utilization, tone_calibration, playbook_compliance, expected_facts_scorer],
)

print("\n" + "=" * 80)
print("EVALUATION COMPLETE")
print("=" * 80)
display(results.tables["eval_results"])

# COMMAND ----------

# DBTITLE 1,Register scorers for production monitoring
from mlflow.genai.scorers import ScorerSamplingConfig, list_scorers, delete_scorer

EXPERIMENT_PATH = "/Users/stephen.hage@databricks.com/swigert_eval"
mlflow.set_experiment(EXPERIMENT_PATH)
experiment = mlflow.get_experiment_by_name(EXPERIMENT_PATH)

# Clean up any previously registered scorers with the same names
existing = {s._server_name for s in list_scorers()}
for name in ["lumen_voice", "context_utilization", "tone_calibration", "playbook_compliance", "expected_facts"]:
    if name in existing:
        delete_scorer(name=name)
        print(f"  Removed existing scorer: {name}")

# Register and start all 5 scorers
scorer_configs = [
    (lumen_voice,          "lumen_voice",          1.0),
    (context_utilization,  "context_utilization",  1.0),
    (tone_calibration,     "tone_calibration",     1.0),
    (playbook_compliance,  "playbook_compliance",  1.0),
    (expected_facts_scorer, "expected_facts",       1.0),
]

registered_scorers = []
for scorer_obj, name, rate in scorer_configs:
    reg = scorer_obj.register(name=name)
    reg.start(sampling_config=ScorerSamplingConfig(sample_rate=rate))
    registered_scorers.append(reg)
    print(f"  ✓ Registered + started: {name} (sample_rate={rate})")

print(f"\n{len(registered_scorers)} scorers registered.")

# --- Validate: run scorers on recent traces to confirm non-null scores ---
print("\nValidating on recent traces...")
sample_traces = mlflow.search_traces(
    experiment_ids=[experiment.experiment_id],
    max_results=4,
    return_type="list",
)

if sample_traces:
    from mlflow.genai.scorers import get_scorer
    validation_scorers = [get_scorer(name=name) for _, name, _ in scorer_configs]
    val_result = mlflow.genai.evaluate(data=sample_traces, scorers=validation_scorers)
    
    # Check for non-null scores
    val_df = val_result.tables["eval_results"]
    print(f"\nValidation results ({len(val_df)} traces):")
    for _, name, _ in scorer_configs:
        col = f"{name}/value"
        if col in val_df.columns:
            non_null = val_df[col].notna().sum()
            print(f"  {name}: {non_null}/{len(val_df)} non-null scores ✓" if non_null > 0 else f"  {name}: ⚠ ALL NULL — scorer may be broken")
        else:
            print(f"  {name}: column not found in results")
    print("\n✓ All scorers validated and monitoring future traces.")
else:
    print("  No traces found yet — scorers are registered but will validate on first incoming trace.")