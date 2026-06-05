"""천명괘(天命卦) 위젯 — 게임의 핵심·랜덤성의 축(D1). 전투 상단 전폭 룰렛.

매 합 6면 중 하나가 굴려 나온다. 굴림은 화면 위쪽 가로 띠에서 슬롯머신처럼 면을
훑다가(roll_frame) 결과 면에 철컥 멈추고(land) flash. 배치 화면에선 현재 6면을 보여준다.
실제 굴림 애니메이션은 게임 화면의 async 재생 루프가 구동한다(17 §6).
"""
from __future__ import annotations
from textual.widget import Widget
from rich.text import Text
from rich.console import Group


def _short(f: str) -> str:
    return f if len(f) <= 4 else f[:3] + "…"


class DiceWidget(Widget):
    def __init__(self, faces=None, **kw):
        super().__init__(**kw)
        self.faces = list(faces or [])
        self.hi = -1          # 현재 하이라이트 면 index (굴리는 중/결과)
        self.result = ""      # 멈춘 결과 면 (없으면 굴리는 중/대기)
        self.flash = False    # 착지 순간 반전 강조
        self.border_title = "天命卦 · 천명괘"

    # ── 게임 화면이 호출 ──
    def set_faces(self, faces):
        self.faces = list(faces)
        self.hi = -1
        self.result = ""
        self.flash = False
        self.refresh()

    def roll_frame(self, idx: int):
        if self.faces:
            self.hi = idx % len(self.faces)
        self.result = ""
        self.flash = False
        self.refresh()

    def land(self, face: str, flash: bool = True):
        self.result = face
        self.flash = flash
        try:
            self.hi = self.faces.index(face)
        except ValueError:
            self.hi = -1
        self.refresh()

    def unflash(self):
        self.flash = False
        self.refresh()

    def clear_roll(self):
        self.hi = -1
        self.result = ""
        self.flash = False
        self.refresh()

    # ── 렌더 ──
    def render(self):
        faces = self.faces or ["·"] * 6
        row = Text(justify="center")
        for i, f in enumerate(faces):
            disp = _short(f)
            if self.result and i == self.hi:
                row.append(f" {disp} ", style="#1a1a1f on #e0b341 bold")   # 결과 면
            elif i == self.hi:
                row.append(f" {disp} ", style="#c8a24a bold")              # 굴리는 중
            else:
                row.append(f" {disp} ", style="#6b665c")
            if i < len(faces) - 1:
                row.append("·", style="#3a3a42")
        if self.result:
            style = "#1a1a1f on #e0b341 bold" if self.flash else "#e0b341 bold"
            line2 = Text(f"▶  {self.result}  ◀", style=style, justify="center")
        elif self.hi >= 0:
            line2 = Text("천명을 읽는다…", style="#9a958a", justify="center")
        else:
            line2 = Text("매 합 한 면이 굴려 나와 그 무공이 펼쳐진다", style="#55504a", justify="center")
        return Group(row, line2)
