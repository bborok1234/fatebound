"""천명회귀 — 앱 셸 (5권 01 §6.5: alt screen 전용 화면 + 종료 시 메인 버퍼 박제)."""
from __future__ import annotations

from textual.app import App

from . import theme as T
from .engine.state import GameState
from .screens.opening import OpeningScreen


class Cheonmyeong(App):
    CSS = f"""
    Screen {{ background: {T.hexc(T.CANVAS)}; }}
    #hud {{ height: auto; }}
    #log {{ background: {T.hexc(T.CANVAS)}; border: none; }}
    #voice, #hints {{ height: 1; }}
    """
    TITLE = "천명회귀"
    summary: dict | None = None

    def __init__(self):
        super().__init__()
        self.state = GameState()

    def on_mount(self) -> None:
        self.push_screen(OpeningScreen())


def main() -> None:
    app = Cheonmyeong()
    app.run()
    # ── 종료 박제 — 떠난 자리에 기록이 남는다 (정본 01 §6.5·03 §0.5) ──
    s = app.summary
    D = f"\x1b[38;2;{T.DIM[0]};{T.DIM[1]};{T.DIM[2]}m"
    I = f"\x1b[38;2;{T.INK[0]};{T.INK[1]};{T.INK[2]}m"
    G = f"\x1b[38;2;{T.GOLD[0]};{T.GOLD[1]};{T.GOLD[2]}m"
    R = "\x1b[0m"
    if s:
        st = app.state
        front = "죽림·흑풍림" if "흑풍림" in st.explored else "죽림"
        nxt = "일류(한천비곡 길목)" if "흑풍림" in st.explored else "이류의 벽"
        print(f"{D} ┌─ 강호행 기록 ──────────────────────────────┐{R}")
        print(f"{D} │ {I}{st.day-1}일의 강호행 — {st.gyeongji} {st.star}성 · 전투 {st.battles_won}승{D}        │{R}")
        print(f"{D} │ 전선: {G}{front}{R}{D} / 다음 벽: {nxt}{D}              │{R}")
        print(f"{D} │ {G}천기노조{R}{D} — 몸은 풋내기여도 독은 늙지 않았다.   │{R}")
        print(f"{D} └────────────────────────────────────────────┘{R}")
    else:
        print(f"{D} (강호행 기록 없음 — 다음에)"+R)


if __name__ == "__main__":
    main()
