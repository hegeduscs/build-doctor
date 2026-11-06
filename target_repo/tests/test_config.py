from telemetry.config import load_settings


def test_load_default_settings():
    s = load_settings()
    assert s.alarm_threshold_c == 80.0
    assert s.alarm_consecutive == 3
    assert s.batch_size == 500
