import pytest

from telemetry.units import c_to_f, f_to_c, kpa_to_bar, normalize_temperature


def test_c_to_f_freezing_and_boiling():
    assert c_to_f(0) == 32
    assert c_to_f(100) == 212


def test_f_to_c_roundtrip():
    for c in (-40, 0, 21.5, 37.2, 100):
        assert f_to_c(c_to_f(c)) == c


def test_kpa_to_bar():
    assert kpa_to_bar(101.325) == pytest.approx(1.01325)


@pytest.mark.parametrize("value,unit,expected", [(25, "C", 25), (77, "F", 25), (298.15, "K", 25)])
def test_normalize_temperature(value, unit, expected):
    assert normalize_temperature(value, unit) == pytest.approx(expected)


def test_normalize_rejects_unknown_unit():
    with pytest.raises(ValueError):
        normalize_temperature(1, "X")
