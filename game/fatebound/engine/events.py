"""
전투 이벤트 스트림 — 엔진이 emit하는 구조화 이벤트(형태 독립성의 핵심, 20 §1).

엔진은 전투를 Event 리스트로 산출하고:
  - TUI는 이를 타이밍·애니메이션·juice(hitstop/flash)로 재생(17)
  - 텍스트 렌더러는 같은 스트림을 무협체 로그로 변환(02 §전투 로그)
  - 헤드리스 sim은 outcome만 읽음
숫자/결과는 모두 엔진이 확정(에이전트/렌더러는 변형 금지, 15 계약).
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Event:
    kind: str                      # round_start, dice, trigger, damage, status, tick, heal, shield, counter, bijang, enemy_action, focus, death, end
    data: dict = field(default_factory=dict)

    def __getattr__(self, k):      # ev.amount 처럼 접근
        try:
            return self.data[k]
        except KeyError:
            raise AttributeError(k) from None


def ev(kind: str, **data) -> Event:
    return Event(kind, data)
