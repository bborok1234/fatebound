"""구궁(九宮) 위젯 — 3×3 배치(17 §5, §13.4). 카드형 미감(#35·doc28·#37 PR②):
rarity 발색 카드 + 천명 강조줄 발광 + 행/열 라벨로 dice→칸 매핑 명료화. 이름 절단 금지, 커서/집기 가시화.

#37 PR②: 단일위젯 Rich-Table 렌더 → 9개 Cell(Static) 위젯의 Textual Grid로.
셀별 :hover/:focus/CSS transition·애니가 가능해진다("정적이라 박스 같다"의 근원 제거).
비주얼은 전부 CSS 클래스(rarity-*/cursor/synergy/ignite/grab/pulse/empty/ghost) — app.tcss가 발색·전이 담당.
game.py가 쓰는 API(move_cursor/toggle_grab/ignite/douse/spot/pulse/current_item/CellClicked/
reactive cursor·grabbed/ghost_item·ghost_delta)는 시그니처·동작 그대로 보존.
"""
from __future__ import annotations
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.console import Group
from ...engine.bag import synergy_cells

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f bold"}
RARITY_DOT = {"common": "○", "rare": "◆", "epic": "◆", "legendary": "★"}
# 카드 팔레트(수묵 + 보석 틴트): rarity → (배경, 테두리, 글자). 미감 천장(#35·doc28).
# app.tcss의 .cell.rarity-* 와 값 동기화(글자색은 여기서 Text 스타일로 발색).
RARITY_CARD = {
    "common":    ("#20242a", "#3a4048", "#aeb6c0"),
    "rare":      ("#13242e", "#3f6f80", "#7fcad8"),
    "epic":      ("#2a2410", "#8a6a2a", "#e6bd4e"),
    "legendary": ("#301a12", "#a85030", "#f4824e"),
}
RARITY_CLASS = {"common": "rarity-common", "rare": "rarity-rare",
                "epic": "rarity-epic", "legendary": "rarity-legendary"}
GRID = 3
ROW_KO = ["1행", "2행", "3행"]   # 천명괘 가로줄(LINES 0~2). 좌측 라벨.
COL_KO = ["1열", "2열", "3열"]   # 천명괘 세로줄(LINES 3~5). 상단 라벨.
SPOT_C = "#e0b341"               # 천명 강조줄(라벨·점등 금빛)
DIM_C = "#55504a"                # 비강조 라벨

# 상태 → CSS 클래스. 칸이 가질 수 있는 모든 상태 클래스(교체 시 전부 제거 후 재부여).
_STATE_CLASSES = ("cursor", "grab", "ghost", "ignite", "pulse", "synergy")


class Cell(Static):
    """구궁 한 칸 = 한 위젯. idx 보유. 내용은 부모가 set_card로 채우고,
    상태(커서/집기/점화/발동/상생/고스트)는 CSS 클래스로만 표현 → 셀별 hover/transition 가능."""

    def __init__(self, idx: int, **kw):
        super().__init__("", **kw)
        self.idx = idx
        self.add_class("cell")

    def on_click(self, event) -> None:
        # 클릭 → 이 칸 index로 CellClicked(좌표 히트테스트 불필요 — 위젯이 곧 칸).
        self.post_message(GugungWidget.CellClicked(self.idx))


