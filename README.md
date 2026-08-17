# Decentralized Infrastructure SLA Uptime & SLA Breach Decision Oracle

An Intelligent Contract decision primitive built on **GenLayer** for automated enterprise IT infrastructure SLA monitoring, DNS health token auditing, and SLA breach decision gates grounded in Google Public DNS and authoritative real-time UTC atomic clock APIs.

---

## 📖 Overview

The `SlaUptimeVault` decision oracle allows enterprise IT providers and clients to register SLA coverage parameters. Rather than holding unbacked token deposits or relying on bank-day currency calendars, it substantively binds **authoritative live UTC atomic clock APIs** (`timeapi.io`) and **Google Public DNS health token records** (`dns.google`) to produce on-chain decision verdicts (`SLA_COVERAGE_ACTIVE` $\rightarrow$ `SLA_VIOLATION_PENALIZED` / `SLA_PERIOD_COMPLETED_PASSED`).

---

## 🛡️ Key Features & Guardrails

1. **Authoritative 24/7/365 UTC Atomic Clock & Freshness Guard**:
   - Queries the live authoritative real-time UTC Clock API (`https://timeapi.io/api/time/current/zone?timeZone=UTC`), ensuring accurate date tracking across weekends, Sundays, and public bank holidays without currency-data latency.
   - Enforces `clock_fresh == True` (`[ERR_CLOCK_01]`) and `today_date >= start_date` (`[ERR_TERM_01]`) before ANY DNS evaluations or violation transitions.
2. **Bidirectional DNS Record Availability Binding**:
   - Criteria requires consensus nodes to independently inspect DNS payload presence and reject proposals if `dns_records_found` is inconsistent in **EITHER direction** (true when missing or false when present).
3. **Data Availability Assertion Guard**:
   - Missing or corrupted DNS responses abort cleanly (`[ERR_DATA_01]`) without penalizing, preventing temporary network dropouts from being recorded as SLA breach violations.
4. **Access Control**:
   - Audits strictly restricted to service provider, client, or contract operator (`[ERR_AUTH_01]`).

---

## 🚀 How to Test in GenLayer Studio

1. **Deploy Contract**: Deploy `SlaUptimeVault` with your wallet address as `operator`.
2. **Create Vault Gate**: Call `create_vault`:
   * `client`: `"0x09fae1aafadb0a3b8382e43ed8d2d56ba92171c3"`
   * `service_domain`: `"google.com"`
   * `expected_health_token`: `"v=spf1"`
   * `start_date`: `"2026-07-01"`
   * `end_date`: `"2026-08-31"`
   > *Returns: `"SLA_VAULT_001"`*
3. **Audit SLA Uptime**: Call `audit_sla_uptime("SLA_VAULT_001")`.
4. **Inspect Decision Verdict**: Call `get_vault("SLA_VAULT_001")`.
