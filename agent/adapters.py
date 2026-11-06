"""MCP -> keretrendszer tool adapterek, a fastmcp kliensre építve.

Miért saját adapter? 2026 őszén a smolagents (mcpadapt) és a langchain-mcp-adapters még az MCP SDK 1.x-re
épül, a szerverünk pedig az SDK 2.x-et (2026-07-28 spec) használja – egy környezetben nem férnek meg.
A protokoll szintjén kompatibilisek, ezért elég egy vékony adapter: tanulságos is, mert látszik,
hogy egy MCP tool = név + leírás + JSON séma + egy hívás.

LlamaIndexhez a hivatalos llama-index-tools-mcp működik (lásd impl_llamaindex.py).
"""
import asyncio
import json

from fastmcp import Client

from .mcp_tools import MCP_URL, WRITE_TOOLS, _schema


def _to_python(res):
    if res.data is not None:
        return res.data
    if res.structured_content is not None:
        return res.structured_content
    return "\n".join(getattr(c, "text", "") for c in res.content)


async def _call(url: str, name: str, args: dict, trace=None):
    async with Client(url) as c:
        res = await c.call_tool(name, args, raise_on_error=False)
    ok = not res.is_error
    if trace is not None:
        trace.tool_calls.append({"name": name, "args": args, "ok": ok})
    out = _to_python(res)
    return out if ok else {"error": out}


async def list_mcp_tools(url: str | None = None, include_write: bool = False):
    async with Client(url or MCP_URL) as c:
        tools = await c.list_tools()
    return [t for t in tools if include_write or t.name not in WRITE_TOOLS]


# ----------------------------------------------------------------------------- LangChain / LangGraph
async def langchain_tools(url: str | None = None, include_write: bool = False, trace=None):
    from langchain_core.tools import StructuredTool

    url = url or MCP_URL
    out = []
    for t in await list_mcp_tools(url, include_write):
        async def _co(_name=t.name, **kwargs):
            res = await _call(url, _name, {k: v for k, v in kwargs.items() if v is not None}, trace)
            return json.dumps(res, ensure_ascii=False, default=str)[:8000]

        out.append(StructuredTool.from_function(coroutine=_co, name=t.name, description=t.description or "",
                                                args_schema=_schema(t)))
    return out


# ----------------------------------------------------------------------------- smolagents
_JSON2SMOL = {"string": "string", "integer": "integer", "number": "number", "boolean": "boolean",
              "array": "array", "object": "object", "null": "null"}


def _smol_inputs(schema: dict) -> dict:
    req = set(schema.get("required", []))
    inputs = {}
    for name, prop in schema.get("properties", {}).items():
        types = [p.get("type") for p in prop.get("anyOf", [])] or [prop.get("type", "string")]
        main = next((t for t in types if t and t != "null"), "string")
        inputs[name] = {"type": _JSON2SMOL.get(main, "any"), "description": prop.get("description", name)}
        if name not in req or "null" in types:
            inputs[name]["nullable"] = True
    return inputs


def smolagents_tools(url: str | None = None, include_write: bool = False, trace=None):
    """Szinkron függvény: smolagents Tool objektumok listája. Async kódból: await asyncio.to_thread(...)."""
    from smolagents import Tool

    url = url or MCP_URL
    mcp_tools = asyncio.run(list_mcp_tools(url, include_write))

    class MCPTool(Tool):
        skip_forward_signature_validation = True

        def __init__(self, t):
            self.name = t.name
            self.description = t.description or t.name
            self.inputs = _smol_inputs(_schema(t))
            self.output_type = "object"
            super().__init__()

        def forward(self, **kwargs):
            args = {k: v for k, v in kwargs.items() if v is not None}
            return asyncio.run(_call(url, self.name, args, trace))

    return [MCPTool(t) for t in mcp_tools]
