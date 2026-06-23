import json

from app.mcp_clients.sql_mcp_client import SQLMCPClient
from app.mcp_clients.jira_mcp_client import JiraMCPClient
from app.llm.nvidia_llm_client import NvidiaLLMClient


DRIFT_THRESHOLD = 0.15


class MonitoringAgent:
    def __init__(self):
        self.sql_client = SQLMCPClient()
        self.jira_client = JiraMCPClient()

        try:
            self.llm_client = NvidiaLLMClient()
        except Exception as e:
            print("LLM client not initialized:", str(e))
            self.llm_client = None

    async def run(self, context):
        print("[Monitoring Agent]")

        state = context.get("state", {})
        memory = context.get("memory", {})

        state.setdefault("performance_metrics", {})
        state.setdefault("reason", [])
        state.setdefault("audit_log_entries", [])
        state.setdefault("threshold_breached", False)
        state.setdefault("errors", [])
        state.setdefault("validation_status", "draft")
        state.setdefault("jira_ticket_key", None)
        state.setdefault("sr117_compliant", False)

        model_id = state.get("model_id")

        try:
            metrics = await self.sql_client.get_all_latest_metrics(model_id)

            if not isinstance(metrics, dict):
                raise Exception("Invalid metrics response")

            drift_val = metrics.get("psi") or metrics.get("PSI")

            if drift_val is not None:
                drift = float(drift_val)
            else:
                drift = float(state.get("drift_score", 0.0))

            state["drift_score"] = drift
            state["performance_metrics"] = metrics
            memory["last_drift"] = drift

            incidents = []

            if drift > DRIFT_THRESHOLD:
                state["threshold_breached"] = True
                state["sr117_compliant"] = False

                incidents = await self.jira_client.get_all_incidents(model_id)

                existing = None

                if isinstance(incidents, list):
                    active = [
                        i for i in incidents
                        if i.get("status") != "approval"
                    ]
                    if active:
                        active.sort(
                            key=lambda x: x.get("created_at", ""),
                            reverse=True
                        )
                        existing = active[0]

                if existing:
                    state["jira_ticket_key"] = existing["key"]
                    state["validation_status"] = existing.get("status", "intake")

                else:
                    ticket = await self.jira_client.create_validation_ticket(
                        model_id=model_id,
                        validation_type="drift_incident"
                    )

                    state["jira_ticket_key"] = ticket["key"]
                    state["validation_status"] = ticket.get("status", "intake")

                    state["audit_log_entries"].append(
                        f"JIRA-CREATED-{ticket['key']}"
                    )

                state["reason"].append(
                    f"Drift {drift} exceeded threshold"
                )

            else:
                state["threshold_breached"] = False
                state["sr117_compliant"] = True

                state["reason"].append(
                    f"Drift {drift} within threshold"
                )

        except Exception as e:
            print("MONITORING ERROR:", str(e))
            state["errors"].append(str(e))

        context["state"] = state
        context["memory"] = memory

        return context
