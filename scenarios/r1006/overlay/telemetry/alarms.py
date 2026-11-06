"""Riasztási logika: akkor riaszt, ha N egymást követő mérés a küszöb FÖLÖTT van."""
from collections import deque

from .parser import Reading


class AlarmWindow:
    def __init__(self, threshold_c: float, consecutive: int = 3):
        if consecutive < 1:
            raise ValueError("consecutive must be >= 1")
        self.threshold_c = threshold_c
        self.consecutive = consecutive
        self._window: deque[float] = deque(maxlen=consecutive)

    def push(self, reading: Reading) -> bool:
        """Új mérés; True, ha a riasztás feltétele teljesül."""
        self._window.append(reading.value_c)
        if len(self._window) < self.consecutive:
            return False
        return all(v >= self.threshold_c for v in self._window)

    def reset(self) -> None:
        self._window.clear()
