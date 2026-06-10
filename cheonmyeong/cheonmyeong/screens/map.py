"""전선 지도 — 게임의 심장 (5권 05 §1·02 §3.8).
지도(authored) + 전선 바(벽 요약 — 깰 만하면 명멸) + 행동: 방치/돌파/일지.
돌파 성공 = 안개 걷힘 연출(대 연출 — 01 §6)."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from .. import theme as T
from ..engine import worldmap
from ..engine.render import fg, R


def _c(rgb):
    return T.hexc(rgb)


def ansi(s: str) -> Text:
    return Text.from_ansi(s)


class MapScreen(Screen):
    BINDINGS = [
        ("i", "idle", "걸어둔다"),
        ("d", "breakthrough", "벽을 친다"),
        ("j", "journal", "일지"),
        ("b", "study", "서재(채비)"),
        ("l", "loot", "전리품"),
        ("t", "mystery", "천기록"),
        ("o", "oneline", "한 줄"),
        ("q", "quit_app", "강호를 접는다"),
    ]

    def __init__(self):
        super().__init__()
        self.wm: worldmap.WorldMap | None = None
        self.dissolve: float | None = None
        self.pulse = 0.0

    def compose(self) -> ComposeResult:
        yield Static(id="maphead")
        yield Static(id="map")
        yield Static(id="frontier")
        yield Static(id="voice")
        yield Static(id="hints")

    def on_mount(self) -> None:
        w = max(80, min(self.app.size.width - 2, 110))
        h = (min(self.app.size.height - 8, 24)) * 2
        self.wm = worldmap.WorldMap(w, h)
        self.refresh_map()
        self.phase = 0.0
        self.set_interval(0.10, self.tick_pulse)

    @property
    def st(self):
        return self.app.state  # type: ignore[attr-defined]

    def tick_pulse(self) -> None:
        if self.st.wall_ready and self.dissolve is None:
            import math
            self.phase += 1.1                       # 정본: 사인 위상 1.1/f · 0.10s/f (01 §6)
            self.pulse = 0.5 + 0.5 * math.sin(self.phase)
            self.refresh_map()

    def refresh_map(self) -> None:
        st = self.st
        head = (fg(T.INK) + " ◆ 전선 — 천명반이 비추는 강호" + R
                + fg(T.DIM) + f"   {st.day}일째 · {st.gyeongji} {st.star}성 · 내공 {st.naegong:.1f}갑자" + R)
        self.query_one("#maphead", Static).update(ansi(head))
        dis = ("흑풍림", self.dissolve) if self.dissolve is not None else None
        rows = self.wm.render(st.explored, t=self.pulse, dissolve=dis)
        # 오버레이: 현재 위치·벽 표식·라벨
        rows = self.overlay(rows)
        self.query_one("#map", Static).update(ansi("\n".join(rows)))
        # 전선 바 (벽 요약 — 세션 첫 시선)
        if "흑풍림" in st.explored:
            bar = (fg(T.DIM) + " 전선: " + R + fg((150, 200, 150)) + "흑풍림 개방" + R
                   + fg(T.DIM) + " · 다음 벽: 일류(한천비곡 길목) — 어스름 속에서 기다린다" + R)
        elif st.wall_ready:
            glow = T.lerp(T.SEAL, (255, 190, 100), self.pulse)
            bar = (fg(T.DIM) + " 전선: " + R + fg(glow) + "◈ 이류의 벽 — 깰 만하다"
                   + R + fg(T.DIM) + f" (돈오 성공 {int(self.st.dono_chance*100)}%)  [D] 친다" + R)
        else:
            pct = int(st.wall_progress * 100)
            bar = (fg(T.DIM) + " 전선: ◈ 이류의 벽 — 축적 " + R
                   + fg(T.AMBER) + f"{pct}%" + R + fg(T.DIM) + " (내공이 차오르는 중 — 벽은 기다린다)" + R)
        self.query_one("#frontier", Static).update(ansi(bar))
        v = (fg(T.GOLD) + " 천기노조" + R + fg(T.DIM)
             + " — 한 발 디디면 한 뼘 보이는 법이지." + R)
        self.query_one("#voice", Static).update(ansi(v))
        hint = (fg(T.DIM) + " [I]걸어둔다  "
                + (fg(T.SEAL) + "[D]벽을 친다  " + fg(T.DIM) if st.wall_ready else "")
                + "[B]서재  [L]전리품  [T]천기록  [J]일지  [O]한 줄  [Q]접는다" + R)
        self.query_one("#hints", Static).update(ansi(hint))

    def overlay(self, rows: list[str]) -> list[str]:
        import re
        CELL = re.compile(r"(?:\x1b\[[0-9;]*m)+.")

        def put(row, col, txt, color, chip=True):
            if 0 <= row < len(rows):
                cells = CELL.findall(rows[row].replace(R, ""))
                for i, ch in enumerate(txt):
                    if 0 <= col + i < len(cells):
                        cells[col + i] = ((f"\x1b[48;2;{T.CHIP[0]};{T.CHIP[1]};{T.CHIP[2]}m" if chip else "")
                                          + fg(color) + ch)
                rows[row] = "".join(cells) + R

        st = self.st
        jx, jy = self.wm.spot("죽림")
        put(int(jy // 2), int(jx), " 죽림 ", (245, 247, 250))
        put(int(jy // 2), int(jx) - 2, "◉ ", T.SEAL, chip=False)
        if "흑풍림" in st.explored:
            hx, hy = self.wm.spot("흑풍림")
            put(int(hy // 2), int(hx) - 1, " 흑풍림 ", (245, 247, 250))
        elif st.wall_ready and self.dissolve is None:
            hx, hy = self.wm.spot("흑풍림")
            jx2, jy2 = self.wm.spot("죽림")
            wx, wy = int((jx2 + hx) / 2) + 3, int((jy2 + hy) / 2 / 2)
            glow = T.lerp(T.SEAL, (255, 190, 100), self.pulse)
            put(wy, wx, " ◈ 이류의 벽 ", glow)
        ux, uy = self.wm.spot("운하성")
        put(int(uy // 2), int(ux), " ? ", (200, 206, 216))
        return rows

    # ── 행동 ──
    def action_idle(self) -> None:
        from .cards import IdleCard
        self.app.push_screen(IdleCard())

    def action_breakthrough(self) -> None:
        if not self.st.wall_ready or self.dissolve is not None:
            return
        from .cards import DonoCard
        self.app.push_screen(DonoCard())

    def action_journal(self) -> None:
        from .journal import JournalScreen
        if self.st.journal:
            self.app.push_screen(JournalScreen())

    def action_study(self) -> None:
        from .study import StudyScreen
        self.app.push_screen(StudyScreen())

    def action_loot(self) -> None:
        from .extras import LootScreen
        self.app.push_screen(LootScreen())

    def action_mystery(self) -> None:
        from .extras import MysteryScreen
        self.app.push_screen(MysteryScreen())

    def action_oneline(self) -> None:
        from .extras import OneLineScreen
        self.app.push_screen(OneLineScreen())

    def action_quit_app(self) -> None:
        self.app.exit()

    # ── 안개 걷힘 (돌파 성공 — 대 연출) ──
    def reveal_heukpung(self) -> None:
        self.dissolve = 0.0
        self._anim = self.set_interval(0.13, self._step)

    def _step(self) -> None:
        self.dissolve = min(1.0, (self.dissolve or 0) + 0.14)
        self.refresh_map()
        if self.dissolve >= 1.0:
            self._anim.stop()
            self.dissolve = None
            if "흑풍림" not in self.st.explored:
                self.st.explored.append("흑풍림")   # 채색 확정 — 디졸브가 끝난 뒤에
            v = (fg(T.DIM) + " 어스름이 걷힌다 — " + R + fg((150, 200, 150)) + "흑풍림" + R
                 + fg(T.DIM) + "에 색이 들었다. 검은 솔바람 너머, 다음 벽이 보인다." + R)
            self.query_one("#voice", Static).update(ansi(v))
            self.refresh_map()
