# Databricks notebook source
# DBTITLE 1,Memory Store Setup
# MAGIC %md
# MAGIC # 03 — Managed Memory Store Setup
# MAGIC
# MAGIC Creates the **Swigert memory store** in Unity Catalog and seeds it with initial entries across four scopes:
# MAGIC
# MAGIC | Scope | Purpose | Seeded Content |
# MAGIC |-------|---------|----------------|
# MAGIC | `customer-{id}` | Per-customer long-term memory | Contact preferences, escalation history, satisfaction signals, network topology |
# MAGIC | `ticket-{id}` | Per-ticket working memory | Classification, communications timeline, diagnostics, resolution |
# MAGIC | `lumen-org` | Shared organizational memory | SLA tiers, communication standards, terminology, escalation paths |
# MAGIC | `lumen-playbooks` | Response playbooks | Fiber cut, latency spike, planned maintenance, escalation response |
# MAGIC
# MAGIC Uses the **UC REST API** (memory stores have no Python SDK yet).

# COMMAND ----------

# DBTITLE 1,Setup: API helper functions
import requests
import json
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.config.host.rstrip('/')
token = w.tokens.create(comment="swigert-memory-setup", lifetime_seconds=3600).token_value

CATALOG = "cmegdemos_catalog"
SCHEMA = "swigert"
STORE_NAME = "agent_memory"
FULL_STORE_NAME = f"{CATALOG}.{SCHEMA}.{STORE_NAME}"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def memory_api(method, path, data=None):
    """Call the UC memory store REST API."""
    url = f"{host}/api/2.1/unity-catalog/{path}"
    resp = requests.request(method, url, headers=headers, json=data)
    if resp.status_code >= 400:
        print(f"ERROR {resp.status_code}: {resp.text}")
        return None
    return resp.json() if resp.text else {}

def create_entry(scope, path, contents, description):
    """Create a memory entry in the store. Paths must start with /memories/."""
    full_path = f"/memories{path}" if not path.startswith("/memories/") else path
    return memory_api(
        "POST",
        f"memory-stores/{FULL_STORE_NAME}/entries?scope={scope}",
        {"path": full_path, "contents": contents, "description": description}
    )

print(f"API helpers ready. Target store: {FULL_STORE_NAME}")

# COMMAND ----------

# DBTITLE 1,Create the memory store
# Create the memory store (idempotent - will error if already exists, that's OK)
result = memory_api("POST", "memory-stores", {
    "name": STORE_NAME,
    "catalog_name": CATALOG,
    "schema_name": SCHEMA,
    "description": "Long-term memory for the Swigert multi-agent service assurance system. Four scopes: customer-{id}, ticket-{id}, lumen-org, lumen-playbooks."
})

if result:
    print(f"Memory store created: {FULL_STORE_NAME}")
    print(json.dumps(result, indent=2))
else:
    # Check if it already exists
    existing = memory_api("GET", f"memory-stores/{FULL_STORE_NAME}")
    if existing:
        print(f"Memory store already exists: {FULL_STORE_NAME}")
        print(json.dumps(existing, indent=2))
    else:
        print("Failed to create or find memory store")

# COMMAND ----------

