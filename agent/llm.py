"""LLM kliens környezeti változókból. OpenAI-kompatibilis chat completions API-t használunk,
így Azure OpenAI, OpenAI, GitHub Models vagy helyi Ollama is működik.

  Azure:   AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, LLM_MODEL=<deployment>
  Egyéb:   OPENAI_API_KEY (+ OPENAI_BASE_URL), LLM_MODEL=<modell>
"""
import os

from openai import AsyncAzureOpenAI, AsyncOpenAI


def model_name() -> str:
    return os.environ.get("LLM_MODEL", "gpt-5.4-mini")


def async_client():
    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        return AsyncAzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        )
    return AsyncOpenAI()  # OPENAI_API_KEY, OPENAI_BASE_URL


def llm_configured() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("OPENAI_API_KEY"))
