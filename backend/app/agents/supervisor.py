import uuid
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.inventory_agent import InventoryAgent
from app.agents.monitoring_agent import MonitoringAgent
from app.agents.regulatory_agent import RegulatoryAgent
from app.agents.tools import check_drift_threshold, regulatory_policy
from app.agents.validation_agent import ValidationAgent


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

    # LLM explanations
    monitoring_explanation: Optional[dict]
    regulatory_explanation: Optional[dict]
    agent_explanations: Dict[str, Any]

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
    monitoring_ran: bool
    validation_ran: bool
    regulatory_ran: bool


class SupervisorAgent:
    def __init__(self):
        self.inventory = InventoryAgent()
        self.monitoring = MonitoringAgent()
        self.validation = ValidationAgent()
        self.regulatory = RegulatoryAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MRMState)

        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("inventory", self.inventory_node)
        workflow.add_node("monitoring", self.monitoring_node)
        workflow.add_node("validation", self.validation_node)
        workflow.add_node("regulatory", self.regulatory_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self.route_agent,
            {
                "inventory": "inventory",
                "monitoring": "monitoring",
                "validation": "validation",
                "regulatory": "regulatory",
                "FINISH": END,
            },
        )

        workflow.add_edge("inventory", "supervisor")
        workflow.add_edge("monitoring", "supervisor")
        workflow.add_edge("validation", "supervisor")
        workflow.add_edge("regulatory", "supervisor")

        return workflow.compile()

    async def run(self, state: dict) -> dict:
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

            "monitoring_explanation": state.get("monitoring_explanation"),
            "regulatory_explanation": state.get("regulatory_explanation"),
            "agent_explanations": state.get("agent_explanations", {}),

            "audit_log_entries": state.get("audit_log_entries", []),
            "data_residency_region": state.get("data_residency_region", "US"),
            "next_agent": state.get("next_agent", "supervisor"),
            "errors": state.get("errors", []),
            "correlation_id": state.get("correlation_id", str(uuid.uuid4())),
            "audit_codes": state.get("audit_codes", []),
            "reason": state.get("reason", []),

            "inventory_ran": state.get("inventory_ran", False),
            "monitoring_ran": state.get("monitoring_ran", False),
            "validation_ran": state.get("validation_ran", False),
            "regulatory_ran": state.get("regulatory_ran", False),
        }

        result = await self.graph.ainvoke(
            normalized_state,
            config={"recursion_limit": 12},
        )

        return dict(result)

    async def supervisor_node(self, state: MRMState) -> dict:
        print(f"[Supervisor] Routing model {state.get('model_id')}")

        state.setdefault("reason", [])
        state.setdefault("model_metadata", None)
        state.setdefault("validation_status", "draft")
        state.setdefault("jira_ticket_key", None)
        state.setdefault("threshold_breached", False)
        state.setdefault("sr117_compliant", False)
        state.setdefault("agent_explanations", {})

        if not state.get("model_metadata") and not state.get("inventory_ran", False):
            state["reason"].append("Routing -> inventory")
            state["next_agent"] = "inventory"
            return state

        if not state.get("monitoring_ran", False):
            state["reason"].append("Routing -> monitoring")
            state["next_agent"] = "monitoring"
            return state

        if (
            state.get("threshold_breached")
            and state.get("jira_ticket_key")
            and state.get("validation_status") != "approval"
            and not state.get("validation_ran", False)
        ):
            state["reason"].append("Routing -> validation")
            state["next_agent"] = "validation"
            return state

        if not state.get("regulatory_ran", False):
            state["reason"].append("Routing -> regulatory")
            state["next_agent"] = "regulatory"
            return state

        state["reason"].append("Workflow complete")
        state["next_agent"] = "FINISH"
        return state

    def route_agent(self, state: MRMState) -> str:
        return state.get("next_agent", "FINISH")

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

        updated_state = context["state"]
        updated_state["inventory_ran"] = True
        updated_state["next_agent"] = "supervisor"

        return updated_state

    async def monitoring_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.monitoring.run(context)

        updated_state = context["state"]
        updated_state["monitoring_ran"] = True
        updated_state["next_agent"] = "supervisor"

        return updated_state

    async def validation_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.validation.run(context)

        updated_state = context["state"]
        updated_state["validation_ran"] = True
        updated_state["next_agent"] = "supervisor"

        return updated_state

    async def regulatory_node(self, state: MRMState) -> dict:
        context = self._make_context(state)
        context = await self.regulatory.run(context)

        updated_state = context["state"]
        updated_state["regulatory_ran"] = True
        updated_state["next_agent"] = "supervisor"

        return updated_state