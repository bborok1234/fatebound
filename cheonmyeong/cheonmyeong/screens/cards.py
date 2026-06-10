"""결정 카드 — 모달 한 장씩 (5권 05 §3). '나중에'가 항상 있다(무FOMO).
방치 카드(걸어두기)·돈오 카드(벽 돌파) — 전부 effects/성공률 텔레그래프."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from .. import theme as T


def _c(rgb):
    return T.hexc(rgb)


class _Card(ModalScreen):
    DEFAULT_CSS = f"""
    _Card {{ align: center middle; background: rgba(10,13,20,0.6); }}
    _Card > Vertical {{
        width: 56; height: auto; padding: 1 2;
        background: {T.hexc(T.CANVAS)}; border: round {T.hexc(T.GOLD)};
    }}
    """


class IdleCard(_Card):
    """방치 카드 — 05 §5: 효율·천장·클락·예상 텔레그래프 → 걸어둔다."""
    BINDINGS = [("enter", "go", "걸어둔다"), ("escape", "later", "나중에")]

    def compose(self) -> ComposeResult:
        st = self.app.state  # type: ignore[attr-defined]
        t = Text()
        t.append("죽림 — 자리를 잡는다\n\n", style=f"bold {_c(T.INK)}")
        t.append("사냥 효율 ", style=_c(T.DIM))
        t.append("▮▮▮▮▯", style=_c(T.POISON))
        t.append(" (독 빌드 — 죽림 적 상성 우위)\n", style=_c(T.DIM))
        t.append("드랍 천장 50", style=_c(T.DIM))
        t.append(" · 주요 소재: 죽력·녹철\n", style=_c(T.DIM))
        t.append("클락: [사냥 8판] [운기조식] [기연 탐색]\n\n", style=_c(T.DIM))
        t.append("예상: ", style=_c(T.DIM))
        t.append("사냥 ~8판 · 내공 +0.05갑자 · 벽 축적 +33%\n\n", style=_c(T.INK))
        t.append("[Enter] 걸어둔다 (하루)", style=_c(T.AMBER))
        t.append("    [Esc] 나중에", style=_c(T.DIM))
        with Vertical():
            yield Static(t)

    def action_go(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        st.idle_day()
        self.dismiss()
        from .journal import JournalScreen
        self.app.push_screen(JournalScreen())

    def action_later(self) -> None:
        self.dismiss()


class DonoCard(_Card):
    """돈오 카드 — 05 §3: 성공률 정직 표기 · 실패=진척 · '나중에'(벽은 기다린다)."""
    BINDINGS = [("enter", "strike", "친다"), ("escape", "later", "나중에")]

    def compose(self) -> ComposeResult:
        st = self.app.state  # type: ignore[attr-defined]
        t = Text()
        t.append("◈ 이류의 벽 — 돈오\n\n", style=f"bold {_c(T.SEAL)}")
        t.append("내공이 임계에 닿았다. 막힌 혈이 ", style=_c(T.DIM))
        t.append("욱신", style=_c(T.SEAL))
        t.append("거린다.\n\n", style=_c(T.DIM))
        t.append(f"성공 {int(st.dono_chance * 100)}%", style=f"bold {_c(T.INK)}")
        t.append(f"  (실패 누적 +10%p — 현재 {st.dono_fails}회)\n", style=_c(T.DIM))
        t.append("실패 시: 주화입마 잠시 — 진척은 남는다\n\n", style=_c(T.DIM))
        t.append("[Enter] 친다", style=_c(T.AMBER))
        t.append("    [Esc] 나중에 (벽은 기다린다)", style=_c(T.DIM))
        with Vertical():
            yield Static(t)

    def action_strike(self) -> None:
        st = self.app.state  # type: ignore[attr-defined]
        ok = st.attempt_breakthrough()
        self.dismiss()
        screen = self.app.screen
        if ok:
            self.app.notify("돈오 — 벽이 갈라진다. 이류.", title="✦ 돌파", timeout=3)
            if hasattr(screen, "reveal_heukpung"):
                screen.reveal_heukpung()
        else:
            self.app.notify(
                f"오늘은 아니다 — 다음 시도 성공 {int(st.dono_chance*100)}% (실패는 진척이다)",
                title="벽", timeout=3)
            if hasattr(screen, "refresh_map"):
                screen.refresh_map()

    def action_later(self) -> None:
        self.dismiss()
