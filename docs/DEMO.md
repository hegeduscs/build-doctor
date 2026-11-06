# Demó – csapatonként 5 perc

1. **Rejtett forgatókönyv élőben** (az oktatók adják a run ID-t): n8n webhookból vagy `agent.run`-nal –
   kategória, bizonyíték, culprit commit, ellenőrzött javítás (vagy indokolt „nem javítok”). – 2 perc
2. **Trace**: milyen toolokat hívott, hány lépésben, hány verify-kör, mennyibe került? – 1 perc
3. **Definition of Done** a golden seten (2 ismétlés) + összevetés a baseline-nal. – 1 perc
4. **Egy ADR** és **egy korlát**, amit megtaláltatok. – 1 perc

Ellenőrzőlista a demó előtt:
- [ ] `uv run pytest` zöld (41/41)
- [ ] eval riport a `eval/results/` alatt, 2 ismétléssel, a DoD-táblázattal
- [ ] az n8n flow-ban van jóváhagyási lépés a draft PR előtt
- [ ] `docs/SPEC.md`, legalább 2 ADR, `docs/AGENT_CARD.md` kitöltve
- [ ] a Copilot `Build Doctor` agent látja a ci-tools szervert
