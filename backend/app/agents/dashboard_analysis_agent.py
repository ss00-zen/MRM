import json
from sqlalchemy import select

from app.core.database import get_db
from app.models.inventory import ModelMetricsHistory
from app.llm.nvidia_llm_client import NvidiaLLMClient


class DashboardAnalysisAgent:
    def __init__(self):
        try:
            self.llm_client = NvidiaLLMClient()
        except Exception:
            self.llm_client = None

    async def run(self, context):
        state = context["state"]

        print("[Dashboard Analysis Agent]")

        state.setdefault("agent_explanations", {})
        state.setdefault("reason", [])

        model_id = state.get("model_id")

        try:
            # ✅ ✅ Fetch DB history
            history = []

            async for db in get_db():
                result = await db.execute(
                    select(ModelMetricsHistory)
                    .where(ModelMetricsHistory.model_id == model_id)
                    .order_by(ModelMetricsHistory.recorded_at.asc())
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

            # ✅ Group metrics
            metric_history = {}

            for h in history:
                m = h["metric_name"]
                v = h["metric_value"]

                metric_history.setdefault(m, []).append(v)

            # ✅ Guard
            if len(metric_history.get("psi", [])) < 3:
                return context

            # ✅ LLM decides visualization + insights
            
            dashboard = await self._llm_generate_dashboard(metric_history)

            # ✅ FORCE REBUILD CHART DATA
            if dashboard and "charts" in dashboard:
                fixed_configs = []

                for chart in dashboard["charts"]:
                    metrics = chart.get("metrics", [])

                    data_subset = {
                        m: metric_history.get(m, [])
                        for m in metrics
                        if m in metric_history
                    }

                    fixed_configs.append({
                        "title": chart.get("title"),
                        "data": data_subset
                    })

                dashboard["chart_configs"] = fixed_configs

            state["agent_explanations"]["dashboard"] = dashboard


        except Exception as e:
            state.setdefault("errors", []).append(str(e))

        return context

    async def _llm_generate_dashboard(self, metric_history):
        fallback = {
            "charts": [],
            "insights": []
        }

        if not self.llm_client:
            return fallback

        prompt = f"""
You are a data visualization expert.

You are given model metric history:

{json.dumps(metric_history)}

TASK:

1. Identify all available metrics
2. Suggest best visualization types
3. Prepare chart configs
4. Provide insights

RULES:
- Return ONLY JSON
- No explanation outside JSON

Return:

{{
  "charts": [
    {{
      "title": "",
      "type": "line|multi-line|bar",
      "metrics": ["metric1", "metric2"]
    }}
  ],
  "insights": [
    "insight1",
    "insight2"
  ]
}}
"""

        try:
            result = await self.llm_client.generate(
                system_prompt="Dashboard generator",
                user_prompt=prompt
            )

            if isinstance(result, dict):
                return result

        except:
            pass

        return fallback
