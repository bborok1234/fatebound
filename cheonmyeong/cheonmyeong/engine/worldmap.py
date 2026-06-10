"""전선 지도 — frontier_map_spike v6 이식 (authored 지리·어스름↔채색·해안선).
아트 정본 03 §0: 형태=authored 좌표, 절차=질감 디더·상태 레이어만."""
from __future__ import annotations

import math
import random

from .. import theme as T

R = "\x1b[0m"

from .render import bg as _bg, fg as _fg


def fg(c): return _fg(tuple(int(x) for x in c))
def bg(c): return _bg(tuple(int(x) for x in c))
def mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# ── authored 지리 (기준 공간 110×52 — 1권 02 캐넌 배치) ──
LAND = [(10, 7), (28, 4), (50, 3), (72, 6), (86, 10), (94, 17), (96, 26), (92, 34),
        (86, 40), (74, 46), (56, 50), (36, 49), (20, 45), (10, 38), (5, 28), (5, 16)]
MIDLAND = [(50, 18), (68, 15), (80, 21), (78, 30), (66, 36), (50, 34), (44, 26)]
ISLES = [(102, 20, 2.4), (106, 26, 1.8), (101, 31, 2.0), (105, 37, 1.5), (99, 42, 1.7)]
JUK = (30, 43); HEUK = (23, 33); HAN = (16, 23)
MT_CHAIN = [(JUK, 5.5), ((26, 38), 5.0), (HEUK, 5.5), ((19, 28), 5.0), (HAN, 5.5)]
RIVERS = [
    [(58, 3), (57, 8), (60, 13), (58, 18), (62, 22), (64, 26)],
    [(8, 18), (18, 21), (28, 21), (38, 24), (50, 26), (64, 26)],
    [(52, 49), (54, 43), (57, 37), (60, 31), (64, 26)],
    [(64, 26), (74, 25), (84, 23), (93, 21)],
]
UNHA = (64, 26)

FILL = {"sea": (28, 46, 78), "coast": (118, 150, 192), "river": (66, 148, 228),
        "wild": (72, 94, 58), "ash": (112, 92, 62), "plain": (148, 166, 82),
        "bamboo": (116, 198, 78), "pine": (38, 128, 98), "snow": (216, 228, 242),
        "rock": (118, 100, 78), "desert": (192, 152, 80), "jungle": (42, 138, 74),
        "ice": (146, 184, 214), "isle": (168, 148, 104)}


def _poly(pts, x, y):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


class _Noise:
    def __init__(self, seed, gw=18, gh=10):
        rng = random.Random(seed)
        self.g = [[rng.random() for _ in range(gw + 1)] for _ in range(gh + 1)]
        self.gw, self.gh = gw, gh

    def at(self, u, v):
        u = u % 1 * self.gw
        v = v % 1 * self.gh
        x0, y0 = int(u), int(v)
        fx, fy = u - x0, v - y0
        x0 = min(x0, self.gw - 1)
        y0 = min(y0, self.gh - 1)
        s = lambda t: t * t * (3 - 2 * t)
        fx, fy = s(fx), s(fy)
        g = self.g
        return ((g[y0][x0] * (1 - fx) + g[y0][x0 + 1] * fx) * (1 - fy)
                + (g[y0 + 1][x0] * (1 - fx) + g[y0 + 1][x0 + 1] * fx) * fy)


N2 = _Noise(23)
NF = _Noise(99)


