"""Duplikált mérések szűrése (ugyanaz a szenzor, ugyanaz az időbélyeg)."""
from .parser import Reading


def dedupe(readings: list[Reading]) -> list[Reading]:
    """Megtartja az első előfordulást, a sorrendet megőrzi. O(n)."""
    out: list[Reading] = []
    for r in readings:
        if any(o.sensor_id == r.sensor_id and o.ts == r.ts for o in out):
            continue
        out.append(r)
    return out
