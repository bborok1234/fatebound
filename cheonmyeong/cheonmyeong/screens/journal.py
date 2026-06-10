"""일지 — 귀가 보고 (5권 05 §2): 통계 한 줄 → 하이라이트 큐레이션 → 천기노조 문장
→ 끝은 결정 큐 입구. 전부 보여주지 않는다(카드 2~3장만)."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from .. import theme as T


def _c(rgb):
    return T.hexc(rgb)


class JournalScreen(Screen):
    BINDINGS = [("enter", "decide", "결정"), ("escape", "back", "지도로")]

    def compose(self) -> ComposeResult:
        st = self.app.state  # type: ignore[attr-defined]
        e = st.journal[-1]
        t = Text()
        t.append(f" ◆ 일지 — {e['day']}일째, 죽림에서\n", style=f"bold {_c(T.INK)}")
        t.append(f" ▸ 사냥 {e['hunts']}판 — 전승. 독 틱이 일을 다 했다\n\n", style=_c(T.DIM))
        # 하이라이트 카드(큐레이션 — 최대 3)
        cards = 0
        if e["best"]:
            star = e["best"].blessed
            style = f"bold {_c(T.GOLD)}" if star else _c(T.INK)
            t.append(" ┌─ 하이라이트 ─────────────────────────────┐\n", style=_c(T.DIM))
            t.append(f" │ {'★ 축복 드랍' if star else '드랍'} — {e['best'].label}\n", style=style)
            cards += 1
        if e["wall"] >= 1.0:
            t.append(f" │ ◈ 이류의 벽 — 축적 100%. 깰 만하다.\n", style=_c(T.SEAL))
            cards += 1
        elif e["wall"] > 0:
            t.append(f" │ ◈ 벽 축적 {int(e['wall']*100)}% — 내공이 차오른다\n", style=_c(T.AMBER))
            cards += 1
        if e["clue"]:
            t.append(" │ ✦ 소문 — “흑풍림 너머, 갑자에 한 번 열리는 동부가 있다더라” (단서 1)\n",
                     style=_c((130, 190, 230)))
            cards += 1
        if cards:
            t.append(" └──────────────────────────────────────────┘\n", style=_c(T.DIM))
        t.append(f"\n 그리고… {e['mishap']}\n\n", style=_c(T.DIM))
        n = 1 if st.wall_ready else 0
        if n:
            t.append(f" 당신 차례가 {n}건 ", style=f"bold {_c(T.AMBER)}")
            t.append("→ [Enter] 결정 큐", style=_c(T.AMBER))
        else:
            t.append(" [Esc] 지도로", style=_c(T.DIM))
        yield Static(t)

    def action_decide(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        self.app.pop_screen()
        if st.wall_ready:
            from .cards import DonoCard
            self.app.push_screen(DonoCard())

    def action_back(self) -> None:
        self.app.pop_screen()
