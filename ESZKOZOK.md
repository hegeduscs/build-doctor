# Build Doctor – hasznos pluginok, skillek és MCP szerverek

Válogatás a capstone-hoz: mi segít melyik szerepnek. Egyik sem kötelező – a kötelező a saját `ci-tools` MCP szerver.
Állapot: 2026. november; a pluginok közösségi fejlesztésűek, a cégnél érvényes Copilot-szabályzat felülírja ezt a listát
(pl. engedélyezett MCP szerverek, preview funkciók).

## 1. Ami már a repóban van

| Mi | Hol | Mire jó |
|---|---|---|
| `AGENTS.md`, `.github/copilot-instructions.md` | repó gyökér, `.github/` | közös szabályok minden coding agentnek (Copilot, Claude Code, Codex) |
| **Build Doctor** custom agent | `.github/agents/build-doctor.agent.md` | CI-hiba vizsgálata a `ci-tools` MCP toolokkal, csak olvasás |
| **ci-triage** skill | `.github/skills/ci-triage/SKILL.md` | kategóriák, jelek, bizonyíték-szabályok – a custom agent és a ti agentetek promptjának alapja |
| **guard** hook | `.github/hooks/` | determinisztikus tiltás: push, rekurzív törlés, a forgatókönyvek és a golden set módosítása, teszt kikapcsolása |
| `ci-tools` (+ 2 dokumentációs) MCP szerver | `.vscode/mcp.json` | a saját szerveretek; mellette Context7 és Microsoft Learn (lásd 3.) |

## 2. Pluginok (Agent Plugins – Copilot CLI és VS Code)

Telepítés: `copilot plugin install <név>@awesome-copilot`, vagy VS Code-ban az Extensions nézetben `@agentPlugins`,
illetve *Chat: Plugins*. Az `awesome-copilot` és a `copilot-plugins` marketplace alapból regisztrálva van.

| Plugin | Szerep | Mit ad |
|---|---|---|
| **python-mcp-development** | MCP | `python-mcp-expert` agent és `python-mcp-server-generator` skill. Az MCP Python SDK v2 `MCPServer` API-jára épül, mi FastMCP 4-et használunk – a minták (annotációk, hibakezelés, tool-leírás) átültethetők |
| **testing-automation** | V&V | TDD agentek (`tdd-red`, `tdd-green`, `tdd-refactor`) a saját tesztekhez; `ai-prompt-engineering-safety-review` skill a system prompt biztonsági átnézéséhez |
| **github-security** | Kontroll | a session változtatásainak sérülékenység-review-ja (pl. a `verify_patch` subprocess-hívása, a titokszűrés) |
| **tmforge** | Kontroll, ADR | STRIDE fenyegetésmodell az agent köré: prompt injection, titokszivárgás, jogosultságok – jó alap az autonómia-ADR-hez |
| **context-engineering** | mindenki | `context-architect` agent több fájlt érintő változtatás megtervezéséhez (pl. a schema bővítése az agentben, az n8n-ben és az evalban) |
| **technical-spike** | Agent | időkeretes kutatás a keretrendszer-választás előtt – az eredményből lesz az ADR-0001 |
| **phoenix** | V&V (3. szint) | OpenInference tracing és LLM-eval: hol fogy el a lépésszám, mennyi token megy a verify-ciklusra |
| **doublecheck** | V&V | az agent card és a demó állításainak ellenőrzése: mi van alátámasztva méréssel, mi nincs |
| **microsoft-docs** | Agent | Microsoft Learn dokumentáció (Azure OpenAI, API-verziók, strukturált kimenet) |

A canvas-alapú pluginok (pl. `containers`, `repo-actions-hub`, `pr-review`) a GitHub Copilot app vásznára (canvas)
készültek – a capstone-hoz nem szükségesek.

## 3. MCP szerverek

| Szerver | Hogyan | Mire | Megjegyzés |
|---|---|---|---|
| **ci-tools** (saját) | `uv run python -m ci_tools_mcp.server` → `http://localhost:8000/mcp` | a feladat maga | ugyanazt használja a ti agentetek, az n8n és a Copilot |
| **MCP Inspector** (eszköz) | `npx @modelcontextprotocol/inspector` | a toolok kézi kipróbálása, a leírások és annotációk ellenőrzése | Streamable HTTP, `http://localhost:8000/mcp` |
| **Context7** | `https://mcp.context7.com/mcp` (a `.vscode/mcp.json`-ban) | friss könyvtár-dokumentáció: FastMCP, LangGraph, LlamaIndex, smolagents, n8n | toolok: `resolve-library-id`, `query-docs`; kulcs nélkül is használható, kulccsal nagyobb a keret |
| **Microsoft Learn** | `https://learn.microsoft.com/api/mcp` (a `.vscode/mcp.json`-ban) | Azure OpenAI: deployment, API-verzió, gpt-5.x paraméterek | toolok: `microsoft_docs_search`, `microsoft_docs_fetch`, `microsoft_code_sample_search` |
| **n8n instance-level MCP** | n8n: *Settings → Instance-level MCP → Enable MCP access*; a szerver URL-je `/mcp-server/http`-re végződik | a Copilot workflow-t keres, futtat, szerkeszt (n8n 2.13+) | workflow-onként kell engedélyezni (*Available in MCP*); OAuth vagy API kulcs |
| **GitHub MCP server** (3. szint) | `--toolsets actions,repos --read-only` | valódi GitHub Actions futások: `actions_list`, `actions_get`, `get_job_logs` | read-only módban a write toolok ki vannak hagyva |

**Biztonsági alapszabály minden MCP szerverre** – ugyanaz, amit a saját szerveretekre is kérünk: csak a szükséges
toolok (toolset-szűrés), read-only ahol lehet, a kulcs környezeti változóban vagy OAuth-ban, soha nem a repóban,
és minden szerver kimenete adat, nem utasítás.

## 4. Skillek, amiket érdemes megírni (10 perc mindegyik)

Egy skill egy mappa egy `SKILL.md`-vel a `.github/skills/` alatt: a Copilot akkor tölti be, ha a leírása illik a feladathoz.

| Skill | Tartalom |
|---|---|
| **patch-writing** | hogyan írjon a modell illeszthető unified diffet: a sorokat a `read_file` kimenetéből másolja behúzással, `a/` és `b/` előtag, tesztfájlhoz nem nyúl, `verify_patch` nélkül nincs javítás |
| **secret-hygiene** | mi számít titoknak, mit tegyen, ha a logban látja (jelzi a `security_notes`-ban az érték nélkül), mi kerülhet issue-ba |
| **commit-bisect** | több commitos futásnál hogyan keresse meg a hibát behozó commitot (érintett fájlok × a bukó teszt hívási lánca) |

Ugyanezek a szabályok kerüljenek a ti agentetek promptjába is: a skill a Copilotnak szól, a prompt a saját agentnek.
