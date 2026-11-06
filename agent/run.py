"""Parancssori futtatás:  python -m agent.run r1001 [--impl langgraph]"""
import argparse
import asyncio
import json
from dataclasses import asdict

from .impls import get_diagnose


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("--impl", default=None)
    a = ap.parse_args()
    diag, trace = asyncio.run(get_diagnose(a.impl)(a.run_id))
    print(json.dumps({"diagnosis": diag.model_dump(), "trace": asdict(trace)}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
