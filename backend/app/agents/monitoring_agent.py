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
            print("LLM init failed:", str(e))
            self.llm_client = None

    async def run(self, context):
        state = context["state"]
        memory = context["memory"]

        print("[Monitoring Agent]")

        state.setdefault("reason", [])
        state.setdefault("errors", [])
        state.setdefault("audit_log_entries", [])
        state.setdefault("jira_ticket_key", None)
        state.setdefault("agent_explanations", {})

        try:
            # ✅ Safe metric fetch
            metrics = await self.sql_client.get_all_latest_metrics(state["model_id"]) or {}
            
            drift = float(
                metrics.get("psi") or
                metrics.get("PSI") or
                metrics.get("psi_score") or
                state.get("drift_score") or   # ✅ important fallback
                0.0
            )


            state["drift_score"] = drift
            state["performance_metrics"] = metrics
            memory["last_drift"] = drift

            # ✅ Fetch incidents safely
            incidents = await self.jira_client.get_all_incidents(state["model_id"])

            # ✅ ✅ FIX: normalize response (CRITICAL)
            if isinstance(incidents, dict):
                incidents = [incidents]
            elif isinstance(incidents, str):
                incidents = []
            elif not isinstance(incidents, list):
                incidents = []

            # ✅ Drift logic
            if drift > DRIFT_THRESHOLD:
                state["threshold_breached"] = True
                state["sr117_compliant"] = False
                print("RAW INCIDENTS:", incidents)
                active = [
                    
                        i for i in incidents
                            if isinstance(i, dict)
                            and i.get("key")        # ✅ must have key
                            and i.get("status")     # ✅ must have status
                            and i.get("status") not in ["approval", "approved", "closed"]

                ]
                print("FILTERED ACTIVE INCIDENTS:", active)

                if active:
                    latest = active[0]
                    state["jira_ticket_key"] = latest.get("key")
                    state["validation_status"] = latest.get("status")
                else:
                    ticket = await self.jira_client.create_validation_ticket(
                        model_id=state["model_id"],
                        validation_type="drift_incident"
                    )

                    if isinstance(ticket, dict):
                        state["jira_ticket_key"] = ticket.get("key")
                        state["validation_status"] = ticket.get("status")

                        state["audit_log_entries"].append(
                            f"JIRA-CREATED-{ticket.get('key')}"
                        )

            else:
                state["threshold_breached"] = False
                state["sr117_compliant"] = True

            # ✅ ✅ LLM explainability
            explanation = await self._llm_explain(
                state["model_id"],
                drift,
                state["threshold_breached"],
                metrics,
                incidents,
            )

            state["agent_explanations"]["monitoring"] = explanation
            state["reason"].append(
                explanation.get("summary", "Monitoring complete")
            )

            print("=== MONITORING LLM OUTPUT ===")
            print(explanation)

        except Exception as e:
            print("Monitoring error:", str(e))
            state["errors"].append(str(e))

        context["state"] = state
        context["memory"] = memory
        return context

    async def _llm_explain(self, model_id, drift, breached, metrics, incidents):
        fallback = {
            "summary": f"Drift = {drift}, breached = {breached}",
            "root_cause": "Unavailable",
            "impact": "Basic threshold evaluation.",
            "recommended_action": "Review model.",
            "confidence": "low"
        }

        if not self.llm_client:
            return fallback

        prompt = f"""
You are a model monitoring expert.

Model ID: {model_id}
Drift: {drift}
Threshold breached: {breached}

Metrics:
{json.dumps(metrics)}

Incidents:
{json.dumps(incidents)}

Explain:
- Root cause of drift
- Impact
- Recommended action

Return JSON:
{{
  "summary": "",
  "root_cause": "",
  "impact": "",
  "recommended_action": "",
  "confidence": "low|medium|high"
}}
"""

        try:
            result = await self.llm_client.generate(
                system_prompt="Model monitoring analysis",
                user_prompt=prompt
            )

            # ✅ handle string output
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception:
                    return fallback

            if isinstance(result, dict):
                return result

        except Exception as e:
            print("LLM ERROR:", str(e))

        return fallback