# DBTITLE 1,Seed: lumen-org scope (organizational memory)
# Organizational memory - shared across all agents
org_entries = [
    {
        "path": "/policies/sla_tiers.md",
        "contents": """# SLA Tier Definitions

| Tier | Response Time | Restore Time | Escalation Trigger | Notes |
|------|--------------|-------------|-------------------|-------|
| Platinum | 15 minutes | 4 hours | 30 min to VP | 24x7 NOC monitoring. Dedicated TAM. |
| Gold | 30 minutes | 8 hours | 60 min to Director | 24x7 support. |
| Silver | 60 minutes | 12 hours | 120 min to Manager | Business hours priority. |
| Bronze | 2 hours | 24 hours | 240 min to Team Lead | Business hours only. |

**Business hours:** Monday-Friday 8:00 AM - 6:00 PM customer local time.
**P1 override:** Any P1 incident for Platinum/Gold customers triggers 24x7 response regardless of business hours.""",
        "description": "SLA tier definitions with response times, restore windows, and escalation triggers"
    },
    {
        "path": "/policies/communication_standards.md",
        "contents": """# Lumen Communication Standards

## Voice & Tone
- Use "we" not "I" — you represent Lumen, not yourself.
- Always reference the ticket number in subject lines and body.
- Acknowledge the customer's frustration before diving into technical details.
- Never promise specific resolution times unless engineering has confirmed.
- Be specific: "We identified elevated latency of 340ms" not "We found some issues."
- For repeat incidents, acknowledge the history explicitly. Never pretend it's a new issue.

## Structure
- Lead with what we know, then what we're doing, then next steps.
- Include: Current Status, Estimated Timeline, Next Update Time, Reference Number.
- For P1/P2: include who is personally engaged ("Our senior network engineering team...").

## Prohibited
- Do NOT blame third parties without also stating Lumen's preventive measures.
- Do NOT use "as per our SLA" defensively when a customer is frustrated.
- Do NOT send generic templates to customers with escalation history.
- Do NOT downplay impact ("minor disruption" when the customer's trading floor is affected).""",
        "description": "Lumen voice and tone guidelines for all customer communications"
    },
    {
        "path": "/terminology/network_terms.md",
        "contents": """# Network Terminology Glossary

- **TTR** — Time to Restore: elapsed time from incident start to service restoration
- **MTTR** — Mean Time to Restore: average TTR across incidents
- **NOC** — Network Operations Center: 24x7 monitoring and first-response team
- **RCA** — Root Cause Analysis: post-incident investigation report
- **CPE** — Customer Premises Equipment: hardware at customer site
- **CO** — Central Office: Lumen facility housing network equipment
- **MPLS** — Multiprotocol Label Switching: private WAN service
- **DIA** — Dedicated Internet Access: committed bandwidth internet
- **SD-WAN** — Software-Defined Wide Area Network: intelligent traffic routing
- **SLA** — Service Level Agreement: contractual performance commitments
- **P1/P2/P3/P4** — Priority levels: Critical/Major/Minor/Informational
- **Splice point** — Physical location where fiber strands are joined""",
        "description": "Network terminology glossary for consistent language across agents"
    },
    {
        "path": "/contacts/escalation_paths.md",
        "contents": """# Escalation Paths

## By Severity
- **P1 Platinum/Gold:** VP of Network Operations (immediate), CTO (if >4 hours)
- **P1 Silver/Bronze:** Director of Operations (within 30 min)
- **P2 Platinum/Gold:** Director of Operations (within 1 hour)
- **P2 Silver/Bronze:** Sr. Manager (within 2 hours)
- **P3/P4:** Standard support queue, team lead review at SLA threshold

## By Region
- **Northeast:** Operations Director — Laura Martinez
- **Southeast:** Operations Director — Robert Chen
- **Midwest:** Operations Director — Amanda Foster
- **West:** Operations Director — David Park
- **Central:** Operations Director — Jennifer Wu

## Account Manager Escalation
Always loop in the assigned account manager within 1 hour of any escalation.""",
        "description": "Escalation paths by severity and region for routing decisions"
    }
]

for entry in org_entries:
    result = create_entry("lumen-org", entry["path"], entry["contents"], entry["description"])
    status = "OK" if result else "FAILED"
    print(f"  [{status}] lumen-org{entry['path']}")

print(f"\nSeeded {len(org_entries)} entries in lumen-org scope")

# COMMAND ----------

