# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Swigert Seed Data Setup
# MAGIC %md
# MAGIC # 01 — Seed Data
# MAGIC Creates the foundational tables in `cmegdemos_catalog.swigert` for the Swigert multi-agent service assurance demo.
# MAGIC
# MAGIC **Tables created:**
# MAGIC - `customers` — Lumen enterprise customers with SLA tiers, contacts, network topology
# MAGIC - `tickets` — Service tickets with severity, status, affected services
# MAGIC - `sla_tiers` — SLA tier definitions (Platinum/Gold/Silver/Bronze)
# MAGIC - `active_outages` — Current network outages by region/service
# MAGIC - `playbooks` — Response playbooks for common scenarios
# MAGIC - `communication_log` — History of customer communications per ticket

# COMMAND ----------

# DBTITLE 1,Load shared YAML config
from pathlib import Path
import yaml

CONFIG_PATH = Path("/Workspace/Users/stephen.hage@databricks.com/agent_memory_tickets/demo_config.yaml")
with CONFIG_PATH.open() as f:
    CONFIG = yaml.safe_load(f)

CATALOG = CONFIG["catalog_name"]
SCHEMA = CONFIG["schema_name"]

spark.sql(f"USE CATALOG `{CATALOG}`")
spark.sql(f"USE SCHEMA `{SCHEMA}`")

print(f"Loaded config from {CONFIG_PATH}")
print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Verify catalog context
# MAGIC %sql
# MAGIC SELECT current_catalog() AS catalog_name, current_schema() AS schema_name;

# COMMAND ----------

# DBTITLE 1,Set catalog context
# MAGIC %sql
# MAGIC USE CATALOG cmegdemos_catalog;
# MAGIC USE SCHEMA swigert;

# COMMAND ----------

