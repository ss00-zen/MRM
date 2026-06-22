import json
import asyncio
from typing import Optional
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class SQLMCPClient:
    _session: Optional[ClientSession] = None
    _mgr = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.base_url = "http://127.0.0.1:9000/mcp"

    async def _close_existing(self):
        if SQLMCPClient._session:
            try:
                await SQLMCPClient._session.__aexit__(None, None, None)
            except Exception:
                pass
            SQLMCPClient._session = None

        if SQLMCPClient._mgr:
            try:
                await SQLMCPClient._mgr.__aexit__(None, None, None)
            except Exception:
                pass
            SQLMCPClient._mgr = None

    async def _get_session(self) -> ClientSession:
        async with self._lock:
            if SQLMCPClient._session is None:
                await self._close_existing()

                # Streamable HTTP transport for /mcp endpoint
                SQLMCPClient._mgr = streamablehttp_client(
                    url=self.base_url,
                    timeout=30,
                    sse_read_timeout=300,
                )
                read, write, _get_session_id = await SQLMCPClient._mgr.__aenter__()

                session_mgr = ClientSession(
                    read_stream=read,
                    write_stream=write,
                    read_timeout_seconds=timedelta(seconds=100),
                )
                SQLMCPClient._session = await session_mgr.__aenter__()
                await SQLMCPClient._session.initialize()

        return SQLMCPClient._session

    async def _call_tool(self, tool_name: str, payload: dict):
        try:
            session = await self._get_session()
            result = await session.call_tool(tool_name, arguments=payload)

            if not result.content:
                return {}

            content_block = result.content[0]
            if hasattr(content_block, "text"):
                text_payload = content_block.text
                try:
                    return json.loads(text_payload)
                except (json.JSONDecodeError, TypeError):
                    return text_payload

            return result

        except Exception as e:
            error_msg = str(e)
            if hasattr(e, "exceptions") and e.exceptions:
                error_msg = f"{error_msg} (Root: {e.exceptions[0]})"

            async with self._lock:
                await self._close_existing()

            print(f"❌ SQLMCPClient Error calling {tool_name}: {error_msg}")
            raise

    async def get_model_inventory(self, model_id):
        return await self._call_tool(
            "query_model_inventory",
            {"model_id": model_id}
        )

    async def get_all_latest_metrics(self, model_id):
        return await self._call_tool(
            "get_all_latest_metrics",
            {"model_id": model_id}
        )

    async def get_metrics_history(self, model_id):
        return await self._call_tool(
            "get_metrics_history",
            {"model_id": model_id}
        )

    async def get_audit_logs(self, model_id):
        return await self._call_tool(
            "get_audit_logs",
            {"model_id": model_id}
        )

    async def insert_metric(self, model_id, metric_name, value, source="mcp"):
        return await self._call_tool(
            "insert_metric",
            {
                "model_id": model_id,
                "metric_name": metric_name,
                "metric_value": value,
                "source": source,
            },
        )

    async def get_validation_record(self, model_id):
        return await self._call_tool(
            "get_validation_record",
            {"model_id": model_id}
        )

    async def update_validation_record(self, record: dict):
        return await self._call_tool(
            "update_validation_record",
            record
        )

    async def generate_sr11_report(self, model_id):
        return await self._call_tool(
            "generate_sr11_report",
            {"model_id": model_id}
        )
