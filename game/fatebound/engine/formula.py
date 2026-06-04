"""
수식 평가 — value 문자열("0.6 * atk", "1.0 * atk + 5", "12")을 컨텍스트(스탯)로 안전 평가.

설계 결정: 정규식+eval(프로토타입)이 아니라 **AST 화이트리스트** 방식.
허용 노드만 평가하므로 임의 코드 실행 불가(보안) + 'atk*0.6 피해' 같이 뒤에 설명이 붙은
지저분한 문자열도 앞쪽 수식만 안전하게 파싱(콘텐츠가 AI 생성이라 견고성 필요).
"""
from __future__ import annotations
import ast
import re
import operator

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

# 허용 변수(스탯 컨텍스트 키). 'def'는 파이썬 키워드라 식에서 'defense'로도 받게 별칭 둠.
ALLOWED_NAMES = {"atk", "hp", "max_hp", "def", "defense", "spd", "crit", "crit_dmg", "luk", "stacks"}
# value 문자열 앞쪽의 수식 토큰만 추출(한글 설명·단위 등 뒤꼬리 제거)
_EXPR_HEAD = re.compile(r"^[\s0-9.+\-*/%()a-z_]+")


def _eval_node(node: ast.AST, ctx: dict) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ctx)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"비허용 상수: {node.value!r}")
    if isinstance(node, ast.Name):
        key = "defense" if node.id == "def" else node.id
        if node.id not in ALLOWED_NAMES:
            raise ValueError(f"비허용 변수: {node.id}")
        return float(ctx.get(node.id, ctx.get(key, 0.0)))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval_node(node.left, ctx), _eval_node(node.right, ctx))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval_node(node.operand, ctx))
    raise ValueError(f"비허용 노드: {ast.dump(node)}")


def evaluate(value, ctx: dict | None = None) -> float:
    """value(숫자 또는 수식 문자열)를 ctx로 평가. 실패 시 앞쪽 숫자/수식만, 그것도 실패면 0.0."""
    ctx = ctx or {}
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return 0.0
    s = str(value).strip()
    m = _EXPR_HEAD.match(s)
    expr = (m.group(0) if m else s).strip().rstrip("+-*/%(")
    if not expr:
        nums = re.findall(r"-?\d+\.?\d*", s)
        return float(nums[0]) if nums else 0.0
    try:
        return _eval_node(ast.parse(expr, mode="eval"), ctx)
    except Exception:
        nums = re.findall(r"-?\d+\.?\d*", s)
        return float(nums[0]) if nums else 0.0
