"""LlamaIndex implementáció – STARTER.

Működik, de minimális. A csapat TODO-i:
  [ ] FunctionAgent vagy ReActAgent? Kell-e AgentWorkflow több agenttel (pl. triage + kódelemző)?
  [ ] output_cls=Diagnosis kipróbálása a finalize() helyett
  [ ] az 1. napi RAG index bekötése toolként (pl. üzemeltetési runbook-ok)?
  [ ] lépéslimit / timeout, token-számlálás
  [ ] write toolok kizárása (include_write=False marad!) – teszttel bizonyítva
"""
import os
import time

from llama_index.core.agent.workflow import FunctionAgent, ToolCall, ToolCallResult
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from .finalize import finalize
from .llm import model_name
from .mcp_tools import MCP_URL, WRITE_TOOLS
from .prompts import SYSTEM_PROMPT
from .schema import Diagnosis, Trace


def _llm():
    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        from llama_index.llms.azure_openai import AzureOpenAI

        return AzureOpenAI(engine=model_name(), model=os.environ.get("LLM_BASE_MODEL", "gpt-4.1-mini"),
                           azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
                           api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"))
    if os.environ.get("OPENAI_BASE_URL"):  # OpenAI-kompatibilis végpont (GitHub Models, Ollama, fake LLM...)
        from llama_index.llms.openai_like import OpenAILike

        return OpenAILike(model=model_name(), api_base=os.environ["OPENAI_BASE_URL"],
                          api_key=os.environ.get("OPENAI_API_KEY", "none"), is_chat_model=True,
                          is_function_calling_model=True, context_window=128000)
    from llama_index.llms.openai import OpenAI

    return OpenAI(model=model_name())


async def diagnose(run_id: str) -> tuple[Diagnosis, Trace]:
    trace = Trace(impl="llamaindex", model=model_name())
    t0 = time.perf_counter()
    spec = McpToolSpec(client=BasicMCPClient(MCP_URL))
    tools = [t for t in await spec.to_tool_list_async() if t.metadata.name not in WRITE_TOOLS]
    agent = FunctionAgent(tools=tools, llm=_llm(), system_prompt=SYSTEM_PROMPT)
    handler = agent.run(user_msg=f"Vizsgáld ki a(z) {run_id} CI futás hibáját, és foglald össze a bizonyítékokkal.")
    async for ev in handler.stream_events():
        if isinstance(ev, ToolCall):
            trace.steps += 1
        elif isinstance(ev, ToolCallResult):
            trace.tool_calls.append({"name": ev.tool_name, "args": ev.tool_kwargs,
                                     "ok": not getattr(ev.tool_output, "is_error", False)})
    result = await handler
    diag = await finalize(run_id, str(result), trace)
    trace.duration_s = round(time.perf_counter() - t0, 2)
    return diag, trace
