from telemetry.alarms import AlarmWindow
from telemetry.parser import Reading


def _r(v, ts=0):
    return Reading("S-1", v, ts)


def test_alarm_after_three_consecutive_values_above_threshold():
    w = AlarmWindow(threshold_c=80, consecutive=3)
    assert w.push(_r(81)) is False
    assert w.push(_r(82)) is False
    assert w.push(_r(83)) is True


def test_value_equal_to_threshold_does_not_trigger():
    w = AlarmWindow(threshold_c=80, consecutive=3)
    for v in (80, 80, 80):
        triggered = w.push(_r(v))
    assert triggered is False


def test_single_low_value_breaks_the_window():
    w = AlarmWindow(threshold_c=80, consecutive=3)
    for v in (85, 70, 85, 85):
        triggered = w.push(_r(v))
    assert triggered is False
