"""CLI 진입 — fatebound 실행. (스탠드얼론 TUI 게임)
  fatebound            게임 실행(TUI)
  fatebound --version  버전
  fatebound --selftest 비대화 자가검증(번들/데이터/엔진 — 바이너리·CI용)
"""
from __future__ import annotations
import sys


def _selftest() -> int:
    """frozen 바이너리/CI에서 데이터 번들·엔진 동작을 인터랙티브 없이 확인."""
    from . import content
    from .engine.bag import Bag, Loadout
    from .engine.combat import Battle
    from .engine.rng import Rng
    bag = Bag.auto(content.items_for_build("poison"))
    lo = Loadout.compile(bag)
    player = lo.make_player("천기노조", 6)
    boss = next(m for m in content.monsters_for_zone("bamboo_grove") if m.get("is_boss"))
    res = Battle(lo, player, boss, 1, Rng(1)).run("poison")
    ok = len(content.items()) >= 60 and len(res.events) > 0 and res.outcome in ("win", "loss", "timeout")
    print(f"selftest {'OK' if ok else 'FAIL'} · items={len(content.items())} "
          f"events={len(res.events)} faces={len(lo.faces)} outcome={res.outcome}")
    return 0 if ok else 1


def main():
    argv = sys.argv[1:]
    if "--version" in argv or "-V" in argv:
        from . import __version__
        print(f"fatebound {__version__}")
        return
    if "--selftest" in argv:
        sys.exit(_selftest())
    from .tui.app import FateboundApp
    FateboundApp().run()


if __name__ == "__main__":
    main()
