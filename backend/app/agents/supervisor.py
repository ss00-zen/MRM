from typing import TypedDict, Optional, List, Dict, Any
import uuid

from langgraph.graph import StateGraph, END

from app.agents.inventory_agent import InventoryAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.monitoring_agent import MonitoringAgent
from app.agents.regulatory_agent import RegulatoryAgent
from app.agents.tools import check_drift_threshold, regulatory_policy


class MRMState(TypedDict, total=False):
    # Model data
    model_id: str
    model_type: str
    model_metadata: Optional[dict]

    # Validation
    validation_status: str
    jira_ticket_key: Optional[str]
    validation_report: Optional[str]

    # Monitoring
    drift_score: float
    performance_metrics: Dict[str, Any]
    threshold_breached: bool

    # Compliance
    sr117_compliant: bool

    # Coordination / audit
    audit_log_entries: List[str]
    data_residency_region: str
    next_agent: str
    errors: List[str]
    correlation_id: str
    audit_codes: List[str]
    reason: List[str]

    # Execution guards
    inventory_ran: bool
    validation_ran: bool
    monitoring_ran: bool
    regulatory_ran: bool


class SupervisorAgent:
    def __init__(self):
        self.inventory = InventoryAgent()
        self.validation = ValidationAgent()
        self.monitoring = MonitoringAgent()
        self.regulatory = RegulatoryAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MRMState)

        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("inventory", self.inventory_node)
        workflow.add_node("validation", self.validation_node)
        workflow.add_node("monitoring", self.monitoring_node)
        workflow.add_node("regulatory", self.regulatory_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self.route_agent,
            {
                "inventory": "inventory",
                "validation": "validation",
                "monitoring": "monitoring",
                "regulatory": "regulatory",
                "FINISH": END,
            },
        )

        workflow.add_edge("inventory", "supervisor")
        workflow.add_edge("validation", "supervisor")
        workflow.add_edge("monitoring", "supervisor")
        workflow.add_edge("regulatory", "supervisor")

        return workflow.compile()

    async def run(self, state: dict):
        normalized_state: MRMState = {
            "model_id": state.get("model_id"),
            "model_type": state.get("model_type", "credit_risk"),
            "model_metadata": state.get("model_metadata"),
            "validation_status": state.get("validation_status", "draft"),
            "jira_ticket_key": state.get("jira_ticket_key"),
            "validation_report": state.get("validation_report"),
            "drift_score": state.get("drift_score", 0.0),
            "performance_metrics": state.get("performance_metrics", {}),
            "threshold_breached": state.get("threshold_breached", False),
            "sr117_compliant": state.get("sr117_compliant", False),
            "audit_log_entries": state.get("audit_log_entries", []),
            "data_residency_region": state.get("data_residency_region", "US"),
            "next_agent": state.get("next_agent", "supervisor"),
            "errors": state.get("errors", []),
            "correlation_id": state.get("correlation_id", str(uuid.uuid4())),
            "audit_codes": state.get("audit_codes", []),
            "reason": state.get("reason", []),

            # guards
            "inventory_ran": state.get("inventory_ran", False),
            "validation_ran": state.get("validation_ran", False),
            "monitoring_ran": state.get("monitoring_ran", False),
            "regulatory_ran": state.get("regulatory_ran", False),
        }

        # ✅ recursion limit prevents endless loops
        result = await self.graph.ainvoke(
            normalized_state,
            config={"recursion_limit": 12}
        )
        return dict(result)

    async def supervisor_node(self, state: MRMState) -> dict:
        print(f"[Supervisor] Routing model {state['model_id']}")

        state.setdefault("reason", [])
        state.setdefault("model_metadata", None)
        state.setdefault("validation_status", "draft")
        state.setdefault("sr117_compliant", False)
        state.setdefault("threshold_breached", False)

        # ✅ 1. Inventory first if metadata missing and not already fetched
        if not state.get("model_metadata") and not state.get("inventory_ran", False):
            state["reason"].append("Routing → inventory")
            return {"next_agent": "inventory"}

        # ✅ 2. Initial validation for new/rejected models
        if (
            state.get("validation_status") in ["draft", "rejected"]
            and not state.get("validation_ran", False)
        ):
            state["reason"].append("Routing → validation")
            return {"next_agent": "validation"}

        # ✅ 3. Monitoring should run once per cycle
        if not state.get("monitoring_ran", False):
            state["reason"].append("Routing → monitoring")
            return {"next_agent": "monitoring"}

        # ✅ 4. If monitoring found drift breach, do validation once more
        if (
            state.get("threshold_breached")
            and state.get("validation_status") == "in_validation"
            and not state.get("validation_ran", False)
        ):
            state["reason"].append("Routing → validation (revalidation)")
            return {"next_agent": "validation"}

        # ✅ 5. Regulatory decision
        if not state.get("regulatory_ran", False):
            state["reason"].append("Routing → regulatory")
            return {"next_agent": "regulatory"}

        # ✅ finish
        state["reason"].append("Workflow complete")
        return {"next_agent": "FINISH"}

    def route_agent(self, state: MRMState) -> str:
        return state["next_agent"]

    def _make_context(self, state: MRMState) -> dict:
        return {
            "state": state,
            "memory": {
                "validation_runs": 0,
                "last_drift": state.get("drift_score", 0.0),
            },
            "tools": {
                "check_drift": check_drift_threshold,
                "policy": regulatory_policy(),
            },
        }

    async def inventory_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.inventory.run(context)
        updated = context["state"]
        updated["inventory_ran"] = True
        updated["next_agent"] = "supervisor"
        return updated

    async def validation_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.validation.run(context)
        updated = context["state"]
        updated["validation_ran"] = True
        updated["next_agent"] = "supervisor"
        return updated

    async def monitoring_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.monitoring.run(context)
        updated = context["state"]
        updated["monitoring_ran"] = True
        updated["next_agent"] = "supervisor"
        return updated

    async def regulatory_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.regulatory.run(context)
        updated = context["state"]
        updated["regulatory_ran"] = True
        updated["next_agent"] = "supervisor"
        return updated
