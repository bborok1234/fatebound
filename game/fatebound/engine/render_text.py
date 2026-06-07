"""이벤트 스트림 → 무협체 전투 로그(02 §전투 로그 · 10 §8 보이스). TUI/CLI 공용.

읽기 우선: 내 공격과 적 공격을 또렷이 구분하고(by_player), 디버그식 화살표 대신
무협 한 줄로. 면 구성·HP 게이지 같은 상시 정보는 상태 패널이 맡으므로 로그는 '사건'만.
"""
from __future__ import annotations
from .events import Event

_STATUS_KO = {"poison": "독", "burn": "화상", "weak": "약화", "vulnerable": "취약", "stun": "기절"}
_TICK_KO = {"poison": "☠ 독", "burn": "🔥 화상"}


def line(e: Event) -> str | None:
    k, d = e.kind, e.data
    if k == "battle_start":
        return f"{d['enemy']}이(가) 앞을 막아선다."
    if k == "round_start":
        return f"[{d['n']}합]"
    if k == "dice":
        return f"  천명괘: {d['face']}" + ("  (다시 굴림)" if d.get("rerolled") else "")
    if k == "m1_line":
        return f"  천명괘 — {d['name']} 강조"
    if k == "m1_fire":
        return None                    # 무공 발동은 구궁 점화·데미지 숫자로(로그 비움)
    if k == "focus":
        return f"    빈 면. 기를 모은다 (응기 {d['count']})"
    if k == "damage":
        crit = " ⚡치명!" if d.get("crit") else ""
        move = (d.get("label") or "").strip()
        amt, hp = d["amount"], d["tgt_hp"]
        if d.get("by_player"):
            return f"    {move or '일격'}, {d['tgt']}에게 {amt} 피해{crit}  (적 HP {hp})"
        opener = "" if move in ("", "평타") else f"의 {move}"
        return f"    {d['src']}{opener}, 나에게 {amt} 피해{crit}  (내 HP {hp})"
    if k == "status":
        s = _STATUS_KO.get(d["status"], d["status"])
        extra = f" {d['stacks']}중첩" if "stacks" in d else ""
        return f"    {d['tgt']}에 {s}{extra}"
    if k == "tick":
        s = _TICK_KO.get(d["status"], d["status"])
        return f"    {s} {d['amount']}  (HP {d['tgt_hp']})"
    if k == "heal":
        if d.get("by_player") is False:                 # 적 자가 회복(흡혈·운기)
            return f"    {d['tgt']}이(가) 기력을 회복한다. +{d['amount']}  (적 HP {d.get('tgt_hp')})"
        return f"    숨을 고른다. 체력 +{d['amount']}"
    if k == "shield":
        if d.get("by_player") is False:                 # 적이 보호막을 두름
            return f"    {d['tgt']}이(가) 호신강을 두른다. 보호막 +{d['amount']}"
        return f"    기를 둘러 막는다. 보호막 +{d['amount']}"
    if k == "counter":
        if d.get("by_player"):
            return f"      되받아친다! {d['amount']} 반격  (적 HP {d['tgt_hp']})"
        return f"      반격에 당한다. {d['amount']} 피해  (내 HP {d['tgt_hp']})"
    if k == "bijang":
        return "  ✦ 비장(秘藏)의 수가 터진다!"
    if k == "summon_attack":
        return f"    {d['name']}이(가) 가세한다. {d['amount']} 피해  (적 HP {d['tgt_hp']})"
    if k == "enemy_action":
        return f"  ! {d['name']}"
    if k == "info":
        return f"    {d['text']}"
    if k == "end":
        r = {"win": "승리", "loss": "패배", "timeout": "무승부"}[d["outcome"]]
        return f"[{r}] {d['rounds']}합 · 남은 체력 {d.get('player_hp')}/{d.get('player_max')}"
    return None


def render(events) -> str:
    return "\n".join(s for s in (line(e) for e in events) if s)
