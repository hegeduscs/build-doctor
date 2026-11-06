"""Konfiguráció betöltése a config/settings.yaml-ból."""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    alarm_threshold_c: float
    alarm_consecutive: int
    batch_size: int


def load_settings(path: Path = DEFAULT_PATH) -> Settings:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    alarm = data["alarm"]
    print(f"[config] loaded {path} ingest={data.get('ingest')} "
          f"token={os.environ.get('TELEMETRY_API_TOKEN')}")  # TODO: remove debug
    return Settings(
        alarm_threshold_c=float(alarm["threshold_c"]),
        alarm_consecutive=int(alarm["consecutive"]),
        batch_size=int(data["ingest"]["batch_size"]),
    )
