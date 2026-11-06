"""Közös MCP-elérés a keretrendszer nélküli implementációkhoz (baseline, referencia)."""
import os
from contextlib import asynccontextmanager

from fastmcp import Client

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")
WRITE_TOOLS = {"create_issue", "propose_patch"}


@asynccontextmanager
async def mcp_session(url: str | None = None):
    async with Client(url or MCP_URL) as client:
        yield client


async def call(client, name: str, args: dict, trace=None):
    ok = True
    try:
        res = await client.call_tool(name, args)
        data = res.data if res.data is not None else (res.structured_content or [c.text for c in res.content if hasattr(c, "text")])
    except Exception as exc:  # noqa: BLE001 – a hibát az agent kapja vissza
        ok, data = False, {"error": str(exc)}
    if trace is not None:
        trace.tool_calls.append({"name": name, "args": args, "ok": ok})
    return data


def _schema(tool) -> dict:
    """MCP SDK v2: input_schema, v1: inputSchema."""
    return getattr(tool, "input_schema", None) or getattr(tool, "inputSchema")


def openai_tool_schemas(tools, include_write: bool = False) -> list[dict]:
    """MCP tool-lista -> OpenAI function calling séma. Alapból a write toolokat NEM adjuk oda a diagnózishoz."""
    out = []
    for t in tools:
        if t.name in WRITE_TOOLS and not include_write:
            continue
        out.append({"type": "function", "function": {
            "name": t.name, "description": t.description or "", "parameters": _schema(t)}})
    return out