# DBTITLE 1,Seed: lumen-playbooks scope
# Playbook memory - response templates and procedures
playbook_entries = [
    {
        "path": "/scenarios/fiber_cut.md",
        "contents": """# Fiber Cut Incident Playbook

## Communication Cadence
- T+0: Acknowledge within SLA window. Confirm impact scope.
- T+15min: Initial customer notification with known impact and ETA.
- T+1hr: Status update even if no new information.
- T+2hr: If unresolved, escalate internally. Update customer with revised ETA.
- T+4hr: VP notification for P1 Platinum.

## Key Messaging Rules
- Lead with what we know, not what we don't.
- If repeat incident on same circuit, acknowledge explicitly. Do NOT pretend it's new.
- Provide specific next steps and timeline, not vague reassurances.
- For healthcare/financial: acknowledge business impact explicitly.

## Diagnostic Steps
1. Verify circuit status in monitoring (SNMP/syslog alerts)
2. Check for correlated outage (OUT-XXXX) — is this part of a larger event?
3. Identify splice point or segment where break occurred
4. Confirm repair crew dispatch and ETA
5. Verify backup/failover path (if customer has redundancy)""",
        "description": "Playbook for fiber cut incidents: timeline, messaging, diagnostics"
    },
    {
        "path": "/scenarios/latency_spike.md",
        "contents": """# Latency / Packet Loss Playbook

## Diagnostic Steps
1. Confirm latency measurements (traceroute, ping, SNMP polling)
2. Check for backbone congestion events
3. Review traffic engineering policies — is traffic being rerouted?
4. Check for DDoS mitigation engagement (scrubbing-related latency)
5. If financial customer during market hours, treat as P1 regardless

## Common Root Causes
- Backbone congestion during traffic peaks
- Traffic reroute due to maintenance or unrelated fiber event
- DDoS scrubbing adding latency to clean traffic
- CPE misconfiguration after firmware update

## Messaging Rules
- Be specific: "We observed latency of {X}ms vs your baseline of {Y}ms"
- For trading floor: acknowledge financial impact explicitly
- Avoid jargon unless contact is known technical""",
        "description": "Playbook for latency and packet loss incidents"
    },
    {
        "path": "/scenarios/escalation_response.md",
        "contents": """# Customer Escalation Playbook

## Tone Shift (MANDATORY)
- Acknowledge frustration: "I understand this has been frustrating..."
- Reference history: "Given your experience with {previous_incident}..."
- Elevate ownership: "I have personally engaged our senior engineering team..."
- Provide concrete commitments, not vague promises.

## Response Times
- Platinum escalation: VP notification 15 min. Customer callback 30 min.
- Gold escalation: Director notification 30 min. Customer response 1 hr.
- Any escalation: Account manager in the loop within 1 hour.

## Prohibited
- Do NOT use generic templates.
- Do NOT reference SLA compliance as a positive.
- Do NOT promise resolution times unless confirmed.
- Do NOT blame third parties without stating Lumen's prevention plan.""",
        "description": "Playbook for handling customer escalations with tone guidance"
    },
    {
        "path": "/scenarios/mass_outage.md",
        "contents": """# Mass Outage Playbook (100+ customers)

## Immediate Actions
1. Activate incident command structure
2. Draft mass notification within 15 minutes
3. Update status page (portal.lumen.com/status)
4. Proactive notification to all affected customers before they contact us

## Communication Template
Subject: [SERVICE ADVISORY] Network Event Affecting {Region} - {Service}

Dear {Contact},

We are experiencing a network event affecting {service} in the {region} area. Our engineering team is actively working to restore service.

Impact: {impact_description}
Start Time: {start_time}
Estimated Restoration: {eta}

We will provide updates every 30 minutes. Real-time status: portal.lumen.com/status

We apologize for the inconvenience.""",
        "description": "Playbook for mass outage events affecting 100+ customers"
    }
]

for entry in playbook_entries:
    result = create_entry("lumen-playbooks", entry["path"], entry["contents"], entry["description"])
    status = "OK" if result else "FAILED"
    print(f"  [{status}] lumen-playbooks{entry['path']}")

print(f"\nSeeded {len(playbook_entries)} entries in lumen-playbooks scope")

# COMMAND ----------

