"""M2 보조 화면 — 전리품 시렁(05 §6 약식) · 천기록(05 §7 카브아웃) · 한 줄 모드(05 §3.12)."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from .. import theme as T
from ..engine.render import fg, R


def _c(rgb):
    return T.hexc(rgb)


def ansi(s: str) -> Text:
    return Text.from_ansi(s)


class LootScreen(Screen):
    """전리품 시렁 — 일괄 처리 우선, 축복은 강조(05 §6 약식: 격자→목록)."""
    BINDINGS = [("a", "salvage", "전부 분해"), ("escape", "back", "지도로")]

    def compose(self) -> ComposeResult:
        yield Static(id="loot")
        yield Static(id="hints")

    def on_mount(self) -> None:
        self.redraw()
        self.query_one("#hints", Static).update(ansi(
            fg(T.DIM) + " [A]기준 미달 전부 분해   [Esc]지도" + R))

    def redraw(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        out = [fg(T.INK) + f" ◆ 전리품 — {len(st.drops)}점의 수확" + R, ""]
        if not st.drops:
            out.append(fg(T.DIM) + "  (시렁이 비었다 — 걸어두면 쌓인다)" + R)
        for d in sorted(st.drops, key=lambda x: -x.quality)[:14]:
            if d.blessed:
                out.append("  " + fg(T.GOLD) + f"★ {d.name} (품질 {d.quality}/50)" + R
                           + fg(T.DIM) + "  ← 축복 — 티어 안의 대박" + R)
            else:
                q = d.quality
                col = (130, 190, 230) if q >= 40 else (T.INK if q >= 25 else T.DIM)
                out.append("  " + fg(col) + f"{d.name} (품질 {q}/50)" + R)
        if len(st.drops) > 14:
            out.append(fg(T.DIM) + f"  … 외 {len(st.drops)-14}점" + R)
        self.query_one("#loot", Static).update(ansi("\n".join(out)))

    def action_salvage(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        before = len(st.drops)
        st.drops = [d for d in st.drops if d.blessed or d.quality >= 40]
        n = before - len(st.drops)
        self.app.notify(f"{n}점 분해 — 죽력 가루 {n*2}", title="분해", timeout=2)
        self.redraw()

    def action_back(self) -> None:
        self.app.pop_screen()


CHEONGI_ART = [
    "▓▓░░░░░░", "▓▓▓░░░░░", "░▓▓▓░░░░", "░░▓▓░░░░",
    "░░░░░░░░", "░░░░░░░░", "░░░░░░░░", "░░░░░░░░",
]


class MysteryScreen(Screen):
    """천기록 — 비밀의 수집화(2권 14 §4): 조각마다 그림이 드러난다(슬라이스: 첫 장 윤곽)."""
    BINDINGS = [("escape", "back", "지도로")]

    def compose(self) -> ComposeResult:
        yield Static(id="myst")
        yield Static(id="hints")

    def on_mount(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        out = [fg(T.INK) + " ◆ 천기록 — 제1장: 봉인은 영원하지 않다" + R,
               fg(T.DIM) + f"   조각 {st.clues}/5 — 운명의 실이 그림을 짠다" + R, ""]
        for i, row in enumerate(CHEONGI_ART):
            line = "   "
            for j, ch in enumerate(row):
                lit = ch == "▓" and st.clues >= 1
                col = (170, 60, 50) if lit else T.dusk((120, 120, 130))
                line += fg(col) + ("▓" if lit else "░") + R
            out.append(line)
        out.append("")
        if st.clues:
            out.append(fg((130, 190, 230)) + " ✦ 단서 1 — “흑풍림 너머, 갑자에 한 번 열리는 동부가 있다더라”" + R)
            out.append(fg(T.DIM) + "   다음 단서: 산적들이 흑풍당에 혈정을 상납한다는 소문 (죽림 객잔 탐문)" + R)
        else:
            out.append(fg(T.DIM) + "   아직 조각이 없다 — 탐문 클락이 소문을 줍는다" + R)
        out.append("")
        out.append(fg(T.GOLD) + " 천기노조" + R + fg(T.DIM)
                   + " — 천 년 전에도 이 그림의 끝은 못 봤다. 이번엔 다르겠지." + R)
        self.query_one("#myst", Static).update(ansi("\n".join(out)))
        self.query_one("#hints", Static).update(ansi(fg(T.DIM) + " [Esc]지도" + R))

    def action_back(self) -> None:
        self.app.pop_screen()


class OneLineScreen(Screen):
    """한 줄 모드 — tmux 상주의 시연판(05 §3.12): 상태 한 줄 + 복귀."""
    BINDINGS = [("enter", "back", "복귀"), ("escape", "back", "복귀")]

    def compose(self) -> ComposeResult:
        yield Static(id="one")

    def on_mount(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        star = " ★기연 단서 대기" if st.clues else ""
        ready = " ◈벽 깰 만함" if st.wall_ready else ""
        line = (fg(T.DIM) + "\n\n  " + R + fg(T.GOLD) + "무명" + R + fg(T.DIM)
                + f" · 죽림 폐관 중 ▸ {st.day}일째 · 드랍 {len(st.drops)} ·"
                + f" 벽 {int(st.wall_progress*100)}%{ready}{star}" + R
                + fg(T.DIM) + "\n\n  (tmux 한 줄 상주의 시연 — [Enter] 본 화면 복귀."
                + " 실게임: 창 제목 OSC 0/2 + 천명반 알림 OSC 9)" + R)
        self.query_one("#one", Static).update(ansi(line))

    def action_back(self) -> None:
        self.app.pop_screen()
