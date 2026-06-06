"""시드 PRNG — 모든 무작위는 여기로(결정론·재현·서버 권위 대비, 20 §4)."""
from __future__ import annotations
import random


class Rng:
    def __init__(self, seed: int | None = None):
        self._r = random.Random(seed)
        self.seed = seed

    def roll(self, n: int) -> int:
        """0..n-1 균등."""
        return self._r.randrange(n)

    def chance(self, pct: float) -> bool:
        """pct(%) 확률로 True."""
        return self._r.random() * 100.0 < pct

    def choice(self, seq):
        return self._r.choice(seq)

    def shuffle(self, seq):
        self._r.shuffle(seq)
        return seq

    def randint(self, a: int, b: int) -> int:
        return self._r.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        return self._r.uniform(a, b)