# DBTITLE 1,SLA tier definitions
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE sla_tiers (
# MAGIC   tier_name STRING COMMENT 'SLA tier: Platinum, Gold, Silver, Bronze',
# MAGIC   response_time_minutes INT COMMENT 'Maximum initial response time in minutes',
# MAGIC   restore_time_hours INT COMMENT 'Maximum service restore time in hours',
# MAGIC   escalation_trigger_minutes INT COMMENT 'Auto-escalate if no response within this many minutes',
# MAGIC   priority_multiplier DOUBLE COMMENT 'Severity score multiplier for this tier',
# MAGIC   description STRING COMMENT 'Tier description and entitlements'
# MAGIC ) COMMENT 'SLA tier definitions governing response times, restore windows, and escalation triggers';
# MAGIC
# MAGIC INSERT INTO sla_tiers VALUES
# MAGIC   ('Platinum', 15, 4, 30, 2.0, 'Enterprise-critical. 24x7 NOC monitoring. Dedicated TAM. 15-min response, 4-hour restore. Auto-escalate to VP at 30 min.'),
# MAGIC   ('Gold', 30, 8, 60, 1.5, 'Business-critical. 24x7 support. 30-min response, 8-hour restore. Auto-escalate to director at 60 min.'),
# MAGIC   ('Silver', 60, 12, 120, 1.0, 'Standard business. Business-hours priority. 60-min response, 12-hour restore. Auto-escalate to manager at 2 hours.'),
# MAGIC   ('Bronze', 120, 24, 240, 0.75, 'Basic support. Business-hours only. 2-hour response, 24-hour restore. Auto-escalate to team lead at 4 hours.');

# COMMAND ----------

# DBTITLE 1,Customer seed data
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE customers (
# MAGIC   customer_id STRING COMMENT 'Unique customer identifier',
# MAGIC   company_name STRING COMMENT 'Customer company name',
# MAGIC   sla_tier STRING COMMENT 'SLA tier: Platinum, Gold, Silver, Bronze',
# MAGIC   primary_contact_name STRING COMMENT 'Primary contact full name',
# MAGIC   primary_contact_email STRING COMMENT 'Primary contact email',
# MAGIC   primary_contact_phone STRING COMMENT 'Primary contact phone',
# MAGIC   preferred_channel STRING COMMENT 'Preferred communication channel: email, phone, portal',
# MAGIC   timezone STRING COMMENT 'Customer timezone',
# MAGIC   account_manager STRING COMMENT 'Assigned Lumen account manager',
# MAGIC   region STRING COMMENT 'Geographic region: Northeast, Southeast, Midwest, West, Central',
# MAGIC   services ARRAY<STRING> COMMENT 'Active Lumen services: MPLS, DIA, SD-WAN, Voice, Cloud Connect, etc.',
# MAGIC   circuits ARRAY<STRING> COMMENT 'Active circuit IDs',
# MAGIC   escalation_history INT COMMENT 'Number of escalations in past 12 months',
# MAGIC   satisfaction_score DOUBLE COMMENT 'Last NPS/CSAT score (0-10)',
# MAGIC   notes STRING COMMENT 'Account notes and special handling instructions'
# MAGIC ) COMMENT 'Lumen enterprise customer profiles with SLA, contact, and network context';
# MAGIC
# MAGIC INSERT INTO customers VALUES
# MAGIC   ('CUST-001', 'LakeLink Fiber', 'Platinum', 'Sarah Chen', 'sarah.chen@lakelinkfiber.com', '+1-312-555-0142', 'email', 'America/Chicago', 'James Rodriguez', 'Midwest',
# MAGIC    ARRAY('MPLS', 'DIA', 'SD-WAN', 'Voice', 'Cloud Connect'), ARRAY('CKT-44521', 'CKT-44522', 'CKT-44530', 'CKT-44531'), 3, 6.2,
# MAGIC    'Critical fiber ISP customer. CPNI-sensitive. 3 escalations in 12 months — relationship is fragile. Sarah is direct and expects specifics, not platitudes. Previous incident (INC-28847) took 6 hours to resolve; she was promised it would not recur.'),
# MAGIC   ('CUST-002', 'Apex Financial Group', 'Platinum', 'Michael Torres', 'mtorres@apexfinancial.com', '+1-212-555-0198', 'phone', 'America/New_York', 'Lisa Park', 'Northeast',
# MAGIC    ARRAY('DIA', 'Cloud Connect', 'DDoS Mitigation', 'Voice'), ARRAY('CKT-33201', 'CKT-33202', 'CKT-33210'), 1, 8.5,
# MAGIC    'Tier-1 financial services. Trading floor connectivity is business-critical — any latency impacts real dollars. Michael prefers phone for P1/P2. Extremely sensitive about market hours (9:30 AM - 4 PM ET). Previous P1 resolved in 2 hours — set a good precedent.'),
# MAGIC   ('CUST-003', 'Pacific Logistics Corp', 'Gold', 'David Kim', 'dkim@pacificlogistics.com', '+1-206-555-0167', 'email', 'America/Los_Angeles', 'James Rodriguez', 'West',
# MAGIC    ARRAY('SD-WAN', 'DIA', 'Voice'), ARRAY('CKT-55801', 'CKT-55802'), 0, 9.1,
# MAGIC    'Growing mid-market account. Very satisfied. David is technical and appreciates detailed root cause explanations. Good candidate for upsell. No escalation history.'),
# MAGIC   ('CUST-004', 'Southeastern University', 'Silver', 'Dr. Patricia Okafor', 'pokafor@seu.edu', '+1-404-555-0134', 'portal', 'America/New_York', 'Lisa Park', 'Southeast',
# MAGIC    ARRAY('DIA', 'Voice', 'MPLS'), ARRAY('CKT-22101', 'CKT-22102'), 2, 5.8,
# MAGIC    'Education sector. Budget-sensitive. Dr. Okafor is frustrated with recurring outages on CKT-22101 — has threatened to RFP competitors. Escalated twice: once for 8-hour outage during finals week, once for billing dispute. Needs white-glove treatment on next incident.'),
# MAGIC   ('CUST-005', 'NovaTech Manufacturing', 'Gold', 'Rachel Nguyen', 'rnguyen@novatech-mfg.com', '+1-313-555-0156', 'email', 'America/Detroit', 'James Rodriguez', 'Midwest',
# MAGIC    ARRAY('MPLS', 'SD-WAN', 'Cloud Connect'), ARRAY('CKT-66701', 'CKT-66702', 'CKT-66703'), 0, 8.8,
# MAGIC    'Manufacturing IoT customer. 24/7 operations — connectivity to cloud analytics platform is production-critical. Rachel is an IT director, very organized, appreciates proactive status updates even when there is no new information.'),
# MAGIC   ('CUST-006', 'Downtown Metro Transit Authority', 'Bronze', 'Carlos Mendez', 'cmendez@dmta.gov', '+1-214-555-0189', 'email', 'America/Chicago', 'Lisa Park', 'Central',
# MAGIC    ARRAY('DIA', 'Voice'), ARRAY('CKT-11501'), 0, 7.5,
# MAGIC    'Government/public sector. Formal communication expected. Procurement process means long lead times for changes. Carlos is the IT manager — responsive but constrained by bureaucratic approval chains.');

# COMMAND ----------

# DBTITLE 1,Tickets seed data
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE tickets (
# MAGIC   ticket_id STRING COMMENT 'Unique ticket identifier',
# MAGIC   customer_id STRING COMMENT 'FK to customers.customer_id',
# MAGIC   created_at TIMESTAMP COMMENT 'Ticket creation timestamp',
# MAGIC   updated_at TIMESTAMP COMMENT 'Last update timestamp',
# MAGIC   status STRING COMMENT 'Ticket status: open, investigating, pending_customer, resolved, escalated',
# MAGIC   severity STRING COMMENT 'Severity: P1 (critical), P2 (major), P3 (minor), P4 (informational)',
# MAGIC   title STRING COMMENT 'Short ticket summary',
# MAGIC   description STRING COMMENT 'Full ticket description from customer',
# MAGIC   affected_service STRING COMMENT 'Primary affected Lumen service',
# MAGIC   affected_circuit STRING COMMENT 'Affected circuit ID if applicable',
# MAGIC   region STRING COMMENT 'Geographic region of the issue',
# MAGIC   assigned_engineer STRING COMMENT 'Assigned NOC/field engineer',
# MAGIC   sla_deadline TIMESTAMP COMMENT 'SLA response deadline',
# MAGIC   root_cause STRING COMMENT 'Root cause if identified',
# MAGIC   resolution STRING COMMENT 'Resolution details if resolved'
# MAGIC ) COMMENT 'Service assurance tickets representing customer-reported issues';
# MAGIC
# MAGIC INSERT INTO tickets VALUES
# MAGIC   -- Active ticket: P1 for LakeLink Fiber (Platinum) - the main demo scenario
# MAGIC   ('INC-30142', 'CUST-001', '2026-09-15T14:23:00Z', '2026-09-15T14:23:00Z',
# MAGIC    'open', 'P1', 'Complete MPLS circuit failure - primary network management link down',
# MAGIC    'Our primary MPLS circuit CKT-44521 connecting our core POP to our disaster recovery site went down at approximately 2:15 PM CT. We have lost connectivity to our DR environment and our OSS/BSS platform is running on local cache only. This is subscriber-service critical. We need immediate attention. This is the SAME circuit that failed last month (INC-28847). I was told this was permanently fixed.',
# MAGIC    'MPLS', 'CKT-44521', 'Midwest', NULL, '2026-09-15T14:38:00Z', NULL, NULL),
# MAGIC
# MAGIC   -- Active ticket: P2 for Apex Financial (Platinum)
# MAGIC   ('INC-30143', 'CUST-002', '2026-09-15T15:10:00Z', '2026-09-15T15:10:00Z',
# MAGIC    'open', 'P2', 'Intermittent latency spikes on DIA circuit - trading floor impacted',
# MAGIC    'We are seeing latency spikes of 200-400ms on CKT-33201 every 5-10 minutes. This started around 2:45 PM ET. Our automated trading systems are triggering circuit-breakers and we are losing execution windows. This is NOT a full outage but the financial impact is significant. Need diagnostics ASAP.',
# MAGIC    'DIA', 'CKT-33201', 'Northeast', 'NOC-Engineer-4', '2026-09-15T15:40:00Z', NULL, NULL),
# MAGIC
# MAGIC   -- Active ticket: P3 for Pacific Logistics (Gold)
# MAGIC   ('INC-30144', 'CUST-003', '2026-09-15T10:30:00Z', '2026-09-15T12:45:00Z',
# MAGIC    'investigating', 'P3', 'SD-WAN failover not triggering on secondary link',
# MAGIC    'Our SD-WAN appliance at our SeaTac warehouse is not failing over to the secondary link when we simulate a primary failure. We discovered this during a routine DR test. Not impacting production currently but we need this resolved before our peak shipping season starts next week.',
# MAGIC    'SD-WAN', 'CKT-55801', 'West', 'NOC-Engineer-2', '2026-09-15T11:00:00Z', NULL, NULL),
# MAGIC
# MAGIC   -- Resolved ticket for demo reference: previous LakeLink Fiber incident
# MAGIC   ('INC-28847', 'CUST-001', '2026-08-12T09:15:00Z', '2026-08-12T15:30:00Z',
# MAGIC    'resolved', 'P1', 'MPLS circuit failure - CKT-44521 down',
# MAGIC    'Primary MPLS circuit CKT-44521 is completely down. OSS/BSS connectivity lost to DR site.',
# MAGIC    'MPLS', 'CKT-44521', 'Midwest', 'NOC-Engineer-7', '2026-08-12T09:30:00Z',
# MAGIC    'Fiber cut at splice point SP-4421 in Naperville CO. Repair crew dispatched and splice completed.',
# MAGIC    'Fiber splice repaired at SP-4421. Circuit restored at 3:30 PM CT. Monitoring for 24 hours. Customer informed that splice point has been reinforced and added to quarterly inspection rotation.');

# COMMAND ----------

# DBTITLE 1,Active outages seed data
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE active_outages (
# MAGIC   outage_id STRING COMMENT 'Unique outage identifier',
# MAGIC   region STRING COMMENT 'Affected geographic region',
# MAGIC   affected_service STRING COMMENT 'Affected service type',
# MAGIC   start_time TIMESTAMP COMMENT 'Outage start time',
# MAGIC   estimated_restore TIMESTAMP COMMENT 'Estimated restore time',
# MAGIC   status STRING COMMENT 'Outage status: active, monitoring, resolved',
# MAGIC   description STRING COMMENT 'Outage description',
# MAGIC   affected_circuits ARRAY<STRING> COMMENT 'List of affected circuit IDs',
# MAGIC   affected_customer_count INT COMMENT 'Number of affected customers'
# MAGIC ) COMMENT 'Active and recent network outages used by triage agent for correlation';
# MAGIC
# MAGIC INSERT INTO active_outages VALUES
# MAGIC   ('OUT-5521', 'Midwest', 'MPLS', '2026-09-15T14:10:00Z', '2026-09-15T18:00:00Z', 'active',
# MAGIC    'Fiber cut on trunk route MKE-ORD-14 affecting multiple MPLS circuits in the Chicago metro area. Repair crew dispatched to Naperville splice point. ETA 4 hours.',
# MAGIC    ARRAY('CKT-44521', 'CKT-44535', 'CKT-44540', 'CKT-44542'), 12),
# MAGIC   ('OUT-5519', 'Northeast', 'DIA', '2026-09-15T13:45:00Z', NULL, 'monitoring',
# MAGIC    'Intermittent congestion on NYC-BOS backbone segment. Traffic engineering team investigating. Some customers experiencing elevated latency.',
# MAGIC    ARRAY('CKT-33201', 'CKT-33215', 'CKT-33220'), 8);

# COMMAND ----------

# DBTITLE 1,Response playbooks
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE playbooks (
# MAGIC   playbook_id STRING COMMENT 'Unique playbook identifier',
# MAGIC   scenario STRING COMMENT 'Scenario name: fiber_cut, latency_spike, planned_maintenance, mass_outage, escalation_response',
# MAGIC   title STRING COMMENT 'Playbook title',
# MAGIC   content STRING COMMENT 'Full playbook content with messaging templates and procedures'
# MAGIC ) COMMENT 'Response playbooks defining communication cadence, templates, and procedures for common scenarios';
# MAGIC
# MAGIC INSERT INTO playbooks VALUES
# MAGIC   ('PB-001', 'fiber_cut', 'Fiber Cut Incident Response',
# MAGIC    '## Fiber Cut Playbook\n\n### Timeline\n- T+0: Acknowledge ticket within SLA window. Confirm impact scope.\n- T+15min: Send initial customer communication with known impact and ETA if available.\n- T+1hr: Status update even if no new information. Show progress.\n- T+2hr: If not resolved, escalate internally and update customer with revised ETA.\n- T+4hr: If P1 Platinum, VP notification triggered automatically.\n\n### Messaging Guidance\n- Lead with what we know, not what we dont.\n- If this is a repeat incident on the same circuit, acknowledge it explicitly. Do NOT pretend it is a new issue.\n- Provide specific next steps and timeline, not vague reassurances.\n- For carrier/financial customers, acknowledge business impact explicitly.\n\n### Template: Initial Acknowledgment\nSubject: [URGENT] Service Impact Notification - {ticket_id}\n\nDear {contact_name},\n\nWe are aware of a service disruption affecting your {service_type} circuit {circuit_id}. Our network operations center detected this issue at {detection_time} and our team is actively working on restoration.\n\n**Current Status:** {status_description}\n**Estimated Restoration:** {eta}\n**Your Reference:** {ticket_id}\n\nWe will provide updates every {update_cadence} until service is restored. You can also check real-time status at portal.lumen.com/status.\n\n{escalation_note_if_repeat_incident}\n\nSincerely,\nLumen Service Assurance'),
# MAGIC
# MAGIC   ('PB-002', 'latency_spike', 'Latency / Packet Loss Response',
# MAGIC    '## Latency Spike Playbook\n\n### Diagnostic Steps\n1. Confirm latency measurements (traceroute, ping, SNMP polling).\n2. Check for backbone congestion events (correlate with OUT- records).\n3. Review traffic engineering policies — is traffic being rerouted through a longer path?\n4. Check for DDoS mitigation engagement (could be scrubbing-related latency).\n5. If financial customer during market hours, treat as P1 regardless of classification.\n\n### Messaging Guidance\n- Be specific about the measurements: "We observed latency of {measured_ms}ms vs your baseline of {baseline_ms}ms."\n- For trading floor customers, acknowledge the financial impact explicitly.\n- Avoid technical jargon unless the contact is known to be technical.\n\n### Common Root Causes\n- Backbone congestion during traffic peaks\n- Traffic reroute due to maintenance or unrelated fiber event\n- DDoS scrubbing adding latency to clean traffic\n- CPE misconfiguration after firmware update'),
# MAGIC
# MAGIC   ('PB-003', 'escalation_response', 'Customer Escalation Response',
# MAGIC    '## Escalation Playbook\n\n### Tone Shift\nWhen a customer escalates, the communication tone MUST shift:\n- Acknowledge their frustration explicitly: "I understand this has been frustrating..."\n- Reference their history: "Given your experience with {previous_incident}, I understand why this is concerning."\n- Elevate ownership: "I have personally engaged our senior engineering team..."\n- Provide concrete commitments, not vague promises.\n\n### Response Time\n- Platinum escalation: VP notification within 15 minutes. Customer callback within 30 minutes.\n- Gold escalation: Director notification within 30 minutes. Customer response within 1 hour.\n- Any escalation: Account manager MUST be in the loop within 1 hour.\n\n### What NOT To Do\n- Do NOT use generic templates for escalated customers.\n- Do NOT reference SLA compliance as a positive if the customer is unhappy.\n- Do NOT promise specific resolution times unless engineering has confirmed.\n- Do NOT blame third parties (vendors, weather, construction crews) without also stating what Lumen is doing to prevent recurrence.');

# COMMAND ----------

# DBTITLE 1,Communication log table
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE communication_log (
# MAGIC   comm_id STRING COMMENT 'Unique communication identifier',
# MAGIC   ticket_id STRING COMMENT 'FK to tickets.ticket_id',
# MAGIC   customer_id STRING COMMENT 'FK to customers.customer_id',
# MAGIC   sent_at TIMESTAMP COMMENT 'When the communication was sent',
# MAGIC   channel STRING COMMENT 'Communication channel: email, phone, portal',
# MAGIC   direction STRING COMMENT 'Direction: outbound (to customer), inbound (from customer)',
# MAGIC   subject STRING COMMENT 'Email subject or call summary',
# MAGIC   body STRING COMMENT 'Full communication body',
# MAGIC   sent_by STRING COMMENT 'Agent or person who sent it',
# MAGIC   tone_flags ARRAY<STRING> COMMENT 'Tone markers: empathetic, technical, urgent, formal, escalation_aware'
# MAGIC ) COMMENT 'Record of all customer communications per ticket for context continuity';
# MAGIC
# MAGIC -- Seed with one historical communication for the previous LakeLink Fiber incident
# MAGIC INSERT INTO communication_log VALUES
# MAGIC   ('COMM-28847-001', 'INC-28847', 'CUST-001', '2026-08-12T09:35:00Z', 'email', 'outbound',
# MAGIC    '[URGENT] Service Impact - INC-28847 - MPLS Circuit CKT-44521',
# MAGIC    'Dear Sarah,\n\nWe are aware of the disruption to your MPLS circuit CKT-44521 and understand the critical nature of this connection to your network operations. Our network operations center identified a fiber issue at approximately 9:15 AM CT and a repair crew has been dispatched.\n\nEstimated restoration: 3:00 PM CT\nYour reference: INC-28847\n\nWe will provide hourly updates until service is restored.\n\nSincerely,\nLumen Service Assurance',
# MAGIC    'Comms Agent', ARRAY('empathetic', 'urgent')),
# MAGIC   ('COMM-28847-002', 'INC-28847', 'CUST-001', '2026-08-12T15:45:00Z', 'email', 'outbound',
# MAGIC    '[RESOLVED] Service Restored - INC-28847 - MPLS Circuit CKT-44521',
# MAGIC    'Dear Sarah,\n\nI am pleased to confirm that your MPLS circuit CKT-44521 has been fully restored as of 3:30 PM CT. The root cause was a fiber cut at splice point SP-4421 in the Naperville CO.\n\nTo prevent recurrence, we have reinforced the splice point and added it to our quarterly physical inspection rotation.\n\nWe sincerely apologize for the disruption to your operations. If you experience any further issues or have questions, please do not hesitate to reach out.\n\nSincerely,\nLumen Service Assurance',
# MAGIC    'Comms Agent', ARRAY('empathetic', 'technical'));

# COMMAND ----------

# DBTITLE 1,Verify seed data
# MAGIC %sql
# MAGIC -- Verify all tables created with correct row counts
# MAGIC SELECT 'sla_tiers' AS table_name, COUNT(*) AS row_count FROM swigert.sla_tiers
# MAGIC UNION ALL SELECT 'customers', COUNT(*) FROM swigert.customers
# MAGIC UNION ALL SELECT 'tickets', COUNT(*) FROM swigert.tickets
# MAGIC UNION ALL SELECT 'active_outages', COUNT(*) FROM swigert.active_outages
# MAGIC UNION ALL SELECT 'playbooks', COUNT(*) FROM swigert.playbooks
# MAGIC UNION ALL SELECT 'communication_log', COUNT(*) FROM swigert.communication_log;