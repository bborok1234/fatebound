"""보관함(寶藏) 인라인 칼럼 — 미배치 무공 목록(모달 대체). 밀러 레이아웃 좌측.

포커스 가능(Tab/클릭). 커서로 무공을 고르면 살핌 패널이 그 무공을 미리보고,
구궁으로 보내면(엔터/우방향) 커서 칸에 배치된다. 키보드+마우스 동등.
"""
from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.console import Group

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f"}
RARITY_DOT = {"common": "○", "rare": "◆", "epic": "◆", "legendary": "★"}


class ReserveWidget(Widget):
    can_focus = True
    sel: reactive[int] = reactive(0)

    class Clicked(Message):
        def __init__(self, row: int) -> None:
            self.row = row
            super().__init__()

    def __init__(self, session, **kw):
        super().__init__(**kw)
        self.session = session

    # ── 화면이 호출 ──
    def items(self):
        return self.session.reserve()

    def current(self):
        its = self.items()
        return its[self.sel] if its and 0 <= self.sel < len(its) else None

    def move(self, d: int):
        n = len(self.items())
        if n:
            self.sel = (self.sel + d) % n

    def clamp(self):
        n = len(self.items())
        self.sel = 0 if n == 0 else max(0, min(self.sel, n - 1))
        self.refresh()

    def watch_sel(self):
        self.refresh()

    def _window(self):
        """긴 목록도 sel이 보이게 — 표시 시작 index와 가시 용량(헤더/인디케이터 보정)."""
        n = len(self.items())
        cap = max(3, (self.size.height or 24) - 2)
        if n <= cap:
            return 0, cap
        return max(0, min(self.sel - cap // 2, n - cap)), cap

    # ── 마우스 ──
    def on_click(self, event):
        # 클릭 y → 실제 무공 index(헤더 1줄 + 윈도 시작 + ▲ 인디케이터 보정)
        start, cap = self._window()
        row = event.offset.y - 1
        if start > 0:
            row -= 1                       # ▲ 더보기 줄
        idx = start + row
        if 0 <= idx < len(self.items()):
            self.post_message(self.Clicked(idx))

    # ── 렌더 ──
    def render(self):
        focused = self.has_focus
        g = [Text("寶藏 · 보관함", style="#c8a24a bold" if focused else "#9a958a")]
        its = self.items()
        if not its:
            g.append(Text("비었다.", style="#55504a"))
            g.append(Text("전투·기연으로", style="#55504a"))
            g.append(Text("무공을 모은다.", style="#55504a"))
            return Group(*g)
        start, cap = self._window()
        end = min(len(its), start + cap)
        if start > 0:
            g.append(Text(f" ▲ {start}개 더", style="#6b665c"))
        for i in range(start, end):
            it = its[i]
            r = RARITY.get(it["rarity"], "white")
            dot = RARITY_DOT.get(it["rarity"], "·")
            if i == self.sel:
                style = "#1a1a1f on #c8a24a bold" if focused else "#e8e2d4 on #3b4660"
                g.append(Text(f" ▸{it['name_ko']} ", style=style))
            else:
                g.append(Text(f" {dot}{it['name_ko']}", style=r))
        if end < len(its):
            g.append(Text(f" ▼ {len(its) - end}개 더", style="#6b665c"))
        if focused:
            g.append(Text("Enter→구궁 배치", style="#55504a"))
        return Group(*g)
