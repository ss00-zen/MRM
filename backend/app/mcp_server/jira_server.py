import httpx
from fastmcp import FastMCP

mcp = FastMCP("MRM-Jira-Server")

JIRA_API_BASE = "http://127.0.0.1:8000/api/jira"


@mcp.tool()
async def create_validation_ticket(model_id: str, validation_type: str = "drift_incident"):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{JIRA_API_BASE}/incidents",
            json={
                "model_id": model_id,
                "validation_type": validation_type,
            },
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_ticket_status(ticket_key: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{JIRA_API_BASE}/incidents/{ticket_key}")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_ticket_by_model(model_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{JIRA_API_BASE}/incidents/by-model/{model_id}")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_all_incidents(model_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{JIRA_API_BASE}/incidents/by-model-all/{model_id}")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def transition_ticket(ticket_key: str, status: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{JIRA_API_BASE}/incidents/{ticket_key}/transition",
            json={"status": status},
        )
        resp.raise_for_status()
        return resp.json()