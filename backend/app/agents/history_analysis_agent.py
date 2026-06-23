import json
from sqlalchemy import select

from app.core.database import get_db
from app.models.inventory import ModelMetricsHistory
from app.llm.nvidia_llm_client import NvidiaLLMClient


class HistoryAnalysisAgent:
    def __init__(self):
        try:
            self.llm_client = NvidiaLLMClient()
        except Exception as e:
            print("LLM init failed:", str(e))
            self.llm_client = None

    async def run(self, context):
        state = context["state"]

        print("[History Analysis Agent]")

        state.setdefault("agent_explanations", {})
        state.setdefault("reason", [])
        state.setdefault("errors", [])

        model_id = state.get("model_id")

        try:
            # ✅ ✅ DIRECT DB FETCH
            history = []

            async for db in get_db():
                result = await db.execute(
                    select(ModelMetricsHistory)
                    .where(ModelMetricsHistory.model_id == model_id)
                    .order_by(ModelMetricsHistory.recorded_at.asc())  # ✅ time order
                )
                rows = result.scalars().all()

                history = [
                    {
                        "metric_name": r.metric_name,
                        "metric_value": r.metric_value,
                        "time": str(r.recorded_at),
                    }
                    for r in rows
                ]

            print("RAW HISTORY:", history)

            # ✅ ✅ Multi-metric grouping
            metric_history = {}

            for h in history:
                metric_name = h.get("metric_name")
                metric_value = h.get("metric_value")

                if metric_name and metric_value is not None:
                    metric_history.setdefault(metric_name, []).append(
                        float(metric_value)
                    )

            print("METRIC HISTORY:", metric_history)

            # ✅ ✅ Guard: need PSI at minimum
            psi_series = metric_history.get("psi", [])

            if len(psi_series) < 3:
                explanation = {
                    "summary": "Not enough data to analyze",
                    "trend": "unknown",
                    "impact": "Insufficient history",
                    "recommended_action": "Collect more historical data",
                    "confidence": "low"
                }

                state["agent_explanations"]["history_analysis"] = explanation
                state["reason"].append("Insufficient history")

                return context

            # ✅ ✅ LLM analysis with full metrics
            explanation = await self._llm_analyze(metric_history)

            state["agent_explanations"]["history_analysis"] = explanation
            state["reason"].append(
                explanation.get("summary", "History analyzed")
            )

        except Exception as e:
            print("History analysis error:", str(e))
            state.setdefault("errors", []).append(str(e))

        return context

    async def _llm_analyze(self, metric_history):
        fallback = {
            "summary": "Fallback history analysis",
            "drift_trend": "unknown",
            "performance_trend": "unknown",
            "overall_health": "unknown",
            "impact": "",
            "recommended_action": "Review manually",
            "confidence": "low"
        }

        if not self.llm_client:
            return fallback

        prompt = f"""
You are a model monitoring expert.

You are given time-series metrics for a model:

{json.dumps(metric_history)}

Metrics include:
- psi → drift signal
- accuracy / precision → performance signal

STRICT INSTRUCTIONS:
- You MUST analyze ALL metrics
- DO NOT focus only on psi
- If performance metrics exist, include them in analysis
- Correlate drift with performance
- ONLY mark "increasing" if ALL consecutive values increase
- ONLY mark "decreasing" if ALL consecutive values decrease
- OTHERWISE → MUST return "stable"
- ONLY mark "negative correlation" if clear inverse relationship exists
- OTHERWISE → return "none"
- DO NOT assume degradation unless performance metrics clearly decline


Analyze:

1. Drift trend (from psi)
2. Performance trend (from accuracy/precision/etc.)
3. How drift is affecting performance
4. Overall model health

IMPORTANT RULES:
- If ONLY psi is present → do basic drift analysis
- If performance metrics exist → MUST include them
- Only say "increasing" if values are strictly increasing
- Only say "decreasing" if strictly decreasing
- Otherwise → "stable"
- Do NOT assume correlation unless clearly visible
- Do NOT infer degradation without clear evidence


RETURN ONLY JSON:
(no explanation, no code, no markdown)

{{
  "summary": "",
  "drift_trend": "increasing|decreasing|stable",
  "performance_trend": "improving|degrading|stable|unknown",
  "correlation": "positive|negative|none",
  "overall_health": "good|warning|critical",
  "impact": "",
  "recommended_action": "",
  "confidence": "low|medium|high"
}}

"""

        try:
            result = await self.llm_client.generate(
                system_prompt="History trend analyzer",
                user_prompt=prompt
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

        return fallback
