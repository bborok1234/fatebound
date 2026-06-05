"""콜드오픈 — 회귀 서사 인트로(17 §13.2). 세이브 없을 때 1회. ↵ 진행 · S 스킵."""
from __future__ import annotations
from textual.screen import Screen
from textual.containers import Center, Middle
from textual.widgets import Static
from textual.reactive import reactive

# 짧은 비트 — 한 번에 한 수(벽글 금지). (본문, 보조)
BEATS = [
    ("강호 제일을 다투던 그날.", "[#d4582f]너는 죽었다.[/]"),
    ("혈마(血魔)의 손에 모든 것이 무너지고", "천하는 핏빛에 잠겼다."),
    ("그런데 눈을 뜨니 다시 열여섯.", "모든 것이 시작되기도 전이다."),
    ("손바닥 위로 본 적 없는 괘가 돈다.", "[#c8a24a]천명반(天命盤)[/]. 죽음마저 되감는 힘이다."),
    ("이번엔 다르다.", "혈마가 강호를 삼키기 전에 [#e8e2d4]끝낸다.[/]"),
]


class ColdOpenScreen(Screen):
    BINDINGS = [("enter", "next"), ("space", "next"), ("s", "skip"), ("escape", "skip")]
    idx: reactive[int] = reactive(0)

    def compose(self):
        with Middle():
            with Center():
                yield Static(id="cold-art")
            with Center():
                yield Static(id="cold-text")
            with Center():
                yield Static(id="cold-foot")

    def on_mount(self):
        self.query_one("#cold-art", Static).update("[#c8a24a]◍[/]")
        self._paint()

    def watch_idx(self):
        try:
            self._paint()
        except Exception:
            pass

    def _paint(self):
        a, b = BEATS[self.idx]
        dots = " ".join("[#c8a24a]●[/]" if i <= self.idx else "[#3a3a42]○[/]" for i in range(len(BEATS)))
        self.query_one("#cold-text", Static).update(f"[#e8e2d4]{a}[/]\n\n{b}")
        self.query_one("#cold-foot", Static).update(f"{dots}\n\n[#9a958a]↵ 계속    ·    S 건너뛰기[/]")

    def action_next(self):
        if self.idx < len(BEATS) - 1:
            self.idx += 1
        else:
            self._go()

    def action_skip(self):
        self._go()

    def _go(self):
        from .buildselect import BuildSelectScreen
        self.app.switch_screen(BuildSelectScreen())