# DBTITLE 1,Seed: customer-CUST-001 scope (Meridian Health)
# Customer memory for Meridian Health (the primary demo customer)
cust001_entries = [
    {
        "path": "/profile/contact.md",
        "contents": """# Meridian Health Systems - Primary Contact
- **Name:** Sarah Chen
- **Email:** sarah.chen@meridianhealth.com
- **Phone:** +1-312-555-0142
- **Timezone:** America/Chicago (Central)
- **Preferred Channel:** Email for initial contact; phone for P1 escalations
- **Communication Style:** Direct and expects specifics. Does not respond well to platitudes or vague reassurances. Appreciates when you acknowledge prior history.""",
        "description": "Meridian Health primary contact details and communication preferences"
    },
    {
        "path": "/profile/account.md",
        "contents": """# Meridian Health Systems - Account Details
- **Customer ID:** CUST-001
- **SLA Tier:** Platinum
- **Account Manager:** James Rodriguez
- **Industry:** Healthcare (HIPAA-sensitive)
- **Services:** MPLS, DIA, SD-WAN, Voice, Cloud Connect
- **Key Circuits:** CKT-44521 (primary MPLS to DR site), CKT-44522, CKT-44530, CKT-44531
- **Contract Value:** Enterprise tier
- **Billing ID:** BILL-MH-4452""",
        "description": "Meridian Health account details, SLA tier, and service inventory"
    },
    {
        "path": "/profile/preferences.md",
        "contents": """# Meridian Health - Communication Preferences (Learned)
- Sarah prefers detailed technical explanations over simplified summaries.
- For P1 incidents, she expects a phone call within 15 minutes of acknowledgment.
- She tracks ticket resolution times and compares to SLA commitments.
- She has explicitly stated she does not want to hear "we're working on it" without specifics.
- After INC-28847, she was promised the fiber splice point would be reinforced and inspected quarterly. Any recurrence on CKT-44521 must reference this commitment.""",
        "description": "Learned communication preferences for Meridian Health from prior interactions"
    },
    {
        "path": "/history/escalations.md",
        "contents": """# Meridian Health - Escalation History

## Escalation 1: INC-28847 (2026-08-12)
- **Trigger:** MPLS circuit CKT-44521 down for 6 hours. EMR connectivity lost.
- **Severity:** P1
- **Resolution:** Fiber splice repair at SP-4421. Circuit restored at 3:30 PM CT.
- **Commitment Made:** Splice point reinforced, added to quarterly inspection rotation.
- **Customer Satisfaction:** Low. Sarah expressed frustration at the 6-hour duration.

## Escalation 2: INC-27103 (2026-06-15)
- **Trigger:** Billing dispute on CKT-44530. Incorrect charges for 2 months.
- **Resolution:** Credits applied, billing system corrected.
- **Customer Satisfaction:** Neutral. Issue resolved but trust was affected.

## Escalation 3: INC-25890 (2026-04-22)
- **Trigger:** SD-WAN configuration change caused 2-hour outage during peak hours.
- **Resolution:** Configuration rolled back, change management process updated.
- **Customer Satisfaction:** Low. Sarah requested advance notification of any future changes.

**Pattern:** 3 escalations in 12 months. Relationship is fragile. Next interaction must be handled with extreme care.""",
        "description": "Escalation history showing 3 incidents in 12 months - fragile relationship"
    },
    {
        "path": "/network/topology.md",
        "contents": """# Meridian Health - Network Topology

## Circuits
- **CKT-44521:** Primary MPLS, Main Campus (Chicago) to DR Site (Aurora). 1 Gbps. CRITICAL - connects EMR to disaster recovery.
- **CKT-44522:** Secondary MPLS, Main Campus to Branch Clinic Network. 500 Mbps.
- **CKT-44530:** DIA, Main Campus internet access. 2 Gbps.
- **CKT-44531:** Cloud Connect, Main Campus to AWS us-east-2. 1 Gbps. Hosts cloud-based analytics.

## Known Vulnerabilities
- CKT-44521 traverses splice point SP-4421 (Naperville CO) — previously failed 2026-08-12.
- No physical redundancy on the DR link (CKT-44521). If it fails, EMR runs on local cache only.
- Cloud Connect (CKT-44531) has no failover path to a secondary cloud region.""",
        "description": "Meridian Health network topology, circuits, and known vulnerabilities"
    }
]

