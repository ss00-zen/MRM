import json
from fastmcp import Client


class JiraMCPClient:
    def __init__(self):
        # FastMCP server endpoint for Jira MCP server
        self.base_url = "http://127.0.0.1:9100/mcp"

    async def _call_tool(self, tool_name: str, payload: dict):
        try:
            client = Client(self.base_url)

            async with client:
                result = await client.call_tool(tool_name, payload)

            if not result:
                return {}

            # FastMCP usually returns content blocks
            if hasattr(result, "content") and result.content:
                first = result.content[0]

                if hasattr(first, "text"):
                    try:
                        return json.loads(first.text)
                    except Exception:
                        return {"raw": first.text}

            if isinstance(result, dict):
                return result

            return {"raw": str(result)}

        except Exception as e:
            print(f"❌ JiraMCPClient Error calling {tool_name}: {str(e)}")
            raise

    async def create_validation_ticket(self, model_id: str, validation_type: str = "initial"):
        return await self._call_tool(
            "create_validation_ticket",
            {
                "model_id": model_id,
                "validation_type": validation_type,
            },
        )

    async def get_ticket_status(self, ticket_key: str):
        return await self._call_tool(
            "get_ticket_status",
            {
                "ticket_key": ticket_key,
            },
        )

    async def get_ticket_by_model(self, model_id: str):
        return await self._call_tool(
            "get_ticket_by_model",
            {
                "model_id": model_id,
            },
        )

    async def transition_state(self, ticket_key: str, status: str):
        return await self._call_tool(
            "transition_ticket",
            {
                "ticket_key": ticket_key,
                "status": status,
            },
        )
    
    async def get_all_incidents(self, model_id: str):
        return await self._call_tool(
            "get_all_incidents",
            {"model_id": model_id}
        )