class GugungWidget(Container):
    can_focus = True
    cursor: reactive[int] = reactive(0)
    grabbed: reactive[int | None] = reactive(None)

    # 4×4 그리드: 코너 + 열라벨3 / 행라벨 + 카드3 (×3행). 셀별 CSS 애니를 위해 위젯 그리드.
    DEFAULT_CSS = """
    GugungWidget {
        layout: grid;
        grid-size: 4 4;
        grid-columns: 4 1fr 1fr 1fr;
        grid-rows: 1 1fr 1fr 1fr;
        grid-gutter: 0 1;
        width: 1fr;
        height: 1fr;
    }
    """

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

    def compose(self):
        # 1행: 코너(빈칸) + 열 라벨 3개
        yield Static("", classes="gug-corner")
        for c in range(GRID):
            yield Static(self._col_label(c), classes="gug-collabel", id=f"gug-col-{c}")
        # 2~4행: 행 라벨 + 카드 3개
        for r in range(GRID):
            yield Static(self._row_label(r), classes="gug-rowlabel", id=f"gug-row-{r}")
            for c in range(GRID):
                yield Cell(r * GRID + c, id=f"gug-cell-{r * GRID + c}")

    def on_mount(self):
        self._render_cells()
        self._render_labels()

    # ── 라벨(천명 강조줄 점등) ──
    def _col_label(self, c: int) -> Text:
        lit = (self.spot_line == GRID + c)
        return Text(((" ▼ " if lit else "") + COL_KO[c]), justify="center",
                    style=f"{SPOT_C} bold" if lit else DIM_C)

    def _row_label(self, r: int) -> Text:
        lit = (self.spot_line == r)
        return Text(ROW_KO[r] + ("◀" if lit else " "), justify="right",
                    style=f"{SPOT_C} bold" if lit else DIM_C)

    def _render_labels(self):
        if not self.is_mounted:
            return
        for r in range(GRID):
            self.query_one(f"#gug-row-{r}", Static).update(self._row_label(r))
            lit = (self.spot_line == r)
            self.query_one(f"#gug-row-{r}", Static).set_class(lit, "lit")
        for c in range(GRID):
            self.query_one(f"#gug-col-{c}", Static).update(self._col_label(c))
            lit = (self.spot_line == GRID + c)
            self.query_one(f"#gug-col-{c}", Static).set_class(lit, "lit")

    # ── 칸 렌더(내용=Text, 상태=CSS 클래스) ──
    def _cell_body(self, idx, it, is_syn) -> Group:
        """칸 본문 텍스트. 발색 배경/테두리는 CSS 클래스가 담당, 글자만 여기서."""
        cur = (idx == self.cursor)
        grab = (idx == self.grabbed)
        ghost = (self.ghost_item is not None and cur)

        # 상태 우선순위(텍스트): 발동 펄스 > 고스트 미리보기 > 일반(rarity/상생/빈칸)
        if idx == self.pulse_idx:
            fg = RARITY_CARD.get((it or {}).get("rarity"), RARITY_CARD["common"])[2] if it else "#e6bd4e"
            name = Text((it["name_ko"] if it else "· · ·"), style=f"bold {fg}", justify="center")
            sub = (Text(f"⚔ {self.pulse_amount}", style="#1a1a1f on #e0b341 bold", justify="center")
                   if self.pulse_amount else Text("발동", style="#e0b341 bold", justify="center"))
        elif ghost:
            name = Text("⇲ " + self.ghost_item["name_ko"], style="#cfe6a8 bold italic", justify="center")
            dtxt = self.ghost_delta or "여기 놓기"
            dcol = "#7fd06a" if dtxt.startswith("▲") else ("#e07a5a" if dtxt.startswith("▼") else "#9a958a")
            sub = Text(dtxt, style=f"{dcol} bold italic", justify="center")
        elif it is None:
            name = Text("· · ·", style="#3a3a42", justify="center")
            sub = Text("빈 칸", style="#33333a", justify="center")
        else:
            fg = RARITY_CARD.get(it["rarity"], RARITY_CARD["common"])[2]
            name = Text(it["name_ko"], style=f"bold {fg}", justify="center")
            if is_syn:
                sub = Text("◆ 상생", style="#5aa67c", justify="center")
            else:
                sub = Text(RARITY_DOT.get(it["rarity"], "·"), style=fg, justify="center")
            if grab:
                name = Text("✋ ", style="#e0b341", justify="center") + name

        return Group(Text("", justify="center"), name, Text("", justify="center"), sub)

    def _cell_classes(self, idx, it, is_syn) -> set:
        """칸이 가져야 할 상태 클래스 집합(rarity 제외). app.tcss가 발색/전이."""
        cur = (idx == self.cursor)
        grab = (idx == self.grabbed)
        ghost = (self.ghost_item is not None and cur)
        cls = set()
        if is_syn and it is not None:
            cls.add("synergy")
        # 상태 우선순위(배경/테두리): pulse > ghost > ignite > grab > cursor.
        # 클래스는 공존시키되 app.tcss 선택자 특이도/순서로 우선순위 구현(아래 주석 참조).
        if idx == self.pulse_idx:
            cls.add("pulse")
        elif ghost:
            cls.add("ghost")
        elif idx in self.active:
            cls.add("ignite")
        elif grab:
            cls.add("grab")
        elif cur:
            cls.add("cursor")
        return cls

    def set_card(self, idx, it, is_syn):
        cell = self.query_one(f"#gug-cell-{idx}", Cell)
        cell.update(self._cell_body(idx, it, is_syn))
        # rarity 클래스
        rcls = RARITY_CLASS.get((it or {}).get("rarity"), "empty" if it is None else "rarity-common")
        for rc in (*RARITY_CLASS.values(), "empty"):
            cell.set_class(rc == rcls, rc)
        # 상태 클래스
        want = self._cell_classes(idx, it, is_syn)
        for sc in _STATE_CLASSES:
            cell.set_class(sc in want, sc)

    def _render_cells(self):
        if not self.is_mounted:
            return
        bag = self.session.bag
        syn, _ = synergy_cells(bag)
        for idx in range(GRID * GRID):
            self.set_card(idx, bag.cells[idx], idx in syn)

    # Container는 render를 위젯 합성에 쓰므로, refresh()는 자식 재계산으로 라우팅.
    def refresh(self, *args, **kwargs):
        self._render_cells()
        self._render_labels()
        return super().refresh(*args, **kwargs)

    # ── 전투 점화·발동(화면이 호출) ──
    def ignite(self, indices):
        self.active = set(indices); self._render_cells()

    def douse(self):
        self.active = set(); self.pulse_idx = None; self.pulse_amount = None; self.spot_line = None
        self._render_cells(); self._render_labels()

    def spot(self, line):
        """천명괘 강조줄 설정(0~5) → 해당 행/열 라벨 점등. 화면이 m1_line에서 호출."""
        self.spot_line = line; self._render_labels()

    def pulse(self, idx, amount=None):
        self.pulse_idx = idx; self.pulse_amount = amount; self._render_cells()

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
        self._render_cells()

    def current_item(self):
        return self.session.bag.cells[self.cursor]

    def watch_cursor(self):
        self._render_cells()

    def watch_grabbed(self):
        self._render_cells()
