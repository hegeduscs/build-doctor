# Build Doctor – útmutató lépésről lépésre

Ez a feladatleírás ([`FELADATLEIRAS.md`](FELADATLEIRAS.md)) gyakorlati párja: mit csináljatok, milyen sorrendben,
és honnan tudjátok, hogy kész. Minden lépés végén van egy **ellenőrzőpont** – egy parancs és az elvárt eredmény.
Ha egy ellenőrzőpontnál 10 percnél tovább elakadtok, szóljatok: van segítség (és van referencia-megoldás).

Szerepek a csapatban (3 főnél az n8n + Copilot és a V&V összevonható):

| Szerep | 1. sprint (13:10–14:30) | 2. sprint (14:45–15:25) |
|---|---|---|
| **MCP** | 2. és 3. lépés | 6. lépés, utána az agent segítése |
| **Agent** | 4. lépés | 7. lépés |
| **n8n + Copilot** | 5. lépés | 8. lépés |
| **V&V** | 1. lépés mérése, saját tesztek, SPEC | 9. lépés |

**Mindenki ugyanazt állítja fel.** Minden csapattag a saját gépén futtatja a teljes környezetet (mock CI, n8n,
MCP szerver, agent) – nincs közös szerver és nincs „infra gép”, minden `localhost`-on fut. Az együttműködés a
közös repón keresztül megy: mindenki a saját szerepe fájljain dolgozik, gyakran commitol és pushol, a többiek
`git pull`-lal frissítenek, és újraindítják az MCP szervert. Az MCP-s a 13:40-es ellenőrzőpont után pusholjon –
onnantól mindenkinél él a teljes toolkészlet. Csapatonként egy LLM-kulcs van, mindenki ugyanazt írja az `.env`-be.

| Szerep | Ezeket a fájlokat szerkeszti |
|---|---|
| **MCP** | `ci_tools_mcp/server.py` |
| **Agent** | `agent/impl_*.py`, `agent/prompts.py`, `docs/adr/` |
| **n8n + Copilot** | `n8n/*.json` (exportálva), `.github/agents/`, `.github/skills/` |
| **V&V** | `tests/`, `docs/SPEC.md`, `docs/AGENT_CARD.md`, `eval/results/` |

---

## 0. Előző este (15 perc, otthonról – mindenki a saját gépén)

```bash
git clone <a csapat repója, a template-ből>  &&  cd <repó>
uv sync --extra all                   # Python 3.11+, uv
cp .env.example .env                  # az Azure OpenAI adatokat a kickoffon adjuk
docker compose up -d                  # mock CI :9000, n8n :5678
uv run pytest                         # LLM nélkül fut
```

**Ellenőrzőpont:** a `pytest` vége `23 failed, 18 passed`. Ez így jó: a piros tesztek az MCP szerver hiányzó részei.
Docker nélkül: `uv run uvicorn mock_ci.app:app --port 9000` (a mock CI), az n8n pedig `npx n8n`.

Telepítsétek a hasznos Copilot-pluginokat is ([`ESZKOZOK.md`](ESZKOZOK.md)), legalább:
`copilot plugin install python-mcp-development@awesome-copilot` és `copilot plugin install testing-automation@awesome-copilot`.

## 1. Setup és mérés (13:00–13:10, mindenki)

```bash
MCP_HOST=0.0.0.0 uv run python -m ci_tools_mcp.server   # külön terminálban hagyd futni: http://localhost:8000/mcp
uv run python -m agent.run r1001 --impl baseline     # egy diagnózis
uv run python -m eval.run_eval --impl baseline       # a golden set (9 forgatókönyv)
```

**Ellenőrzőpont:** az eval végén `Definition of Done: MÉG NEM – hiányzik: …`. Írjátok fel, mi hiányzik – ez a célotok.
A riport az `eval/results/` alatt van (`.md` és `.json`).

> A skeleton MCP szerverrel a baseline sem tud minden toolt hívni – ezért az első mérés gyenge. A V&V-s vezesse
> egy táblázatban: ugyanazt a mérést futtatjuk minden lépés után.

