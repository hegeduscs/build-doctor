"""HTTP végpont az n8n-nek:  uvicorn agent.api:app --port 8080
POST /diagnose {"run_id": "r1001"}  ->  {"diagnosis": {...}, "trace": {...}}"""
from dataclasses import asdict

from fastapi import FastAPI
from pydantic import BaseModel

from .impls import get_diagnose

app = FastAPI(title="Build Doctor agent API")


class DiagnoseIn(BaseModel):
    run_id: str
    impl: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/diagnose")
async def diagnose(req: DiagnoseIn):
    diag, trace = await get_diagnose(req.impl)(req.run_id)
    t = asdict(trace)
    return {"diagnosis": diag.model_dump(), "trace": {k: t[k] for k in ("impl", "model", "steps", "tokens_in",
                                                                        "tokens_out", "duration_s", "notes")},
            "tool_calls": t["tool_calls"]}


class IssueIn(BaseModel):
    run_id: str
    title: str
    body: str


@app.post("/actions/create-issue")
async def create_issue(req: IssueIn):
    """Jóváhagyott írás (pl. az n8n szabálya vagy egy ember döntése után) – MCP-n keresztül,
    így a szerver védelmei (WRITE_MODE, titok-szűrés) és az audit napló érvényesek."""
    from .mcp_tools import call, mcp_session

    async with mcp_session() as mcp:
        return await call(mcp, "create_issue", req.model_dump())
