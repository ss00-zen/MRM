from app.mcp_clients.sql_mcp_client import SQLMCPClient
from app.mcp_clients.jira_mcp_client import JiraMCPClient


class MonitoringAgent:
    def __init__(self):
        self.sql_client = SQLMCPClient()
        self.jira_client = JiraMCPClient()

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

        model_id = state.get("model_id")

        try:
            print("🔵 Calling MCP for metrics...")

            metrics = await self.sql_client.get_all_latest_metrics(model_id)

            print("✅ MCP response:", metrics)

            if not isinstance(metrics, dict):
                raise Exception("Invalid metrics response from MCP")

            drift_val = metrics.get("psi") or metrics.get("PSI")
            drift = float(drift_val) if drift_val is not None else state.get("drift_score", 0.0)

            state["drift_score"] = drift
            state["performance_metrics"] = metrics
            memory["last_drift"] = drift

            print("📊 Drift value:", drift)

            threshold = 0.15

            if drift > threshold:
                print("🚨 Threshold breached")
                state["threshold_breached"] = True
                state["sr117_compliant"] = False   # ✅ IMPORTANT

                # ✅ SAFE INCIDENT FETCH (fix for your 404 problem)
                try:
                    incidents = await self.jira_client.get_all_incidents(model_id)
                except Exception:
                    print("⚠️ No incidents found (404 handled)")
                    incidents = []

                existing_incident = None

                if isinstance(incidents, list):
                    active = [
                        i for i in incidents
                        if i.get("validation_type") == "drift_incident"
                        and i.get("status") != "approval"
                    ]

                    if active:
                        active.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                        existing_incident = active[0]

                if existing_incident:
                    print("✅ Existing incident:", existing_incident["key"])
                    state["validation_status"] = existing_incident.get("status", "intake")

                else:
                    print("🚨 Creating Jira ticket...")

                    ticket = await self.jira_client.create_validation_ticket(
                        model_id=model_id,
                        validation_type="drift_incident"
                    )

                    print("📦 Jira ticket created:", ticket)

                    state["validation_status"] = ticket.get("status", "intake")
                    state["audit_log_entries"].append(f"JIRA-CREATED-{ticket['key']}")

                state["reason"].append(
                    f"Drift {drift} > threshold ({threshold})"
                )

            else:
                state["threshold_breached"] = False
                state["sr117_compliant"] = True   # ✅ IMPORTANT

                state["reason"].append(
                    f"Drift {drift} within limit"
                )

        except Exception as e:
            print("❌ MONITORING ERROR:", str(e))
            state["errors"].append(str(e))
            state["reason"].append("Monitoring failed")

        context["state"] = state
        context["memory"] = memory

        return context
