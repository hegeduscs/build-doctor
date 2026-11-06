"""Szenzorkeretek parszolása.

Keretformátum (pontosvesszővel tagolt):  <sensor_id>;<value>;<unit>;<unix_ts>
Példa:  S-017;23.5;C;1730000000
"""
from dataclasses import dataclass

from .units import normalize_temperature


@dataclass(frozen=True)
class Reading:
    sensor_id: str
    value_c: float
    ts: int


class FrameError(ValueError):
    pass


def parse_frame(frame: str) -> Reading:
    parts = frame.strip().split(";")
    if len(parts) != 4:
        raise FrameError(f"expected 4 fields, got {len(parts)}: {frame!r}")
    sensor_id, raw_value, unit, raw_ts = parts
    if not sensor_id:
        raise FrameError("empty sensor id")
    try:
        value = float(raw_value)
        ts = int(raw_ts)
    except ValueError as exc:
        raise FrameError(f"bad number in frame {frame!r}") from exc
    return Reading(sensor_id=sensor_id, value_c=normalize_temperature(value, unit), ts=ts)


def parse_batch(frames: list[str]) -> list[Reading]:
    return [parse_frame(f) for f in frames if f]
