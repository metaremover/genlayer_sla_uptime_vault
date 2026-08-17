# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
import re
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class SlaVault:
    id: str
    client: str
    provider: str
    service_domain: str
    expected_health_token: str
    start_date: str
    end_date: str
    status: str
    last_audit_proof: str


class SlaUptimeVault(gl.Contract):
    operator: str
    vaults: TreeMap[str, SlaVault]
    next_vault_id: u256

    def __init__(self, operator: str):
        self.operator = operator.strip().strip('"').strip("'").lower()
        # GenLayer VM automatically instantiates storage-backed TreeMaps.
        # We must never assign TreeMap() manually in the constructor.
        self.next_vault_id = u256(0)

    @gl.public.write
    def create_vault(
        self,
        client: str,
        service_domain: str,
        expected_health_token: str,
        start_date: str,
        end_date: str
    ) -> str:
        sender = str(gl.message.sender_address).lower()
        client_clean = client.strip().strip('"').strip("'").lower()
        domain_clean = service_domain.strip().strip('"').strip("'").lower()
        token_clean = expected_health_token.strip().strip('"').strip("'")
        s_date = start_date.strip().strip('"').strip("'")
        e_date = end_date.strip().strip('"').strip("'")

        # Sanitize domain name removing protocol prefixes if present
        if domain_clean.startswith("https://"):
            domain_clean = domain_clean[8:]
        elif domain_clean.startswith("http://"):
            domain_clean = domain_clean[7:]
        domain_clean = domain_clean.split("/")[0].strip()

        assert len(domain_clean) > 3 and "." in domain_clean, "[ERR_VAL_01] Invalid domain format."
        assert len(token_clean) > 0, "[ERR_VAL_02] Expected health token cannot be empty."
        assert len(s_date) == 10 and len(e_date) == 10, "[ERR_VAL_04] Dates must follow YYYY-MM-DD format."
        assert e_date >= s_date, "[ERR_VAL_05] end_date must be on or after start_date."

        v_num = int(self.next_vault_id) + 1
        self.next_vault_id = u256(v_num)
        v_id = "SLA_VAULT_" + str(v_num).zfill(3)

        new_vault = SlaVault(
            id=v_id,
            client=client_clean,
            provider=sender,
            service_domain=domain_clean,
            expected_health_token=token_clean,
            start_date=s_date,
            end_date=e_date,
            status="SLA_COVERAGE_ACTIVE",
            last_audit_proof=f"SLA decision gate initialized for service '{domain_clean}' ({s_date} to {e_date}). Awaiting DNS health audit."
        )

        self.vaults[v_id] = new_vault
        return v_id

    @gl.public.write
    def audit_sla_uptime(self, vault_id: str) -> None:
        assert vault_id in self.vaults, "[ERR_STATE_01] SLA Vault ID does not exist."

        vault = self.vaults[vault_id]
        sender = str(gl.message.sender_address).lower()

        # Access Control Guardrail: Only provider, client, or operator can trigger SLA audit
        assert sender == vault.provider or sender == vault.client or sender == self.operator, \
            "[ERR_AUTH_01] Unauthorized: caller must be service provider, client, or contract operator."

        assert vault.status == "SLA_COVERAGE_ACTIVE", "[ERR_STATE_02] SLA decision is already finalized."

        domain = vault.service_domain
        expected_token = vault.expected_health_token
        s_date = vault.start_date
        e_date = vault.end_date

        # STEP 1: AUTHORITATIVE UTC CLOCK & FRESHNESS GUARD (FIRST ROUND)
        # We query the authoritative real-time UTC Clock API (timeapi.io)
        # to ensure fresh 24/7/365 date coverage across weekends and holidays before evaluating DNS
        time_url = "https://timeapi.io/api/time/current/zone?timeZone=UTC"

        def get_time_input() -> str:
            time_response = gl.nondet.web.render(time_url, mode="text")
            return (
                f"Authoritative UTC Atomic Clock API Response:\n\n"
                f"{time_response}\n\n"
                f"SLA coverage start date: {s_date}\n"
                f"SLA coverage end date: {e_date}"
            )

        time_task = (
            "You are an authoritative calendar date & clock freshness auditor.\n"
            "Parse the live UTC Clock API response.\n"
            "Extract the live ISO date (format YYYY-MM-DD from dateTime or year/month/day fields) - this is today's current UTC date.\n"
            "Compare today's date against SLA start_date and end_date.\n\n"
            "Output JSON format:\n"
            "{\n"
            '  "today_date": "<YYYY-MM-DD>",\n'
            '  "term_started": true/false,\n'
            '  "term_expired": true/false,\n'
            '  "clock_fresh": true/false\n'
            "}\n"
            "Set clock_fresh to true if a valid current UTC date was successfully parsed.\n"
            "Set term_started to true if today_date >= start_date.\n"
            "Set term_expired to true if today_date >= end_date.\n"
            "Respond ONLY with raw JSON."
        )

        time_criteria = (
            "Independently parse the live UTC Clock API JSON to extract the current UTC date. "
            "Compare it against the SLA start and end dates using string comparison. "
            "REJECT the leader if: "
            "(1) today_date does not match the live UTC date from the API response (YYYY-MM-DD), "
            "(2) term_started boolean is inconsistent with (today_date >= start_date) in EITHER direction, "
            "(3) term_expired boolean is inconsistent with (today_date >= end_date) in EITHER direction, or "
            "(4) clock_fresh is marked true when the clock API response is missing or unparseable."
        )

        time_result = gl.eq_principle.prompt_non_comparative(
            get_time_input,
            task=time_task,
            criteria=time_criteria
        )

        raw_time = time_result.strip()
        if "</think>" in raw_time:
            raw_time = raw_time.split("</think>")[-1].strip()
        if raw_time.startswith("```"):
            t_lines = raw_time.split("\n")
            if len(t_lines) >= 3 and t_lines[0].startswith("```") and t_lines[-1].startswith("```"):
                raw_time = "\n".join(t_lines[1:-1]).strip()
            else:
                raw_time = raw_time.replace("```json", "").replace("```", "").strip()

        time_parsed = json.loads(raw_time)
        term_started = bool(time_parsed.get("term_started", False))
        term_expired = bool(time_parsed.get("term_expired", False))
        clock_fresh = bool(time_parsed.get("clock_fresh", False))
        today_str = str(time_parsed.get("today_date", ""))

        # Freshness and Start-Date Guard: Prevent ANY violation or audit transition before start_date
        assert clock_fresh == True, "[ERR_CLOCK_01] Failed to retrieve fresh authoritative UTC time."
        assert term_started == True, f"[ERR_TERM_01] SLA audit rejected: current UTC date ({today_str}) is before coverage start_date ({s_date})."

        # STEP 2: GOOGLE PUBLIC DNS HEALTH AUDIT (SECOND ROUND)
        # Derive Google Public DNS TXT query URL internally from service domain
        dns_url = "https://dns.google/resolve?name=" + domain + "&type=TXT"

        def get_input() -> str:
            web_data = gl.nondet.web.render(dns_url, mode="text")
            return (
                f"Google Public DNS TXT Record API Response for Domain '{domain}':\n\n"
                f"{web_data}\n\n"
                f"Required SLA Health Token: '{expected_token}'"
            )

        task = (
            "You are an enterprise IT infrastructure SLA auditor.\n"
            "Parse the Google Public DNS API JSON response provided in the input.\n\n"
            "The JSON payload contains an 'Answer' array of TXT records. Each item in Answer has:\n"
            "- name: domain string\n"
            "- type: 16 (TXT record)\n"
            "- data: TXT record content string (e.g. \"v=spf1 include:_spf.google.com ~all\")\n\n"
            "Your job:\n"
            "1. Inspect if valid DNS Answer TXT records are present in the response (dns_records_found).\n"
            "2. Inspect all 'data' strings in the 'Answer' array for the required SLA health token.\n"
            "3. If valid DNS records exist AND the required health token is present: health_verified=true.\n"
            "4. If valid DNS records exist BUT the required health token is missing: health_verified=false (SLA breach).\n"
            "5. If DNS query failed or Answer array is missing/error: dns_records_found=false, health_verified=false.\n\n"
            "Output JSON format:\n"
            "{\n"
            '  "dns_records_found": true/false,\n'
            '  "health_verified": true/false,\n'
            '  "detected_txt_record": "<matching TXT record string, or empty>",\n'
            '  "summary": "<brief IT infrastructure SLA audit sentence>"\n'
            "}\n"
            "Respond ONLY with raw JSON."
        )

        criteria = (
            "Independently parse the Google Public DNS JSON response from the input. "
            "Inspect the 'Answer' array yourself and check all 'data' strings for the required SLA health token. "
            "REJECT the leader's proposal if: "
            "(1) the proposed dns_records_found boolean is inconsistent with whether valid DNS Answer records exist in EITHER direction (true when missing or false when present), "
            "(2) the proposed health_verified boolean is inconsistent with whether the required health token exists in the DNS Answer array in EITHER direction, "
            "(3) the proposed detected_txt_record does not match the actual DNS Answer data, or "
            "(4) the proposal asserts health_verified=true when dns_records_found is false. "
            "The output must be valid JSON with keys: dns_records_found, health_verified, "
            "detected_txt_record, and summary."
        )

        consensus_result = gl.eq_principle.prompt_non_comparative(
            get_input,
            task=task,
            criteria=criteria
        )

        # Clean thinking blocks and markdown wrappers
        raw_json = consensus_result.strip()
        if "</think>" in raw_json:
            raw_json = raw_json.split("</think>")[-1].strip()
        if raw_json.startswith("```"):
            lines = raw_json.split("\n")
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                raw_json = "\n".join(lines[1:-1]).strip()
            else:
                raw_json = raw_json.replace("```json", "").replace("```", "").strip()

        result = json.loads(raw_json)
        found = bool(result.get("dns_records_found", False))
        health_verified = bool(result.get("health_verified", False))
        detected_record = str(result.get("detected_txt_record", "")).strip()
        summary = str(result.get("summary", ""))

        # Guard against missing DNS data vs actual health breach
        assert found == True, "[ERR_DATA_01] Failed to retrieve DNS records for domain. Audit aborted without penalization."

        if not health_verified:
            # SLA Violated / Outage -> Finalize Verdict SLA_VIOLATION_PENALIZED
            vault.status = "SLA_VIOLATION_PENALIZED"
            vault.last_audit_proof = (
                f"SLA VIOLATION DETECTED (Audited {today_str}): Required health token '{expected_token}' not found in DNS records for '{domain}'. "
                f"SLA penalty condition triggered. " + summary
            )
        else:
            if term_expired:
                # SLA Term Completed Without Outage -> SLA_PERIOD_COMPLETED_PASSED
                vault.status = "SLA_PERIOD_COMPLETED_PASSED"
                vault.last_audit_proof = (
                    f"SLA TERM COMPLETED ({today_str} >= {e_date}): DNS health check passed for '{domain}' with record '{detected_record}'. "
                    f"SLA period successfully verified intact. " + summary
                )
            else:
                # Coverage term still active -> Remain SLA_COVERAGE_ACTIVE for ongoing audits
                vault.last_audit_proof = (
                    f"SLA HEALTHY AS OF {today_str}: Health record '{detected_record}' verified on '{domain}'. "
                    f"Coverage active until {e_date}. SLA remains ACTIVE for ongoing monitoring."
                )

        self.vaults[vault_id] = vault

    @gl.public.view
    def get_vault(self, vault_id: str) -> SlaVault:
        assert vault_id in self.vaults, "[ERR_STATE_01] SLA Vault ID does not exist."
        return self.vaults[vault_id]

    @gl.public.view
    def is_sla_violated(self, vault_id: str) -> bool:
        assert vault_id in self.vaults, "[ERR_STATE_01] SLA Vault ID does not exist."
        return self.vaults[vault_id].status == "SLA_VIOLATION_PENALIZED"

    @gl.public.view
    def get_total_vaults(self) -> u256:
        return self.next_vault_id
