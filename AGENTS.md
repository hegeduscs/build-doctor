# Build Doctor – szabályok coding agenteknek (Copilot, Claude Code, Codex)

## Mi ez a repó?
Capstone projekt: agentic asszisztens, ami elbukott CI futások okát deríti ki.
- `mock_ci/` – hamis CI szerver (NE módosítsd a viselkedését a forgatókönyvekhez igazítva)
- `scenarios/` – generált CI futások (log, junit, overlay). **Kézzel nem szerkesztjük.**
- `target_repo/` – a "célrepó", aminek a buildje elbukik. **Nem javítjuk**, ez a vizsgált rendszer.
- `ci_tools_mcp/` – MCP szerver (a csapat írja)
- `agent/` – agent-implementációk; a szerződés: `agent/schema.py` (Diagnosis, Trace)
- `eval/` – golden set és eval-futtató; `tests/` – LLM nélküli tesztek

## Parancsok
- Telepítés: `uv sync --extra <smolagents|llamaindex|langgraph|all>`
- Tesztek (LLM nélkül): `uv run pytest`
- Mock CI: `docker compose up -d mock-ci` vagy `uv run uvicorn mock_ci.app:app --port 9000`
- MCP szerver: `uv run python -m ci_tools_mcp.server` (http://localhost:8000/mcp)
- Egy diagnózis: `uv run python -m agent.run r1001 --impl baseline`
- Eval: `uv run python -m eval.run_eval --impl <impl> --repeat 2` (a végén a Definition of Done)
- Csak az 1. szintű MCP-tesztek: `uv run pytest -m "not level2"`

## Konvenciók
- Python 3.11+, típusannotáció mindenhol, `pydantic` modellek a határokon.
- MCP tool: `@mcp.tool(annotations=READ|WRITE)` + `@audited("read"|"write")`; a docstring a modellnek szól.
- Új tool vagy agent-viselkedés = új teszt a `tests/` alatt.
- Titok (API kulcs, token) soha nem kerül kódba, logba, promptba, diagnózisba vagy issue-ba. `.env` nincs commitolva.
- Javítás (`fix_patch`, `propose_patch`) csak `verify_patch`-csel ellenőrizve; a sandbox: `POST /runs/{id}/verify`.

## Tilos
- Tesztet törölni, `skip`-pelni vagy az elvárt értéket átírni, hogy zöld legyen.
- A `scenarios/` és `eval/cases/` tartalmát a saját agentedhez igazítani.
- Write toolt (create_issue, propose_patch) hívni diagnózis közben.
- `main`-re pusholni, force push.
