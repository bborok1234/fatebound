"""회귀(回歸) 전환 화면 — 죽음을 처벌이 아니라 진척으로 연출(17 §4.5, 19 §1 마일스톤)."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.containers import Center, Middle
from textual.widgets import Static

# 회귀 마일스톤 서사(19 §1.2)
MILESTONES = {
    1: "처음 죽고 다시 눈을 떴을 때, 그는 깨달았다 — 천명반은 죽음마저 되감는다. '…한 번 더.'",
    3: "회귀를 거듭하니 기억이 또렷해진다. 혈마는 이 굴레를 안다. 나를, 기다리고 있다.",
    7: "천명반의 균열에서 목소리가 샌다. '몇 번을 돌아와도 끝은 같다.' …정말 그럴까.",
    15: "회귀가 혈마의 봉인을 푼다. 나의 회귀가 적을 키운다 — 굴레는 구원이자 저주.",
    30: "수십 번의 생을 산 자. 이제, 혈마의 목을 보러 간다.",
}


class ReincarnateScreen(ModalScreen):
    BINDINGS = [("enter", "dismiss"), ("space", "dismiss")]

    def __init__(self, session, gain: int, reason: str):
        super().__init__()
        self.session = session
        self.gain = gain
        self.reason = reason

    def compose(self):
        s = self.session
        n = s.reincarnations
        lines = [
            "[#d4582f bold]━━━  회 귀 (回 歸)  ━━━[/]", "",
            f"제 {n}생, {self.reason}하여 스러지다.",
            "[#9a958a]천명반이 천천히 되감긴다…[/]", "",
            f"[#c8a24a]깨달음(悟)  +{self.gain}  →  누적 {s.insight}[/]",
        ]
        if n in MILESTONES:
            lines += ["", f"[#e8e2d4]〔천명〕 {MILESTONES[n]}[/]"]
        lines += ["", f"[#5aa67c]제 {n+1}생 · 시작 경지 Lv{s.level}[/]",
                  "", "[#9a958a]계속하려면 [Enter][/]"]
        with Middle():
            with Center():
                yield Static("\n".join(lines), id="reincarnate-box")
