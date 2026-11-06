"""Egy elbukott CI futás webhook-értesítésének szimulálása az n8n felé.

  python scripts/simulate_failure.py r1001
  python scripts/simulate_failure.py r1001 --test      # az n8n szerkesztő "Listen for test event" URL-je
"""
import argparse

import httpx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("--n8n", default="http://localhost:5678")
    ap.add_argument("--path", default="ci-failed")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    url = f"{a.n8n}/{'webhook-test' if a.test else 'webhook'}/{a.path}"
    payload = {"event": "workflow_run.failed", "run_id": a.run_id, "repo": "evopro-training/telemetry-ingest"}
    r = httpx.post(url, json=payload, timeout=200)
    print(r.status_code, r.text[:2000])


if __name__ == "__main__":
    main()
