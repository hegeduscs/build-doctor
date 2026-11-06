"""Hamis, OpenAI-kompatibilis LLM szerver FÜSTTESZTHEZ (API-kulcs nélkül).

Nem gondolkodik: fix sorrendben meghív néhány toolt (get_ci_run -> get_failed_tests -> get_diff),
aztán egy "unknown" kategóriájú diagnózist ad a diff első módosított sorával mint bizonyítékkal.
Arra jó, hogy a csővezeték (MCP <-> keretrendszer <-> n8n <-> eval) kulcs nélkül is végigfusson.

Indítás:   uvicorn scripts.fake_llm:app --port 9100
Használat: OPENAI_BASE_URL=http://localhost:9100/v1 OPENAI_API_KEY=fake LLM_MODEL=fake-model
"""
import json
import os
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="fake LLM")
PLAN = ["get_ci_run", "get_failed_tests", "get_diff"]


def _text(m):
    c = m.get("content")
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c or ""


def _called(messages):
    names = []
    for m in messages:
        for tc in m.get("tool_calls") or []:
            names.append(tc["function"]["name"])
        if m.get("role") == "assistant":  # pl. smolagents szövegként tárolja a korábbi hívásokat
            names += [n for n in PLAN if re.search(rf"\b{n}\b", _text(m))]
    return names


def _run_id(messages):
    for m in messages:
        hit = re.search(r"\br\d{4}\b", _text(m))
        if hit:
            return hit.group(0)
    return "r0000"


def _diagnosis(messages):
    run_id = _run_id(messages)
    blob = "\n".join(_text(m) for m in messages if m.get("role") in ("tool", "function", "user"))
    blob = blob.replace("\\n", "\n").replace('\\"', '"')
    ev = []
    m = re.search(r"\+\+\+ b/(\S+)\n@@ -\d+(?:,\d+)? \+(\d+)", blob)
    if m:
        path, start = m.group(1), int(m.group(2))
        hunk = blob[m.end():].split("\n")[1:]
        line = start
        for h in hunk:
            if h.startswith("+"):
                ev.append({"file": path, "line": line, "quote": h[1:].strip()})
                break
            if not h.startswith("-"):
                line += 1
    return {"run_id": run_id, "category": "unknown", "root_cause": "fake LLM: nem elemez, csak a diffet idézi",
            "evidence": ev, "suggested_fix": "n/a", "confidence": float(os.environ.get("FAKE_CONFIDENCE", "0.1")),
            "needs_human": "FAKE_CONFIDENCE" not in os.environ, "security_notes": ""}


def _completion(model, message, finish):
    return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion", "created": int(time.time()),
            "model": model, "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}


def _tool_call(name, args):
    return {"id": f"call_{uuid.uuid4().hex[:10]}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
@app.post("/openai/deployments/{dep}/chat/completions")
async def chat(req: Request, dep: str | None = None):
    body = await req.json()
    model, messages = body.get("model", dep or "fake"), body.get("messages", [])
    tools = {t["function"]["name"]: t for t in body.get("tools") or []}
    rf = body.get("response_format") or {}
    called = _called(messages)
    nxt = next((n for n in PLAN if n in tools and n not in called), None)
    run_id = _run_id(messages)
    if nxt:
        msg, finish = {"role": "assistant", "content": None, "tool_calls": [_tool_call(nxt, {"run_id": run_id})]}, "tool_calls"
    elif rf.get("type") == "json_schema":
        msg, finish = {"role": "assistant", "content": json.dumps(_diagnosis(messages), ensure_ascii=False)}, "stop"
    else:
        struct = next((n for n, t in tools.items() if "category" in json.dumps(t["function"].get("parameters", {}))), None)
        if struct:  # LangChain ToolStrategy: a strukturált választ egy "tool" hívásaként várja
            msg, finish = {"role": "assistant", "content": None, "tool_calls": [_tool_call(struct, _diagnosis(messages))]}, "tool_calls"
        elif "final_answer" in tools:  # smolagents
            msg, finish = {"role": "assistant", "content": None,
                           "tool_calls": [_tool_call("final_answer", {"answer": json.dumps(_diagnosis(messages), ensure_ascii=False)})]}, "tool_calls"
        else:
            msg, finish = {"role": "assistant", "content": "Vizsgálat kész. " + json.dumps(_diagnosis(messages), ensure_ascii=False)}, "stop"
    comp = _completion(model, msg, finish)
    if not body.get("stream"):
        return JSONResponse(comp)

    def sse():
        delta = {"role": "assistant", "content": msg.get("content")}
        if msg.get("tool_calls"):
            delta["tool_calls"] = [dict(tc, index=i) for i, tc in enumerate(msg["tool_calls"])]
        chunk = {"id": comp["id"], "object": "chat.completion.chunk", "created": comp["created"], "model": model,
                 "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        end = dict(chunk, choices=[{"index": 0, "delta": {}, "finish_reason": finish}], usage=comp["usage"])
        yield f"data: {json.dumps(end, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": "fake-model", "object": "model"}]}