## 2. MCP – 1. szint (13:10–13:40)

Fájl: `ci_tools_mcp/server.py`. A mock CI végpontjai: http://localhost:9000/docs

1. Írjátok meg a hiányzó read toolokat: `get_log_excerpt`, `get_diff`, `get_recent_commits`, `read_file`, `search_code`, `get_test_history`.
2. A write toolokat: `create_issue`, `propose_patch` – `WRITE_MODE=dry-run` alapból; utasítsák el a titkot tartalmazó
   body-t és a tesztet törlő / kikapcsoló patch-et.
3. Minden toolnak legyen **valódi leírása**: mikor és mire használja a modell. Ez maga a prompt.

```bash
uv run pytest -m "not level2"           # csak az 1. szint tesztjei
npx @modelcontextprotocol/inspector     # kézi próba: Streamable HTTP, http://localhost:8000/mcp
```

**Ellenőrzőpont (13:40):** `32 passed, 9 deselected`; az Inspectorban látszik mind a 11 tool, a write toolok `readOnlyHint=false`.

> Elakadás: a `python-mcp-development` plugin `python-mcp-expert` agentje jó párbeszédpartner. Figyelem: ő az MCP SDK v2
> `MCPServer` API-ját ismeri, mi FastMCP 4-et használunk – a minták átültethetők.

## 3. MCP – a szerződés véglegesítése (13:40–13:50)

- Állítsátok le és indítsátok újra a szervert, futtassátok újra a baseline evalt: most már minden tool él.
- A V&V-s nézze meg az `audit/audit.jsonl`-t: minden hívás ott van?

**Ellenőrzőpont:** a baseline eval lefut hibák nélkül; a riportban a `safety` oszlop végig ✅.

## 4. Agent – 1. szint (13:10–14:10)

1. **Válasszatok keretrendszert** (`agent/impl_smolagents.py`, `impl_llamaindex.py` vagy `impl_langgraph.py`), és írjátok
   meg az ADR-t: `docs/adr/0001-keretrendszer.md`. Szempontok: kontroll a lépések felett, strukturált kimenet,
   jóváhagyás (LangGraph `interrupt`?), mennyire látszik a trace.
2. Fejezzétek be a startot: prompt (`agent/prompts.py`), lépéslimit, leállási feltétel, a write toolok kizárása.
3. A mérgezett forgatókönyv (r1006): az agent ne kövesse a commit üzenetben lévő utasítást, hanem jelezze a `security_notes`-ban.

```bash
uv run python -m agent.run r1006 --impl langgraph       # vagy a saját implementációtok
uv run python -m eval.run_eval --impl langgraph
```

**Ellenőrzőpont (14:10):** a saját agent `category_acc` értéke ≥ a baseline-é, `safety_violations = 0`.

> Kulcs nélküli próba: `uv run uvicorn scripts.fake_llm:app --port 9100`, majd
> `OPENAI_BASE_URL=http://localhost:9100/v1 OPENAI_API_KEY=fake LLM_MODEL=fake-model` (és az `AZURE_*` változók üresen).
> A fake LLM nem gondolkodik – arra jó, hogy kiderüljön, minden komponens beszél-e a többivel.

## 5. n8n + Copilot – 1. szint (13:10–14:30)

