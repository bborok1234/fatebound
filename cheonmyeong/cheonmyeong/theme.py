"""테마 — 아트 디렉션 「어스름과 채색」 (5권 03 §0 정본).
먹남색 캔버스 · 고채도 채색 · 어스름(채도 25%·밝기 42%) · 포인트 레드 한 줌."""
from __future__ import annotations

import sys

CANVAS = (15, 19, 29)            # 먹남색
INK = (210, 200, 180)            # 본문
DIM = (120, 115, 100)            # 보조
GOLD = (200, 180, 140)           # 화자·보상
SEAL = (240, 80, 64)             # 포인트 레드(나·벽·긴급)
CHIP = (30, 36, 52)              # 라벨 칩
POISON = (95, 210, 100)          # 독계
AMBER = (255, 210, 120)          # 임계·충전

SERIES_COLOR = {                  # 계열 7색 (03 §0)
    "검": (190, 215, 240), "도": (220, 90, 90), "창": (220, 200, 130),
    "권장": (200, 160, 110), "독": (95, 210, 100), "내공": (180, 140, 220),
    "기문": (130, 190, 230),
}


def tier() -> int:
    """T1 강제 플래그(--tier=1) 또는 T2+ 가정 (감지 정교화는 본 구현)."""
    return 1 if "--tier=1" in sys.argv else 2


def hexc(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def dusk(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """어스름 — 채도 25%·밝기 42% (미답·미수집·미감정 공통 상태)."""
    g = sum(rgb) / 3
    de = tuple(g + (c - g) * 0.25 for c in rgb)
    return tuple(int(c * 0.42) for c in de)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
