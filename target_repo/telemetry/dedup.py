"""Duplikált mérések szűrése (ugyanaz a szenzor, ugyanaz az időbélyeg)."""
from .parser import Reading


def dedupe(readings: list[Reading]) -> list[Reading]:
    """Megtartja az első előfordulást, a sorrendet megőrzi. O(n)."""
    seen: set[tuple[str, int]] = set()
    out: list[Reading] = []
    for r in readings:
        key = (r.sensor_id, r.ts)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
