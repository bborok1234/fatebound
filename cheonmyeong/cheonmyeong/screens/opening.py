"""회귀 오프닝 + 계열 선택 (5권 02 §3.1 — 두루마리 텍스트 3~4행, 계열 7카드).
슬라이스: 독계만 활성(나머지 어스름 잠금 — 점진 공개)."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from .. import theme as T
from ..data import slice_pack as P


def _c(rgb):
    return T.hexc(rgb)


class SeriesCard(Static):
    def __init__(self, idx: int, name: str, res: str, gist: str, quip: str, active: bool):
        self.series_name = name
        self.active = active
        col = T.SERIES_COLOR[name] if active else T.dusk(T.SERIES_COLOR[name])
        t = Text()
        t.append(f" {name} \n", style=f"bold {_c(col)}")
        t.append(f" {res}\n", style=_c(T.dusk(T.INK)) if not active else _c(T.DIM))
        if active:
            t.append(f" {gist}\n", style=_c(T.INK))
            t.append(f" “{quip}”", style=f"italic {_c(T.GOLD)}")
        else:
            t.append(" (다음 회차에)\n", style=_c(T.dusk(T.INK)))
            t.append(" 어스름에 잠겨 있다", style=_c(T.dusk(T.INK)))
        super().__init__(t)
        self.styles.border = ("round", _c(col if active else T.dusk(T.DIM)))
        self.styles.width = 24
        self.styles.height = 7
        self.styles.margin = (0, 1)


class OpeningScreen(Screen):
    BINDINGS = [("enter", "pick", "독계로 시작")]

    def compose(self) -> ComposeResult:
        head = Text()
        head.append(" ◆ 천명회귀 ", style=f"bold {_c(T.INK)}")
        head.append("— 회귀 첫날", style=_c(T.DIM))
        yield Static(head)
        body = Text()
        for ln in P.VOICE["opening"]:
            body.append("  " + ln + "\n", style=_c(T.INK))
        yield Static(body)
        pick = Text()
        pick.append("\n  천기노조", style=f"bold {_c(T.GOLD)}")
        pick.append(f" — {P.VOICE['series_pick']}\n", style=_c(T.DIM))
        yield Static(pick)
        name_row = Input(value="천기노조", id="name")
        name_row.border_title = "이름 (기본값 그대로 Enter면 통과)"
        name_row.styles.width = 36
        yield name_row
        with Vertical():
            with Horizontal():
                for i, (n, r, g, q, a) in enumerate(P.SERIES_CARDS[:4]):
                    yield SeriesCard(i, n, r, g, q, a)
            with Horizontal():
                for i, (n, r, g, q, a) in enumerate(P.SERIES_CARDS[4:], 4):
                    yield SeriesCard(i, n, r, g, q, a)
        hint = Text()
        hint.append("  [Enter] ", style=_c(T.AMBER))
        hint.append("독계로 시작", style=_c(T.INK))
        hint.append("  (다른 계열은 슬라이스 밖 — 어스름)", style=_c(T.DIM))
        yield Static(hint)

    def action_pick(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "천기노조"
        self.app.state.name = name  # type: ignore[attr-defined]
        from .stage import StageScreen
        self.app.push_screen(StageScreen("죽림 산적"))

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self.action_pick()
