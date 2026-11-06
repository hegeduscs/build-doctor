"""smolagents implementáció – STARTER.

Működik, de minimális. A csapat TODO-i (a demón és az ADR-ben ezekre kérdezünk rá):
  [ ] CodeAgent vagy ToolCallingAgent? (CodeAgent: Python kódot ír akcióként -> sandbox kell!)
  [ ] max_steps és a leállás: mi történik, ha elfogy?
  [ ] system prompt finomítása (prompts.SYSTEM_PROMPT) – a prompt injection kezelése
  [ ] token- és lépésszámlálás pontosítása a trace-ben
  [ ] írás (create_issue / propose_patch) SOSEM a diagnózis része – ezt teszttel is bizonyítsátok
"""
import asyncio
import os
import time

from .adapters import smolagents_tools
from .finalize import finalize
from .llm import model_name
from .prompts import SYSTEM_PROMPT
from .schema import Diagnosis, Trace

MAX_STEPS = 10


def _model():
    from smolagents import AzureOpenAIServerModel, OpenAIServerModel

    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        return AzureOpenAIServerModel(model_id=model_name(), azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                                      api_key=os.environ["AZURE_OPENAI_API_KEY"],
                                      api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"))
    return OpenAIServerModel(model_id=model_name(), api_base=os.environ.get("OPENAI_BASE_URL"),
                             api_key=os.environ.get("OPENAI_API_KEY"))


def _run_sync(run_id: str, trace: Trace) -> str:
    from smolagents import ToolCallingAgent

    agent = ToolCallingAgent(tools=smolagents_tools(trace=trace), model=_model(), max_steps=MAX_STEPS,
                             verbosity_level=int(os.environ.get("SMOL_VERBOSITY", "0")))  # 1-2: részletes konzol-log
    task = f"{SYSTEM_PROMPT}\n\nVizsgáld ki a(z) {run_id} CI futás hibáját, és foglald össze a bizonyítékokkal együtt."
    result = agent.run(task)
    trace.steps = len(agent.memory.steps)
    usage = getattr(agent.monitor, "get_total_token_counts", lambda: None)()
    if usage is not None:
        trace.tokens_in = getattr(usage, "input_tokens", 0)
        trace.tokens_out = getattr(usage, "output_tokens", 0)
    return str(result)


async def diagnose(run_id: str) -> tuple[Diagnosis, Trace]:
    trace = Trace(impl="smolagents", model=model_name())
    t0 = time.perf_counter()
    notes = await asyncio.to_thread(_run_sync, run_id, trace)
    diag = await finalize(run_id, notes, trace)
    trace.duration_s = round(time.perf_counter() - t0, 2)
    return diag, trace
