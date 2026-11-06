"""Teljes feldolgozás: parszolás -> deduplikálás -> riasztás."""
from .alarms import AlarmWindow
from .config import Settings
from .dedup import dedupe
from .parser import parse_batch


def process(frames: list[str], settings: Settings) -> dict:
    readings = dedupe(parse_batch(frames))
    windows: dict[str, AlarmWindow] = {}
    alarms: list[str] = []
    for r in sorted(readings, key=lambda r: (r.sensor_id, r.ts)):
        w = windows.setdefault(r.sensor_id, AlarmWindow(settings.alarm_threshold_c, settings.alarm_consecutive))
        if w.push(r) and r.sensor_id not in alarms:
            alarms.append(r.sensor_id)
    return {"readings": len(readings), "alarms": alarms}