for entry in cust001_entries:
    result = create_entry("customer-CUST-001", entry["path"], entry["contents"], entry["description"])
    status = "OK" if result else "FAILED"
    print(f"  [{status}] customer-CUST-001{entry['path']}")

print(f"\nSeeded {len(cust001_entries)} entries in customer-CUST-001 scope")

# COMMAND ----------

# DBTITLE 1,Seed: ticket-INC-30142 scope (active demo ticket)
# Ticket working memory for the main demo scenario
ticket_entries = [
    {
        "path": "/triage/classification.md",
        "contents": """# Ticket INC-30142 - Triage Classification

- **Severity:** P1 (Critical)
- **Affected Service:** MPLS
- **Affected Circuit:** CKT-44521
- **Region:** Midwest
- **Customer:** Meridian Health Systems (CUST-001, Platinum SLA)
- **SLA Response Deadline:** 2026-09-15T14:38:00Z (15 minutes from creation)
- **SLA Restore Deadline:** 2026-09-15T18:23:00Z (4 hours from creation)

## Routing Decision
- Immediate customer communication required (Comms Agent)
- Diagnostics needed (Diagnostics Agent) - correlate with OUT-5521
- This is a REPEAT incident on CKT-44521 (previous: INC-28847, 2026-08-12)
- Customer has escalation history (3 in 12 months) - handle with care

## Correlated Outage
- OUT-5521: Fiber cut on trunk MKE-ORD-14, affecting Chicago metro MPLS circuits including CKT-44521
- Repair crew dispatched to Naperville splice point. ETA 4 hours.""",
        "description": "Triage classification for INC-30142: P1 MPLS failure, repeat incident, Platinum customer"
    },
    {
        "path": "/triage/related_tickets.md",
        "contents": """# INC-30142 - Related Tickets & Outages

## Previous Ticket (SAME CIRCUIT)
- **INC-28847** (2026-08-12): MPLS CKT-44521 failure. Root cause: fiber cut at splice point SP-4421. Resolved in 6 hours. Customer was told SP-4421 was reinforced and on quarterly inspection.

## Active Outage
- **OUT-5521**: Fiber cut on trunk route MKE-ORD-14. 12 customers affected. Repair crew dispatched. ETA 4 hours.
- CKT-44521 is confirmed in the OUT-5521 affected circuit list.

## Duplicate Check
- No duplicate tickets from this customer for this incident.
- 3 other customers have opened tickets related to OUT-5521.""",
        "description": "Related tickets and active outage correlation for INC-30142"
    }
]

for entry in ticket_entries:
    result = create_entry("ticket-INC-30142", entry["path"], entry["contents"], entry["description"])
    status = "OK" if result else "FAILED"
    print(f"  [{status}] ticket-INC-30142{entry['path']}")

print(f"\nSeeded {len(ticket_entries)} entries in ticket-INC-30142 scope")

# COMMAND ----------

# DBTITLE 1,Verify: Search memory entries
# Verify memory store by searching each scope
for scope in ["lumen-org", "lumen-playbooks", "customer-CUST-001", "ticket-INC-30142"]:
    result = memory_api(
        "POST",
        f"memory-stores/{FULL_STORE_NAME}/entries:search",
        {"scope": scope, "query": "summary"}
    )
    if result and "entries" in result:
        print(f"\n{scope}: {len(result['entries'])} entries")
        for e in result["entries"]:
            print(f"  - {e.get('path', 'unknown')}")
    else:
        print(f"\n{scope}: No entries found or search failed")

print("\n--- Memory store setup complete ---")