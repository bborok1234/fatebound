"""커맨드 팔레트(Ctrl+P) — 비공간 내비게이션 + 무공 퍼지검색.

행동(강호로·보관함·배속·도움말)과 보유 무공을 한 입력으로 찾아 실행한다.
무공을 고르면 그 칸으로 커서가 점프(배치된 것) 또는 보관함이 열린다(미배치).
"""
from __future__ import annotations
from textual.command import Provider, Hit, DiscoveryHit


class FateboundCommands(Provider):
    def _cmds(self):
        from .screens.game import GameScreen
        scr = self.screen
        if not isinstance(scr, GameScreen) or scr.busy:
            return []
        s = scr.session
        out = [
            ("강호 지도 — 갈림길로 나선다", scr.action_journey, "전투·사건·객잔·보스"),
            ("보관함 — 무공 배치", scr.action_focus_reserve, "미배치 무공을 구궁에"),
            ("배속 전환", scr.action_speed, "전투 속도 ×1/2/4"),
            ("도움말", scr.action_help, "조작 안내"),
        ]
        for i, c in enumerate(s.bag.cells):
            if c:
                r, col = divmod(i, 3)
                out.append((f"무공 · {c['name_ko']}  (구궁 {r+1}행 {col+1}열)",
                            (lambda idx=i: scr.goto_cell(idx)), c.get("gist_ko", "")))
        for it in s.reserve():
            out.append((f"무공 · {it['name_ko']}  (보관함)",
                        (lambda iid=it["item_id"]: scr.select_reserve(iid)), "보관함에서 선택→Enter 배치"))
        return out

    async def search(self, query):
        matcher = self.matcher(query)
        for text, cb, help in self._cmds():
            score = matcher.match(text)
            if score > 0:
                yield Hit(score, matcher.highlight(text), cb, help=help or None)

    async def discover(self):
        for text, cb, help in self._cmds()[:4]:      # 빈 팔레트: 주요 행동
            yield DiscoveryHit(text, cb, help=help or None)