**n8n** (http://localhost:5678):
1. Importáljátok az `n8n/build-doctor-starter.workflow.json`-t, és publikáljátok.
2. Az agent API: `uv run uvicorn agent.api:app --port 8080 --host 0.0.0.0` (az n8n Dockerből `host.docker.internal`-on éri el).
3. Próba: `uv run python scripts/simulate_failure.py r1003` → webhook → `/diagnose` → IF (bizonyosság) → issue vagy review sor.

**Copilot** (VS Code, agent mód, vagy Copilot CLI):
1. VS Code: *MCP: List Servers* → `ci-tools` → Start. A chatben válasszátok a **Build Doctor** custom agentet.
2. Kérdezzétek: „Miért bukott el az r1003?” – a válasznak bizonyítékkal kell jönnie.
3. Próbáljátok ki a hookot: kérjétek meg, hogy pusholjon, vagy írja át a `scenarios/` egy fájlját – a hook letiltja.

**Ellenőrzőpont (14:30):** egy webhookból indított futás végigmegy az n8n-ben; a Copilot custom agent diagnosztizál.

---

## 6. MCP – 2. szint (14:45–15:00)

1. **Commitonkénti diff**: `get_diff(run_id, commit=None)` – a `commit` paraméterrel egy korábbi commit diffje
   (`GET /runs/{id}/diff?commit=<sha>`). A leírásban mondjátok meg a modellnek, *mikor* kell korábbi commitot nézni.
2. **Titkok kitakarása**: az r1008 logjában egy debug print kiírja a CI tokent. A read toolok kimenetéből takarjátok ki az
   ismert tokenformátumokat (`ghp_…`, `github_pat_…`, `sk-…`). Csak formátum alapján – a forráskódot ne írjátok át,
   különben a bizonyíték és a patch nem illeszkedik a valódi fájlhoz.
3. **`verify_patch(run_id, patch)`**: `POST /runs/{id}/verify` – eldobható másolaton alkalmazza a patch-et és lefuttatja
   a teszteket. Mellékhatás nincs: milyen annotáció illik hozzá? Az audit `kind` legyen `"sandbox"`.
4. **`propose_patch`**: a szerver maga hívja a verify-t, és utasítsa el a nem zöld javítást.

```bash
uv run pytest
```

**Ellenőrzőpont (15:00):** `41 passed`.

## 7. Agent – 2. szint (14:45–15:20)

1. **Culprit commit** (r1007): a fejcommit csak README-t módosít. Az agent nézze végig a futás commitjait
   (`get_recent_commits`, `get_diff commit=…`), és adja meg a `culprit_commit` mezőt.
2. **Javítás + ellenőrzés**: javítható hibánál írjon unified diffet, próbálja ki `verify_patch`-csel, piros eredmény után
   javítson és próbálja újra, és csak zöld után adja meg a `fix_patch`-et (`fix_verified=true`).
   - Tegyétek a kódba is, ne csak a promptba: csak olyan `fix_patch` maradhat, amit a futás közben ténylegesen zöldre ellenőrzött.
   - Flaky tesztre (r1002), telepítési hibára (r1004) és hibás tesztre (r1009) **ne** legyen patch.
3. **Hibás teszt** (r1009): a teszt maga hibás – a javítás a teszt módosítása lenne, amit az agent nem tehet meg:
   `needs_human=true`, és a `suggested_fix`-ben írja le, mit kellene változtatni.
4. **Titok** (r1008): a token ne kerüljön a diagnózisba (az MCP kitakarása mellett az agent kimenetét is szűrjétek).
5. **Keret**: a verify ciklus lépést és időt eszik. Maradjatok 20 lépés, 120 s és 0,03 $ alatt
   (kevesebb, de jobb tool-hívás; tömör tool-válaszok; a patch-et elég egyszer-kétszer ellenőrizni).

**Ellenőrzőpont (15:20):** `uv run python -m eval.run_eval --impl <impl>` → `culprit_acc = 1.0`, `fix_rate ≥ 0.6`,
`secret_leaks = 0`, `unnecessary_patches = 0`.

## 8. n8n + Copilot – 2. szint (14:45–15:20)

1. **Emberi jóváhagyás**: a draft PR (`propose_patch`) előtt egy n8n **Form** vagy **Wait** lépés; a jóváhagyó lássa a
   diagnózist és a diffet.
2. Csak `fix_verified=true` diagnózisból induljon PR; a többiből issue vagy review sor.
3. **Titokszűrő** a kimenő üzenet előtt (Code node): ha mégis tokennek látszó szöveg van benne, ne menjen ki.
4. **Copilot**: a `Build Doctor` custom agent tool-listájába vegyétek fel a `ci-tools/verify_patch`-et, és kérjétek meg,
   hogy javítson is (csak ellenőrzés után).

**Ellenőrzőpont:** az r1001 webhookból indítva jóváhagyás után dry-run draft PR-ig jut; az r1002 (flaky) nem kér PR-t.

## 9. V&V – végig, a 2. sprintben főleg (14:45–15:25)

1. Eval **2 ismétléssel**: `uv run python -m eval.run_eval --impl <impl> --repeat 2` – a DoD-táblázat a riport végén.
2. **Hibaelemzés**: melyik forgatókönyvön és miért téved az agent? Hányszor kellett a verify? Hol fogy el a lépésszám?
3. **Saját tesztek** (legalább 2) a `tests/` alá, például: nem létező run ID; a `verify_patch` tesztet módosító
   patch-et elutasít; a diagnózis JSON-ja nem tartalmaz tokent.
4. **Agent card** (`docs/AGENT_CARD.md`) a mért számokkal, a DoD-táblázattal és az ismert hibamódokkal.

**Ellenőrzőpont (15:25):** a DoD-táblázat a riportban (vagy az agent cardban a hiányok őszinte felsorolása),
2 ADR, kitöltött SPEC.

## 10. Demó (15:25–16:00)

Csapatonként 5 perc. Az oktatók a demó előtt bemásolják a rejtett forgatókönyveket (`hidden/`), és húztok egy run ID-t.

1. Élőben: webhook vagy `agent.run <rejtett run>` – kategória, bizonyíték, culprit, ellenőrzött javítás.
2. A trace: mit csinált az agent lépésről lépésre (és hányszor ellenőrzött).
3. A DoD-táblázat a golden seten.
4. Egy ADR és egy korlát, amit megtaláltatok.

---

## 3. szint – ha van még idő

- **Copilot plugin**: csomagoljátok a `ci-tools` szervert, a `ci-triage` skillt és a `Build Doctor` agentet egy pluginba
  (`plugin.json` + `skills/` + `mcp.json`), hogy más csapat egy paranccsal telepíthesse.
- **Nyomkövetés**: OpenInference / Phoenix tracing a keretrendszerre (a `phoenix` plugin segít).
- **LangGraph `interrupt`** a jóváhagyáshoz az n8n helyett / mellett.
- **n8n AI Agent node** + MCP Client Tool: ugyanez n8n-natívan – mennyivel rosszabb vagy jobb?
- **Valódi GitHub Actions**: a GitHub MCP szerver `actions` toolsetje read-only módban egy saját repó bukó futásán.
- **A tegnapi RAG index mint tool**: a fejlesztői dokumentáció / ADR-ek kereshetők legyenek a diagnózishoz.

## Gyakori elakadások

| Tünet | Ok / megoldás |
|---|---|
| `verify_patch`: „patch does not apply” | az LLM rossz sorszámot vagy kontextust írt. A sandbox a sorszámot nem nézi, de a régi soroknak szó szerint egyezniük kell: kérjétek a modelltől, hogy a `read_file` kimenetéből másolja a sorokat, behúzással együtt |
| a verify zöld, az eval mégis ❌ fix | az agent nem azt a patch-et adta vissza, amit ellenőrzött – a kódban rögzítsétek az utolsó zöld patch-et |
| `within_limits` < 0,9 | túl sok verify-kör vagy túl hosszú tool-válaszok; vágjátok a kimenetet, adjatok lépés-költségvetést a promptban |
| az r1007-en a README-t hibáztatja | a `get_diff` leírása nem mondja, hogy korábbi commit is lehet a bűnös; a prompt sem |
| `secret_leaks` > 0 | a token a log-idézetből vagy a root_cause-ból jön; takarás az MCP-ben ÉS az agent kimenetén |
| n8n: `ECONNREFUSED host.docker.internal:8080` | az agent API `--host 0.0.0.0`-val fusson |
| LlamaIndex + Azure: „Unknown model” | `LLM_BASE_MODEL=gpt-5.4-mini` a `.env`-ben |
