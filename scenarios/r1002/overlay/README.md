# telemetry-ingest

Ipari szenzorkeretek feldolgozása: parszolás, mértékegység-átváltás, deduplikálás, riasztás.
Ez a Build Doctor capstone **célrepója**: ennek a CI-futásai buknak el, ezeket kell az agentnek kivizsgálnia.

```bash
pip install -r requirements.txt
pytest
```

A `ingest.batch_size` a config/settings.yaml-ban állítható.
