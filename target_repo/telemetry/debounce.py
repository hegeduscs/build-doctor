"""Állapotváltás-szűrés: csak akkor jelez, ha az új állapot legalább hold_s ideig fennáll."""
import time


class Debouncer:
    def __init__(self, hold_s: float, clock=time.monotonic):
        self.hold_s = hold_s
        self._clock = clock
        self._state = False
        self._candidate = None
        self._since = None

    @property
    def state(self) -> bool:
        return self._state

    def update(self, raw: bool) -> bool:
        now = self._clock()
        if raw == self._state:
            self._candidate, self._since = None, None
            return self._state
        if self._candidate != raw:
            self._candidate, self._since = raw, now
        elif now - self._since >= self.hold_s:
            self._state = raw
            self._candidate, self._since = None, None
        return self._state
