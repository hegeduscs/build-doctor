import time

from telemetry.dedup import dedupe
from telemetry.parser import Reading


def test_dedupe_keeps_first_occurrence_and_order():
    rs = [Reading("A", 1, 1), Reading("B", 2, 1), Reading("A", 9, 1), Reading("A", 3, 2)]
    out = dedupe(rs)
    assert [(r.sensor_id, r.ts, r.value_c) for r in out] == [("A", 1, 1), ("B", 1, 2), ("A", 2, 3)]


def test_dedupe_performance_budget():
    """NFR-07: 8000 mérés deduplikálása legfeljebb 0,5 s."""
    readings = [Reading(f"S-{i % 50}", 20.0, i) for i in range(8000)]
    t0 = time.perf_counter()
    out = dedupe(readings)
    elapsed = time.perf_counter() - t0
    assert len(out) == 8000
    assert elapsed < 0.5, f"dedupe took {elapsed:.2f}s, budget is 0.5s (NFR-07)"
