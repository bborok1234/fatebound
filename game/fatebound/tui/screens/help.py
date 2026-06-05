"""도움말 오버레이(17 §13.3) — 키맵 + 핵심 개념. 어느 화면에서나 ? 로 호출, Esc/? 로 닫기."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.containers import Center, Middle
from textual.widgets import Static

HELP = """[#c8a24a]━━  도움말 (天命回歸)  ━━[/]

[#e0b341]조작[/]
  [#c8a24a]방향키[/]  구궁 칸 이동
  [#c8a24a]Enter [/]  무공 집기 / 놓기 (두 칸 교환)
  [#c8a24a]Space [/]  강호 지도 · 다음 갈림길 선택
  [#c8a24a]I     [/]  보관함 · 모은 무공을 구궁에 배치
  [#c8a24a]F     [/]  전투 재생 배속 (×1·2·4)
  [#c8a24a]?     [/]  이 도움말
  [#c8a24a]Q     [/]  종료 (진행은 자동 저장됨)

[#e0b341]핵심 개념[/]
  [#7fa8d4]구궁(九宮)[/]   3×3에 무공을 배치한다. 배치가 곧 빌드.
  [#7fa8d4]천명괘[/]      매 합 6면 주사위를 굴려 그 면의 무공이 발동.
  [#5aa67c]상생(相生)[/]   인접한 무공이 서로를 강화(녹색 링크).
  [#e0b341]비장(秘藏)[/]   전투 중 차오르는 필살 한 수. 자동으로 터진다.
  [#e8e2d4]강호 지도[/]   갈림길에서 전투·정예·사건·객잔·기연·보스를 골라 나아간다.
  [#d4582f]회귀(回歸)[/]   죽어도 깨달음을 안고 다시 시작, 더 강하게.

[#9a958a]닫기: Esc · ? · Enter[/]"""


class HelpScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss"), ("question_mark", "dismiss"),
                ("enter", "dismiss"), ("space", "dismiss"), ("q", "dismiss")]

    def compose(self):
        with Middle():
            with Center():
                yield Static(HELP, id="help-box")
