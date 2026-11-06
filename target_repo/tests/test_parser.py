import pytest

from telemetry.parser import FrameError, parse_batch, parse_frame


def test_parse_frame_celsius():
    r = parse_frame("S-017;23.5;C;1730000000")
    assert r.sensor_id == "S-017"
    assert r.value_c == pytest.approx(23.5)
    assert r.ts == 1730000000


def test_parse_frame_fahrenheit_is_normalized():
    r = parse_frame("S-001;212;F;1730000001")
    assert r.value_c == pytest.approx(100)


def test_parse_frame_rejects_short_frame():
    with pytest.raises(FrameError):
        parse_frame("S-017;23.5;C")


def test_parse_batch_skips_empty_lines():
    out = parse_batch(["S-1;1;C;1", "", "  ", "S-2;2;C;2"])
    assert [r.sensor_id for r in out] == ["S-1", "S-2"]
