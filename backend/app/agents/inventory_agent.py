import uuid
from app.mcp_clients.sql_mcp_client import SQLMCPClient


class InventoryAgent:
    def __init__(self):
        self.sql_client = SQLMCPClient()

    async def run(self, context):
        print("[Inventory Agent] Fetching model inventory")

        state = context["state"]

        # ✅ Ensure required fields exist
        state.setdefault("model_metadata", None)
        state.setdefault("audit_log_entries", [])
        state.setdefault("errors", [])
        state.setdefault("audit_codes", [])
        state.setdefault("reason", [])
        state.setdefault("correlation_id", str(uuid.uuid4()))
        state.setdefault("performance_metrics", {})
        state.setdefault("validation_status", "draft")
        state.setdefault("drift_score", 0.0)
        state.setdefault("threshold_breached", False)
        state.setdefault("sr117_compliant", False)

        try:
            model = await self.sql_client.get_model_inventory(state["model_id"])

            if model:
                # ✅ FIX: MCP returns dict → use direct key access
                state["model_metadata"] = {
                    "model_id": model.get("model_id"),
                    "model_name": model.get("model_name"),
                    "model_type": model.get("model_type"),
                    "model_owner": model.get("model_owner"),
                    "business_unit": model.get("business_unit"),
                    "data_region": model.get("data_region"),
                    "risk_tier": model.get("risk_tier"),
                    "approval_status": model.get("approval_status"),
                }

                state["audit_log_entries"].append(
                    f"INVENTORY-FETCH-{state['correlation_id']}"
                )

                state["reason"].append("Model metadata loaded from MCP ✅")

            else:
                # ✅ explicitly set to avoid undefined state
                state["model_metadata"] = None

                state["errors"].append("INV-404: Model inventory not found")
                state["audit_codes"].append("AUDIT-INV-404")
                state["reason"].append("Model metadata not found")

        except Exception as e:
            state["errors"].append(f"INV-500: {str(e)}")
            state["audit_codes"].append("AUDIT-INV-500")
            state["reason"].append("Inventory fetch failed")

        context["state"] = state
        return context