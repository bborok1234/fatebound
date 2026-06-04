"""구궁(九宮) 위젯 — 3×3 배치를 Rich Table 한 장으로 렌더(CJK 정렬). 커서 네비·집기/놓기·시너지 하이라이트."""
from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY
from ...engine.bag import synergy_cells

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f bold"}
GRID = 3


class GugungWidget(Widget):
    cursor: reactive[int] = reactive(0)
    grabbed: reactive[int | None] = reactive(None)

    def __init__(self, session, **kw):
        super().__init__(**kw)
        self.session = session

    # ── 조작(화면이 호출) ──
    def move_cursor(self, dr: int, dc: int):
        r, c = divmod(self.cursor, GRID)
        r = max(0, min(GRID - 1, r + dr))
        c = max(0, min(GRID - 1, c + dc))
        self.cursor = r * GRID + c

    def toggle_grab(self):
        if self.grabbed is None:
            if self.session.bag.cells[self.cursor] is not None:
                self.grabbed = self.cursor
        else:
            self.session.move(self.grabbed, self.cursor)   # 스왑
            self.grabbed = None
        self.refresh()

    def current_item(self):
        return self.session.bag.cells[self.cursor]

    def watch_cursor(self):
        self.refresh()

    def render(self):
        bag = self.session.bag
        syn, _ = synergy_cells(bag)
        t = Table(show_header=False, box=HEAVY, padding=0, border_style="#3a3a42",
                  expand=False, pad_edge=False)
        for _ in range(GRID):
            t.add_column(justify="center", width=9, no_wrap=True)
        for r in range(GRID):
            row = []
            for c in range(GRID):
                idx = r * GRID + c
                it = bag.cells[idx]
                if it is None:
                    cell = Text("· · ·", style="#3a3a42", justify="center")
                else:
                    name = it["name_ko"]
                    disp = name if len(name) <= 4 else name[:3] + "…"
                    style = RARITY.get(it["rarity"], "white")
                    cell = Text(disp, style=style, justify="center")
                    if idx in syn:
                        cell.append("\n⇄", style="#5aa67c")
                # 커서/집기 테두리 대용: 배경/마커
                if idx == self.grabbed:
                    cell.stylize("on #4a3a2a")
                elif idx == self.cursor:
                    cell.stylize("on #2a2a33")
                row.append(cell)
            t.add_row(*row)
        return t
