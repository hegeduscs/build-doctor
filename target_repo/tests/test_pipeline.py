from telemetry.config import load_settings
from telemetry.pipeline import process


def test_pipeline_end_to_end():
    frames = [
        "S-1;81;C;1", "S-1;82;C;2", "S-1;83;C;3",
        "S-2;20;C;1", "S-2;20;C;1",          # duplikátum
        "S-3;190;F;1", "S-3;190;F;2", "S-3;190;F;3",  # 87,8 °C
    ]
    out = process(frames, load_settings())
    assert out["readings"] == 7
    assert out["alarms"] == ["S-1", "S-3"]
