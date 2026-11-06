"""LangGraph / LangChain v1 implementáció – STARTER.

Működik, de minimális. A csapat TODO-i:
  [ ] create_agent helyett saját StateGraph? (explicit állapot: run, bizonyítékok, hipotézisek)
  [ ] recursion_limit / lépéslimit – mi történik, ha elfogy?
  [ ] human-in-the-loop: a propose_patch-hez külön gráf interrupt()-tal (jóváhagyás után fut)
  [ ] checkpointer (InMemorySaver) a folytathatósághoz, trace a demóhoz
  [ ] write toolok kizárása a diagnózisból – teszttel bizonyítva
"""
import os
import time

from langchain.agents import create_agent

from .adapters import langchain_tools
from .llm import model_name
from .prompts import SYSTEM_PROMPT
from .schema import Diagnosis, Trace

RECURSION_LIMIT = 25  # LangGraph lépések (LLM + tool csomópontok együtt)


def _chat_model():
    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(azure_deployment=model_name(), azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                               api_key=os.environ["AZURE_OPENAI_API_KEY"],
                               api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"))
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model_name(), base_url=os.environ.get("OPENAI_BASE_URL"))


async def diagnose(run_id: str) -> tuple[Diagnosis, Trace]:
    trace = Trace(impl="langgraph", model=model_name())
    t0 = time.perf_counter()
    agent = create_agent(_chat_model(), tools=await langchain_tools(trace=trace), system_prompt=SYSTEM_PROMPT,
                         response_format=Diagnosis)
    state = await agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Vizsgáld ki a(z) {run_id} CI futás hibáját."}]},
        config={"recursion_limit": RECURSION_LIMIT},
    )
    msgs = state["messages"]
    trace.steps = sum(1 for m in msgs if m.type == "ai")
    for m in msgs:
        u = getattr(m, "usage_metadata", None)
        if u:
            trace.tokens_in += u.get("input_tokens", 0)
            trace.tokens_out += u.get("output_tokens", 0)
    diag: Diagnosis = state["structured_response"]
    diag.run_id = run_id
    trace.duration_s = round(time.perf_counter() - t0, 2)
    return diag, trace
