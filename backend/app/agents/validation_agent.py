from app.mcp_clients.jira_mcp_client import JiraMCPClient


class ValidationAgent:
    def __init__(self):
        self.jira_client = JiraMCPClient()

    async def run(self, context):
        state = context["state"]
        memory = context["memory"]

        print("[Validation Agent]")

        # ✅ Ensure fields exist
        state.setdefault("jira_ticket_key", None)
        state.setdefault("validation_status", "draft")
        state.setdefault("audit_log_entries", [])
        state.setdefault("reason", [])
        state.setdefault("errors", [])

        try:
            # ✅ 1. If no incident → DO NOTHING
            if not state.get("jira_ticket_key"):
                state["reason"].append(
                    "No active validation incident → skipping validation"
                )
                return context

            # ✅ 2. ALWAYS fetch current status from Jira
            current = await self.jira_client.get_ticket_status(
                state["jira_ticket_key"]
            )

            current_status = current.get("status", "intake")

            print("📡 Jira current status:", current_status)

            # ✅ ✅ CRITICAL FIX
            # Always sync Jira status → state
            state["validation_status"] = current_status

            # ✅ 3. Lifecycle progression
            next_stage = {
                "intake": "draft",
                "draft": "testing",
                "testing": "docs_review",
                "docs_review": "approval",
                "approval": "approval",  # terminal
            }

            new_status = next_stage.get(current_status, current_status)

            # ✅ 4. Transition only if needed
            if new_status != current_status:
                print(f"📤 Transitioning {current_status} → {new_status}")

                updated = await self.jira_client.transition_state(
                    state["jira_ticket_key"],
                    new_status
                )

                state["validation_status"] = updated["status"]

                state["audit_log_entries"].append(
                    f"JIRA-TRANSITION-{state['jira_ticket_key']}-{updated['status']}"
                )

                state["reason"].append(
                    f"Validation progressed: {current_status} → {updated['status']}"
                )

            else:
                state["reason"].append(
                    f"Validation already at stage: {current_status}"
                )

        except Exception as e:
            print("❌ VALIDATION ERROR:", str(e))

            state["errors"].append(f"VAL-500: {str(e)}")
            state["reason"].append("Validation execution failed")

        # ✅ Update memory
        memory["validation_runs"] = memory.get("validation_runs", 0) + 1

        context["state"] = state
        context["memory"] = memory

        return context