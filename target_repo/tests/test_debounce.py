import time

from telemetry.debounce import Debouncer


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_debounce_switches_after_hold_time():
    clock = FakeClock()
    d = Debouncer(hold_s=1.0, clock=clock)
    assert d.update(True) is False
    clock.t = 0.5
    assert d.update(True) is False
    clock.t = 1.1
    assert d.update(True) is True


def test_debounce_ignores_short_glitch_real_clock():
    d = Debouncer(hold_s=0.2)
    d.update(True)
    time.sleep(0.05)
    assert d.update(True) is False, "a 0,2 s-os tartási idő előtt nem válthat állapotot"
