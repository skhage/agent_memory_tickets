# Databricks notebook source
# DBTITLE 1,UC Functions for Swigert Agents
# MAGIC %md
# MAGIC # 02 — Unity Catalog Functions
# MAGIC Agent tools implemented as UC functions in `cmegdemos_catalog.swigert`.
# MAGIC
# MAGIC These functions are registered in Unity Catalog and can be called by any agent as tools.
# MAGIC
# MAGIC **Functions:**
# MAGIC - `check_sla_status` — Returns SLA tier, response deadline, and compliance status for a customer + ticket
# MAGIC - `search_active_outages` — Returns active outages matching a region and/or service type
# MAGIC - `get_ticket_details` — Returns full ticket state, timeline, and assigned engineer
# MAGIC - `get_customer_profile` — Returns customer metadata, SLA tier, preferences, and history
# MAGIC - `get_communication_history` — Returns prior communications for a ticket or customer

# COMMAND ----------

# DBTITLE 1,Set catalog context
# MAGIC %sql
# MAGIC USE CATALOG cmegdemos_catalog;
# MAGIC USE SCHEMA swigert;

# COMMAND ----------

# DBTITLE 1,check_sla_status
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION check_sla_status(
# MAGIC   p_customer_id STRING COMMENT 'Customer ID to check SLA for',
# MAGIC   p_ticket_created_at STRING COMMENT 'Ticket creation timestamp as ISO string'
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   customer_id STRING,
# MAGIC   company_name STRING,
# MAGIC   sla_tier STRING,
# MAGIC   response_time_minutes INT,
# MAGIC   restore_time_hours INT,
# MAGIC   sla_deadline STRING,
# MAGIC   minutes_remaining DOUBLE,
# MAGIC   sla_breached BOOLEAN,
# MAGIC   escalation_trigger_minutes INT
# MAGIC )
# MAGIC COMMENT 'Returns SLA status for a customer given a ticket creation time. Used by Triage Agent to determine response urgency and escalation triggers.'
# MAGIC RETURN
# MAGIC   SELECT
# MAGIC     c.customer_id,
# MAGIC     c.company_name,
# MAGIC     c.sla_tier,
# MAGIC     s.response_time_minutes,
# MAGIC     s.restore_time_hours,
# MAGIC     CAST(CAST(p_ticket_created_at AS TIMESTAMP) + INTERVAL '1' MINUTE * s.response_time_minutes AS STRING) AS sla_deadline,
# MAGIC     TIMESTAMPDIFF(MINUTE, CURRENT_TIMESTAMP(), CAST(p_ticket_created_at AS TIMESTAMP) + INTERVAL '1' MINUTE * s.response_time_minutes) AS minutes_remaining,
# MAGIC     CURRENT_TIMESTAMP() > (CAST(p_ticket_created_at AS TIMESTAMP) + INTERVAL '1' MINUTE * s.response_time_minutes) AS sla_breached,
# MAGIC     s.escalation_trigger_minutes
# MAGIC   FROM customers c
# MAGIC   JOIN sla_tiers s ON c.sla_tier = s.tier_name
# MAGIC   WHERE c.customer_id = p_customer_id;

# COMMAND ----------

# DBTITLE 1,search_active_outages
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION search_active_outages(
# MAGIC   p_region STRING COMMENT 'Region to search for outages (e.g., Midwest, Northeast). Pass NULL for all regions.',
# MAGIC   p_service STRING COMMENT 'Service type to filter (e.g., MPLS, DIA). Pass NULL for all services.'
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   outage_id STRING,
# MAGIC   region STRING,
# MAGIC   affected_service STRING,
# MAGIC   start_time TIMESTAMP,
# MAGIC   estimated_restore TIMESTAMP,
# MAGIC   status STRING,
# MAGIC   description STRING,
# MAGIC   affected_circuits ARRAY<STRING>,
# MAGIC   affected_customer_count INT
# MAGIC )
# MAGIC COMMENT 'Searches for active network outages by region and/or service type. Used by Triage Agent to correlate tickets with known outages.'
# MAGIC RETURN
# MAGIC   SELECT *
# MAGIC   FROM active_outages
# MAGIC   WHERE status IN ('active', 'monitoring')
# MAGIC     AND (p_region IS NULL OR region = p_region)
# MAGIC     AND (p_service IS NULL OR affected_service = p_service);

# COMMAND ----------

# DBTITLE 1,get_ticket_details
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_ticket_details(
# MAGIC   p_ticket_id STRING COMMENT 'Ticket ID to retrieve details for'
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   ticket_id STRING,
# MAGIC   customer_id STRING,
# MAGIC   company_name STRING,
# MAGIC   created_at TIMESTAMP,
# MAGIC   updated_at TIMESTAMP,
# MAGIC   status STRING,
# MAGIC   severity STRING,
# MAGIC   title STRING,
# MAGIC   description STRING,
# MAGIC   affected_service STRING,
# MAGIC   affected_circuit STRING,
# MAGIC   region STRING,
# MAGIC   assigned_engineer STRING,
# MAGIC   sla_deadline TIMESTAMP,
# MAGIC   root_cause STRING,
# MAGIC   resolution STRING,
# MAGIC   sla_tier STRING
# MAGIC )
# MAGIC COMMENT 'Returns full ticket details joined with customer context. Used by all agents to understand current ticket state.'
# MAGIC RETURN
# MAGIC   SELECT
# MAGIC     t.ticket_id, t.customer_id, c.company_name,
# MAGIC     t.created_at, t.updated_at, t.status, t.severity,
# MAGIC     t.title, t.description, t.affected_service,
# MAGIC     t.affected_circuit, t.region, t.assigned_engineer,
# MAGIC     t.sla_deadline, t.root_cause, t.resolution,
# MAGIC     c.sla_tier
# MAGIC   FROM tickets t
# MAGIC   JOIN customers c ON t.customer_id = c.customer_id
# MAGIC   WHERE t.ticket_id = p_ticket_id;

# COMMAND ----------

# DBTITLE 1,get_customer_profile
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_customer_profile(
# MAGIC   p_customer_id STRING COMMENT 'Customer ID to retrieve profile for'
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   customer_id STRING,
# MAGIC   company_name STRING,
# MAGIC   sla_tier STRING,
# MAGIC   primary_contact_name STRING,
# MAGIC   primary_contact_email STRING,
# MAGIC   preferred_channel STRING,
# MAGIC   timezone STRING,
# MAGIC   account_manager STRING,
# MAGIC   region STRING,
# MAGIC   services ARRAY<STRING>,
# MAGIC   escalation_history INT,
# MAGIC   satisfaction_score DOUBLE,
# MAGIC   notes STRING,
# MAGIC   recent_ticket_count BIGINT
# MAGIC )
# MAGIC COMMENT 'Returns customer profile with SLA tier, contact preferences, satisfaction signals, and recent ticket count. Used by Comms Agent for tone calibration.'
# MAGIC RETURN
# MAGIC   SELECT
# MAGIC     c.*,
# MAGIC     (SELECT COUNT(*) FROM tickets t WHERE t.customer_id = c.customer_id AND t.created_at > CURRENT_TIMESTAMP() - INTERVAL '90' DAY) AS recent_ticket_count
# MAGIC   FROM customers c
# MAGIC   WHERE c.customer_id = p_customer_id;

# COMMAND ----------

# DBTITLE 1,get_communication_history
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_communication_history(
# MAGIC   p_ticket_id STRING COMMENT 'Ticket ID to retrieve communication history for. Pass NULL to search by customer.',
# MAGIC   p_customer_id STRING COMMENT 'Customer ID to retrieve all communications for. Used when ticket_id is NULL.'
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   comm_id STRING,
# MAGIC   ticket_id STRING,
# MAGIC   customer_id STRING,
# MAGIC   sent_at TIMESTAMP,
# MAGIC   channel STRING,
# MAGIC   direction STRING,
# MAGIC   subject STRING,
# MAGIC   body STRING,
# MAGIC   sent_by STRING,
# MAGIC   tone_flags ARRAY<STRING>
# MAGIC )
# MAGIC COMMENT 'Returns communication history for a ticket or customer. Used by Comms Agent to maintain conversation continuity and avoid repeating information.'
# MAGIC RETURN
# MAGIC   SELECT *
# MAGIC   FROM communication_log
# MAGIC   WHERE (p_ticket_id IS NOT NULL AND ticket_id = p_ticket_id)
# MAGIC      OR (p_ticket_id IS NULL AND customer_id = p_customer_id)
# MAGIC   ORDER BY sent_at DESC;