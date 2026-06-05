"""사건 카드(17 §13.5, events.json) — 서사 + karma 선택지 → 결과. dismiss(True)로 종료."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.containers import Vertical, Center, Middle
from textual.widgets import Static
from textual.reactive import reactive

REQ_KO = {"build:poison": "독 기틀", "build:crit": "치명 기틀",
          "build:guard": "방어 기틀", "build:dice": "주사위 기틀"}


def _req_ko(req: str) -> str:
    if not req:
        return ""
    if req in REQ_KO:
        return f"［{REQ_KO[req]} 필요］"
    if req.startswith("karma>="):
        return f"［명성 {req.split('>=')[1]}+ 필요］"
    return f"［{req} 필요］"


class EventScreen(ModalScreen):
    BINDINGS = [("up", "move(-1)"), ("down", "move(1)"),
                ("1", "pick(0)"), ("2", "pick(1)"), ("3", "pick(2)"), ("4", "pick(3)"),
                ("enter", "confirm"), ("space", "confirm")]
    sel: reactive[int] = reactive(0)

    def __init__(self, session, event):
        super().__init__()
        self.session = session
        self.event = event
        self.choices = event.get("choices", [])
        self.phase = "choose"   # choose → result

    def compose(self):
        with Middle():
            with Center():
                with Vertical(id="event-box"):
                    yield Static(id="ev-title")
                    yield Static(id="ev-text")
                    yield Static(id="ev-choices")
                    yield Static(id="ev-foot")

    def on_mount(self):
        self.query_one("#ev-title", Static).update(f"[#7fa8d4]❖ {self.event.get('title_ko','사건')}[/]")
        self.query_one("#ev-text", Static).update(f"[#e8e2d4]{self.event.get('text_ko','')}[/]")
        self._paint()

    def watch_sel(self):
        try:
            if self.phase == "choose":
                self._paint()
        except Exception:
            pass

    def _avail(self, i):
        return self.session.choice_available(self.choices[i])

    def _paint(self):
        lines = []
        for i, c in enumerate(self.choices):
            ok = self._avail(i)
            req = _req_ko(c.get("require", ""))
            label = c.get("label_ko", "")
            if not ok:
                lines.append(f"[#55504a]   {i+1}. {label} {req}[/]")
            elif i == self.sel:
                lines.append(f"[#1a1a1f on #c8a24a] ▸ {i+1}. {label} [/] [#9a958a]{req}[/]")
            else:
                lines.append(f"[#e8e2d4]   {i+1}. {label}[/] [#9a958a]{req}[/]")
        self.query_one("#ev-choices", Static).update("\n".join(lines))
        self.query_one("#ev-foot", Static).update("[#9a958a]↑↓/숫자 선택 · Enter 결정[/]")

    def action_move(self, d: int):
        if self.phase != "choose":
            return
        n = len(self.choices)
        i = self.sel
        for _ in range(n):
            i = (i + d) % n
            if self._avail(i):
                self.sel = i
                break

    def action_pick(self, i: int):
        if self.phase == "choose" and i < len(self.choices) and self._avail(i):
            self.sel = i

    def action_confirm(self):
        if self.phase == "result":
            self.dismiss(True)
            return
        if not self._avail(self.sel):
            return
        res = self.session.resolve_event_choice(self.event, self.choices[self.sel])
        self.phase = "result"
        eff = res["effects"]
        bits = []
        for k, ko, sign in [("gold", "골드", ""), ("shards", "파편", ""), ("essence", "정수", ""), ("karma", "명성", "")]:
            v = int(eff.get(k, 0))
            if v:
                col = "#5aa67c" if v > 0 else "#d4582f"
                bits.append(f"[{col}]{ko} {'+' if v>0 else ''}{v}[/]")
        if res["granted"]:
            bits.append(f"[#c8a24a]무공 획득: {res['granted']['name_ko']}[/]")
        summary = "   ".join(bits) if bits else "[#9a958a](변화 없음)[/]"
        self.query_one("#ev-text", Static).update(f"[#cfc8b8 italic]{res['result_ko']}[/]\n\n{summary}")
        self.query_one("#ev-choices", Static).update("")
        self.query_one("#ev-foot", Static).update("[#9a958a]계속하려면 [Enter][/]")
