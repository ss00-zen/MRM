from app.mcp_clients.jira_mcp_client import JiraMCPClient


class ValidationAgent:
    def __init__(self):
        self.jira_client = JiraMCPClient()

    async def run(self, context):
        state = context["state"]
        memory = context["memory"]

        print("[Validation Agent]")

        # Ensure required fields exist
        state.setdefault("jira_ticket_key", None)
        state.setdefault("validation_status", "draft")
        state.setdefault("audit_log_entries", [])
        state.setdefault("reason", [])
        state.setdefault("errors", [])

        try:
            jira_ticket_key = state.get("jira_ticket_key")

            # 1. No incident → skip
            if not jira_ticket_key:
                state["reason"].append(
                    "No active validation incident -> skipping validation"
                )
                return context

            # 2. Fetch latest Jira status
            current = await self.jira_client.get_ticket_status(jira_ticket_key)

            if not isinstance(current, dict):
                raise Exception("Invalid Jira ticket response")

            current_status = current.get("status", "intake")

            print("Jira current status:", current_status)

            # Sync Jira → state
            state["validation_status"] = current_status

            # ✅ Terminal condition
            if current_status == "approval":
                state["reason"].append("Validation already approved")
                return context

            # 3. Lifecycle progression
            next_stage = {
                "intake": "draft",
                "draft": "testing",
                "testing": "docs_review",
                "docs_review": "approval",
                "approval": "approval",
            }

            new_status = next_stage.get(current_status, current_status)

            # 4. Transition only if needed
            if new_status != current_status:
                print(f"Transitioning {current_status} -> {new_status}")

                updated = await self.jira_client.transition_state(
                    jira_ticket_key,
                    new_status
                )

                if not isinstance(updated, dict):
                    raise Exception("Invalid Jira transition response")

                updated_status = updated.get("status", new_status)

                state["validation_status"] = updated_status

                state["audit_log_entries"].append(
                    f"JIRA-TRANSITION-{jira_ticket_key}-{updated_status}"
                )

                state["reason"].append(
                    f"Validation progressed: {current_status} -> {updated_status}"
                )

            else:
                state["reason"].append(
                    f"Validation already at stage: {current_status}"
                )

        except Exception as e:
            print("VALIDATION ERROR:", str(e))

            state["errors"].append(f"VAL-500: {str(e)}")
            state["reason"].append("Validation execution failed")

        # Update memory
        memory["validation_runs"] = memory.get("validation_runs", 0) + 1

        context["state"] = state
        context["memory"] = memory

        return context
