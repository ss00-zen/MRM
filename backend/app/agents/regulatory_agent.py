class RegulatoryAgent:
    async def run(self, context):
        state = context["state"]
        memory = context["memory"]

        print("[Regulatory Agent]")

        drift = memory["last_drift"]

        if state["threshold_breached"]:
            state["sr117_compliant"] = False

            state["reason"].append(
                f"Non-compliant due to drift {drift}"
            )
        else:
            state["sr117_compliant"] = True

            state["reason"].append(
                f"Compliant with drift {drift}"
            )

        context["state"] = state
        context["memory"] = memory

        return context
