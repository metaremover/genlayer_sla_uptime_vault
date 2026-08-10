# Decentralized Infrastructure SLA Uptime & SLA Breach Decision Oracle

An Intelligent Contract decision primitive built on **GenLayer** for automated enterprise IT infrastructure SLA monitoring, DNS health token auditing, and SLA breach decision gates grounded in Google Public DNS and grounded time APIs.

---

## 📖 Overview

The `SlaUptimeVault` decision oracle allows enterprise IT providers and clients to register SLA coverage parameters. Rather than holding unbacked token deposits, it substantively binds Google Public DNS health token records (`dns.google`) and grounded calendar dates (`api.frankfurter.app`) to produce on-chain decision verdicts (`SLA_COVERAGE_ACTIVE` $\rightarrow$ `SLA_VIOLATION_PENALIZED` / `SLA_PERIOD_COMPLETED_PASSED`).

---

## 🛡️ Key Features & Guardrails

1. **Start-Date Timing Guard**: Enforces `today_date >= start_date` using grounded time from Frankfurter API (`[ERR_TERM_01]`), rejecting premature audits before the SLA coverage start date.
2. **Unfakeable Derived Endpoints**: Query URLs constructed internally from registered service domain (`dns.google/resolve?name={domain}&type=TXT`). No user-supplied URLs.
3. **Substantive 2-Way Validator Criteria**: Criteria requires verifying nodes to independently parse DNS Answer TXT arrays and reject any leader proposal if health status is inconsistent in EITHER direction.
4. **Access Control**: Audits strictly restricted to service provider, client, or contract operator (`[ERR_AUTH_01]`).

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
