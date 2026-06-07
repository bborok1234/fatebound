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
CW = 18  # 칸 내부폭(셀) — 구궁=화면 주인공(#35). 한글 이름 + 카드 여백. 이름 절단 금지.
ROW_KO = ["1행", "2행", "3행"]   # 천명괘 가로줄(LINES 0~2). 좌측 라벨.
COL_KO = ["1열", "2열", "3열"]   # 천명괘 세로줄(LINES 3~5). 상단 라벨.
SPOT_C = "#e0b341"               # 천명 강조줄(라벨·점등 금빛)
DIM_C = "#55504a"                # 비강조 라벨


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
        self.pulse_amount = None        # 그 칸이 이번 합 낸 출력(기여 귀속)
        self.spot_line = None           # 천명괘 강조줄(0~5: 행0~2/열3~5). 화면이 m1_line에서 설정 → 라벨 점등

    def on_click(self, event) -> None:
        # 클릭 좌표 → 3×3 칸(비례 히트테스트). 좌측 행라벨 열(~5)·상단 헤더(~2) 보정.
        LW, HH = 5, 2
        w = max(1, self.size.width - LW); h = max(1, self.size.height - HH)
        gx = max(0, event.offset.x - LW); gy = max(0, event.offset.y - HH)
        col = min(2, max(0, int(gx * 3 / w)))
        row = min(2, max(0, int(gy * 3 / h)))
        self.post_message(self.CellClicked(row * 3 + col))

    # ── 전투 점화·발동(화면이 호출) ──
    def ignite(self, indices):
        self.active = set(indices); self.refresh()

    def douse(self):
        self.active = set(); self.pulse_idx = None; self.pulse_amount = None; self.spot_line = None; self.refresh()

    def spot(self, line):
        """천명괘 강조줄 설정(0~5) → 해당 행/열 라벨 점등. 화면이 m1_line에서 호출."""
        self.spot_line = line; self.refresh()

    def pulse(self, idx, amount=None):
        self.pulse_idx = idx; self.pulse_amount = amount; self.refresh()

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
        t = Table(show_header=True, box=HEAVY, padding=0, border_style="#55504a",
                  expand=False, pad_edge=False)
        t.add_column("", justify="right", width=4, no_wrap=True, vertical="middle")   # 좌측 행 라벨
        for c in range(GRID):                                # 상단 열 라벨 — 천명 강조 시 점등
            clit = (self.spot_line == GRID + c)
            hdr = Text((("▼" if clit else "") + COL_KO[c]), justify="center",
                       style=f"{SPOT_C} bold" if clit else DIM_C)
            t.add_column(hdr, justify="center", width=CW, no_wrap=True)

        for r in range(GRID):
            rlit = (self.spot_line == r)                     # 행 강조줄 → 좌측 라벨 점등(◀천명)
            rlab = Text(ROW_KO[r] + ("◀" if rlit else " "), justify="right",
                        style=f"{SPOT_C} bold" if rlit else DIM_C)
            row = [rlab]
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
                    name.stylize("bold on #e0b341")                                 # 발동! 캐스케이드 플래시
                    if self.pulse_amount:
                        sub = Text(f"⚔{self.pulse_amount}", style="#1a1a1f on #e0b341 bold", justify="center")
                    else:
                        sub.stylize("on #e0b341")
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

                # 셀 카드화 — 위·아래 여백으로 격자를 키워 코어(구궁)가 패널을 채우게(존재감↑, #35)
                cell = Text("\n", justify="center")
                cell.append_text(name); cell.append("\n\n"); cell.append_text(sub); cell.append("\n")
                row.append(cell)
            t.add_row(*row)
        return t
