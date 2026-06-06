"""구궁(九宮) 위젯 — 3×3 배치(17 §5, §13.4). 가독성 우선:
이름 절단 금지(칸폭 12로 5자 수용), 커서/집기 확실히 가시화, 상생 녹색 표기.
"""
from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY
from ...engine.bag import synergy_cells

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f bold"}
RARITY_DOT = {"common": "○", "rare": "◆", "epic": "◆", "legendary": "★"}
GRID = 3
CW = 12  # 칸 내부폭(셀) — 한글 5자(10셀) + 여유. 이름 절단 금지.


class GugungWidget(Widget):
    can_focus = True
    cursor: reactive[int] = reactive(0)
    grabbed: reactive[int | None] = reactive(None)

    class CellClicked(Message):
        def __init__(self, idx: int) -> None:
            self.idx = idx
            super().__init__()

    def __init__(self, session, **kw):
        super().__init__(**kw)
        self.session = session
        self.active: set = set()        # 천명괘로 강조된 줄(전투 중 점화)
        self.ghost_item = None          # 커서 칸에 미리볼 무공(잡기/보관함 선택, 화면이 설정)
        self.ghost_delta = None         # 고스트 칸에 함께 보일 출력 델타(예 "▲+43%")
        self.pulse_idx = None           # 발동 캐스케이드: 지금 터지는 칸(전투 중)

    def on_click(self, event) -> None:
        # 클릭 좌표 → 3×3 칸(비례 히트테스트). 화면이 집기/놓기 처리.
        w = max(1, self.size.width); h = max(1, self.size.height)
        col = min(2, max(0, int(event.offset.x * 3 / w)))
        row = min(2, max(0, int(event.offset.y * 3 / h)))
        self.post_message(self.CellClicked(row * 3 + col))

    # ── 전투 점화·발동(화면이 호출) ──
    def ignite(self, indices):
        self.active = set(indices); self.refresh()

    def douse(self):
        self.active = set(); self.pulse_idx = None; self.refresh()

    def pulse(self, idx):
        self.pulse_idx = idx; self.refresh()

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
        t = Table(show_header=False, box=HEAVY, padding=0, border_style="#55504a",
                  expand=False, pad_edge=False)
        for _ in range(GRID):
            t.add_column(justify="center", width=CW, no_wrap=True)

        for r in range(GRID):
            row = []
            for c in range(GRID):
                idx = r * GRID + c
                it = bag.cells[idx]
                cur = (idx == self.cursor)
                grab = (idx == self.grabbed)
                # 호버 고스트: 잡기/보관함 선택 시 커서 칸에 놓일 무공을 미리보기(화면이 ghost_item 설정)
                ghost = (self.ghost_item is not None and cur)

                if it is None:
                    name = Text("· · ·", style="#3a3a42", justify="center")
                    sub = Text("빈 칸", style="#33333a", justify="center")
                else:
                    nm = it["name_ko"]
                    style = RARITY.get(it["rarity"], "white")
                    if idx in syn:
                        name = Text(nm, style="#5aa67c bold", justify="center")
                        sub = Text("◆ 상생", style="#5aa67c", justify="center")
                    else:
                        name = Text(nm, style=style, justify="center")
                        dot = RARITY_DOT.get(it["rarity"], "·")
                        sub = Text(dot, style=style, justify="center")

                # 커서/집기 — 확실히 보이게(밝은 배경 + 마커). 발동 펄스·점화·고스트가 최우선.
                if idx == self.pulse_idx:
                    name.stylize("bold on #e0b341"); sub.stylize("on #e0b341")     # 발동! 캐스케이드 플래시
                elif ghost:
                    gnm = self.ghost_item["name_ko"]
                    name = Text("⇲" + gnm, style="#c8a24a bold italic", justify="center")
                    dtxt = self.ghost_delta or "여기 놓기"                          # 원인(칸)+결과(델타) 같은 자리
                    dcol = "#5aa67c" if dtxt.startswith("▲") else ("#d4582f" if dtxt.startswith("▼") else "#9a958a")
                    sub = Text(dtxt, style=f"{dcol} bold italic", justify="center")
                    name.stylize("on #2d3a22"); sub.stylize("on #2d3a22")          # 미리보기 배경(연녹)
                elif idx in self.active:
                    name.stylize("bold on #4a3a12"); sub.stylize("on #4a3a12")     # 천명 줄 점화(금빛)
                elif grab:
                    name = Text("✋", style="#e0b341") + name
                    name.stylize("on #6b4423"); sub.stylize("on #6b4423")
                elif cur:
                    name = Text("▸", style="#c8a24a bold") + name + Text("◂", style="#c8a24a bold")
                    name.stylize("bold on #3b4660")
                    sub.stylize("on #3b4660")

                cell = Text("\n", justify="center")
                cell.append_text(name); cell.append("\n"); cell.append_text(sub)
                row.append(cell)
            t.add_row(*row)
        return t
