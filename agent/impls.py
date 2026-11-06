"""Implementáció kiválasztása: AGENT_IMPL=baseline | smolagents | llamaindex | langgraph | <saját modul neve>"""
import importlib
import os

ALIASES = {"baseline": "baseline_agent", "smolagents": "impl_smolagents", "llamaindex": "impl_llamaindex",
           "langgraph": "impl_langgraph", "reference": "reference_agent"}


def get_diagnose(name: str | None = None):
    name = name or os.environ.get("AGENT_IMPL", "baseline")
    mod = importlib.import_module(f"agent.{ALIASES.get(name, name)}")
    return mod.diagnose
