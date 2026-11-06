# Build Doctor – capstone skeleton

Agentic fejlesztői asszisztens, ami egy **elbukott CI futás** okát és a hibát behozó commitot kideríti,
bizonyítékkal alátámasztott diagnózist ad, a javítást sandboxban kipróbálja, és csak zöld tesztek után javasol
draft PR-t – emberi jóváhagyással.
Feladatleírás: [`FELADATLEIRAS.md`](FELADATLEIRAS.md) · lépésről lépésre: [`UTMUTATO.md`](UTMUTATO.md) ·
eszközök: [`ESZKOZOK.md`](ESZKOZOK.md)

```mermaid
flowchart LR
  CI["Mock CI :9000<br/>(scenarios/, /verify sandbox)"] -- webhook --> N8N["n8n :5678"]
  N8N -- "POST /diagnose" --> API["Agent API :8080"]
  API --> AG["Agent<br/>baseline / smolagents /<br/>LlamaIndex / LangGraph"]
  AG <-- MCP --> MCP["ci-tools MCP :8000"]
  MCP -- REST --> CI
  DEV["Fejlesztő<br/>VS Code / Copilot CLI"] <-- MCP --> MCP
  N8N -- "emberi jóváhagyás után<br/>issue / draft PR" --> API
```

## Indulás – mindenki ugyanígy, a saját gépén

A lépésenkénti menetrend ellenőrzőpontokkal: [`UTMUTATO.md`](UTMUTATO.md). Az első két lépés mindenkinél azonos,
utána szerepenként válik szét a munka.

### 0. Setup (előző este vagy 13:00-kor)

```bash
git clone <a csapat repója> && cd <repó>
uv sync --extra all                 # Python 3.11+, uv
cp .env.example .env                # Azure OpenAI kulcs (kulcs nélkül: fake LLM, lent)
docker compose up -d                # mock CI :9000, n8n :5678
uv run pytest                       # elvárt: 23 failed, 18 passed – a piros tesztek a hiányzó MCP toolok
```

### 1. Első mérés (13:00–13:10)

```bash
# 1. terminál – hagyd futni (a 0.0.0.0 kell, hogy a Dockerben futó n8n is elérje)
MCP_HOST=0.0.0.0 uv run python -m ci_tools_mcp.server       # http://localhost:8000/mcp

# 2. terminál
uv run python -m agent.run r1001 --impl baseline            # egy diagnózis
uv run python -m eval.run_eval --impl baseline              # vége: „Definition of Done: MÉG NEM – hiányzik: …”
```

### 2. Innen szerepenként – `UTMUTATO.md`

| Szerep | Lépések | Első parancs |
|---|---|---|
| **MCP** | 2–3., 6. | `npx @modelcontextprotocol/inspector` (Streamable HTTP, `http://localhost:8000/mcp`), majd `uv run pytest -m "not level2"` |
| **Agent** | 4., 7. | `uv run python -m agent.run r1006 --impl langgraph` (vagy `smolagents`, `llamaindex`) |
| **n8n + Copilot** | 5., 8. | http://localhost:5678 → import: `n8n/build-doctor-starter.workflow.json`; agent API: `uv run uvicorn agent.api:app --port 8080 --host 0.0.0.0` |
| **V&V** | 1., 9. | `uv run python -m eval.run_eval --impl <impl> --repeat 2` |

Ha valaki módosítja és pusholja az MCP szervert: `git pull`, majd az 1. terminálban Ctrl+C és újraindítás.

### Parancsok – referencia

```bash
uv run pytest -m "not level2"                     # MCP 1. szint (kész: 32 passed)
uv run pytest                                     # + 2. szint (kész: 41 passed)
uv run python -m eval.run_eval --impl <impl> --repeat 2   # riport + DoD: eval/results/
uv run python scripts/simulate_failure.py r1003   # webhook az n8n-nek, mintha a CI bukott volna
uv run uvicorn mock_ci.app:app --port 9000        # mock CI Docker nélkül (n8n Docker nélkül: npx n8n)
```

**Kulcs nélküli füstteszt:** `uv run uvicorn scripts.fake_llm:app --port 9100`, majd
`OPENAI_BASE_URL=http://localhost:9100/v1 OPENAI_API_KEY=fake LLM_MODEL=fake-model`. A fake LLM nem gondolkodik,
csak végigviszi a csővezetéket: arra jó, hogy kiderüljön, minden komponens beszél-e a többivel.


## Mappák

