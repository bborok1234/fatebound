"""렌더 유틸 — 스파이크 검증분 이식: 하프블록 스프라이트(상태 침식)·이름 물듦·게이지.
ANSI 문자열을 생산하고 rich Text.from_ansi로 Textual에 올린다(스파이크 코드 재사용)."""
from __future__ import annotations

import random

from .. import theme as T

R = "\x1b[0m"


def fg(c): return f"\x1b[38;2;{c[0]};{c[1]};{c[2]}m"
def bg(c): return f"\x1b[48;2;{c[0]};{c[1]};{c[2]}m"


# 죽림 산적 (sprite_spike 검증 그리드)
BANDIT = """
.....KKKKK......
....KSSSSSK.....
....KSWSWSK.....
....KSSSSSK.....
.....KSSSK......
....RRRRRRR.....
...RRBBBBBRR....
..RR.BBBBB.RR...
..H..BBBBB..H...
.....BBBBB......
....BB...BB.....
....BB...BB.....
...LL.....LL....
...LL.....LL....
..FF.......FF...
""".strip().splitlines()
BANDIT_PAL = dict(K=(60, 45, 30), S=(225, 180, 140), W=(20, 20, 20), R=(140, 50, 40),
                  B=(90, 70, 50), H=(190, 190, 200), L=(70, 55, 70), F=(50, 40, 35))

VIPER = """
......GGG.......
....GGYYYGG.....
...GY.W.W.YG....
...GYYYYYYYG....
....GGYYYGG.....
......GYG.......
......GYG.......
.....GYG........
....GYG.........
...GYG..........
..GYG...........
.GYYG...........
.GYYYG..........
..GGGG..........
""".strip().splitlines()
VIPER_PAL = dict(G=(70, 140, 60), Y=(150, 200, 90), W=(230, 60, 50))

SPRITES = {"죽림 산적": (BANDIT, BANDIT_PAL), "청죽 살모사": (VIPER, VIPER_PAL)}


def sprite(name: str, poison: int = 0, seed: int = 3) -> list[str]:
    """하프블록 렌더 + 중독 침식(sprite_spike 검증 문법)."""
    grid, pal = SPRITES.get(name, (BANDIT, BANDIT_PAL))
    rng = random.Random(seed)
    w = max(len(r) for r in grid)
    grid = [r.ljust(w, ".") for r in grid]
    if len(grid) % 2:
        grid = grid + ["." * w]
    px = {}
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            c = pal.get(ch, (255, 0, 255))
            if poison and rng.random() < poison * 0.13:
                c = (int(c[0] * 0.3), 200, int(c[2] * 0.3))
            px[(x, y)] = c
    out = []
    for y in range(0, len(grid), 2):
        line = ""
        for x in range(w):
            t_, b_ = px.get((x, y)), px.get((x, y + 1))
            if t_ and b_:
                line += fg(t_) + bg(b_) + "▀" + R
            elif t_:
                line += fg(t_) + "▀" + R
            elif b_:
                line += fg(b_) + "▄" + R
            else:
                line += " "
        out.append(line)
    return out


def tinted_name(name: str, stacks: float, mx: int = 6) -> str:
    """이름 글자 단위 채색 — 중독 물듦(확정 상시 연출)."""
    out = ""
    for i, ch in enumerate(name):
        k = max(0.0, min(1.0, (stacks - i * mx / max(1, len(name))) / 2.0))
        out += fg(T.lerp(T.INK, T.POISON, k)) + ch
    return out + R


def hp_bar(cur: int, mx: int, width: int = 16, col=(150, 60, 55)) -> str:
    f = int(width * cur / mx) if mx else 0
    return fg(col) + "█" * f + fg((60, 55, 50)) + "░" * (width - f) + R


def gauge(cur: int, mx: int = 6, filled: str = "▮", empty: str = "▯") -> str:
    return filled * min(cur, mx) + empty * max(0, mx - cur)


def dots(cur: float, mx: int = 6) -> str:
    n = min(int(cur), mx)
    return (fg(T.POISON) + "●" * n) + fg(T.DIM) + "○" * (mx - n) + R