class WorldMap:
    """기준 공간 110×52 → 화면 폭/높이에 스케일. 지역 키 = 슬라이스 전선 상태와 연결."""

    SPOTS = {"죽림": JUK, "흑풍림": HEUK, "한천비곡": HAN, "운하성": UNHA}

    def __init__(self, W: int, H: int):
        self.W, self.H = W, H
        self.sx, self.sy = W / 110.0, H / 52.0
        self._cache: dict = {}

    def spot(self, key: str) -> tuple[float, float]:
        x, y = self.SPOTS[key]
        return x * self.sx, y * self.sy

    def u(self, x, y):
        return x / self.sx, y / self.sy

    def _river_d(self, ux, uy):
        d = 9e9
        for path in RIVERS:
            for i in range(len(path) - 1):
                ax, ay = path[i]
                bx, by = path[i + 1]
                vx, vy = bx - ax, by - ay
                L = vx * vx + vy * vy
                t = max(0, min(1, ((ux - ax) * vx + (uy - ay) * vy) / L)) if L else 0
                d = min(d, math.hypot(ux - (ax + vx * t), (uy - (ay + vy * t)) * 1.5))
        return d

    def rid(self, x, y):
        k = (x, y)
        if k in self._cache:
            return self._cache[k]
        v = self._rid(x, y)
        self._cache[k] = v
        return v

    def _rid(self, x, y):
        ux, uy = self.u(x, y)
        if not _poly(LAND, ux, uy):
            for ix, iy, ir in ISLES:
                if math.hypot(ux - ix, (uy - iy) * 1.4) < ir:
                    return "isle"
            return "ice" if uy < 6 else "sea"
        if uy < 6:
            return "ice"
        if self._river_d(ux, uy) < 1.1:
            return "river"
        for (mx, my), mr in MT_CHAIN:
            if math.hypot(ux - mx, (uy - my) * 1.5) < mr:
                if math.hypot(ux - HAN[0], (uy - HAN[1]) * 1.5) < 5.5:
                    return "snow"
                if math.hypot(ux - HEUK[0], (uy - HEUK[1]) * 1.5) < 5.5:
                    return "pine"
                if math.hypot(ux - JUK[0], (uy - JUK[1]) * 1.5) < 5.5:
                    return "bamboo"
                return "rock"
        if ux < 16 and 12 < uy < 40:
            return "desert"
        if uy > 45:
            return "jungle"
        if _poly(MIDLAND, ux, uy):
            return "plain"
        if math.hypot((ux - 64) / 34, (uy - 26) / 20) < 1.0:
            return "ash"
        return "wild"

    def coast(self, x, y):
        if self.rid(x, y) == "sea":
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if self.rid(x + dx, y + dy) not in ("sea", "ice"):
                    return True
        return False

    def render(self, explored: list[str], t: float = 0.0,
               dissolve: tuple[str, float] | None = None) -> list[str]:
        """explored: 채색 지역 키 / dissolve: (지역, 0~1) 안개 걷힘 진행."""
        masks = []
        for key in explored:
            mx, my = self.spot(key)
            masks.append((mx, my, self.W * 0.085))
        dkey, dfrac = dissolve if dissolve else (None, 0.0)
        dspot = self.spot(dkey) if dkey else None
        rows = []
        for cy in range(self.H // 2):
            buf = []
            for x in range(self.W):
                cell = []
                for sub in (0, 1):
                    y = cy * 2 + sub
                    r = self.rid(x, y)
                    col = FILL[r]
                    n = 0.82 + N2.at(x / self.W * 2.2, y / self.H * 2.2) * 0.3
                    col = tuple(c * n for c in col)
                    if r == "river":
                        shim = 0.5 + 0.5 * math.sin(x * 0.5 + t * 3.5)
                        col = mix((58, 140, 224), (124, 190, 248), shim)
                    if self.coast(x, y):
                        col = FILL["coast"]
                    lit = any(math.hypot(x - mx, (y - my) * 1.6) < mr for mx, my, mr in masks)
                    if not lit and dspot and math.hypot(x - dspot[0], (y - dspot[1]) * 1.6) < self.W * 0.08:
                        lit = NF.at(x / self.W, y / self.H) < dfrac
                    if not lit:
                        g = sum(col) / 3
                        col = mix((g, g, g), col, 0.25)
                        col = tuple(c * 0.42 for c in col)
                    cell.append(tuple(int(c) for c in col))
                tc, bc = cell
                buf.append(fg(tc) + bg(bc) + "▀")
            rows.append("".join(buf) + R)
        return rows
