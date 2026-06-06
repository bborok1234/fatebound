"""M1 배치 분석 — 최적/그리디 배치 + 깊이 측정 (doc 27 P7).

용도 둘:
  1) 다양성 게이트(테스트): 배치가 출력을 의미있게 바꾸되(라이트 텔레그래프 가치) '1초 소트'는 아님을 락인.
  2) 라이트 자동배치 추천(P6 플로어 올리기): smart_greedy/optimal을 UI가 제안.
순수 결정론(random 미사용) — 헤드리스, import-linter clean.
"""
from __future__ import annotations
import itertools

from .combat_m1 import cell_eff, _m1


def build_output(cells, scale):
    """배치된 9무공의 합당 출력(스폿라이트 전) = Σ cell_eff."""
    return sum(cell_eff(cells, i, scale) for i in range(9))


def optimal_arrangement(cells, scale, method="hill", restarts=24):
    """최적(또는 근사) 배치 순열. method='enum'=전수 9!(정확·느림), 'hill'=결정론 언덕오르기(빠름)."""
    if method == "enum":
        return list(max(itertools.permutations(cells), key=lambda a: build_output(list(a), scale)))
    best, best_out = None, -1.0
    n = len(cells)
    for r in range(restarts):
        arr = list(cells[r % n:] + cells[:r % n])     # 결정론 시작(회전 — random 없이 다양 시작점)
        improved = True
        while improved:
            improved = False
            cur = build_output(arr, scale)
            for i in range(9):
                for j in range(i + 1, 9):
                    arr[i], arr[j] = arr[j], arr[i]
                    if build_output(arr, scale) > cur + 1e-9:
                        cur = build_output(arr, scale); improved = True
                    else:
                        arr[i], arr[j] = arr[j], arr[i]
        o = build_output(arr, scale)
        if o > best_out:
            best, best_out = list(arr), o
    return best


def naive_greedy(cells):
    """라이트가 1초에 푸는 무브: 최고 base를 중앙(4), 나머지 원순서."""
    base = lambda it: (_m1(it) or {}).get("base", 0)
    order = sorted(range(9), key=lambda i: -base(cells[i]))
    arr = [None] * 9
    arr[4] = cells[order[0]]
    for s, i in zip([0, 1, 2, 3, 5, 6, 7, 8], order[1:]):
        arr[s] = cells[i]
    return arr


def smart_greedy(cells):
    """영리한 휴리스틱: 페이로드는 고배수 칸(중앙), 증폭기는 중앙 인접(중앙십자), 나머지 코너."""
    base = lambda it: (_m1(it) or {}).get("base", 0)
    amp = lambda it: (_m1(it) or {}).get("amp", 0)
    payloads = sorted([c for c in cells if base(c) > 0], key=lambda c: -base(c))
    amps = sorted([c for c in cells if amp(c) > 0 and base(c) <= 0], key=lambda c: -amp(c))
    others = [c for c in cells if base(c) <= 0 and amp(c) <= 0]
    arr = [None] * 9
    pool = list(payloads)
    if pool:
        arr[4] = pool.pop(0)                           # 최강 페이로드 = 중앙(×1.5)
    ai = 0
    for s in (1, 3, 5, 7):                              # 증폭기 = 중앙십자
        if ai < len(amps):
            arr[s] = amps[ai]; ai += 1
    for s in (0, 2, 6, 8):                              # 나머지 페이로드 = 코너
        if pool:
            arr[s] = pool.pop(0)
    leftovers = pool + amps[ai:] + others
    for s in range(9):
        if arr[s] is None and leftovers:
            arr[s] = leftovers.pop(0)
    return arr


def placement_depth(cells, scale, method="hill"):
    """배치 깊이 리포트: 최적 vs 단순/영리 그리디 출력 격차(%)."""
    opt = build_output(optimal_arrangement(cells, scale, method), scale)
    naive = build_output(naive_greedy(cells), scale)
    smart = build_output(smart_greedy(cells), scale)
    return {
        "optimal": opt, "naive_greedy": naive, "smart_greedy": smart,
        "gap_vs_naive": (opt - naive) / opt * 100 if opt else 0.0,
        "gap_vs_smart": (opt - smart) / opt * 100 if opt else 0.0,
    }
