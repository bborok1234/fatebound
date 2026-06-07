"""구궁(九宮) 위젯 — 3×3 배치(17 §5, §13.4). 카드형 미감(#35·doc28):
rarity 발색 카드 + 천명 강조줄 발광 + 행/열 라벨로 dice→칸 매핑 명료화. 이름 절단 금지, 커서/집기 가시화.
"""
from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.box import ROUNDED
from ...engine.bag import synergy_cells

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f bold"}
RARITY_DOT = {"common": "○", "rare": "◆", "epic": "◆", "legendary": "★"}
# 카드 팔레트(수묵 + 보석 틴트): rarity → (배경, 테두리, 글자). 미감 천장(#35·doc28).
RARITY_CARD = {
    "common":    ("#20242a", "#3a4048", "#aeb6c0"),
    "rare":      ("#13242e", "#3f6f80", "#7fcad8"),
    "epic":      ("#2a2410", "#8a6a2a", "#e6bd4e"),
    "legendary": ("#301a12", "#a85030", "#f4824e"),
}
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

    # ── 렌더: 카드형 3×3 + 행/열 라벨 ──
    def _card(self, idx, it, is_syn) -> Panel:
        """칸 1개 = rarity 발색 카드. 상태(발동·고스트·점화·집기·커서)는 배경/테두리로 우선 표현."""
        cur = (idx == self.cursor)
        grab = (idx == self.grabbed)
        ghost = (self.ghost_item is not None and cur)

        if it is None:
            bg, bd, fg = "#191b20", "#2e2e36", "#3a3a42"
            name = Text("· · ·", style=fg, justify="center")
            sub = Text("빈 칸", style="#33333a", justify="center")
        else:
            bg, bd, fg = RARITY_CARD.get(it["rarity"], RARITY_CARD["common"])
            name = Text(it["name_ko"], style=f"bold {fg}", justify="center")
            if is_syn:
                bd = "#5aa67c"
                sub = Text("◆ 상생", style="#5aa67c", justify="center")
            else:
                sub = Text(RARITY_DOT.get(it["rarity"], "·"), style=fg, justify="center")

        # 상태 우선순위: 발동 펄스 > 고스트 미리보기 > 천명 점화 > 집기 > 커서
        if idx == self.pulse_idx:
            bg, bd = "#5a4410", "#f0d472"
            name.stylize("bold")
            if self.pulse_amount:
                sub = Text(f"⚔ {self.pulse_amount}", style="#1a1a1f on #e0b341 bold", justify="center")
        elif ghost:
            bg, bd = "#23301a", "#9cc06a"
            name = Text("⇲ " + self.ghost_item["name_ko"], style="#cfe6a8 bold italic", justify="center")
            dtxt = self.ghost_delta or "여기 놓기"
            dcol = "#7fd06a" if dtxt.startswith("▲") else ("#e07a5a" if dtxt.startswith("▼") else "#9a958a")
            sub = Text(dtxt, style=f"{dcol} bold italic", justify="center")
        elif idx in self.active:
            bg, bd = "#3a2e10", SPOT_C                    # 천명 줄 점화(금빛 발광)
        elif grab:
            bg, bd = "#3a2818", "#e0b341"
            name = Text("✋ ", style="#e0b341") + name
        elif cur:
            bg, bd = "#222a3a", "#c8a24a"                 # 커서

        body = Text("\n", justify="center")
        body.append_text(name)
        body.append("\n\n")
        body.append_text(sub)
        return Panel(Align.center(body, vertical="middle"), box=ROUNDED,
                     style=f"on {bg}", border_style=bd, padding=(0, 1), width=CW, height=6)

    def render(self):
        bag = self.session.bag
        syn, _ = synergy_cells(bag)
        t = Table(show_header=True, box=None, padding=(0, 1), expand=False, pad_edge=False)
        t.add_column("", justify="right", width=4, no_wrap=True, vertical="middle")   # 좌측 행 라벨
        for c in range(GRID):                                # 상단 열 라벨 — 천명 강조 시 점등
            clit = (self.spot_line == GRID + c)
            hdr = Text(((" ▼ " if clit else "") + COL_KO[c]), justify="center",
                       style=f"{SPOT_C} bold" if clit else DIM_C)
            t.add_column(hdr, justify="center", no_wrap=True)

        for r in range(GRID):
            rlit = (self.spot_line == r)                     # 행 강조줄 → 좌측 라벨 점등(◀천명)
            rlab = Text(ROW_KO[r] + ("◀" if rlit else " "), justify="right",
                        style=f"{SPOT_C} bold" if rlit else DIM_C)
            row = [rlab]
            for c in range(GRID):
                idx = r * GRID + c
                row.append(self._card(idx, bag.cells[idx], idx in syn))
            t.add_row(*row)
        return t
