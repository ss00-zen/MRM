import json

from app.llm.nvidia_llm_client import NvidiaLLMClient

DRIFT_THRESHOLD = 0.15


class RegulatoryAgent:
    def __init__(self):
        try:
            self.llm_client = NvidiaLLMClient()
        except Exception as e:
            print("LLM init failed:", str(e))
            self.llm_client = None

    async def run(self, context):
        state = context["state"]
        memory = context["memory"]

        print("[Regulatory Agent]")

        state.setdefault("reason", [])
        state.setdefault("errors", [])
        state.setdefault("agent_explanations", {})

        # ✅ ALWAYS use state drift (single source of truth)
        drift = state.get("drift_score", 0.0)
        threshold_breached = drift > DRIFT_THRESHOLD
        validation_status = state.get("validation_status")
        risk_tier = (
            state.get("model_metadata", {}) or {}
        ).get("risk_tier")

        try:
            # ✅ ✅ RULE-BASED COMPLIANCE (CRITICAL FIX)
            if threshold_breached:
                state["sr117_compliant"] = False
            else:
                state["sr117_compliant"] = True

            # ✅ LLM ONLY EXPLAINS (NOT DECIDES)
            llm_result = await self._llm_explain(
                drift,
                threshold_breached,
                validation_status,
                risk_tier,
                state["sr117_compliant"]
            )

            # ✅ FORCE consistency (LLM cannot override rules)
            llm_result["compliant"] = state["sr117_compliant"]

            state["agent_explanations"]["regulatory"] = llm_result
            state["reason"].append(
                llm_result.get("summary", "Regulatory evaluated")
            )

            print("=== REGULATORY LLM OUTPUT ===")
            print(llm_result)

        except Exception as e:
            print("Regulatory error:", str(e))
            state["errors"].append(str(e))

        context["state"] = state
        context["memory"] = memory
        return context

    async def _llm_explain(self, drift, breached, status, risk, compliant):
        fallback = {
            "compliant": compliant,
            "summary": "Rule-based decision",
            "justification": "Compliance determined by drift threshold",
            "impact": "",
            "recommended_action": ""
        }

        if not self.llm_client:
            return fallback

        prompt = f"""
You are an SR 11-7 compliance expert.

IMPORTANT:
- Compliance is already determined.
- You MUST NOT change it.
- Only explain the reasoning.

Inputs:
- drift: {drift}
- threshold_breached: {breached}
- validation_status: {status}
- risk_tier: {risk}
- compliant: {compliant}

Explain:
1. Why the model is compliant or not
2. Impact
3. Recommended action

Return JSON:
{{
  "compliant": {str(compliant).lower()},
  "summary": "",
  "justification": "",
  "impact": "",
  "recommended_action": "",
  "confidence": "low|medium|high"
}}
"""

        try:
            result = await self.llm_client.generate(
                system_prompt="Regulatory explanation engine",
                user_prompt=prompt
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

        return fallback