| Mappa | Mi van benne | Ki dolgozik rajta |
|---|---|---|
| `target_repo/` | A „célrepó” (telemetry-ingest): ennek buknak a buildjei. Nem javítjuk. | – |
| `scenarios/` | 9 generált, **valódi pytest futásból** származó CI-hiba (log, junit, overlay, commitonkénti diff) | – |
| `mock_ci/` | GitHub Actions-szerű REST API a forgatókönyvekhez (`/docs` alatt Swagger) + `POST /runs/{id}/verify` sandbox | – |
| `ci_tools_mcp/` | MCP szerver – 3 kész példa tool, a többi **TODO** | MCP |
| `agent/` | `schema.py` (szerződés), `baseline_agent.py` (workflow, nem agent), keretrendszer-startok, API | Agent |
| `n8n/` | Importálható starter workflow | n8n + Copilot |
| `.github/`, `.vscode/`, `AGENTS.md` | Copilot: custom agent, skill, hook, MCP konfiguráció | n8n + Copilot |
| `eval/` | Golden set (`cases/`) és eval-futtató | V&V |
| `tests/` | LLM nélküli tesztek (mock CI, MCP szerződés) | V&V + MCP |
| `docs/` | SPEC, ADR-sablon, agent card, demó-checklist | mindenki |
| `hidden/` | Ide kerülnek a demón a rejtett forgatókönyvek (az oktatók hozzák) | – |

## Forgatókönyvek (golden set)

| run | ág | mi történt (röviden) |
|---|---|---|
| r1001 | feature/units-refactor | „refactor: simplify temperature conversion” |
| r1002 | main | „docs: document batch size setting” |
| r1003 | chore/config-names | „chore: rename config keys for clarity” |
| r1004 | deps/pyyaml-7 | dependabot frissítés |
| r1005 | feature/dedupe-cleanup | „perf: keep dedupe logic simple and readable” |
| r1006 | fix/alarm-threshold | külsős hozzájáruló javítása ☠ (prompt injectiont tartalmaz) |
| r1007 | release/1.4 | két commit: „docs: changelog for 1.4” és előtte egy refaktor |
| r1008 | chore/startup-logging | „chore: log effective settings at startup” 🔑 (titok a logban) |
| r1009 | test/strict-roundtrip | „test: make F->C roundtrip exact, add body temperature” |

Az elvárt eredmények az `eval/cases/` alatt vannak – **az agent nem láthatja őket** (a hook is tiltja).

## Implementációk

`AGENT_IMPL` vagy `--impl`: `baseline` · `smolagents` · `llamaindex` · `langgraph` · `<saját modul az agent/ alatt>`.
Mindegyik ugyanazt adja: `async def diagnose(run_id) -> (Diagnosis, Trace)`. A 2. szintű mezők (`culprit_commit`,
`fix_patch`, `fix_verified`) opcionálisak – a baseline nem tölti ki őket, ezért nem teljesíti a Definition of Done-t.

## A javítás ellenőrzése (sandbox)

`POST /runs/{run_id}/verify {"patch": "<unified diff>"}` – a futás állapotának eldobható másolatán alkalmazza a patch-et
(`git apply`, ha az nem megy, szó szerinti hunk-csere), lefuttatja a teszteket, és visszaadja: `applied`, `tests_ok`,
`passed`, `failed`, `failed_tests`, `violations` (tesztfájl módosítása, skip/xfail), `tail`. A `tests_ok` csak akkor igaz,
ha minden teszt zöld, és nem futott kevesebb teszt, mint a javítás nélkül. A telepítési hibákat (requirements) nem
tudja ellenőrizni – a sandbox nem telepít csomagot.

Az MCP toolokat a smolagents és a LangChain felé saját, vékony adapter köti be (`agent/adapters.py`), mert
a hivatalos adapterek 2026 őszén még az MCP SDK 1.x-re épülnek. A LlamaIndex a hivatalos `llama-index-tools-mcp`-t használja.

## Hibaelhárítás

- **n8n nem éri el az agent API-t / MCP-t**: Dockerből a gép `host.docker.internal`; a szolgáltatásokat `0.0.0.0`-ra
  kell kötni (`--host 0.0.0.0`, `MCP_HOST=0.0.0.0`). Linuxon a compose `extra_hosts` beállítása ezt megoldja.
- **Azure + LlamaIndex**: `LLM_MODEL` = deployment neve, `LLM_BASE_MODEL` = a mögötte lévő modell neve.
- **smolagents konzol-log**: `SMOL_VERBOSITY=1` vagy `2`.
- `SCENARIO_DIRS` elválasztója minden platformon `;`.
