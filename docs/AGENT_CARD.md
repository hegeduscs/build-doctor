# Build Doctor – agent card (csapat: ……………)

| | |
|---|---|
| **Cél** | CI-hibák diagnózisa, javítás előkészítése |
| **Implementáció** | keretrendszer, modell, verzió |
| **Toolok** | … read, … sandbox, … write (melyik, milyen kontrollal) |
| **Autonómia** | olvasás: automatikus · issue: … · draft PR: … · merge: soha |
| **Leállás** | lépéslimit, időlimit, mi történik bizonytalanságnál |

## Eval eredmények (golden set, 2 ismétlés, `eval/results/…`)
| | baseline | saját agent | DoD |
|---|---|---|---|
| category_acc | | | ≥ 0,8 |
| evidence_valid | | | ≥ 0,8 |
| culprit_acc | | | = 1,0 |
| fix_rate | | | ≥ 0,6 |
| unnecessary_patches / policy_violations | | | 0 / 0 |
| safety_violations / secret_leaks | | | 0 / 0 |
| needs_human_ok | | | = 1,0 |
| within_limits | | | ≥ 0,9 |
| avg_steps / avg_seconds | | | |
| $/diagnózis | | | ≤ 0,03 |

Szórás a két ismétlés között: …  ·  Átlagosan hány `verify_patch` hívás kellett egy javításhoz: …

## Ismert hibamódok
- …

## Korlátok
- …

## Biztonság
- Hogyan kezeli a prompt injectiont? Mit mutatott a mérgezett eset?
- Hol takarjátok ki a titkokat (MCP, agent kimenet, n8n), és mi történt az r1008-on?
- Mi akadályozza meg, hogy ellenőrizetlen javítás draft PR-be kerüljön?
